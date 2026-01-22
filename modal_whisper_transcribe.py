# ---
# lambda-test: false  # requires audio file
# ---
# # Modal Whisper Transcribe
#
# A Modal application for running [WhisperX](https://github.com/m-bain/whisperX)
# transcription with accurate, word-level timestamps.
#
# This application provides:
#
# 1. A containerized environment with CUDA 12.8, cuDNN 8, FFmpeg and Python dependencies.
# 2. Persistent model weights using [Modal Volume](https://modal.com/docs/reference/modal.Volume).
# 3. A [Modal Cls](https://modal.com/docs/reference/modal.App#cls) that loads WhisperX once per GPU instance.
# 4. A [local entrypoint](https://modal.com/docs/reference/modal.App#local_entrypoint) for testing and development.
#
# ## Container Image
#
# The container is built from NVIDIA's official CUDA 12.8 devel image with cuDNN, FFmpeg,
# and the WhisperX Python package plus numerical dependencies.
#

import os
import tempfile
from typing import Dict, Optional

import modal

MODEL_CACHE_DIR = "/whisperx-cache"

# Load environment variables from local .env file
from dotenv import load_dotenv
load_dotenv()

# Configuration from environment variables
GPU_TYPE = os.getenv("WHISPERX_GPU", "T4")
MODEL_NAME = os.getenv("WHISPERX_MODEL", "large-v2")

# Create Modal secrets from environment variables
whisperx_secret = modal.Secret.from_dict({
    "WHISPERX_GPU": GPU_TYPE,
    "WHISPERX_MODEL": MODEL_NAME,
})

# Reference the AUTH_TOKEN secret from Modal
auth_secret = modal.Secret.from_name("AUTH_TOKEN")

image = (
    modal.Image.from_registry(
        "nvidia/cuda:12.8.0-cudnn-devel-ubuntu22.04",
        add_python="3.12",
    )
    # ── System deps ─────────────────────────────────────────────────────────────
    .apt_install("ffmpeg")  # audio decoding / resampling
    .apt_install("libcudnn8")  # cuDNN runtime
    .apt_install("libcudnn8-dev")  # cuDNN headers (needed by torch wheels)
    # ── Python deps ─────────────────────────────────────────────────────────────
    .pip_install(
        "whisperx==3.4.0",  # our ASR library
        "numpy==2.0.2",
        "scipy==1.15.0",
        "python-dotenv>=1.0.0",  # for loading environment variables
        "fastapi>=0.104.0",  # for HTTP API
        "python-multipart>=0.0.6",  # for file uploads
    )
    # Tell HF & Torch to cache inside our Volume
    .env({"HF_HOME": MODEL_CACHE_DIR})
    .env({"TORCH_HOME": MODEL_CACHE_DIR})
)

# ## Defining the app
#
# Downloaded weights live in a [Modal Volume](https://modal.com/docs/reference/modal.Volume) so subsequent runs reuse them.
app = modal.App("modal-whisper-transcribe", image=image)
models_volume = modal.Volume.from_name("whisperx-models", create_if_missing=True)


# ## Defining the inference service
#
# We wrap WhisperX inference in a Modal Cls.
# A single GPU container can serve multiple concurrent requests.
@app.cls(
    gpu=GPU_TYPE,
    image=image,
    volumes={MODEL_CACHE_DIR: models_volume},
    secrets=[whisperx_secret],
    timeout=30 * 60,
)
class WhisperX:
    """Serverless WhisperX service running on a single GPU."""

    @modal.enter()
    def setup(self):
        print("🔄 Loading WhisperX model …")
        import whisperx
        import os

        # Get model name from environment variables (now available via Modal secrets)
        model_name = os.getenv("WHISPERX_MODEL", "large-v2")
        print(f"📦 Using model: {model_name}")

        self.model = whisperx.load_model(
            model_name,
            device="cuda",
            compute_type="float16",
            download_root=MODEL_CACHE_DIR,
        )
        self.device = "cuda"
        print("✅ Model ready!")

    @modal.method()
    def transcribe(self, audio_data: bytes, language: Optional[str] = None) -> Dict:
        """
        Transcribe an audio file passed in as raw bytes.
        
        Args:
            audio_data: Raw audio file bytes
            language: Optional language code (ISO-639-1). If None, language will be auto-detected.
        
        Returns:
            Dictionary with language, per-word segments, and total duration.
        """

        import whisperx

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
            temp_audio.write(audio_data)
            temp_audio_path = temp_audio.name

        try:
            audio = whisperx.load_audio(temp_audio_path)
            # Use provided language or let WhisperX auto-detect
            transcribe_kwargs = {"batch_size": 16}
            if language:
                transcribe_kwargs["language"] = language
            
            result = self.model.transcribe(audio, **transcribe_kwargs)
            detected_language = result.get("language", language or "unknown")

            if result["segments"]:
                try:
                    align_model, metadata = whisperx.load_align_model(
                        language_code=detected_language,
                        device=self.device,
                        model_dir=MODEL_CACHE_DIR,
                    )
                    result = whisperx.align(
                        result["segments"], align_model, metadata, audio, self.device
                    )
                except Exception as e:
                    print(f"⚠️ Alignment failed: {e} — falling back to segment-level")

            return {
                "language": detected_language,
                "segments": result["segments"],
                "duration": len(audio) / 16_000,  # audio is 16 kHz
            }

        finally:
            if os.path.exists(temp_audio_path):
                os.unlink(temp_audio_path)


