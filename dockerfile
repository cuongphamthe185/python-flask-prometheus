FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt /app/
COPY metric_total_sftpgo.py /app/
RUN pip install --no-cache-dir -r requirements.txt
EXPOSE 8195

CMD ["python", "-u", "metric_total_sftpgo.py"]