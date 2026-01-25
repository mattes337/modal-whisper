#!/usr/bin/env python3
"""
Test script for the updated YouTube transcribe API with browser support
"""

import requests
import json
import sys

def test_youtube_api():
    """Test the YouTube API endpoints"""
    
    # API endpoints
    post_url = "https://mattes337--modal-youtube-transcribe-youtube-transcribe-api.modal.run"
    get_url = "https://mattes337--modal-youtube-transcribe-youtube-transcribe-api-get.modal.run"
    
    # Test videos - trying different ones
    test_videos = [
        "https://www.youtube.com/watch?v=jNQXAC9IVRw",  # "Me at the zoo" - first YouTube video
        "https://www.youtube.com/watch?v=9bZkp7q19f0",  # PSY - GANGNAM STYLE
        "https://www.youtube.com/watch?v=kJQP7kiw5Fk",  # Luis Fonsi - Despacito
    ]
    
    print("Testing YouTube Transcribe API with Browser Support")
    print("=" * 60)
    
    for i, video_url in enumerate(test_videos, 1):
        print(f"\nTest {i}: {video_url}")
        print("-" * 40)
        
        # Test POST endpoint
        try:
            print("Testing POST endpoint...")
            response = requests.post(
                post_url,
                json={"url": video_url},
                timeout=120  # 2 minutes timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    print(f"✅ SUCCESS with method: {result.get('method', 'unknown')}")
                    print(f"   Title: {result['metadata']['title'][:50]}...")
                    print(f"   Duration: {result['metadata']['duration']} seconds")
                    print(f"   Formats available: {result['total_formats']}")
                    
                    if result.get('transcript') and not result['transcript'].get('error'):
                        print(f"   Transcript: Available in {result['transcript']['language']}")
                        print(f"   Transcript entries: {len(result['transcript']['entries'])}")
                    else:
                        print(f"   Transcript: {result.get('transcript', {}).get('error', 'Not available')}")
                    
                    # Success! No need to test other videos
                    return True
                else:
                    print(f"❌ FAILED: {result.get('error', 'Unknown error')}")
            else:
                print(f"❌ HTTP Error: {response.status_code}")
                print(f"   Response: {response.text[:200]}...")
                
        except requests.exceptions.Timeout:
            print("❌ TIMEOUT: Request took too long")
        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
    
    print("\n" + "=" * 60)
    print("All test videos failed. YouTube restrictions are very aggressive.")
    return False

if __name__ == "__main__":
    success = test_youtube_api()
    sys.exit(0 if success else 1)