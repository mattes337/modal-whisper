#!/usr/bin/env python3
"""
Test script for YouTube transcription API

This script tests the YouTube transcription endpoint with various scenarios:
1. Basic metadata and transcript extraction
2. Video download (opt-in)
3. Error handling for invalid URLs
"""

import requests
import json
import sys
import os
from typing import Dict, Any

# Default server configuration
SERVER_URL = os.getenv("SERVER_URL", "http://localhost:8000")

def test_youtube_transcribe(url: str, download_video: bool = False) -> Dict[str, Any]:
    """
    Test the YouTube transcription endpoint
    
    Args:
        url: YouTube URL to test
        download_video: Whether to download the video file
        
    Returns:
        API response as dictionary
    """
    endpoint = f"{SERVER_URL}/v1/youtube/transcribe"
    
    payload = {
        "url": url,
        "download_video": download_video
    }
    
    try:
        print(f"Testing YouTube transcription for: {url}")
        print(f"Download video: {download_video}")
        print(f"Endpoint: {endpoint}")
        print("-" * 50)
        
        response = requests.post(endpoint, json=payload, timeout=60)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Success!")
            
            # Print summary information
            if "metadata" in result:
                metadata = result["metadata"]
                print(f"Title: {metadata.get('title', 'N/A')}")
                print(f"Duration: {metadata.get('duration', 0)} seconds")
                print(f"Uploader: {metadata.get('uploader', 'N/A')}")
                print(f"View Count: {metadata.get('view_count', 0):,}")
            
            if "transcript" in result and result["transcript"]:
                transcript = result["transcript"]
                if "entries" in transcript:
                    print(f"Transcript Language: {transcript.get('language', 'N/A')}")
                    print(f"Transcript Entries: {len(transcript['entries'])}")
                    # Show first few transcript entries
                    for i, entry in enumerate(transcript["entries"][:3]):
                        print(f"  [{entry.get('start', 0):.1f}s] {entry.get('text', '')}")
                    if len(transcript["entries"]) > 3:
                        print(f"  ... and {len(transcript['entries']) - 3} more entries")
                else:
                    print(f"Transcript Error: {transcript.get('error', 'Unknown error')}")
            
            if "video_downloaded" in result and result["video_downloaded"]:
                if "video_size_bytes" in result:
                    size_mb = result["video_size_bytes"] / (1024 * 1024)
                    print(f"Video Downloaded: {size_mb:.2f} MB")
                elif "video_data" in result and isinstance(result["video_data"], dict):
                    print(f"Video Download Error: {result['video_data'].get('error', 'Unknown error')}")
            
            print(f"Total Formats Available: {result.get('total_formats', 0)}")
            print(f"Transcript Languages Available: {len(result.get('transcript_languages', []))}")
            
            return result
        else:
            print(f"❌ Error: {response.status_code}")
            try:
                error_detail = response.json()
                print(f"Error Detail: {error_detail}")
            except:
                print(f"Error Text: {response.text}")
            return {"error": f"HTTP {response.status_code}"}
            
    except requests.exceptions.Timeout:
        print("❌ Request timed out")
        return {"error": "Request timeout"}
    except requests.exceptions.ConnectionError:
        print(f"❌ Could not connect to server at {SERVER_URL}")
        print("Make sure the server is running with: python app.py")
        return {"error": "Connection error"}
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return {"error": str(e)}

def test_health_check():
    """
    Test the health check endpoint to verify YouTube Modal connection
    """
    endpoint = f"{SERVER_URL}/health"
    
    try:
        print("Testing health check...")
        response = requests.get(endpoint, timeout=10)
        
        if response.status_code == 200:
            health = response.json()
            print(f"✅ Server Status: {health.get('status', 'unknown')}")
            print(f"Modal Connected: {health.get('modal_connected', False)}")
            print(f"YouTube Modal Connected: {health.get('youtube_modal_connected', False)}")
            
            if not health.get('youtube_modal_connected', False):
                print("⚠️  YouTube Modal app is not connected. Make sure it's deployed.")
                return False
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def main():
    """
    Main test function
    """
    print("YouTube Transcription API Test")
    print("=" * 50)
    
    # Test health check first
    print("\n1. Health Check")
    print("-" * 20)
    if not test_health_check():
        print("\n❌ Health check failed. Exiting.")
        sys.exit(1)
    
    # Test cases
    test_cases = [
        {
            "name": "Basic YouTube Video (Rick Roll)",
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "download_video": False
        },
        {
            "name": "Short YouTube URL",
            "url": "https://youtu.be/dQw4w9WgXcQ",
            "download_video": False
        },
        {
            "name": "Video ID Only",
            "url": "dQw4w9WgXcQ",
            "download_video": False
        },
        {
            "name": "Invalid URL",
            "url": "https://invalid-url.com/video",
            "download_video": False
        }
    ]
    
    # Add video download test if requested
    if len(sys.argv) > 1 and sys.argv[1] == "--download":
        test_cases.append({
            "name": "Video Download Test (Rick Roll)",
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "download_video": True
        })
        print("\n⚠️  Video download test enabled. This may take longer and use more bandwidth.")
    
    # Run tests
    for i, test_case in enumerate(test_cases, 2):
        print(f"\n{i}. {test_case['name']}")
        print("-" * 20)
        
        result = test_youtube_transcribe(
            test_case["url"], 
            test_case["download_video"]
        )
        
        print()
    
    print("\n" + "=" * 50)
    print("Test completed!")
    print("\nTo test video download, run: python test_youtube_api.py --download")
    print("Note: Video download tests use more bandwidth and take longer.")

if __name__ == "__main__":
    main()