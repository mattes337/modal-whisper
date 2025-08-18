# Modal WhisperX API

A FastAPI webserver that provides OpenAI Whisper API compatibility using Modal and WhisperX for high-quality audio transcription with word-level timestamps.

## Features

- **OpenAI Whisper API Compatible**: Drop-in replacement for OpenAI's transcription API
- **WhisperX Integration**: Uses WhisperX via Modal for accurate word-level timestamps
- **Multiple Response Formats**: Supports both `json` and `verbose_json` formats
- **Concurrent Processing**: Handles multiple transcription requests simultaneously
- **Docker Support**: Easy deployment with Docker and Docker Compose
- **Health Monitoring**: Built-in health check endpoints

## Quick Start

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

### Transcription Endpoint

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

### Health Check

**GET** `/health`

Returns service health status.

### Service Information

**GET** `/`

Returns service information and available endpoints.

## Prerequisites

- Python 3.11+ (fully compatible with Python 3.13)
- Modal account and API key configured (for production use)
- WhisperX model deployed on Modal (using the provided `whisperx_transcribe.py`)
- Docker and Docker Compose (for containerized deployment)

## Current Implementation Status

**✅ Completed:**
- FastAPI webserver with OpenAI Whisper API compatibility
- Multipart/form-data file upload handling
- JSON and verbose_json response formats
- Docker configuration (Dockerfile + docker-compose.yml)
- Health check and service information endpoints
- Comprehensive test suite

**⚠️ Note:** The current implementation includes a mock transcription function for testing. For production use, replace `app.py` with `app_production.py` which includes proper Modal integration.

## Configuration

The service uses the existing Modal app `example-whisperx-transcribe` defined in `whisperx_transcribe.py`. Make sure this Modal app is deployed and accessible before starting the webserver.

## Development

### Project Structure

```
.
├── app.py                    # FastAPI webserver
├── whisperx_transcribe.py    # Modal WhisperX service
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
- Health check endpoint
- Root information endpoint  
- JSON format transcription
- Verbose JSON format transcription

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

## Limitations

- Only supports `whisper-1` model
- Response formats limited to `json` and `verbose_json`
- Some OpenAI API fields are populated with placeholder values
- Requires active Modal deployment for WhisperX processing

## License

This project is provided as-is for educational and development purposes.