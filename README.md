# Modal WhisperX API

A FastAPI webserver that provides OpenAI Whisper API compatibility using Modal and WhisperX for high-quality audio transcription with word-level timestamps. Now includes YouTube video transcription and metadata extraction capabilities.

## Features

- **OpenAI Whisper API Compatible**: Drop-in replacement for OpenAI's transcription API
- **WhisperX Integration**: Uses WhisperX via Modal for accurate word-level timestamps
- **YouTube Transcription**: Extract metadata, transcripts, and optionally download YouTube videos
- **Multiple Response Formats**: Supports both `json` and `verbose_json` formats
- **Concurrent Processing**: Handles multiple transcription requests simultaneously
- **Docker Support**: Easy deployment with Docker and Docker Compose
- **Health Monitoring**: Built-in health check endpoints
- **Low Resource YouTube Processing**: Optimized for quick metadata and transcript extraction

## Quick Start

### Prerequisites Setup

**🚨 CRITICAL**: You MUST complete the Modal setup before the API will work!

1. **Modal Setup** (Required - API will fail without this):
   ```bash
   # Install Modal CLI
   pip install modal
   
   # Authenticate with Modal
   modal token new
   
   # Deploy WhisperX service - THIS IS REQUIRED!
   modal deploy modal_whisper_transcribe.py
   
   # Deploy YouTube transcription service - REQUIRED for YouTube features!
   modal deploy modal_youtube_transcribe.py
   
   # Verify deployment succeeded
   modal app list
   ```
   ✅ You should see both `modal-whisper-transcribe` and `modal-youtube-transcribe` listed as deployed apps.

2. **Environment Variables** (Optional if using `modal token new`):
   ```bash
   # Set Modal API token (if not using modal token new)
   export MODAL_TOKEN_ID="your-token-id"
   export MODAL_TOKEN_SECRET="your-token-secret"
   ```

### Using Docker Compose (Recommended)

1. Clone the repository and navigate to the project directory
2. Build and start the service:
   ```bash
   docker-compose up --build
   ```
3. The API will be available at `http://localhost:8000`

### Manual Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Start the server:
   ```bash
   uvicorn app:app --host 0.0.0.0 --port 8000
   ```

## API Usage

### Audio Transcription Endpoint

**POST** `/v1/audio/transcriptions`

#### Required Parameters
- `file`: Audio file (multipart/form-data, max 25MB)
- `model`: Must be `whisper-1`

#### Optional Parameters
- `prompt`: Text prompt to guide transcription
- `response_format`: `json` (default) or `verbose_json`
- `temperature`: Sampling temperature (default: 0.0)
- `language`: ISO-639-1 language code (auto-detected if not provided)

#### Example Usage

```bash
# Simple transcription
curl -X POST "http://localhost:8000/v1/audio/transcriptions" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@audio.mp3" \
  -F "model=whisper-1"

# Verbose output with timestamps
curl -X POST "http://localhost:8000/v1/audio/transcriptions" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@audio.mp3" \
  -F "model=whisper-1" \
  -F "response_format=verbose_json"
```

#### Response Formats

**JSON Format** (`response_format=json`):
```json
{
  "text": "This is the transcribed text from the audio."
}
```

**Verbose JSON Format** (`response_format=verbose_json`):
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
      "temperature": 0,
      "avg_logprob": -0.1,
      "compression_ratio": 1.0,
      "no_speech_prob": 0.0
    }
  ],
  "text": "This is the first segment."
}
```

### YouTube Transcription Endpoint

**POST** `/v1/youtube/transcribe`

Extract metadata, transcripts, and optionally download YouTube videos.

#### Request Body (JSON)
```json
{
  "url": "https://www.youtube.com/watch?v=VIDEO_ID",
  "download_video": false
}
```

#### Parameters
- `url` (required): YouTube URL, short URL, or video ID
- `download_video` (optional): Whether to download the video file (default: false)

#### Example Usage

```bash
# Extract metadata and transcript only
curl -X POST "http://localhost:8000/v1/youtube/transcribe" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}'

# Extract metadata, transcript, and download video
curl -X POST "http://localhost:8000/v1/youtube/transcribe" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://youtu.be/dQw4w9WgXcQ", "download_video": true}'

# Using video ID only
curl -X POST "http://localhost:8000/v1/youtube/transcribe" \
  -H "Content-Type: application/json" \
  -d '{"url": "dQw4w9WgXcQ"}'