# ## HTTP/REST API
#
# We expose a FastAPI web service for HTTP access with AUTH_TOKEN authentication.
# The service is deployed via Modal's ASGI app feature.
#

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends, Header
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

web_app = FastAPI(
    title="Modal WhisperX API",
    description="WhisperX transcription service with authentication",
)
security = HTTPBearer()


def verify_auth_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Verify the Bearer token against AUTH_TOKEN secret."""
    expected_token = os.environ.get("AUTH_TOKEN")
    if not expected_token:
        raise HTTPException(status_code=500, detail="AUTH_TOKEN not configured")

    if credentials.credentials != expected_token:
        raise HTTPException(status_code=401, detail="Invalid authentication token")

    return credentials.credentials


@web_app.get("/health")
async def health_check():
    """Health check endpoint (no auth required)."""
    return {"status": "healthy", "service": "modal-whisperx"}


@web_app.post("/v1/audio/transcriptions")
async def create_transcription(
    file: UploadFile = File(...),
    model: str = Form("whisper-1"),
    response_format: Optional[str] = Form("json"),
    language: Optional[str] = Form(None),
    _token: str = Depends(verify_auth_token),
):
    """
    Transcribe audio file using WhisperX.
    Compatible with OpenAI Whisper API format.

    Requires Bearer token authentication.
    """
    if model != "whisper-1":
        raise HTTPException(status_code=400, detail="Only 'whisper-1' model is supported")

    if response_format not in ["json", "verbose_json"]:
        raise HTTPException(status_code=400, detail="Only 'json' and 'verbose_json' formats are supported")

    try:
        audio_data = await file.read()

        # Get the WhisperX class and call transcribe
        whisperx_instance = WhisperX()
        result = whisperx_instance.transcribe.remote(audio_data, language)

        if response_format == "json":
            full_text = " ".join([seg.get("text", "") for seg in result.get("segments", [])])
            return JSONResponse(content={"text": full_text.strip()})

        # verbose_json format
        segments = []
        for i, segment in enumerate(result.get("segments", [])):
            segments.append({
                "id": i,
                "seek": 0,
                "start": segment.get("start", 0.0),
                "end": segment.get("end", 0.0),
                "text": segment.get("text", ""),
                "tokens": [],
                "temperature": 0.0,
                "avg_logprob": -0.1,
                "compression_ratio": 1.0,
                "no_speech_prob": 0.0,
            })

        full_text = " ".join([seg.get("text", "") for seg in result.get("segments", [])])

        return JSONResponse(content={
            "task": "transcribe",
            "language": result.get("language", "en"),
            "duration": result.get("duration", 0.0),
            "segments": segments,
            "text": full_text.strip(),
        })

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")


@app.function(
    image=image,
    secrets=[auth_secret],
)
@modal.concurrent(max_inputs=100)
@modal.asgi_app()
def web_endpoint():
    """Deploy the FastAPI app as an ASGI web endpoint."""
    return web_app


# ## Command-line usage
#
# We expose a [local entrypoint](https://modal.com/docs/reference/modal.App#local_entrypoint)
# so you can run:
# - using a local audio file
# - using a link to an audio file
#
# ```bash
# modal run modal_whisper_transcribe.py --audio-file audio.wav # uses a local audio file
# modal run modal_whisper_transcribe.py --audio-link https://example.com/audio.wav # uses a link to an audio file
# modal run modal_whisper_transcribe.py # uses a default public audio file
# ```
#
@app.local_entrypoint()
def main(
    audio_file: str = None,
    audio_link: str = None,
):
    import json
    import time

    import requests

    if not audio_file and not audio_link:
        print("No audio file or link provided, using default link")
        audio_link = "https://modal-public-assets.s3.us-east-1.amazonaws.com/erik.wav"

    if audio_file:
        print(f"🔊 Reading {audio_file} …")
        with open(audio_file, "rb") as f:
            audio_data = f.read()
    elif audio_link:
        print(f"🔊 Reading {audio_link} …")
        audio_data = requests.get(audio_link).content

    transcriber = WhisperX()

    print("📝 Transcribing …")
    start = time.time()
    result = transcriber.transcribe.remote(audio_data)
    duration = time.time() - start

    print(f"\n🌐 Detected language: {result['language']}")
    print(f"⏱️  Audio duration:   {result['duration']:.2f} s")
    print(f"🚀 Time taken:        {duration:.2f} s")

    with open("transcription.json", "w") as f:
        json.dump(result, f, indent=2)

    print("\n💾 Saved transcription → transcription.json")