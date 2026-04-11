FROM python:3.10-slim

# ज़रूरी सिस्टम टूल्स इंस्टॉल करें
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

# लाइब्रेरी इंस्टॉल करें
RUN pip install --no-cache-dir -r requirements.txt

# सिर्फ Chromium ब्राउज़र इंस्टॉल करें (हल्का रखने के लिए)
RUN playwright install --with-deps chromium

ENV PORT=8080
EXPOSE 8080

CMD ["python", "main.py"]
