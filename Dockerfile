# Python इमेज जिसमें Playwright सपोर्ट है
FROM mcr.microsoft.com/playwright:v1.40.0-focal

# Python और Pip को सेट करना
RUN apt-get update && apt-get install -y python3 python3-pip

# काम करने की जगह
WORKDIR /app

# फाइलें कॉपी करें
COPY . /app

# लाइब्रेरी इंस्टॉल करें
RUN pip3 install --no-cache-dir -r requirements.txt

# जरूरी ब्राउज़र इंस्टॉल करें
RUN playwright install chromium

# रेंडर के लिए पोर्ट
ENV PORT=8080
EXPOSE 8080

# बोट चलाने की कमांड (python3 का उपयोग करें)
CMD ["python3", "main.py"]
