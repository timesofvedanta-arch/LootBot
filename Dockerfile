# Python का बेस इमेज
FROM mcr.microsoft.com/playwright:v1.40.0-jammy

# काम करने की जगह (Working Directory)
WORKDIR /app

# फाइलें कॉपी करें
COPY . /app

# लाइब्रेरी इंस्टॉल करें
RUN pip install --no-cache-dir -r requirements.txt

# Playwright के लिए जरूरी ब्राउज़र बाइनरी इंस्टॉल करें
RUN playwright install chromium

# बोट चलाने की कमांड
CMD ["python", "main.py"]