```

#### Response Format

```json
{
  "success": true,
  "metadata": {
    "id": "dQw4w9WgXcQ",
    "title": "Rick Astley - Never Gonna Give You Up (Official Video)",
    "description": "The official video for...",
    "duration": 212,
    "view_count": 1400000000,
    "like_count": 15000000,
    "upload_date": "20091025",
    "uploader": "Rick Astley",
    "uploader_id": "RickAstleyVEVO",
    "channel_url": "https://www.youtube.com/channel/UCuAXFkgsw1L7xaCfnd5JJOw",
    "thumbnail": "https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg",
    "thumbnails": [...]
  },
  "transcript": {
    "language": "en",
    "entries": [
      {
        "text": "We're no strangers to love",
        "start": 0.0,
        "duration": 3.5
      },
      ...
    ]
  },
  "transcript_languages": [
    {
      "language": "English",
      "language_code": "en",
      "is_generated": false,
      "is_translatable": true
    }
  ],
  "formats": [...],
  "total_formats": 25,
  "video_downloaded": false
}
```

#### Video Download (Opt-in)

When `download_video: true` is specified:
- Video is limited to 720p maximum to save bandwidth
- Video data is returned as base64-encoded string in `video_data` field
- `video_size_bytes` field indicates the file size
- **Warning**: Video downloads use significant bandwidth and storage

### Health Check

**GET** `/health`

Returns service health status including YouTube Modal connection.

### Service Information

**GET** `/`

Returns service information and available endpoints.

## Prerequisites

- Python 3.11+ (fully compatible with Python 3.13)
- **Modal account and API key** (required for transcription functionality)
- **WhisperX model deployed on Modal** (using the provided `modal_whisper_transcribe.py`)
- Docker and Docker Compose (for containerized deployment)

## Environment Configuration

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and fill in your Modal credentials:
   ```bash
   MODAL_TOKEN_ID=your_modal_token_id_here
   MODAL_TOKEN_SECRET=your_modal_token_secret_here
   MODAL_ENVIRONMENT=main
   MODAL_APP_NAME=modal-whisper-transcribe
   YOUTUBE_MODAL_APP_NAME=modal-youtube-transcribe
   ```

3. Get your Modal credentials from [Modal Settings](https://modal.com/settings)

## Implementation Status

**✅ Production Ready Features:**
- FastAPI webserver with OpenAI Whisper API compatibility
- Multipart/form-data handling for audio file uploads
- Response formatting for both `json` and `verbose_json` formats
- Docker containerization with health checks
- Comprehensive test suite
- Full Modal integration with WhisperX
- Production-ready error handling and service validation

## Configuration

### Modal Setup (Required)

**⚠️ IMPORTANT**: The Modal WhisperX service must be deployed before the API will work. Modal apps start automatically on-demand when called. Without deployment, transcription requests will fail with a 500 error.

1. **Create Modal Account**: Sign up at [modal.com](https://modal.com)
2. **Install and Authenticate**:
   ```bash
   pip install modal
   modal token new
   ```
3. **Deploy Services** (Critical Steps):
   ```bash
   # Deploy WhisperX service
   modal deploy modal_whisper_transcribe.py
   
   # Deploy YouTube transcription service
   modal deploy modal_youtube_transcribe.py
   ```
   
   **Verify deployment**:
   ```bash
   modal app list
   ```
   You should see both `modal-whisper-transcribe` and `modal-youtube-transcribe` in the list of running apps.

4. **Update App Name** (if needed): Modify the app name in `app.py` if different from "modal-whisper-transcribe"

### Environment Variables

```bash
# Modal API credentials (if not using modal token new)
export MODAL_TOKEN_ID="your-token-id"
export MODAL_TOKEN_SECRET="your-token-secret"

# Optional: Custom Modal app name
export MODAL_APP_NAME="your-whisperx-app-name"

