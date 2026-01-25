# Modal WhisperX HTTP API Guide

This guide covers how to use the Modal WhisperX transcription services via HTTP.

## Deployment Options

There are **two ways** to access the API:

| Option | URL | Authentication | Use Case |
|--------|-----|----------------|----------|
| **Modal Direct** | `https://<your-workspace>--modal-whisper-transcribe-web-endpoint.modal.run` | Bearer token required | Production, direct cloud access |
| **Local Proxy** | `http://localhost:8000` | None | Development, testing |

---

## Option 1: Modal Direct HTTP Endpoints (Recommended for Production)

### Setup

1. **Create an AUTH_TOKEN secret in Modal**:
   ```bash
   modal secret create AUTH_TOKEN AUTH_TOKEN=your-secret-token-here
   ```

2. **Deploy the services**:
   ```bash
   modal deploy modal_whisper_transcribe.py
   modal deploy modal_youtube_transcribe.py
   ```

3. **Get your endpoint URLs** from the Modal dashboard or deployment output.

### Authentication

All endpoints (except `/health`) require Bearer token authentication:

```
Authorization: Bearer your-secret-token-here
```

---

## Audio Transcription API

### Endpoint

```
POST /v1/audio/transcriptions
```

### Headers

| Header | Value | Required |
|--------|-------|----------|
| `Authorization` | `Bearer <AUTH_TOKEN>` | Yes (Modal Direct) |
| `Content-Type` | `multipart/form-data` | Yes |

### Form Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file` | file | Yes | Audio file (wav, mp3, m4a, etc.) |
| `model` | string | Yes | Must be `whisper-1` |
| `response_format` | string | No | `json` (default) or `verbose_json` |
| `language` | string | No | ISO-639-1 code (e.g., `en`, `de`). Auto-detected if omitted |

### Examples

#### cURL - Simple Transcription (Modal Direct)

```bash
curl -X POST "https://YOUR-WORKSPACE--modal-whisper-transcribe-web-endpoint.modal.run/v1/audio/transcriptions" \
  -H "Authorization: Bearer your-secret-token" \
  -F "file=@audio.mp3" \
  -F "model=whisper-1"
```

#### cURL - With Language & Verbose Output

```bash
curl -X POST "https://YOUR-WORKSPACE--modal-whisper-transcribe-web-endpoint.modal.run/v1/audio/transcriptions" \
  -H "Authorization: Bearer your-secret-token" \
  -F "file=@audio.mp3" \
  -F "model=whisper-1" \
  -F "language=en" \
  -F "response_format=verbose_json"
```

#### Python - Using requests

```python
import requests

url = "https://YOUR-WORKSPACE--modal-whisper-transcribe-web-endpoint.modal.run/v1/audio/transcriptions"
headers = {"Authorization": "Bearer your-secret-token"}

with open("audio.mp3", "rb") as f:
    response = requests.post(
        url,
        headers=headers,
        files={"file": f},
        data={"model": "whisper-1", "response_format": "verbose_json"}
    )

print(response.json())
```

#### Python - OpenAI SDK Compatible

```python
from openai import OpenAI

# Point to your Modal endpoint
client = OpenAI(
    api_key="your-secret-token",
    base_url="https://YOUR-WORKSPACE--modal-whisper-transcribe-web-endpoint.modal.run/v1"
)

with open("audio.mp3", "rb") as f:
    transcript = client.audio.transcriptions.create(
        model="whisper-1",
        file=f,
        response_format="verbose_json"
    )

print(transcript.text)
```

### Response Formats

#### JSON Format (default)

```json
{
  "text": "This is the transcribed text from the audio."
}
```

#### Verbose JSON Format

```json
{
  "task": "transcribe",
  "language": "en",
  "duration": 12.34,
  "segments": [
    {
      "id": 0,
      "seek": 0,
      "start": 0.0,
      "end": 5.0,
      "text": "This is the first segment.",
      "tokens": [],
      "temperature": 0.0,
      "avg_logprob": -0.1,
      "compression_ratio": 1.0,
      "no_speech_prob": 0.0
    }
  ],
  "text": "This is the transcribed text from the audio."
}
```

---

## YouTube Transcription API

### Endpoint

```
POST /v1/youtube/transcribe
GET  /v1/youtube/transcribe?url=<youtube-url>
```

### Headers

| Header | Value | Required |
|--------|-------|----------|
| `Authorization` | `Bearer <AUTH_TOKEN>` | Yes (Modal Direct) |
| `Content-Type` | `application/json` | Yes (POST only) |

### Request Body (POST)

```json
{
  "url": "https://www.youtube.com/watch?v=VIDEO_ID",
  "force_whisper": false
}
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `url` | string | Yes | YouTube URL, short URL, or video ID |
| `force_whisper` | boolean | No | Skip YouTube captions, always use WhisperX (default: `false`) |

### Transcription Strategy

1. **First**: Tries to fetch official YouTube transcript (fast, no download)
2. **Fallback**: If no transcript available, downloads audio and transcribes with WhisperX

Use `force_whisper: true` to always use WhisperX for higher quality transcription.

### Examples

#### cURL - POST Request (Modal Direct)

```bash
curl -X POST "https://YOUR-WORKSPACE--modal-youtube-transcribe-web-endpoint.modal.run/v1/youtube/transcribe" \
  -H "Authorization: Bearer your-secret-token" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}'
