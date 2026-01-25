import modal
import json
import re
import tempfile
import os
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create Modal app
app = modal.App("modal-youtube-transcribe")

# Reference the AUTH_TOKEN secret from Modal
auth_secret = modal.Secret.from_name("AUTH_TOKEN")

# Define the image with required dependencies (v2 - API update)
image = (
    modal.Image.debian_slim()
    .apt_install([
        "ffmpeg",  # For audio extraction
        "curl", "unzip"
    ])
    .run_commands([
        # Install Deno (required by yt-dlp for YouTube JS runtime)
        "curl -fsSL https://deno.land/install.sh | sh",
        "ln -s /root/.deno/bin/deno /usr/local/bin/deno"
    ])
    .pip_install([
        "yt-dlp",  # Latest version for newest YouTube workarounds
        "youtube-transcript-api>=0.6.2",
        "requests>=2.31.0",
        "python-dotenv>=1.0.0",
        "fastapi>=0.104.0"
    ])
)


def extract_video_id(url: str) -> Optional[str]:
    """Extract video ID from various YouTube URL formats"""
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)',
        r'youtube\.com\/v\/([^&\n?#]+)',
        r'youtube\.com\/shorts\/([^&\n?#]+)'
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    # If it's already just a video ID
    if re.match(r'^[a-zA-Z0-9_-]{11}$', url):
        return url

    return None


@app.function(image=image, timeout=60)
def get_youtube_transcript(video_id: str) -> Dict[str, Any]:
    """
    Try to get the official YouTube transcript.
    This usually works without bot detection issues.

    Returns:
        Dictionary with transcript data or error
    """
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound

    try:
        # Create API instance (new API in v1.0.0+)
        ytt_api = YouTubeTranscriptApi()

        # Get available transcripts
        transcript_list = ytt_api.list(video_id)
        available_transcripts = []

        for transcript_info in transcript_list:
            available_transcripts.append({
                "language": transcript_info.language,
                "language_code": transcript_info.language_code,
                "is_generated": transcript_info.is_generated,
                "is_translatable": transcript_info.is_translatable
            })

        # Try to get transcript - prefer manual over auto-generated, English first
        transcript_data = None
        selected_language = None
        is_generated = None

        # First try manual English
        try:
            transcript = transcript_list.find_manually_created_transcript(['en'])
            transcript_data = transcript.fetch()
            selected_language = 'en'
            is_generated = False
        except:
            pass

        # Then try auto-generated English
        if not transcript_data:
            try:
                transcript = transcript_list.find_generated_transcript(['en'])
                transcript_data = transcript.fetch()
                selected_language = 'en'
                is_generated = True
            except:
                pass

        # Then try any manual transcript
        if not transcript_data:
            try:
                for t in transcript_list:
                    if not t.is_generated:
                        transcript_data = t.fetch()
                        selected_language = t.language_code
                        is_generated = False
                        break
            except:
                pass

        # Finally try any auto-generated transcript
        if not transcript_data:
            try:
                for t in transcript_list:
                    if t.is_generated:
                        transcript_data = t.fetch()
                        selected_language = t.language_code
                        is_generated = True
                        break
            except:
                pass

        if transcript_data:
            # Convert to full text - handle both dict and FetchedTranscriptSnippet objects
            segments = []
            for entry in transcript_data:
                if hasattr(entry, 'text'):
                    segments.append({
                        'text': entry.text,
                        'start': getattr(entry, 'start', 0),
                        'duration': getattr(entry, 'duration', 0)
                    })
                else:
                    segments.append(entry)

            full_text = ' '.join([s['text'] if isinstance(s, dict) else s.text for s in transcript_data])

            return {
                "success": True,
                "source": "youtube_official",
                "language": selected_language,
                "is_generated": is_generated,
                "available_languages": available_transcripts,
                "segments": segments,
                "text": full_text
            }
        else:
            return {
                "success": False,
                "error": "No transcript found in any language"
            }

    except TranscriptsDisabled:
        return {
            "success": False,
            "error": "Transcripts are disabled for this video"
        }
    except NoTranscriptFound:
        return {
            "success": False,
            "error": "No transcript found for this video"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to get transcript: {str(e)}"
        }


@app.function(image=image, timeout=300)
def download_youtube_audio(video_id: str) -> Dict[str, Any]:
    """
    Download audio from YouTube video for transcription.

    Returns:
        Dictionary with audio data (bytes) or error
    """
    import yt_dlp

    try:
        temp_dir = tempfile.mkdtemp()
        output_path = os.path.join(temp_dir, 'audio')

        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': output_path,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'wav',
                'preferredquality': '192',
            }],
            'quiet': True,
            'no_warnings': True,
            # Use player clients that work better without authentication
            'extractor_args': {
                'youtube': {
                    'player_client': ['android_sdkless', 'web_safari', 'web'],
                }
            },
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
        }

        url = f"https://www.youtube.com/watch?v={video_id}"

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get('title', 'Unknown')
            duration = info.get('duration', 0)

        # Find the audio file
        audio_file = output_path + '.wav'
        if not os.path.exists(audio_file):
            # Try other extensions
            for ext in ['.m4a', '.mp3', '.webm', '.opus']:
                if os.path.exists(output_path + ext):
                    audio_file = output_path + ext
                    break

        if os.path.exists(audio_file):
            with open(audio_file, 'rb') as f:
                audio_data = f.read()

            # Cleanup
            os.remove(audio_file)
            os.rmdir(temp_dir)

            return {
                "success": True,
                "audio_data": audio_data,
                "title": title,
                "duration": duration
            }
        else:
            return {
                "success": False,
                "error": "Audio file not found after download"
            }

    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to download audio: {str(e)}"
        }


