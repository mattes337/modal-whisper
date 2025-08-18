#!/usr/bin/env python3
"""
Test script for the Modal WhisperX API
This script tests the API endpoints without requiring Docker or Modal setup.
"""

import requests
import json
import io
import wave
import struct
import math

def create_test_audio():
    """Create a simple test audio file in memory"""
    # Create a simple sine wave audio file
    sample_rate = 16000
    duration = 2  # seconds
    frequency = 440  # Hz (A4 note)
    
    # Generate sine wave samples
    samples = []
    for i in range(int(sample_rate * duration)):
        t = i / sample_rate
        sample = int(32767 * math.sin(2 * math.pi * frequency * t))
        samples.append(sample)
    
    # Create WAV file in memory
    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, 'wb') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(struct.pack('<' + 'h' * len(samples), *samples))
    
    wav_buffer.seek(0)
    return wav_buffer.getvalue()

def test_health_endpoint(base_url):
    """Test the health check endpoint"""
    print("Testing health endpoint...")
    try:
        response = requests.get(f"{base_url}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Health check failed: {e}")
        return False

def test_root_endpoint(base_url):
    """Test the root endpoint"""
    print("\nTesting root endpoint...")
    try:
        response = requests.get(base_url)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Root endpoint test failed: {e}")
        return False

def test_transcription_json(base_url):
    """Test transcription with JSON format"""
    print("\nTesting transcription (JSON format)...")
    try:
        audio_data = create_test_audio()
        
        files = {'file': ('test.wav', audio_data, 'audio/wav')}
        data = {'model': 'whisper-1', 'response_format': 'json'}
        
        response = requests.post(f"{base_url}/v1/audio/transcriptions", files=files, data=data)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"JSON transcription test failed: {e}")
        return False

def test_transcription_verbose(base_url):
    """Test transcription with verbose JSON format"""
    print("\nTesting transcription (Verbose JSON format)...")
    try:
        audio_data = create_test_audio()
        
        files = {'file': ('test.wav', audio_data, 'audio/wav')}
        data = {'model': 'whisper-1', 'response_format': 'verbose_json'}
        
        response = requests.post(f"{base_url}/v1/audio/transcriptions", files=files, data=data)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Verbose JSON transcription test failed: {e}")
        return False

def main():
    """Run all tests"""
    base_url = "http://localhost:8000"
    
    print("Modal WhisperX API Test Suite")
    print("=" * 40)
    print(f"Testing API at: {base_url}")
    print("Note: Make sure the API server is running before running this test.")
    print()
    
    tests = [
        test_health_endpoint,
        test_root_endpoint,
        test_transcription_json,
        test_transcription_verbose
    ]
    
    results = []
    for test in tests:
        try:
            result = test(base_url)
            results.append(result)
        except Exception as e:
            print(f"Test failed with exception: {e}")
            results.append(False)
    
    print("\n" + "=" * 40)
    print("Test Results:")
    print(f"Health Check: {'PASS' if results[0] else 'FAIL'}")
    print(f"Root Endpoint: {'PASS' if results[1] else 'FAIL'}")
    print(f"JSON Transcription: {'PASS' if results[2] else 'FAIL'}")
    print(f"Verbose JSON Transcription: {'PASS' if results[3] else 'FAIL'}")
    
    passed = sum(results)
    total = len(results)
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The API is working correctly.")
    else:
        print("❌ Some tests failed. Check the server logs for details.")

if __name__ == "__main__":
    main()