```

#### cURL - GET Request

```bash
curl "https://YOUR-WORKSPACE--modal-youtube-transcribe-web-endpoint.modal.run/v1/youtube/transcribe?url=dQw4w9WgXcQ" \
  -H "Authorization: Bearer your-secret-token"
```

#### cURL - Force WhisperX Transcription

```bash
curl -X POST "https://YOUR-WORKSPACE--modal-youtube-transcribe-web-endpoint.modal.run/v1/youtube/transcribe" \
  -H "Authorization: Bearer your-secret-token" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://youtu.be/dQw4w9WgXcQ", "force_whisper": true}'
```

#### Python

```python
import requests

url = "https://YOUR-WORKSPACE--modal-youtube-transcribe-web-endpoint.modal.run/v1/youtube/transcribe"
headers = {
    "Authorization": "Bearer your-secret-token",
    "Content-Type": "application/json"
}
data = {
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "force_whisper": False
}

response = requests.post(url, headers=headers, json=data)
print(response.json())
```

### Response Format

#### YouTube Official Transcript

```json
{
  "success": true,
  "video_id": "dQw4w9WgXcQ",
  "source": "youtube_official",
  "language": "en",
  "is_auto_generated": false,
  "text": "We're no strangers to love You know the rules and so do I...",
  "segments": [
    {
      "text": "We're no strangers to love",
      "start": 0.0,
      "duration": 3.5
    }
  ],
  "available_languages": [
    {
      "language": "English",
      "language_code": "en",
      "is_generated": false,
      "is_translatable": true
    }
  ]
}
```

#### WhisperX Transcription (fallback or forced)

```json
{
  "success": true,
  "video_id": "dQw4w9WgXcQ",
  "source": "whisperx",
  "title": "Rick Astley - Never Gonna Give You Up",
  "duration": 212,
  "language": "en",
  "text": "We're no strangers to love You know the rules and so do I...",
  "segments": [
    {
      "start": 0.0,
      "end": 3.5,
      "text": "We're no strangers to love"
    }
  ]
}
```

---

## Health Check

### Endpoint

```
GET /health
```

No authentication required.

### Example

```bash
# Modal Direct
curl "https://YOUR-WORKSPACE--modal-whisper-transcribe-web-endpoint.modal.run/health"

# Local
curl "http://localhost:8000/health"
```

### Response

```json
{
  "status": "healthy",
  "service": "modal-whisperx"
}
```

---

## Option 2: Local Proxy Server

For development and testing, run the local FastAPI server that proxies to Modal.

### Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Start server
uvicorn app:app --host 0.0.0.0 --port 8000
```

### Usage

Same endpoints as above, but:
- URL: `http://localhost:8000`
- No authentication required

```bash
# Audio transcription
curl -X POST "http://localhost:8000/v1/audio/transcriptions" \
  -F "file=@audio.mp3" \
  -F "model=whisper-1"

# YouTube transcription
curl -X POST "http://localhost:8000/v1/youtube/transcribe" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=VIDEO_ID"}'

# Health check
curl "http://localhost:8000/health"
```

---

## Error Responses

### 400 Bad Request

```json
{
  "detail": "Only 'whisper-1' model is supported"
}
```

### 401 Unauthorized

```json
{
  "detail": "Invalid authentication token"
}
```

### 500 Internal Server Error

```json
{
  "detail": "Transcription failed: <error message>"
}
```

### 503 Service Unavailable

```json
{
  "detail": "Modal service not available. Please ensure Modal app is deployed and accessible."
}
```

---

## Supported URL Formats (YouTube)

The YouTube API accepts various URL formats:

| Format | Example |
|--------|---------|
| Standard | `https://www.youtube.com/watch?v=dQw4w9WgXcQ` |
| Short | `https://youtu.be/dQw4w9WgXcQ` |
| Embed | `https://www.youtube.com/embed/dQw4w9WgXcQ` |
| Shorts | `https://youtube.com/shorts/VIDEO_ID` |
| Video ID only | `dQw4w9WgXcQ` |

---

## Rate Limits & Timeouts

| Service | Timeout | Concurrent Requests |
|---------|---------|---------------------|
| Audio Transcription | 30 minutes | 100 |
| YouTube Transcription | 15 minutes | 100 |

---

## Quick Reference

### Modal Direct Endpoints

```
Base URL: https://YOUR-WORKSPACE--modal-whisper-transcribe-web-endpoint.modal.run

POST /v1/audio/transcriptions    # Audio transcription (requires auth)
GET  /health                     # Health check (no auth)
```

```
Base URL: https://YOUR-WORKSPACE--modal-youtube-transcribe-web-endpoint.modal.run

POST /v1/youtube/transcribe      # YouTube transcription (requires auth)
GET  /v1/youtube/transcribe      # YouTube transcription (requires auth)
GET  /health                     # Health check (no auth)
```

### Local Proxy Endpoints

```
Base URL: http://localhost:8000

POST /v1/audio/transcriptions    # Audio transcription
POST /v1/youtube/transcribe      # YouTube transcription
GET  /health                     # Health check
GET  /                           # Service info
```
