#!/usr/bin/env python3
"""
Simple webhook test server to receive transcription results.

Run this script to start a local webhook server on port 8001,
then use http://localhost:8001/webhook as the webhook_url when
testing the transcription API.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn
import json
from datetime import datetime

app = FastAPI(title="Webhook Test Server")

@app.post("/webhook")
async def receive_webhook(request: Request):
    """Receive and log webhook data from transcription service."""
    try:
        data = await request.json()
        timestamp = datetime.now().isoformat()
        
        print(f"\n🎯 Webhook received at {timestamp}")
        print(f"📝 Language: {data.get('language', 'unknown')}")
        print(f"⏱️  Duration: {data.get('duration', 0):.2f}s")
        print(f"📊 Segments: {len(data.get('segments', []))}")
        
        # Print first few words of transcription
        segments = data.get('segments', [])
        if segments:
            first_text = ' '.join([seg.get('text', '') for seg in segments[:3]]).strip()
            print(f"📄 Preview: {first_text}...")
        
        # Save to file for inspection
        with open(f"webhook_result_{timestamp.replace(':', '-')}.json", "w") as f:
            json.dump(data, f, indent=2)
        
        return JSONResponse(
            content={"status": "received", "timestamp": timestamp},
            status_code=200
        )
    
    except Exception as e:
        print(f"❌ Error processing webhook: {e}")
        return JSONResponse(
            content={"error": str(e)},
            status_code=400
        )

@app.get("/")
async def root():
    """Root endpoint with instructions."""
    return {
        "message": "Webhook Test Server",
        "webhook_endpoint": "/webhook",
        "usage": "Use http://localhost:8001/webhook as webhook_url in transcription requests"
    }

if __name__ == "__main__":
    print("🚀 Starting webhook test server...")
    print("📡 Use http://localhost:8001/webhook as your webhook_url")
    print("🔍 Webhook results will be saved as JSON files and logged to console")
    uvicorn.run(app, host="0.0.0.0", port=8001)