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

# Define the image with required dependencies including headless browser
image = (
    modal.Image.debian_slim()
    .apt_install([
        "wget", "gnupg", "ca-certificates", "fonts-liberation", 
        "libasound2", "libatk-bridge2.0-0", "libdrm2", "libxcomposite1",
        "libxdamage1", "libxrandr2", "libgbm1", "libxss1", "libgconf-2-4"
    ])
    .pip_install([
        "yt-dlp>=2023.12.30",
        "youtube-transcript-api>=0.6.2",
        "requests>=2.31.0",
        "playwright>=1.40.0",
        "beautifulsoup4>=4.12.0",
        "python-dotenv>=1.0.0",
        "fastapi>=0.104.0"
    ])
    .run_commands([
        "playwright install chromium",
        "playwright install-deps chromium"
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

@app.function(image=image, timeout=300)
def extract_youtube_data_browser(video_url: str) -> Dict[str, Any]:
    """
    Extract YouTube data using headless browser to avoid bot detection
    
    Args:
        video_url: YouTube URL or video ID
        
    Returns:
        Dictionary containing metadata, transcript, and download formats
    """
    from playwright.sync_api import sync_playwright
    from youtube_transcript_api import YouTubeTranscriptApi
    import yt_dlp
    import time
    
    try:
        # Extract video ID
        video_id = extract_video_id(video_url)
        if not video_id:
            return {"error": "Invalid YouTube URL or video ID"}
        
        full_url = f"https://www.youtube.com/watch?v={video_id}"
        
        # Use Playwright to get cookies and user agent
        with sync_playwright() as p:
            # Launch browser with anti-detection measures
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding',
                    '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                ]
            )
            
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                extra_http_headers={
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                }
            )
            
            # Add init script to remove webdriver property
            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
            """)
            
            page = context.new_page()
            
            # Navigate to YouTube homepage first
            try:
                page.goto('https://www.youtube.com', wait_until='networkidle', timeout=30000)
                time.sleep(2)
                
                # Simulate some mouse movement
                page.mouse.move(100, 100)
                page.mouse.move(200, 200)
                
                # Now navigate to the specific video
                page.goto(full_url, wait_until='networkidle', timeout=30000)
                time.sleep(3)  # Wait for page to fully load
                
                # Check if we hit bot detection
                if "confirm you're not a bot" in page.content().lower():
                    browser.close()
                    return {"error": "Bot detection triggered even with browser"}
                
                # Extract cookies for yt-dlp
                cookies = context.cookies()
                cookie_dict = {}
                for cookie in cookies:
                    if 'youtube.com' in cookie['domain']:
                        cookie_dict[cookie['name']] = cookie['value']
                
            except Exception as e:
                browser.close()
                return {"error": f"Browser navigation failed: {str(e)}"}
            
            browser.close()
        
        # Now use yt-dlp with the extracted cookies
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'writesubtitles': False,
            'writeautomaticsub': False,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
        }
        
        # Add cookies if we got them
        if cookie_dict:
            # Convert cookies to string format for yt-dlp
            cookie_string = '; '.join([f'{k}={v}' for k, v in cookie_dict.items()])
            ydl_opts['http_headers']['Cookie'] = cookie_string
        
        # Extract video info with cookies
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(full_url, download=False)
            except Exception as e:
                return {"error": f"Failed to extract video info even with browser cookies: {str(e)}"}
        
        # Extract metadata
        metadata = {
            "id": video_id,
            "title": info.get("title", ""),
            "description": info.get("description", ""),
            "duration": info.get("duration", 0),
            "view_count": info.get("view_count", 0),
            "like_count": info.get("like_count", 0),
            "upload_date": info.get("upload_date", ""),
            "uploader": info.get("uploader", ""),
            "uploader_id": info.get("uploader_id", ""),
            "channel_url": info.get("channel_url", ""),
            "thumbnail": info.get("thumbnail", ""),
            "thumbnails": info.get("thumbnails", [])[:3] if info.get("thumbnails") else []
        }
        
        # Extract download formats
        formats = []
        if info.get("formats"):
            for fmt in info["formats"]:
                if fmt.get("url"):
                    format_info = {
                        "format_id": fmt.get("format_id", ""),
                        "ext": fmt.get("ext", ""),
                        "quality": fmt.get("quality", ""),
                        "format_note": fmt.get("format_note", ""),
                        "filesize": fmt.get("filesize"),
                        "url": fmt.get("url", ""),
                        "vcodec": fmt.get("vcodec", ""),
                        "acodec": fmt.get("acodec", ""),
                        "width": fmt.get("width"),
                        "height": fmt.get("height"),
                        "fps": fmt.get("fps"),
                        "abr": fmt.get("abr"),
                        "vbr": fmt.get("vbr"),
                    }
                    formats.append(format_info)
        
        # Get transcript
        transcript = None
        transcript_languages = []
        
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            available_transcripts = []
            
            for transcript_info in transcript_list:
                available_transcripts.append({
                    "language": transcript_info.language,
                    "language_code": transcript_info.language_code,
                    "is_generated": transcript_info.is_generated,
                    "is_translatable": transcript_info.is_translatable
                })
            
            transcript_languages = available_transcripts
            
            # Try to get English transcript first
            try:
                transcript_data = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
            except:
                if available_transcripts:
                    first_lang = available_transcripts[0]["language_code"]
                    transcript_data = YouTubeTranscriptApi.get_transcript(video_id, languages=[first_lang])
                else:
                    transcript_data = None
            
            if transcript_data:
                transcript = {
                    "language": transcript_data[0].get("language", "unknown") if transcript_data else "unknown",
                    "entries": transcript_data
                }
                
        except Exception as e:
            transcript = {"error": f"No transcript available: {str(e)}"}
        
        return {
            "success": True,
            "method": "browser",
            "metadata": metadata,
            "formats": formats,
            "transcript": transcript,
            "transcript_languages": transcript_languages,
            "total_formats": len(formats)
        }
        
    except Exception as e:
        return {"error": f"Browser extraction failed: {str(e)}"}

@app.function(image=image, timeout=300, cpu=0.25, memory=512)  # Low resource configuration
def extract_youtube_data(video_url: str, download_video: bool = False) -> Dict[str, Any]:
    """
    Extract metadata, transcript, and optionally download video from a YouTube video
    Uses browser method first to avoid bot detection, falls back to direct method
    
    Args:
        video_url: YouTube URL or video ID
        download_video: Whether to download the actual video file (opt-in)
        
    Returns:
        Dictionary containing metadata, transcript, and optionally video data
    """
    # Try browser method first (more reliable against bot detection)
    browser_result = extract_youtube_data_browser.remote(video_url)
    
    # If browser method succeeded and we don't need video download, return it
    if browser_result.get("success") and not download_video:
        return browser_result
    
    # If browser method failed or we need video download, try direct method
    import yt_dlp
    from youtube_transcript_api import YouTubeTranscriptApi
    
    try:
        # Extract video ID
        video_id = extract_video_id(video_url)
        if not video_id:
            return {"error": "Invalid YouTube URL or video ID"}
        
        # Configure yt-dlp options with better headers
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'writesubtitles': False,
            'writeautomaticsub': False,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
        }
        
        # If video download is requested, add download options
        video_data = None
        if download_video:
            # Create temporary directory for download
            temp_dir = tempfile.mkdtemp()
            ydl_opts.update({
                'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
                'format': 'best[height<=720]',  # Limit to 720p to save bandwidth
            })
        
        # Extract video info
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=download_video)
            except Exception as e:
                # If both methods failed, return combined error
                if not browser_result.get("success"):
                    return {
                        "error": f"Both browser and direct methods failed. Browser: {browser_result.get('error', 'Unknown')}. Direct: {str(e)}"
                    }
                else:
                    return {"error": f"Failed to extract video info: {str(e)}"}
        
        # If video was downloaded, read the file
        if download_video and info:
            try:
                # Find the downloaded file
                downloaded_file = None
                for file in os.listdir(temp_dir):
                    if file.endswith(('.mp4', '.webm', '.mkv')):
                        downloaded_file = os.path.join(temp_dir, file)
                        break
                
                if downloaded_file and os.path.exists(downloaded_file):
                    with open(downloaded_file, 'rb') as f:
                        video_data = f.read()
                    # Clean up
                    os.remove(downloaded_file)
                    os.rmdir(temp_dir)
                else:
                    video_data = {"error": "Video file not found after download"}
            except Exception as e:
                video_data = {"error": f"Failed to read downloaded video: {str(e)}"}
        
        # Extract metadata
        metadata = {
            "id": video_id,
            "title": info.get("title", ""),
            "description": info.get("description", ""),
            "duration": info.get("duration", 0),
            "view_count": info.get("view_count", 0),
            "like_count": info.get("like_count", 0),
            "upload_date": info.get("upload_date", ""),
            "uploader": info.get("uploader", ""),
            "uploader_id": info.get("uploader_id", ""),
            "channel_url": info.get("channel_url", ""),
            "thumbnail": info.get("thumbnail", ""),
            "thumbnails": info.get("thumbnails", [])[:3] if info.get("thumbnails") else []  # First 3 thumbnails
        }
        
        # Extract download formats (video + audio) - metadata only
        formats = []
        if info.get("formats"):
            for fmt in info["formats"]:
                if fmt.get("url"):  # Only include formats with direct URLs
                    format_info = {
                        "format_id": fmt.get("format_id", ""),
                        "ext": fmt.get("ext", ""),
                        "quality": fmt.get("quality", ""),
                        "format_note": fmt.get("format_note", ""),
                        "filesize": fmt.get("filesize"),
                        "url": fmt.get("url", ""),
                        "vcodec": fmt.get("vcodec", ""),
                        "acodec": fmt.get("acodec", ""),
                        "width": fmt.get("width"),
                        "height": fmt.get("height"),
                        "fps": fmt.get("fps"),
                        "abr": fmt.get("abr"),  # Audio bitrate
                        "vbr": fmt.get("vbr"),  # Video bitrate
                    }
                    formats.append(format_info)
        
        # Get transcript
        transcript = None
        transcript_languages = []
        
        try:
            # Try to get available transcript languages
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            available_transcripts = []
            
            for transcript_info in transcript_list:
                available_transcripts.append({
                    "language": transcript_info.language,
                    "language_code": transcript_info.language_code,
                    "is_generated": transcript_info.is_generated,
                    "is_translatable": transcript_info.is_translatable
                })
            
            transcript_languages = available_transcripts
            
            # Get the first available transcript (original language preference)
            transcript_data = None
            selected_language = "unknown"
            
            if available_transcripts:
                # Try to get the first available transcript (usually original language)
                first_transcript = available_transcripts[0]
                try:
                    transcript_data = YouTubeTranscriptApi.get_transcript(video_id, languages=[first_transcript["language_code"]])
                    selected_language = first_transcript["language_code"]
                except:
                    # If first fails, try English as fallback
                    try:
                        transcript_data = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
                        selected_language = "en"
                    except:
                        transcript_data = None
            
            if transcript_data:
                transcript = {
                    "language": selected_language,
                    "entries": transcript_data
                }
                
        except Exception as e:
            transcript = {"error": f"No transcript available: {str(e)}"}
        
        result = {
            "success": True,
            "method": "direct_fallback" if not browser_result.get("success") else "direct_with_download",
            "metadata": metadata,
            "formats": formats,
            "transcript": transcript,
            "transcript_languages": transcript_languages,
            "total_formats": len(formats),
            "video_downloaded": download_video
        }
        
        # Add video data if downloaded
        if download_video:
            if isinstance(video_data, bytes):
                # Convert to base64 for JSON serialization
                import base64
                result["video_download"] = {
                    "downloaded": True,
                    "format": "720p mp4",
                    "size_bytes": len(video_data),
                    "content_base64": base64.b64encode(video_data).decode('utf-8')
                }
            else:
                result["video_download"] = {
                    "downloaded": False,
                    "error": video_data.get("error", "Unknown error") if isinstance(video_data, dict) else str(video_data)
                }
        
        return result
        
    except Exception as e:
        return {"error": f"All methods failed: {str(e)}"}

# ## HTTP/REST API with Authentication
#
# FastAPI web service with AUTH_TOKEN authentication
#

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

web_app = FastAPI(
    title="Modal YouTube Transcribe API",
    description="YouTube metadata and transcript extraction service with authentication",
)
security = HTTPBearer()


class YouTubeRequest(BaseModel):
    url: str = Field(..., description="YouTube URL or video ID")
    download_video: bool = Field(False, description="Whether to download the video file")


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
    request: YouTubeRequest,
    _token: str = Depends(verify_auth_token),
) -> Dict[str, Any]:
    """
    Extract metadata and transcript from a YouTube video.

    Requires Bearer token authentication.

    Expected JSON payload:
    {
        "url": "https://www.youtube.com/watch?v=VIDEO_ID",
        "download_video": false
    }
    """
    try:
        result = extract_youtube_data.remote(request.url, request.download_video)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"API error: {str(e)}")


@web_app.get("/v1/youtube/transcribe")
async def youtube_transcribe_get(
    url: str = Query(..., description="YouTube URL or video ID"),
    download_video: bool = Query(False, description="Whether to download the video file"),
    _token: str = Depends(verify_auth_token),
) -> Dict[str, Any]:
    """
    GET endpoint for YouTube transcription.

    Requires Bearer token authentication.

    Usage: GET /v1/youtube/transcribe?url=https://www.youtube.com/watch?v=VIDEO_ID&download_video=false
    """
    try:
        result = extract_youtube_data.remote(url, download_video)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"API error: {str(e)}")


@app.function(
    image=image,
    secrets=[auth_secret],
)
@modal.concurrent(max_inputs=100)
@modal.asgi_app()
def web_endpoint():
    """Deploy the FastAPI app as an ASGI web endpoint."""
    return web_app

# Optional: Local testing function
@app.local_entrypoint()
def test_local():
    """Test the function locally"""
    # Try a different video that might be less restricted
    test_url = "https://www.youtube.com/watch?v=9bZkp7q19f0"  # PSY - GANGNAM STYLE (very popular, older video)
    result = extract_youtube_data.remote(test_url, download_video=False)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    # For local testing
    test_local()