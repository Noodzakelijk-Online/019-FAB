FROM python:3.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libgl1 \
        poppler-utils \
        tesseract-ocr \
        tesseract-ocr-eng \
        tesseract-ocr-nld \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./requirements.txt
RUN python -m pip install --no-cache-dir --disable-pip-version-check -r requirements.txt \
    && rm -rf /var/lib/apt/lists/* /root/.cache/pip

COPY src ./src
COPY config/config_template.ini ./config/config_template.ini

RUN groupadd --system --gid 10001 fab \
    && useradd --system --uid 10001 --gid fab --home-dir /app fab \
    && mkdir -p data downloads/sort-out logs output/support \
    && chown -R fab:fab /app

USER fab

EXPOSE 5001

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import os,urllib.request; t=os.environ.get('FAB_LOCAL_API_TOKEN',''); r=urllib.request.Request('http://127.0.0.1:5001/api/live',headers={'Authorization':'Bearer '+t} if t else {}); urllib.request.urlopen(r,timeout=3).read()"

CMD ["python", "-m", "src.operations.local_api"]
