#!/usr/bin/env python3
"""
Model Downloader Script for Real-time Video Processing

This script downloads and sets up the ML models required for advanced video processing.
"""

import os
import sys
import shutil
import urllib.request
import logging
import zipfile
import tarfile
from pathlib import Path

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ModelDownloader")

MODELS = {
    "yolov8": {
        "url": "https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt",
        "filename": "yolov8n.pt",
        "target_dir": "models",
        "description": "YOLOv8 Nano - Object Detection Model"
    },
    "face_recognition": {
        "url": "https://github.com/ageitgey/face_recognition_models/archive/refs/tags/v0.3.0.zip",
        "filename": "face_recognition_models.zip",
        "extract": True,
        "target_dir": "models/face_recognition",
        "description": "Face Recognition Models"
    },
    "haarcascades": {
        "url": "https://github.com/opencv/opencv/archive/refs/tags/4.7.0.zip",
        "filename": "opencv.zip",
        "extract": True,
        "extract_dir": "opencv-4.7.0/data/haarcascades",
        "target_dir": "models/haarcascades",
        "description": "OpenCV Haar Cascades"
    }
}

def create_directory(directory):
    """Create directory if it doesn't exist"""
    os.makedirs(directory, exist_ok=True)
    logger.info(f"Directory ready: {directory}")

def download_file(url, filename):
    """Download file from URL"""
    try:
        logger.info(f"Downloading {filename} from {url}")
        urllib.request.urlretrieve(url, filename)
        logger.info(f"Downloaded {filename} successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to download {filename}: {e}")
        return False

def extract_zip(filename, extract_dir=None, target_dir=None):
    """Extract ZIP file"""
    try:
        logger.info(f"Extracting {filename}")
        with zipfile.ZipFile(filename, 'r') as zip_ref:
            if extract_dir:
                # Extract specific directory
                members = [m for m in zip_ref.namelist() if m.startswith(extract_dir)]
                zip_ref.extractall("temp", members=members)
                
                # Move to target directory
                if target_dir:
                    source_dir = os.path.join("temp", extract_dir)
                    if os.path.exists(source_dir):
                        create_directory(target_dir)
                        for item in os.listdir(source_dir):
                            source_item = os.path.join(source_dir, item)
                            target_item = os.path.join(target_dir, item)
                            shutil.copy2(source_item, target_item)
                            logger.info(f"Copied {item} to {target_dir}")
            else:
                # Extract everything
                target = target_dir if target_dir else "."
                zip_ref.extractall(target)
            
            logger.info(f"Extracted {filename} successfully")
            return True
    except Exception as e:
        logger.error(f"Failed to extract {filename}: {e}")
        return False
    finally:
        # Clean up temp directory
        if os.path.exists("temp"):
            shutil.rmtree("temp")

def download_models():
    """Download and setup all models"""
    success_count = 0
    total_models = len(MODELS)
    
    for name, model in MODELS.items():
        logger.info(f"Processing {name}: {model['description']}")
        
        # Create target directory
        create_directory(model["target_dir"])
        
        # Set download path
        download_path = os.path.join("downloads", model["filename"])
        create_directory("downloads")
        
        # Download file
        if download_file(model["url"], download_path):
            
            # Extract if needed
            if model.get("extract", False):
                extract_dir = model.get("extract_dir")
                extract_zip(download_path, extract_dir, model["target_dir"])
            else:
                # Just copy the file to the target directory
                target_file = os.path.join(model["target_dir"], model["filename"])
                shutil.copy2(download_path, target_file)
                logger.info(f"Copied {model['filename']} to {model['target_dir']}")
            
            success_count += 1
    
    logger.info(f"Downloaded {success_count}/{total_models} models successfully")
    return success_count == total_models

def main():
    print("=" * 70)
    print("Real-time Video Processing - Model Downloader")
    print("=" * 70)
    print(f"This script will download ML models for advanced video processing.")
    print(f"Models will be stored in the project's 'models' directory.\n")
    
    try:
        if download_models():
            print("\n✅ All models downloaded and set up successfully!")
            return 0
        else:
            print("\n❌ Some models failed to download. Check logs for details.")
            return 1
    except KeyboardInterrupt:
        print("\n\nModel download canceled by user.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