@app.function(image=image, timeout=600)
def transcribe_youtube(video_url: str, force_whisper: bool = False) -> Dict[str, Any]:
    """
    Transcribe a YouTube video.

    Strategy:
    1. Try to get official YouTube transcript first (fast, no download needed)
    2. If no transcript available, download audio and transcribe with WhisperX

    Args:
        video_url: YouTube URL or video ID
        force_whisper: If True, skip YouTube transcript and use WhisperX directly

    Returns:
        Dictionary with transcript and metadata
    """
    # Import WhisperX service from the other Modal app
    WhisperX = modal.Cls.from_name("modal-whisper-transcribe", "WhisperX")

    # Extract video ID
    video_id = extract_video_id(video_url)
    if not video_id:
        return {"error": "Invalid YouTube URL or video ID"}

    # Step 1: Try to get official YouTube transcript (unless force_whisper)
    if not force_whisper:
        transcript_result = get_youtube_transcript.remote(video_id)

        if transcript_result.get("success"):
            return {
                "success": True,
                "video_id": video_id,
                "source": "youtube_official",
                "language": transcript_result.get("language"),
                "is_auto_generated": transcript_result.get("is_generated"),
                "text": transcript_result.get("text"),
                "segments": transcript_result.get("segments"),
                "available_languages": transcript_result.get("available_languages")
            }

        # Log why we're falling back
        transcript_error = transcript_result.get("error", "Unknown error")
        print(f"YouTube transcript not available: {transcript_error}")
        print("Falling back to WhisperX transcription...")

    # Step 2: Download audio and transcribe with WhisperX
    audio_result = download_youtube_audio.remote(video_id)

    if not audio_result.get("success"):
        return {
            "error": f"Failed to download audio: {audio_result.get('error')}",
            "transcript_error": transcript_result.get("error") if not force_whisper else None
        }

    # Transcribe with WhisperX
    try:
        whisperx = WhisperX()
        whisper_result = whisperx.transcribe.remote(audio_result["audio_data"])

        # Convert WhisperX output to our format
        full_text = ' '.join([seg.get('text', '') for seg in whisper_result.get('segments', [])])

        return {
            "success": True,
            "video_id": video_id,
            "source": "whisperx",
            "title": audio_result.get("title"),
            "duration": audio_result.get("duration"),
            "language": whisper_result.get("language"),
            "text": full_text.strip(),
            "segments": whisper_result.get("segments", [])
        }

    except Exception as e:
        return {
            "error": f"WhisperX transcription failed: {str(e)}",
            "audio_downloaded": True
        }


# ## HTTP/REST API with Authentication

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

web_app = FastAPI(
    title="Modal YouTube Transcribe API",
    description="YouTube transcription service - uses official transcripts when available, falls back to WhisperX",
)
security = HTTPBearer()


class TranscribeRequest(BaseModel):
    url: str = Field(..., description="YouTube URL or video ID")
    force_whisper: bool = Field(False, description="Force WhisperX transcription even if YouTube transcript exists")


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
    return {"status": "healthy", "service": "modal-youtube-transcribe"}


@web_app.post("/v1/youtube/transcribe")
async def youtube_transcribe_post(
    request: TranscribeRequest,
    _token: str = Depends(verify_auth_token),
) -> Dict[str, Any]:
    """
    Transcribe a YouTube video.

    Strategy:
    1. First tries to get the official YouTube transcript (fast)
    2. If unavailable, downloads audio and transcribes with WhisperX

    Set force_whisper=true to skip YouTube transcript and always use WhisperX.
    """
    try:
        result = transcribe_youtube.remote(request.url, request.force_whisper)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"API error: {str(e)}")


@web_app.get("/v1/youtube/transcribe")
async def youtube_transcribe_get(
    url: str = Query(..., description="YouTube URL or video ID"),
    force_whisper: bool = Query(False, description="Force WhisperX transcription"),
    _token: str = Depends(verify_auth_token),
) -> Dict[str, Any]:
    """GET endpoint for YouTube transcription."""
    try:
        result = transcribe_youtube.remote(url, force_whisper)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"API error: {str(e)}")


@app.function(
    image=image,
    secrets=[auth_secret],
    timeout=15 * 60,  # 15 minutes to accommodate transcribe_youtube (10min) + buffer
)
@modal.concurrent(max_inputs=100)
@modal.asgi_app()
def web_endpoint():
    """Deploy the FastAPI app as an ASGI web endpoint."""
    return web_app


# Local testing
@app.local_entrypoint()
def test_local():
    """Test the function locally"""
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Rick Astley - Never Gonna Give You Up
    print(f"Testing with: {test_url}")
    result = transcribe_youtube.remote(test_url)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    test_local()
