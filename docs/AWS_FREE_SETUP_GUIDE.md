# 🌩️ AWS Free Tier Setup Guide for Video Processing Platform

This guide will help you set up AWS services for the video processing platform using **AWS Free Tier** benefits.

## 📋 AWS Free Tier Overview

### What's Included (12 months free):
- **S3**: 5 GB of storage, 20,000 GET requests, 2,000 PUT requests
- **Kinesis**: 1 million records per month (first 12 months)
- **Lambda**: 1 million requests per month (always free)
- **EC2**: 750 hours of t2.micro instances (Linux/Windows)
- **CloudWatch**: 10 custom metrics, 10 alarms

### Estimated Costs for This Project:
- **Free Tier Usage**: $0/month for moderate usage
- **Beyond Free Tier**: ~$5-15/month for heavy usage

---

## 🚀 Step 1: Create AWS Account

### 1.1 Sign Up
1. Go to [aws.amazon.com](https://aws.amazon.com)
2. Click **"Create an AWS Account"**
3. Provide email and password
4. Choose **"Personal"** account type
5. Enter contact information
6. **Payment Info**: Required but won't be charged for free tier usage
7. **Phone Verification**: AWS will call/text you
8. **Support Plan**: Choose **"Basic Plan"** (free)

### 1.2 Initial Setup
```bash
# After account creation, sign in to AWS Console
# Visit: https://console.aws.amazon.com
```

---

## 🔧 Step 2: Configure IAM (Security)

### 2.1 Create IAM User (Best Practice)
1. **Go to IAM Console**: Search "IAM" in AWS Console
2. **Click "Users"** → **"Add User"**
3. **Username**: `video-processing-user`
4. **Access Type**: ✅ Programmatic access
5. **Permissions**: Click **"Attach existing policies directly"**

### 2.2 Required Permissions
Attach these managed policies:
- `AmazonS3FullAccess` (for video/frame storage)
- `AmazonKinesisFullAccess` (for real-time streaming)

### 2.3 Get Access Keys
1. **Download credentials CSV** (IMPORTANT: Save this safely!)
2. Note down:
   - `Access Key ID`
   - `Secret Access Key`

**⚠️ Security Note**: Never share these keys or commit them to code!

---

## 📦 Step 3: Set Up S3 (Storage)

### 3.1 Create S3 Bucket
1. **Go to S3 Console**: Search "S3" in AWS Console
2. **Click "Create Bucket"**
3. **Bucket Name**: `your-video-processing-frames` (must be globally unique)
4. **Region**: Choose nearest region (e.g., `us-east-1`)
5. **Settings**:
   - ✅ Block all public access (recommended)
   - ✅ Bucket versioning: Disabled (to save costs)
   - ✅ Default encryption: Enabled

### 3.2 Configure CORS (for web uploads)
1. **Go to your bucket** → **Permissions** → **CORS**
2. **Add this configuration**:
```json
[
    {
        "AllowedHeaders": ["*"],
        "AllowedMethods": ["GET", "PUT", "POST", "DELETE", "HEAD"],
        "AllowedOrigins": ["*"],
        "ExposeHeaders": ["ETag"],
        "MaxAgeSeconds": 3000
    }
]
```

### 3.3 Create Folder Structure
In your bucket, create these folders:
- `frames/` (for captured video frames)
- `uploads/` (for uploaded video files)
- `analysis/` (for AI analysis results)
- `exports/` (for data exports)

---

## 🌊 Step 4: Set Up Kinesis (Real-time Streaming)

### 4.1 Create Kinesis Data Stream
1. **Go to Kinesis Console**: Search "Kinesis" in AWS Console
2. **Click "Create data stream"**
3. **Stream Name**: `video-processing-stream`
4. **Capacity Mode**: 
   - Choose **"Provisioned"** for predictable costs
   - **Shards**: 1 (sufficient for free tier)
5. **Click "Create data stream"**

### 4.2 Stream Configuration
- **Retention**: 24 hours (default, free)
- **Encryption**: Disabled (to avoid extra costs)
- **Monitoring**: Basic (included in free tier)

---

## 🔐 Step 5: Configure Your Application

### 5.1 Update .env File
Create/update your `.env` file:
```env
# AWS Configuration
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
AWS_DEFAULT_REGION=us-east-1

# S3 Configuration
S3_BUCKET_NAME=your-video-processing-frames

# Kinesis Configuration  
KINESIS_STREAM_NAME=video-processing-stream

# Application Settings
FLASK_ENV=development
SECRET_KEY=your-secret-key-change-this
MAX_CONTENT_LENGTH=104857600
```

### 5.2 Install AWS CLI (Optional but Recommended)
```bash
# Windows (using pip)
pip install awscli

# Verify installation
aws --version

# Configure AWS CLI
aws configure
# Enter your Access Key ID
# Enter your Secret Access Key  
# Default region: us-east-1
# Output format: json
```

### 5.3 Test AWS Connection
```bash
# Test S3 access
aws s3 ls s3://your-video-processing-frames

# Test from your application
python -c "
import boto3
import os
from dotenv import load_dotenv

load_dotenv()
s3 = boto3.client('s3', 
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name=os.getenv('AWS_DEFAULT_REGION')
)

# List buckets
buckets = s3.list_buckets()
print('S3 Connection successful!')
print('Buckets:', [b['Name'] for b in buckets['Buckets']])
"
```

---

## 💰 Step 6: Monitor Usage & Costs

### 6.1 Set Up Billing Alerts
1. **Go to Billing Console**: Search "Billing" in AWS Console
2. **Go to "Budgets"** → **"Create budget"**
3. **Budget Type**: Cost budget
4. **Amount**: $5 (safety threshold)
5. **Alert**: Email when 80% of budget is reached

### 6.2 Monitor Free Tier Usage
1. **AWS Console** → **Billing** → **Free Tier**
2. Check usage for:
   - S3 storage and requests
   - Kinesis records
   - Any other services

### 6.3 Cost Optimization Tips
```bash
# Keep costs minimal:
# ✅ Use 1 Kinesis shard only
# ✅ Keep S3 objects small
# ✅ Delete old files regularly  
# ✅ Use lifecycle policies for S3
# ✅ Monitor free tier usage monthly
```

---

## 🔄 Step 7: Application Integration

### 7.1 Test Video Upload to S3
```python
# Test upload functionality
# Run your Flask app and try uploading a frame
python app.py
# Go to http://localhost:5000
# Start camera and click "Upload Frame"
```

### 7.2 Test Kinesis Streaming
```python
# Enable advanced analysis and check Kinesis
# Data should appear in your stream
```

### 7.3 Verify in AWS Console
1. **S3**: Check if frames appear in `frames/` folder
2. **Kinesis**: Monitor incoming records
3. **CloudWatch**: Check for any errors

---

## 🛠️ Step 8: Production Setup (Optional)

### 8.1 Advanced S3 Configuration
```bash
# Set up lifecycle policies to delete old files
# Go to S3 → Your Bucket → Management → Lifecycle
# Create rule to delete files older than 30 days
```

### 8.2 Enhanced Security
```bash
# Create more restrictive IAM policy
# Limit S3 access to specific bucket only
# Use environment-specific roles
```

### 8.3 Monitoring Setup
```bash
# Set up CloudWatch alarms for:
# - S3 upload errors
# - Kinesis throttling
# - Application errors
```

---

## 🚨 Troubleshooting

### Common Issues:

#### 1. "Access Denied" Error
```bash
# Check IAM permissions
# Verify access keys in .env file
# Ensure bucket policies allow access
```

#### 2. "Bucket Not Found"
```bash
# Verify bucket name in .env
# Check region settings
# Ensure bucket exists in correct region
```

#### 3. Kinesis "Stream Not Found"
```bash
# Verify stream name
# Check if stream is active
# Wait for stream to become active after creation
```

#### 4. High Costs
```bash
# Check billing dashboard
# Review S3 storage usage
# Monitor Kinesis shard hours
# Set up proper budgets
```

---

## 📊 Expected Usage Patterns

### Free Tier Limits:
- **S3**: Store ~1000 video frames (5MB each)
- **Kinesis**: Process ~33,000 analysis events/day
- **Total**: Suitable for development and light testing

### Beyond Free Tier:
- **S3**: ~$0.023/GB/month for standard storage
- **Kinesis**: ~$0.015/hour per shard
- **Data Transfer**: ~$0.09/GB (only if accessing from outside AWS)

---

## 🎯 Best Practices

### 1. Security
- ✅ Use IAM users, not root account
- ✅ Rotate access keys regularly
- ✅ Use least privilege principle
- ✅ Enable MFA on root account

### 2. Cost Management
- ✅ Monitor usage weekly
- ✅ Set up billing alerts
- ✅ Delete unused resources
- ✅ Use S3 lifecycle policies

### 3. Performance
- ✅ Choose nearest region
- ✅ Use appropriate S3 storage class
- ✅ Monitor Kinesis shard utilization
- ✅ Implement retry logic

---

## 📞 Support Resources

### AWS Support:
- **Free Tier Support**: Basic support included
- **Documentation**: https://docs.aws.amazon.com
- **Forums**: AWS Developer Forums
- **Billing Questions**: AWS Support Chat

### Application Support:
- Check logs for detailed error messages
- Use health check endpoint: `/api/health`
- Monitor application statistics

---

## 🎉 Success Checklist

After setup, you should have:
- ✅ AWS account with free tier benefits
- ✅ IAM user with proper permissions
- ✅ S3 bucket for file storage
- ✅ Kinesis stream for real-time data
- ✅ Application connected to AWS services
- ✅ Billing alerts configured
- ✅ Test uploads working

**🎊 Congratulations! Your free AWS cloud integration is ready!**

---

## 💡 Pro Tips

1. **Start Small**: Use minimal resources and scale up
2. **Monitor Closely**: Check usage daily for first week
3. **Automate Cleanup**: Set up S3 lifecycle rules
4. **Stay Updated**: AWS free tier terms can change
5. **Backup Config**: Save your .env file securely

Remember: The free tier gives you 12 months to experiment and build without costs!
