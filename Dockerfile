FROM python:3.9-slim-buster

WORKDIR /app

# Install Tesseract OCR and its language data
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-nld \
    tesseract-ocr-eng \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# Install Playwright browsers
RUN pip install playwright && playwright install --with-deps chromium

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Set environment variables for Tesseract data path if needed
ENV TESSDATA_PREFIX /usr/share/tesseract-ocr/4.00/tessdata

CMD ["python", "src/main.py"]


