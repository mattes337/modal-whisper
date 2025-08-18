from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional, Annotated
from pydantic import BaseModel, Field
import tempfile
import os
from dotenv import load_dotenv
import modal

# Load environment variables from .env file
load_dotenv()

app = FastAPI(title="Modal WhisperX API", description="OpenAI Whisper API compatible transcription service using Modal and WhisperX")

# Initialize Modal app connection
try:
    # Get Modal app name from environment variable
    modal_app_name = os.getenv("MODAL_APP_NAME", "modal-whisper-transcribe")
    
    # Try newer Modal API first
    try:
        modal_app = modal.App.lookup(modal_app_name)
    except AttributeError:
        # Fallback to older API
        modal_app = modal.App.from_name(modal_app_name, create_if_missing=False)
    USE_MODAL = True
except Exception as e:
    print(f"Warning: Could not connect to Modal app: {e}")
    USE_MODAL = False

@app.post("/v1/audio/transcriptions")
async def create_transcription(
    file: UploadFile = File(...),
    model: str = Form(...),
    prompt: Optional[str] = Form(None),
    response_format: Optional[str] = Form("json"),
    temperature: Optional[float] = Form(0.0),
    language: Optional[str] = Form(None)
):
    """
    Transcribe audio file using WhisperX via Modal.
    Compatible with OpenAI Whisper API format.
    """
    
    # Validate model
    if model != "whisper-1":
        raise HTTPException(status_code=400, detail="Only 'whisper-1' model is supported")
    
    # Validate response format
    if response_format not in ["json", "verbose_json"]:
        raise HTTPException(status_code=400, detail="Only 'json' and 'verbose_json' response formats are supported")
    
    try:
        # Read audio file
        audio_data = await file.read()
        
        if not USE_MODAL:
            raise HTTPException(status_code=503, detail="Modal service not available. Please ensure Modal app is deployed and accessible.")
        
        # Get reference to the deployed WhisperX class
        whisperx_cls = modal.Cls.from_name(modal_app_name, "WhisperX")
        
        # Call WhisperX transcription via Modal
        result = whisperx_cls().transcribe.remote(audio_data, language)
        
        # Format response based on requested format
        if response_format == "json":
            # Simple format - just the text
            full_text = " ".join([segment.get("text", "") for segment in result.get("segments", [])])
            return JSONResponse(content={"text": full_text.strip()})
        
        elif response_format == "verbose_json":
            # Detailed format with segments and timestamps
            segments = []
            for i, segment in enumerate(result.get("segments", [])):
                # Format segment to match OpenAI structure
                formatted_segment = {
                    "id": i,
                    "seek": 0,  # WhisperX doesn't provide seek info
                    "start": segment.get("start", 0.0),
                    "end": segment.get("end", 0.0),
                    "text": segment.get("text", ""),
                    "tokens": [],  # WhisperX doesn't provide token info in same format
                    "temperature": temperature,
                    "avg_logprob": -0.1,  # Placeholder value
                    "compression_ratio": 1.0,  # Placeholder value
                    "no_speech_prob": 0.0  # Placeholder value
                }
                segments.append(formatted_segment)
            
            full_text = " ".join([segment.get("text", "") for segment in result.get("segments", [])])
            
            response_data = {
                "task": "transcribe",
                "language": result.get("language", "en"),
                "duration": result.get("duration", 0.0),
                "segments": segments,
                "text": full_text.strip()
            }
            
            return JSONResponse(content=response_data)
    
    except HTTPException:
        # Re-raise HTTP exceptions (like 503) without wrapping
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy", 
        "service": "modal-whisperx",
        "modal_connected": USE_MODAL
    }

@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": "Modal WhisperX API",
        "description": "OpenAI Whisper API compatible transcription service",
        "modal_connected": USE_MODAL,
        "endpoints": {
            "transcription": "/v1/audio/transcriptions",
            "health": "/health"
        }
    }

if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host=host, port=port)