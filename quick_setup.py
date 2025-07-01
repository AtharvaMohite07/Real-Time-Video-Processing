#!/usr/bin/env python3
"""
Quick Setup Script for Real-time Video Processing Platform
This script will set up the environment and download necessary models
"""

import os
import sys
import subprocess
import urllib.request
import zipfile
import json
from pathlib import Path

def print_banner():
    """Print setup banner"""
    print("=" * 60)
    print("🎥 Real-time Video Processing Platform Setup")
    print("=" * 60)
    print()

def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 9):
        print("❌ Python 3.9+ is required. Current version:", sys.version)
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
    return True
from pathlib import Path

def main():
    print("🎥 Real-time Video Processing Platform - Quick Setup")
    print("=" * 60)
    
    # Check Python version
    if sys.version_info < (3, 9):
        print("❌ Python 3.9+ required")
        return 1
    
    print("✅ Python version OK")
    
    # Create virtual environment if it doesn't exist
    if not Path("venv").exists():
        print("📦 Creating virtual environment...")
        subprocess.run([sys.executable, "-m", "venv", "venv"])
        print("✅ Virtual environment created")
    
    # Determine pip path
    if os.name == 'nt':  # Windows
        pip_cmd = "venv\\Scripts\\pip"
        activate_cmd = "venv\\Scripts\\activate"
    else:  # Unix-like
        pip_cmd = "venv/bin/pip"
        activate_cmd = "source venv/bin/activate"
    
    # Install dependencies
    if Path("requirements.txt").exists():
        print("📥 Installing dependencies...")
        result = subprocess.run([pip_cmd, "install", "-r", "requirements.txt"])
        if result.returncode == 0:
            print("✅ Dependencies installed")
        else:
            print("❌ Failed to install dependencies")
            return 1
    
    # Create .env file if it doesn't exist
    if not Path(".env").exists():
        if Path(".env.example").exists():
            shutil.copy(".env.example", ".env")
            print("✅ .env file created from .env.example")
        else:
            # Create basic .env file
            with open(".env", "w") as f:
                f.write("""# Real-time Video Processing Configuration
AWS_ACCESS_KEY_ID=your_aws_access_key_here
AWS_SECRET_ACCESS_KEY=your_aws_secret_key_here
AWS_REGION=us-east-1
S3_BUCKET_NAME=video-processing-bucket
KINESIS_STREAM_NAME=video-analytics-stream
FLASK_ENV=development
FLASK_DEBUG=True
""")
            print("✅ Basic .env file created")
    
    # Create necessary directories
    directories = ["models", "saved_frames", "uploads", "processed", "logs"]
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
    print("✅ Project directories created")
    
    # Print next steps
    print("\n🎉 Setup completed!")
    print(f"\n📋 Next steps:")
    print(f"1. Activate virtual environment: {activate_cmd}")
    print(f"2. Edit .env file with your AWS credentials (optional)")
    print(f"3. Run the application: python app.py")
    print(f"4. Open http://localhost:5000 in your browser")
    
    if shutil.which("docker"):
        print(f"\n🐳 Alternative - Use Docker:")
        print(f"   docker-compose up --build")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
