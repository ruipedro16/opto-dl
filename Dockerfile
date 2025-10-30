FROM python:3.13-slim-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ffmpeg \
        ca-certificates \
        wget \
        unzip \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install -U "yt-dlp[default]" requests

RUN wget https://www.bok.net/Bento4/binaries/Bento4-SDK-1-6-0-641.x86_64-unknown-linux.zip \
    && unzip Bento4-SDK-1-6-0-641.x86_64-unknown-linux.zip \
    && cp Bento4-SDK-1-6-0-641.x86_64-unknown-linux/bin/mp4decrypt /usr/local/bin/mp4decrypt \
    && rm -rf Bento4-SDK-1-6-0-641.x86_64-unknown-linux.zip Bento4-SDK-1-6-0-641.x86_64-unknown-linux/

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