FROM python:3.13-slim-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        ffmpeg \
        ca-certificates \
        wget \
        unzip \
        jq \
        libglib2.0-0 \
        libnss3 \
        libgdk-pixbuf2.0-0 \
        libgtk-3-0 \
        libx11-6 \
        libx11-xcb1 \
        libxcb1 \
        libxcomposite1 \
        libxcursor1 \
        libxdamage1 \
        libxext6 \
        libxfixes3 \
        libxi6 \
        libxrandr2 \
        libxrender1 \
        libxss1 \
        libxtst6 \
        libatk1.0-0 \
        libatk-bridge2.0-0 \
        libcups2 \
        libdbus-1-3 \
        libatspi2.0-0 \
        libdrm2 \
        libgbm1 \
        libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Install Google Chrome and ChromeDriver
RUN JSON_DATA=$(wget -q -O - "https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json") \
    && CHROME_URL=$(echo "${JSON_DATA}" | jq -r '.channels.Stable.downloads.chrome[] | select(.platform=="linux64") | .url') \
    && CHROMEDRIVER_URL=$(echo "${JSON_DATA}" | jq -r '.channels.Stable.downloads.chromedriver[] | select(.platform=="linux64") | .url') \
    && wget -q "${CHROME_URL}" -O chrome-linux64.zip \
    && wget -q "${CHROMEDRIVER_URL}" -O chromedriver-linux64.zip \
    && unzip chrome-linux64.zip \
    && unzip chromedriver-linux64.zip \
    && mv chrome-linux64 /opt/chrome \
    && mv chromedriver-linux64/chromedriver /usr/local/bin/chromedriver \
    && rm chrome-linux64.zip chromedriver-linux64.zip

RUN wget https://www.bok.net/Bento4/binaries/Bento4-SDK-1-6-0-641.x86_64-unknown-linux.zip \
    && unzip Bento4-SDK-1-6-0-641.x86_64-unknown-linux.zip \
    && cp Bento4-SDK-1-6-0-641.x86_64-unknown-linux/bin/mp4decrypt /usr/local/bin/mp4decrypt \
    && rm -rf Bento4-SDK-1-6-0-641.x86_64-unknown-linux.zip Bento4-SDK-1-6-0-641.x86_64-unknown-linux/

RUN python3 -m pip install -U "yt-dlp[default]" requests

RUN wget -q -O /usr/local/bin/yt-dlp-rtp-support https://cld.pt/dl/download/518a5134-5c40-4c40-aed7-08d3beb8b2d1/yt-dlp-rtp-support_linux \
    && chmod +x /usr/local/bin/yt-dlp-rtp-support

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x opto-dl.py

RUN useradd -m -u 1000 appuser \
    && chown -R appuser:appuser /app

USER appuser

ENTRYPOINT ["./opto-dl.py"]
CMD ["--help"]