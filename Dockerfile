FROM python:3.9-slim
RUN apt-get update && apt-get install -y ffmpeg
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p downloads
EXPOSE 10000
CMD ["gunicorn", "--bind", "0.0.0.0:10000", "app:app"]