# Optional: WhisperX configuration
export WHISPERX_GPU="T4"          # GPU type (T4, A10G, A100, etc.)
export WHISPERX_MODEL="large-v2"   # Model size (tiny, base, small, medium, large, large-v2, large-v3)
```

## Development

### Project Structure

```
.
├── app.py                    # FastAPI webserver
├── modal_whisper_transcribe.py    # Modal WhisperX service
├── requirements.txt          # Python dependencies
├── Dockerfile               # Docker configuration
├── docker-compose.yml       # Docker Compose setup
├── REST.md                  # API specification
├── TASKS.md                 # Implementation tasks
└── README.md               # This file
```

### Running Tests

#### Automated Test Suite

Use the provided test script to verify all API functionality:

```bash
# Make sure the API server is running first
python test_api.py
```

This will test:
- Health check endpoint ✅ (should always pass)
- Root information endpoint ✅ (should always pass)
- JSON format transcription ❌ (will fail without Modal setup)
- Verbose JSON format transcription ❌ (will fail without Modal setup)

**Expected Results**:
- **With Modal deployed**: All tests should pass
- **Without Modal deployed**: Transcription tests will fail with 500 error: `"Function has not been hydrated with the metadata it needs to run on Modal, because the App it is defined on is not running."` (Note: This error message is misleading - Modal apps don't need to be continuously running)

**If transcription tests fail**: See the [Troubleshooting](#troubleshooting) section below.

#### Local Testing with WhisperX

The `modal_whisper_transcribe.py` file includes a local entrypoint for testing the WhisperX transcription directly without the API server:

```bash
# Test with a local audio file
modal run modal_whisper_transcribe.py --audio-file audio.wav

# Test with a remote audio file URL
modal run modal_whisper_transcribe.py --audio-link https://example.com/audio.wav

# Test with default sample audio (no arguments)
modal run modal_whisper_transcribe.py
```

This local entrypoint:
- Downloads and transcribes audio files directly
- Outputs transcription results with language detection and timing information
- Saves results to `transcription.json` for inspection
- Useful for testing WhisperX functionality independently of the API server

#### Manual Testing with cURL

Test the API with sample audio files:

```bash
# Test basic transcription
curl -X POST "http://localhost:8000/v1/audio/transcriptions" \
  -F "file=@test_audio.wav" \
  -F "model=whisper-1"

# Test health endpoint
curl http://localhost:8000/health
```

## Deployment

### Docker

```bash
# Build image
docker build -t modal-whisper .

# Run container
docker run -p 8000:8000 modal-whisper
```

### Docker Compose

```bash
# Start service
docker-compose up -d

# View logs
docker-compose logs -f

# Stop service
docker-compose down
```

## Troubleshooting

### Common Issues

#### 1. "Function has not been hydrated with the metadata it needs to run on Modal"

**Error**: `Status: 500, Error: {"detail":"Transcription failed: Function has not been hydrated with the metadata it needs to run on Modal, because the App it is defined on is not running."}`

**Solution**: The Modal app is not deployed or there's an issue with the app connection. Follow these steps:

1. **Deploy the Modal app**:
   ```bash
   modal deploy modal_whisper_transcribe.py
   ```

2. **Verify the app is deployed**:
   ```bash
   modal app list
   ```
   Look for `modal-whisper-transcribe` in the deployed apps list. Note: Modal apps don't need to be "running" - they start automatically when called.

3. **Check app logs** (if deployment fails):
   ```bash
   modal app logs modal-whisper-transcribe
   ```

4. **Ensure Modal authentication**:
   ```bash
   modal token new
   ```

#### 2. Modal Authentication Issues

**Error**: Authentication or permission errors

**Solution**:
1. Re-authenticate with Modal:
   ```bash
   modal token new
   ```
2. Verify your Modal account has sufficient credits
3. Check that your `.env` file has correct Modal credentials (if using environment variables)

#### 3. Test API Failures

**Error**: `python test_api.py` shows transcription tests failing

**Solution**:
1. Ensure the API server is running:
   ```bash
   uvicorn app:app --host 0.0.0.0 --port 8000
   ```
2. Verify Modal app is deployed (see issue #1 above)
3. Check that the Modal app name matches between `modal_whisper_transcribe.py` and your environment

#### 4. Docker Issues

**Error**: Container fails to connect to Modal

**Solution**:
1. Ensure Modal credentials are properly set in `.env` file
2. Deploy Modal app from your host machine (not inside Docker)
3. Verify Docker container can access Modal API (network connectivity)

### Getting Help

If you continue to experience issues:
1. Check Modal's [documentation](https://modal.com/docs)
2. Verify your Modal account status and credits
3. Review the Modal app logs: `modal app logs modal-whisper-transcribe`

## Limitations

- Only supports `whisper-1` model
- Response formats limited to `json` and `verbose_json`
- Some OpenAI API fields are populated with placeholder values
- Requires active Modal deployment for WhisperX processing
- File size limit: 25MB
- WhisperX model performance depends on Modal compute resources

## License

This project is provided as-is for educational and development purposes.