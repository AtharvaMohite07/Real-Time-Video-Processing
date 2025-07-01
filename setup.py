#!/usr/bin/env python3
"""
Setup script for Real-time Video Processing project
This script will set up the project environment and download required models
"""

import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path

def print_header(text):
    """Print a formatted header"""
    print("\n" + "=" * 70)
    print(f"{text}")
    print("=" * 70)

def run_command(command, description):
    """Run a command and return success status"""
    print(f"\n➡️ {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, text=True, capture_output=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        print(f"Error output: {e.stderr}")
        return False

def check_prerequisites():
    """Check for required tools and libraries"""
    print_header("Checking Prerequisites")
    
    # Check Python version
    python_version = platform.python_version()
    print(f"Python version: {python_version}")
    if int(python_version.split('.')[0]) < 3 or int(python_version.split('.')[1]) < 9:
        print("❌ Python 3.9+ is required")
        return False
    
    # Check for pip
    if not run_command("pip --version", "Checking pip"):
        return False
    
    # Check for virtualenv
    venv_exists = run_command("python -m venv --help", "Checking venv support")
    if not venv_exists:
        print("Installing virtualenv...")
        run_command("pip install virtualenv", "Installing virtualenv")
    
    # Check Docker if available (optional)
    run_command("docker --version", "Checking Docker")
    run_command("docker-compose --version", "Checking Docker Compose")
    
    print("\n✅ All critical prerequisites satisfied")
    return True

def setup_virtual_environment():
    """Set up a Python virtual environment"""
    print_header("Setting Up Virtual Environment")
    
    # Create virtual environment if it doesn't exist
    venv_dir = "venv"
    if os.path.exists(venv_dir):
        print(f"Virtual environment already exists at {venv_dir}")
    else:
        if not run_command(f"python -m venv {venv_dir}", "Creating virtual environment"):
            return False
    
    # Determine activation script based on platform
    if platform.system() == "Windows":
        activate_script = f"{venv_dir}\\Scripts\\activate"
    else:
        activate_script = f"source {venv_dir}/bin/activate"
    
    print(f"\n🔍 To activate the virtual environment, run: {activate_script}")
    return True

def install_requirements():
    """Install required packages"""
    print_header("Installing Dependencies")
    
    # Determine pip command based on virtual environment
    venv_dir = "venv"
    if os.path.exists(venv_dir):
        if platform.system() == "Windows":
            pip_cmd = f"{venv_dir}\\Scripts\\pip"
        else:
            pip_cmd = f"{venv_dir}/bin/pip"
    else:
        pip_cmd = "pip"
    
    # Install requirements
    return run_command(f"{pip_cmd} install -r requirements.txt", "Installing requirements")

def setup_project_directories():
    """Set up project directories"""
    print_header("Setting Up Project Structure")
    
    # List of directories to create
    directories = [
        "models",
        "models/yolo",
        "models/face_recognition",
        "saved_frames",
        "uploads",
        "logs",
        "data"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✅ Created directory: {directory}")
    
    return True

def download_models():
    """Download required ML models"""
    print_header("Downloading ML Models")
    
    return run_command("python download_models.py", "Downloading ML models")

def configure_environment():
    """Configure environment settings"""
    print_header("Configuring Environment")
    
    # Create .env file if it doesn't exist
    if not os.path.exists(".env"):
        if os.path.exists(".env.example"):
            shutil.copy(".env.example", ".env")
            print("✅ Created .env file from .env.example")
        else:
            with open(".env", "w") as f:
                f.write("# Application Settings\n")
                f.write("FLASK_ENV=development\n")
                f.write("FLASK_DEBUG=True\n")
                f.write(f"SECRET_KEY={os.urandom(24).hex()}\n\n")
                
                f.write("# AWS Configuration\n")
                f.write("AWS_ACCESS_KEY_ID=\n")
                f.write("AWS_SECRET_ACCESS_KEY=\n")
                f.write("AWS_REGION=us-east-1\n")
                f.write("S3_BUCKET_NAME=video-processing-bucket\n")
            
            print("✅ Created default .env file")
    else:
        print("ℹ️ .env file already exists")
    
    print("\n⚠️ Remember to set your AWS credentials in the .env file if using cloud features")
    return True

def main():
    """Main setup function"""
    print_header("Real-time Video Processing - Setup")
    print("\nThis script will set up your environment for the Real-time Video Processing project.")
    
    steps = [
        {"function": check_prerequisites, "name": "Check Prerequisites"},
        {"function": setup_project_directories, "name": "Setup Project Structure"},
        {"function": setup_virtual_environment, "name": "Setup Virtual Environment"},
        {"function": install_requirements, "name": "Install Requirements"},
        {"function": configure_environment, "name": "Configure Environment"},
        {"function": download_models, "name": "Download ML Models"}
    ]
    
    success_count = 0
    for step in steps:
        if step["function"]():
            success_count += 1
        else:
            print(f"\n⚠️ {step['name']} step failed. Continuing with next steps...")
    
    print_header("Setup Summary")
    print(f"Completed {success_count}/{len(steps)} steps successfully")
    
    if success_count == len(steps):
        print("\n🎉 Setup completed successfully! You can now run the application:")
        if platform.system() == "Windows":
            print("   venv\\Scripts\\activate")
        else:
            print("   source venv/bin/activate")
        print("   python app.py")
    else:
        print("\n⚠️ Setup completed with some issues. Please review the output above.")
    
    return 0 if success_count == len(steps) else 1

if __name__ == "__main__":
    sys.exit(main())
