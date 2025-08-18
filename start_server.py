#!/usr/bin/env python3
"""
Startup script for Modal WhisperX API
Handles Python version compatibility and provides clear error messages.
"""

import sys
import subprocess
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    if version.major != 3:
        print("❌ Error: Python 3 is required")
        return False
    
    if version.minor >= 13:
        print("⚠️  Warning: Python 3.13+ may have compatibility issues with older FastAPI versions")
        print("   Recommended: Use Python 3.11 or 3.12 for best compatibility")
        print("   Continuing anyway...")
    
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} detected")
    return True

def check_dependencies():
    """Check if required dependencies are installed"""
    required_packages = ['fastapi', 'uvicorn', 'requests']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package} is installed")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package} is missing")
    
    if missing_packages:
        print(f"\n❌ Missing packages: {', '.join(missing_packages)}")
        print("Please install dependencies with: pip install -r requirements.txt")
        return False
    
    return True

def check_modal_setup():
    """Check if Modal is set up and app is deployed"""
    print("\n🔍 Checking Modal setup...")
    
    try:
        import modal
        print("✅ Modal package is installed")
        
        # Try to check if the app exists
        modal_app_name = os.getenv("MODAL_APP_NAME", "example-whisperx-transcribe")
        
        try:
            # This will work if Modal is authenticated and app exists
            modal_app = modal.App.lookup(modal_app_name)
            print(f"✅ Modal app '{modal_app_name}' found")
            return True
        except Exception as e:
            print(f"⚠️  Modal app '{modal_app_name}' not found or not accessible")
            print("\n🚨 IMPORTANT: Transcription will not work without Modal deployment!")
            print("\n📋 To fix this:")
            print("   1. Install Modal CLI: pip install modal")
            print("   2. Authenticate: modal token new")
            print("   3. Deploy app: modal deploy whisperx_transcribe.py")
            print("   4. Verify: modal app list (app will show as deployed, not running)")
            print("\n📖 See README.md Troubleshooting section for details")
            print("\n⚡ Server will start anyway, but transcription endpoints will fail")
            return False
            
    except ImportError:
        print("❌ Modal package not installed")
        print("💡 Install with: pip install modal")
        return False

def start_server():
    """Start the FastAPI server"""
    # Get host and port from environment variables
    host = os.getenv("HOST", "0.0.0.0")
    port = os.getenv("PORT", "8000")
    
    print("\n🚀 Starting Modal WhisperX API server...")
    print(f"📍 Server will be available at: http://localhost:{port}")
    print(f"📖 API documentation at: http://localhost:{port}/docs")
    print(f"❤️  Health check at: http://localhost:{port}/health")
    print("\n⏹️  Press Ctrl+C to stop the server\n")
    
    try:
        # Use subprocess to avoid Python version compatibility issues
        cmd = [sys.executable, "-m", "uvicorn", "app:app", "--host", host, "--port", port, "--reload"]
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped by user")
    except Exception as e:
        print(f"\n❌ Error starting server: {e}")
        print("\n💡 Troubleshooting tips:")
        print("   1. Make sure all dependencies are installed: pip install -r requirements.txt")
        print("   2. Try using Python 3.11 or 3.12 if you're using Python 3.13+")
        print(f"   3. Check if port {port} is already in use")
        print("   4. Check your .env file for correct HOST and PORT settings")
        return False
    
    return True

def main():
    """Main startup function"""
    print("Modal WhisperX API Server")
    print("=" * 40)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    print("\n📦 Checking dependencies...")
    if not check_dependencies():
        sys.exit(1)
    
    # Check Modal setup (non-blocking)
    check_modal_setup()
    
    # Start the server
    start_server()

if __name__ == "__main__":
    main()