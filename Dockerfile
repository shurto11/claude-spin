FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y gcc python3-dev && rm -rf /var/lib/apt/lists/*
RUN pip install RPLCD smbus2 lgpio

COPY servo.py .

CMD ["python", "servo.py"]
