# opto-dl

A command-line tool for downloading DRM-protected video content from [opto.sic.pt](https://opto.sic.pt).

## Features

- Download videos from opto.sic.pt URLs
- Automatic extraction of manifest and license URLs
- Stream selection (choose specific video/audio quality)
- Subtitle download support
- Batch downloads from a file containing multiple URLs
- List available streams before downloading

## Dependencies

Install Python dependencies using:

```bash
pip install -r requirements.txt
```

The following tools must also be installed and available in your PATH:

1. **Chrome/Chromium Browser**
2. **yt-dlp**
3. **mp4decrypt**
4. **ffmpeg**

## Installation

### Option 1: Local Installation

```bash
git clone <repository-url>
cd opto-dl
pip install -r requirements.txt
```

Ensure all external tools (Chrome, yt-dlp, mp4decrypt, ffmpeg) are installed.

### Option 2: Docker (Recommended)

Using Docker eliminates the need to install dependencies manually. All required tools (Chrome, yt-dlp, mp4decrypt, ffmpeg) are included in the container.

**Build the Docker image:**

```bash
docker build -t opto-dl .
```

**Run with Docker:**

```bash
# Download to current directory
docker run --rm -v "$(pwd):/output" opto-dl --url "https://opto.sic.pt/video/..." -o /output/video.mp4

# List streams
docker run --rm opto-dl --url "https://opto.sic.pt/video/..." --list-streams

# With verbose output
docker run --rm -v "$(pwd):/output" opto-dl --url "https://opto.sic.pt/video/..." -o /output/video.mp4 -v

# Batch download from file
docker run --rm -v "$(pwd):/output" -v "$(pwd)/urls.txt:/app/urls.txt" opto-dl -f /app/urls.txt
```

**Docker Notes:**

- Use `-v "$(pwd):/output"` to mount the current directory for saving downloaded files
- Output files must be written to `/output/` inside the container to persist on the host
- The container runs as a non-root user (appuser) for security
- All dependencies (Chrome, ChromeDriver, ffmpeg, mp4decrypt, yt-dlp) are pre-installed

## Usage

### Basic Usage

Download a video by URL:

```bash
python opto-dl.py --url "https://opto.sic.pt/video/..."
```

### Advanced Options

**List available streams:**

```bash
python opto-dl.py --url "https://opto.sic.pt/video/..." --list-streams
```

**Select specific streams:**

```bash
python opto-dl.py --url "https://opto.sic.pt/video/..." \
  --video-stream "video-stream-id" \
  --audio-stream "audio-stream-id" \
  -o output.mp4
```

**Download with subtitles:**

```bash
python opto-dl.py --url "https://opto.sic.pt/video/..." \
  --download-subtitles \
  -o output.mp4
```

**Download using manifest and license URLs directly:**

> Note: Using `--manifest` and `--license-url` is more stable and faster than using `--url`

```bash
python opto-dl.py \
  --manifest "https://...manifest.mpd" \
  --license-url "https://...license?..." \
  -o output.mp4
```

**Batch download from file:**

Create a text file with URLs (one per line or space-separated):

```bash
python opto-dl.py -f urls.txt
```

### Command-Line Options

```
-f, --file FILE              File containing multiple URLs to download
--url URL                    URL of the video from opto.sic.pt
--manifest URL               Direct URL to the MPD manifest
--license-url URL            License URL for DRM decryption
--timeout SECONDS            Timeout for page loading (default: 15)
--download-subtitles         Download available subtitles
--store-manifest             Save the manifest file locally
--list-streams               List available streams without downloading
--audio-stream ID            Select specific audio stream by ID
--video-stream ID            Select specific video stream by ID
-o, --output FILE            Output filename (must have .mp4 or .mkv extension)
-v, --verbose                Enable verbose logging
```

## How It Works

1. **Extract URLs**: Uses Selenium with Chrome to visit the video page and capture network requests containing the manifest (.mpd) and license URLs
2. **Parse Manifest**: Parses the DASH MPD manifest to identify available video/audio/subtitle streams
3. **Download Streams**: Downloads encrypted video and audio streams using yt-dlp
4. **Get Decryption Keys**: Obtains decryption keys from cdrm-project.com API using the PSSH from the manifest
5. **Decrypt**: Decrypts video and audio streams using mp4decrypt
6. **Merge**: Merges decrypted streams into a single file using ffmpeg

## Notes

- Using `--url` is less stable and slower than using `--manifest` and `--license-url` directly
- The tool uses a temporary directory for intermediate files, which is automatically cleaned up
- By default, the tool selects the highest quality video stream and the highest bandwidth audio stream
- Chrome must be installed and accessible for the URL extraction feature to work
