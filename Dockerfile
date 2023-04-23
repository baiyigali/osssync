FROM python:3.9-alpine

WORKDIR /app

RUN pip install watchdog
RUN pip install oss2

COPY service.py .

CMD ["python", "service.py"]
