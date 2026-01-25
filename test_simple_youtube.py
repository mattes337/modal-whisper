#!/usr/bin/env python3
"""
Simple YouTube API test with a different video to avoid bot detection
"""

import requests
import json

def test_youtube_api():
    """Test the YouTube transcription API with a simple video"""
    
    # Test with a different video that might not trigger bot detection
    test_urls = [
        "https://www.youtube.com/watch?v=jNQXAC9IVRw",  # "Me at the zoo" - first YouTube video
        "https://www.youtube.com/watch?v=9bZkp7q19f0",  # PSY - Gangnam Style
    ]
    
    base_url = "http://localhost:8000"
    
    print("YouTube Transcription API Simple Test")
    print("=" * 50)
    
    # Test health check first
    print("\n1. Health Check")
    print("-" * 20)
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        if response.status_code == 200:
            health_data = response.json()
            print(f"✅ Health check passed: {response.status_code}")
            print(f"YouTube Modal Connected: {health_data.get('youtube_modal_connected', 'Unknown')}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return
    
    # Test transcription with different videos
    for i, url in enumerate(test_urls, 1):
        print(f"\n{i + 1}. Testing Video: {url}")
        print("-" * 50)
        
        try:
            payload = {
                "url": url,
                "download_video": False
            }
            
            response = requests.post(
                f"{base_url}/v1/youtube/transcribe",
                json=payload,
                timeout=60
            )
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    print("✅ Success!")
                    print(f"Title: {data.get('metadata', {}).get('title', 'N/A')}")
                    print(f"Duration: {data.get('metadata', {}).get('duration', 'N/A')} seconds")
                    
                    transcript = data.get('transcript', {})
                    if 'error' not in transcript:
                        print(f"Transcript Language: {transcript.get('language', 'N/A')}")
                        entries = transcript.get('entries', [])
                        print(f"Transcript Entries: {len(entries)}")
                        if entries:
                            print(f"First Entry: {entries[0].get('text', 'N/A')[:100]}...")
                    else:
                        print(f"Transcript Error: {transcript.get('error')}")
                    
                    # Check available languages
                    languages = data.get('transcript_languages', [])
                    print(f"Available Languages: {len(languages)}")
                    if languages:
                        lang_codes = [lang.get('language_code') for lang in languages[:3]]
                        print(f"Language Codes: {', '.join(lang_codes)}")
                    
                    break  # Success, no need to try other videos
                else:
                    print(f"❌ API returned success=false")
                    print(f"Response: {json.dumps(data, indent=2)[:500]}...")
            else:
                print(f"❌ Error: {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"Error Detail: {error_data}")
                except:
                    print(f"Error Text: {response.text[:200]}...")
                    
        except Exception as e:
            print(f"❌ Request failed: {e}")
    
    print("\n" + "=" * 50)
    print("Simple test completed!")

if __name__ == "__main__":
    test_youtube_api()