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
        "requests>=2.25.0",  # for webhook calls
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
    def transcribe(self, audio_data: bytes, language: Optional[str] = None, webhook_url: Optional[str] = None) -> Dict:
        """
        Transcribe an audio file passed in as raw bytes.
        
        Args:
            audio_data: Raw audio file bytes
            language: Optional language code (ISO-639-1). If None, language will be auto-detected.
            webhook_url: Optional webhook URL to POST the result to when transcription is complete.
        
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

            result_data = {
                "language": detected_language,
                "segments": result["segments"],
                "duration": len(audio) / 16_000,  # audio is 16 kHz
            }
            
            # Call webhook if provided
            if webhook_url:
                try:
                    import requests
                    response = requests.post(
                        webhook_url,
                        json=result_data,
                        headers={"Content-Type": "application/json"},
                        timeout=30
                    )
                    print(f"✅ Webhook called successfully: {response.status_code}")
                except Exception as e:
                    print(f"⚠️ Webhook call failed: {e}")
            
            return result_data

        finally:
            if os.path.exists(temp_audio_path):
                os.unlink(temp_audio_path)


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