#!/usr/bin/env python3
"""
Download and synchronize ML models from cloud storage (AWS S3)
"""

import os
import sys
import boto3
import logging
import botocore
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ModelSync")

# Default paths
DEFAULT_MODEL_DIR = "models"
DEFAULT_BUCKET = os.getenv("S3_BUCKET_NAME", "video-processing-models")
DEFAULT_PREFIX = "models/"

def setup_s3_client():
    """Set up and return S3 client"""
    try:
        s3_client = boto3.client(
            's3',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_REGION', 'us-east-1')
        )
        return s3_client
    except Exception as e:
        logger.error(f"Failed to set up S3 client: {e}")
        return None

def download_models_from_s3(bucket_name=DEFAULT_BUCKET, 
                          prefix=DEFAULT_PREFIX, 
                          target_dir=DEFAULT_MODEL_DIR):
    """Download ML models from S3 bucket"""
    s3_client = setup_s3_client()
    if not s3_client:
        logger.error("S3 client setup failed. Cannot download models.")
        return False
    
    try:
        # Ensure target directory exists
        os.makedirs(target_dir, exist_ok=True)
        
        # List objects in the bucket with given prefix
        logger.info(f"Listing objects in s3://{bucket_name}/{prefix}")
        response = s3_client.list_objects_v2(
            Bucket=bucket_name,
            Prefix=prefix
        )
        
        if 'Contents' not in response:
            logger.warning(f"No objects found in s3://{bucket_name}/{prefix}")
            return False
        
        # Download each object
        download_count = 0
        for obj in response['Contents']:
            key = obj['Key']
            file_name = os.path.basename(key)
            
            # Skip empty directory markers
            if not file_name:
                continue
            
            # Create subdirectory structure if needed
            rel_path = key[len(prefix):] if key.startswith(prefix) else key
            target_path = os.path.join(target_dir, rel_path)
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            
            # Download file
            logger.info(f"Downloading {key} to {target_path}")
            s3_client.download_file(bucket_name, key, target_path)
            download_count += 1
        
        logger.info(f"Successfully downloaded {download_count} model files")
        return True
        
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == '404':
            logger.error(f"Bucket {bucket_name} not found")
        else:
            logger.error(f"S3 error: {e}")
        return False
    except Exception as e:
        logger.error(f"Error downloading models: {e}")
        return False

def upload_models_to_s3(bucket_name=DEFAULT_BUCKET, 
                       prefix=DEFAULT_PREFIX, 
                       source_dir=DEFAULT_MODEL_DIR):
    """Upload local ML models to S3 bucket"""
    s3_client = setup_s3_client()
    if not s3_client:
        logger.error("S3 client setup failed. Cannot upload models.")
        return False
    
    try:
        if not os.path.exists(source_dir):
            logger.error(f"Source directory {source_dir} does not exist")
            return False
        
        upload_count = 0
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                local_path = os.path.join(root, file)
                rel_path = os.path.relpath(local_path, source_dir)
                s3_key = prefix + rel_path.replace(os.sep, '/')
                
                logger.info(f"Uploading {local_path} to s3://{bucket_name}/{s3_key}")
                s3_client.upload_file(local_path, bucket_name, s3_key)
                upload_count += 1
        
        logger.info(f"Successfully uploaded {upload_count} model files")
        return True
        
    except Exception as e:
        logger.error(f"Error uploading models: {e}")
        return False

def check_model_versions(bucket_name=DEFAULT_BUCKET, prefix=DEFAULT_PREFIX):
    """Check for model version updates in S3"""
    s3_client = setup_s3_client()
    if not s3_client:
        return {}
    
    try:
        response = s3_client.list_objects_v2(
            Bucket=bucket_name,
            Prefix=prefix
        )
        
        models = {}
        if 'Contents' in response:
            for obj in response['Contents']:
                key = obj['Key']
                file_name = os.path.basename(key)
                if file_name:
                    models[file_name] = {
                        'size': obj['Size'],
                        'last_modified': obj['LastModified'].isoformat(),
                        's3_key': key
                    }
        
        return models
        
    except Exception as e:
        logger.error(f"Error checking model versions: {e}")
        return {}

