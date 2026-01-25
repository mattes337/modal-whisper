#!/usr/bin/env python3
"""
Deployment script for Modal apps

This script deploys both the WhisperX transcription app and the YouTube transcription app to Modal.
It provides a convenient way to deploy both services with proper error handling and verification.
"""

import subprocess
import sys
import os
from typing import List, Tuple

def run_command(command: List[str], description: str) -> Tuple[bool, str]:
    """
    Run a command and return success status and output
    
    Args:
        command: Command to run as list of strings
        description: Description of what the command does
        
    Returns:
        Tuple of (success, output)
    """
    print(f"\n🔄 {description}...")
    print(f"Running: {' '.join(command)}")
    
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode == 0:
            print(f"✅ {description} completed successfully")
            if result.stdout.strip():
                print(f"Output: {result.stdout.strip()}")
            return True, result.stdout
        else:
            print(f"❌ {description} failed")
            print(f"Error: {result.stderr.strip()}")
            return False, result.stderr
            
    except subprocess.TimeoutExpired:
        print(f"❌ {description} timed out after 5 minutes")
        return False, "Command timed out"
    except Exception as e:
        print(f"❌ {description} failed with exception: {e}")
        return False, str(e)

def check_modal_auth() -> bool:
    """
    Check if Modal is properly authenticated
    
    Returns:
        True if authenticated, False otherwise
    """
    success, output = run_command(["modal", "token", "current"], "Checking Modal authentication")
    return success

def deploy_app(app_file: str, app_name: str) -> bool:
    """
    Deploy a Modal app
    
    Args:
        app_file: Path to the app file
        app_name: Name of the app for display
        
    Returns:
        True if deployment succeeded, False otherwise
    """
    if not os.path.exists(app_file):
        print(f"❌ App file not found: {app_file}")
        return False
    
    success, output = run_command(
        ["modal", "deploy", app_file],
        f"Deploying {app_name}"
    )
    
    return success

def list_apps() -> bool:
    """
    List deployed Modal apps to verify deployment
    
    Returns:
        True if command succeeded, False otherwise
    """
    success, output = run_command(["modal", "app", "list"], "Listing deployed apps")
    
    if success:
        print("\n📋 Deployed Modal Apps:")
        print(output)
        
        # Check if our apps are in the list
        apps_found = []
        if "modal-whisper-transcribe" in output:
            apps_found.append("modal-whisper-transcribe")
        if "modal-youtube-transcribe" in output:
            apps_found.append("modal-youtube-transcribe")
        
        if len(apps_found) == 2:
            print("\n✅ Both apps are successfully deployed!")
        elif len(apps_found) == 1:
            print(f"\n⚠️  Only {apps_found[0]} is deployed. Check the other deployment.")
        else:
            print("\n❌ Neither app appears to be deployed successfully.")
    
    return success

def main():
    """
    Main deployment function
    """
    print("Modal Apps Deployment Script")
    print("=" * 40)
    print("This script will deploy both Modal apps:")
    print("1. modal-whisper-transcribe (WhisperX transcription)")
    print("2. modal-youtube-transcribe (YouTube transcription)")
    print()
    
    # Check if Modal CLI is available
    try:
        subprocess.run(["modal", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Modal CLI not found. Please install it first:")
        print("   pip install modal")
        sys.exit(1)
    
    # Check authentication
    if not check_modal_auth():
        print("\n❌ Modal authentication failed.")
        print("Please authenticate with Modal first:")
        print("   modal token new")
        sys.exit(1)
    
    # Deploy apps
    apps_to_deploy = [
        ("modal_whisper_transcribe.py", "WhisperX Transcription App"),
        ("modal_youtube_transcribe.py", "YouTube Transcription App")
    ]
    
    deployment_results = []
    
    for app_file, app_name in apps_to_deploy:
        success = deploy_app(app_file, app_name)
        deployment_results.append((app_name, success))
        
        if not success:
            print(f"\n⚠️  {app_name} deployment failed. Continuing with next app...")
    
    # Summary
    print("\n" + "=" * 40)
    print("Deployment Summary:")
    
    all_successful = True
    for app_name, success in deployment_results:
        status = "✅ Success" if success else "❌ Failed"
        print(f"  {app_name}: {status}")
        if not success:
            all_successful = False
    
    # List apps to verify
    print("\n" + "-" * 40)
    list_apps()
    
    # Final status
    if all_successful:
        print("\n🎉 All apps deployed successfully!")
        print("\nNext steps:")
        print("1. Start your FastAPI server: python app.py")
        print("2. Test the endpoints:")
        print("   - Audio transcription: POST /v1/audio/transcriptions")
        print("   - YouTube transcription: POST /v1/youtube/transcribe")
        print("3. Run tests: python test_youtube_api.py")
    else:
        print("\n⚠️  Some deployments failed. Please check the errors above.")
        print("You can retry individual deployments with:")
        print("   modal deploy <app_file>")
        sys.exit(1)

if __name__ == "__main__":
    main()