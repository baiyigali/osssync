import os
import time
import hashlib
import oss2

class OSSSync:
    def __init__(self, access_key_id, access_key_secret, endpoint, bucket_name, ignore=[]):
        auth = oss2.Auth(access_key_id, access_key_secret)
        self.bucket = oss2.Bucket(auth, endpoint, bucket_name)
        self.ignore = ignore
    
    def download_dir(self, src_dir, dst_dir):
        it = oss2.ObjectIterator(self.bucket, prefix=src_dir, max_keys=1000)
        for obj in it:
            key = obj.key
            basename = os.path.basename(key)
            if len(basename) <= 0 or basename in self.ignore:
                continue
            os.makedirs(dst_dir, exist_ok=True)
            if not os.path.exists(os.path.join(str(dst_dir), basename)):
                self.bucket.get_object_to_file(
                    key, os.path.join(str(dst_dir), basename)
                )            
                print(f"Downloaded {key} to {dst_dir}")

    def upload_file(self, local_path, oss_path):
        with open(local_path, 'rb') as f:
            self.bucket.put_object(oss_path, f)
        print(f"Uploaded {local_path} to {oss_path}")
    
    def delete_file(self, oss_path):
        self.bucket.delete_object(oss_path)
        print(f"Deleted {oss_path}")

class DirWatcher:
    def __init__(self, path, oss_sync, interval=1):
        self.path = path
        self.oss_sync = oss_sync
        self.interval = interval
        self.file_hashes = {}
    
    def watch(self):
        print(f"Watching directory {self.path}...")
        while True:
            time.sleep(self.interval)
            self.check_changes()
    
    def check_changes(self):
        new_hashes = {}
        for root, dirs, files in os.walk(self.path):
            for filename in files:
                filepath = os.path.join(root, filename)
                hash_value = self.hash_file(filepath)
                if hash_value != self.file_hashes.get(filepath):
                    self.sync_file(filepath)
                new_hashes[filepath] = hash_value
        self.file_hashes = new_hashes
    
    def hash_file(self, filepath):
        hash_md5 = hashlib.md5()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def sync_file(self, filepath):
        oss_path = os.path.relpath(filepath, self.path).replace('\\', '/')
        if os.path.exists(filepath):
            self.oss_sync.upload_file(filepath, oss_path)
            print(f"Uploaded {filepath} to OSS path {oss_path}")
        else:
            self.oss_sync.delete_file(oss_path)
            print(f"Deleted OSS path {oss_path}")

if __name__ == '__main__':

    endpoint = os.environ["OSS_ENDPOINT"]
    access_key_id = os.environ["OSS_ACCESS_KEY_ID"]
    access_key_secret = os.environ["OSS_ACCESS_KEY_SECRET"]
    bucket_name = os.environ["OSS_BUCKET_NAME"]
    local_dir = os.environ["LOCAL_DIR"]
    oss_dir = os.environ["OSS_DIR"]
    
    ignore = ['.DS_Store']
    oss_sync = OSSSync(access_key_id, access_key_secret, endpoint, bucket_name, ignore)
    oss_sync.download_dir(oss_dir, local_dir)

    dir_watcher = DirWatcher(local_dir, oss_sync)
    dir_watcher.watch()