def sync_models(bucket_name=DEFAULT_BUCKET, 
                prefix=DEFAULT_PREFIX, 
                target_dir=DEFAULT_MODEL_DIR):
    """Synchronize models - download only if newer or missing"""
    logger.info("Starting model synchronization...")
    
    # Check what's available in S3
    remote_models = check_model_versions(bucket_name, prefix)
    if not remote_models:
        logger.warning("No models found in S3 or connection failed")
        return False
    
    # Ensure target directory exists
    os.makedirs(target_dir, exist_ok=True)
    
    sync_count = 0
    for model_name, model_info in remote_models.items():
        local_path = os.path.join(target_dir, model_name)
        
        should_download = False
        
        if not os.path.exists(local_path):
            logger.info(f"Model {model_name} not found locally, downloading...")
            should_download = True
        else:
            # Check if local file is older or different size
            local_stat = os.stat(local_path)
            local_size = local_stat.st_size
            
            if local_size != model_info['size']:
                logger.info(f"Model {model_name} size differs, updating...")
                should_download = True
        
        if should_download:
            try:
                s3_client = setup_s3_client()
                if s3_client:
                    s3_client.download_file(bucket_name, model_info['s3_key'], local_path)
                    logger.info(f"Downloaded {model_name}")
                    sync_count += 1
                else:
                    logger.error(f"S3 client not available for downloading {model_name}")
            except Exception as e:
                logger.error(f"Failed to download {model_name}: {e}")
    
    logger.info(f"Synchronization complete. Updated {sync_count} models.")
    return True

def main():
    print("=" * 70)
    print("Real-time Video Processing - Cloud Model Sync")
    print("=" * 70)
    print("This script will download ML models from S3 storage")
    
    # Parse arguments
    import argparse
    parser = argparse.ArgumentParser(description="Download ML models from S3")
    parser.add_argument("--bucket", default=DEFAULT_BUCKET, help="S3 bucket name")
    parser.add_argument("--prefix", default=DEFAULT_PREFIX, help="S3 key prefix")
    parser.add_argument("--target", default=DEFAULT_MODEL_DIR, help="Local target directory")
    parser.add_argument("--action", choices=['download', 'upload', 'sync', 'check'], 
                       default='download', help="Action to perform")
    args = parser.parse_args()
    
    if not os.getenv('AWS_ACCESS_KEY_ID') or not os.getenv('AWS_SECRET_ACCESS_KEY'):
        print("\n⚠️ AWS credentials not found in environment variables.")
        print("Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY or create a .env file.")
        return 1
    
    success = False
    
    if args.action == 'download':
        print(f"\n📥 Downloading models from s3://{args.bucket}/{args.prefix}")
        success = download_models_from_s3(args.bucket, args.prefix, args.target)
    elif args.action == 'upload':
        print(f"\n📤 Uploading models to s3://{args.bucket}/{args.prefix}")
        success = upload_models_to_s3(args.bucket, args.prefix, args.target)
    elif args.action == 'sync':
        print(f"\n🔄 Synchronizing models with s3://{args.bucket}/{args.prefix}")
        success = sync_models(args.bucket, args.prefix, args.target)
    elif args.action == 'check':
        print(f"\n🔍 Checking model versions in s3://{args.bucket}/{args.prefix}")
        models = check_model_versions(args.bucket, args.prefix)
        if models:
            print("\nAvailable models:")
            for name, info in models.items():
                size_mb = info['size'] / (1024 * 1024)
                print(f"  - {name}: {size_mb:.2f} MB (modified: {info['last_modified']})")
            success = True
        else:
            print("No models found or connection failed")
    
    if success:
        print(f"\n✅ {args.action.capitalize()} operation completed successfully")
        return 0
    else:
        print(f"\n❌ {args.action.capitalize()} operation failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
