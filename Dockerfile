# Use Microsoft Playwright Python image
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

LABEL maintainer="Mangal Kiran"

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
 && playwright install chromium

# Copy main code
COPY main.py .

# Environment variables (पूरी तरह आपकी जानकारी के अनुसार)
ENV PORT=10000
ENV BOT_TOKEN=8797754610:AAHM-KFFsdNoBJa2VIfrew5uFvgwGvyL-uI
ENV MONGO_URI=mongodb+srv://timesofvedanta:Mk626425@lootbot.ypsol8i.mongodb.net/?appName=Lootbot
ENV WEBAPP_URL=https://lootbot-1.onrender.com
ENV ADMIN_ID=1216607288

# Expose port
EXPOSE $PORT

# Run the bot
CMD ["python", "main.py"]
