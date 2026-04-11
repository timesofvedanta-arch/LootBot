FROM mcr.microsoft.com/playwright:v1.40.0-focal

# Python इंस्टॉल करें
RUN apt-get update && apt-get install -y python3 python3-pip

WORKDIR /app
COPY . /app

# Pip को अपडेट करें और लाइब्रेरी डालें
RUN python3 -m pip install --upgrade pip
RUN pip3 install --no-cache-dir -r requirements.txt
RUN playwright install chromium

ENV PORT=8080
EXPOSE 8080

CMD ["python3", "main.py"]
