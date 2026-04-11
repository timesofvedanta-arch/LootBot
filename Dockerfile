FROM mcr.microsoft.com/playwright:v1.40.0-jammy
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chromium
# रेंडर के लिए पोर्ट सेट करना
ENV PORT=8080
EXPOSE 8080
CMD ["python", "main.py"]
