from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional, Annotated
from pydantic import BaseModel, Field
import tempfile
import os
import json

app = FastAPI(title="Modal WhisperX API", description="OpenAI Whisper API compatible transcription service using Modal and WhisperX")

class TranscriptionRequest(BaseModel):
    file: str
    model: Optional[str] = Field(default="whisper-1")
    prompt: Optional[str] = Field(default=None)
    response_format: Optional[str] = Field(default="json")
    temperature: Optional[float] = Field(default=0)
    language: Optional[str] = Field(default=None)

# Mock transcription function for testing
def mock_transcribe(audio_data: bytes) -> dict:
    """Mock transcription function for testing purposes"""
    return {
        "language": "en",
        "segments": [
            {
                "start": 0.0,
                "end": 5.0,
                "text": "This is a mock transcription segment."
            },
            {
                "start": 5.0,
                "end": 10.0,
                "text": "This demonstrates the API functionality."
            }
        ],
        "duration": 10.0
    }

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
    
    # Validate file size (25MB limit)
    if file.size and file.size > 25 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size exceeds 25MB limit")
    
    # Validate response format
    if response_format not in ["json", "verbose_json"]:
        raise HTTPException(status_code=400, detail="Only 'json' and 'verbose_json' response formats are supported")
    
    try:
        # Read audio file
        audio_data = await file.read()
        
        # Use mock transcription for testing
        # In production, replace this with actual Modal WhisperX integration
        result = mock_transcribe(audio_data)
        
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
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "modal-whisperx"}

@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": "Modal WhisperX API",
        "description": "OpenAI Whisper API compatible transcription service",
        "endpoints": {
            "transcription": "/v1/audio/transcriptions",
            "health": "/health"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)