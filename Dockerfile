FROM python:3.12-slim
WORKDIR /app
COPY server/ ./server/
WORKDIR /app/server
EXPOSE 8080
CMD ["python", "main.py"]
