# Playwright की ऑफिशियल इमेज जिसमें ब्राउज़र और Python पहले से हैं
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

# काम करने की जगह (Folder)
WORKDIR /app

# सारी फाइलें कॉपी करें
COPY . /app

# लाइब्रेरी इंस्टॉल करें
RUN pip install --no-cache-dir -r requirements.txt

# रेंडर के लिए पोर्ट सेट करें
ENV PORT=8080
EXPOSE 8080

# बोट चलाने की कमांड
CMD ["python", "main.py"]
