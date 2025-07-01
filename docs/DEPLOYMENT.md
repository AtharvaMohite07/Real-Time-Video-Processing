# 🚀 Deployment Guide - Real-time Video Processing Platform

This guide covers all deployment options for the Real-time Video Processing Platform, from development to production.

## 📋 Table of Contents

1. [Quick Start](#quick-start)
2. [Development Setup](#development-setup)
3. [Local Deployment](#local-deployment)
4. [Docker Deployment](#docker-deployment)
5. [Production Deployment](#production-deployment)
6. [Cloud Deployment (AWS)](#cloud-deployment-aws)
7. [Monitoring & Maintenance](#monitoring--maintenance)
8. [Troubleshooting](#troubleshooting)

---

## 🏃 Quick Start

### Option 1: Automated Setup (Recommended)
```bash
# Clone and setup
git clone <your-repo-url>
cd Real-Time-Video-Processing

# Run automated setup
python quick_setup.py

# Start the application
python app.py
```

### Option 2: Manual Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Edit .env with your configuration
# Then start the application
python app.py
```

Visit `http://localhost:5000` to access the web interface.

---

## 🔧 Development Setup

### Prerequisites
- Python 3.8+ 
- pip
- Virtual environment (recommended)
- Git

### Step-by-step Setup

1. **Create Virtual Environment**
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # Linux/Mac
   source venv/bin/activate
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Environment Configuration**
   ```bash
   cp .env.example .env
   # Edit .env file with your settings
   ```

4. **Start Development Server**
   ```bash
   python app.py
   ```

### Development Features
- Hot reload enabled
- Debug mode active
- Detailed error messages
- Development logging

---

## 💻 Local Deployment

### For Local Production Testing

1. **Setup Production Environment**
   ```bash
   python deploy_production.py setup
   ```

2. **Configure Environment**
   ```bash
   # Edit .env.prod with production settings
   nano .env.prod
   ```

3. **Run with Gunicorn**
   ```bash
   gunicorn --config gunicorn.conf.py app:app
   ```

### Local Docker Deployment

1. **Build and Run**
   ```bash
   docker-compose up --build
   ```

2. **Access Services**
   - Main app: `http://localhost:5000`
   - Nginx: `http://localhost:80`
   - Redis: `localhost:6379`

---

## 🐳 Docker Deployment

### Development Docker Setup

```bash
# Build and start all services
docker-compose up --build

# Run in background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Production Docker Setup

```bash
# Use production configuration
docker-compose -f docker-compose.prod.yml up --build -d

# Monitor health
docker-compose -f docker-compose.prod.yml ps
```

### Docker Services Overview

| Service | Port | Purpose |
|---------|------|---------|
| web | 5000/8000 | Main Flask application |
| nginx | 80, 443 | Reverse proxy & load balancer |
| redis | 6379 | Session storage & caching |
| db | 5432 | PostgreSQL database (production) |
| monitoring | 9090 | Prometheus monitoring |

---

## 🌐 Production Deployment

### Option 1: Automated Production Setup

```bash
# Run production setup wizard
python deploy_production.py setup

# Deploy
./deploy.sh
```

### Option 2: Manual Production Setup

#### 1. Server Preparation

**Ubuntu/Debian:**
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install additional dependencies
sudo apt install -y nginx certbot python3-certbot-nginx
```

#### 2. Application Deployment

```bash
# Clone repository
git clone <your-repo-url> /opt/video-processing
cd /opt/video-processing

# Setup production environment
cp .env.example .env.prod
# Edit .env.prod with production values

# Deploy with Docker
docker-compose -f docker-compose.prod.yml up -d
```

#### 3. SSL Setup (Optional but Recommended)

```bash
# Install SSL certificate
sudo certbot --nginx -d yourdomain.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

#### 4. Firewall Configuration

```bash
# Configure UFW
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
```

### Production Environment Variables

Critical variables for `.env.prod`:

```env
# Security
SECRET_KEY=your-super-secret-key-change-this
FLASK_ENV=production
FLASK_DEBUG=false

# Database
DATABASE_URL=postgresql://user:password@db:5432/video_processing

# AWS (Required for cloud features)
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_DEFAULT_REGION=us-west-2
S3_BUCKET_NAME=your-bucket
KINESIS_STREAM_NAME=your-stream

# Performance
WORKER_PROCESSES=4
MAX_CONTENT_LENGTH=104857600

# Security
CORS_ORIGINS=https://yourdomain.com
```

---

## ☁️ Cloud Deployment (AWS)

### AWS Infrastructure Setup

#### 1. EC2 Instance

**Launch Instance:**
- AMI: Ubuntu 22.04 LTS
- Instance Type: t3.large (minimum for video processing)
- Security Group: Allow 80, 443, 22
- Storage: 50GB+ EBS volume

**Setup Script:**
```bash
#!/bin/bash
# EC2 User Data Script
apt update
apt install -y docker.io docker-compose nginx git

# Clone application
git clone <your-repo-url> /opt/video-processing
cd /opt/video-processing

# Setup production
python3 deploy_production.py setup

# Deploy
docker-compose -f docker-compose.prod.yml up -d
```

#### 2. AWS Services Configuration

**S3 Bucket:**
```bash
aws s3 mb s3://your-video-processing-bucket
aws s3api put-bucket-cors --bucket your-video-processing-bucket --cors-configuration file://cors.json
```

**Kinesis Stream:**
```bash
aws kinesis create-stream --stream-name video-processing-stream --shard-count 1
```

**IAM Policy:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::your-video-processing-bucket/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "kinesis:PutRecord",
        "kinesis:PutRecords"
      ],
      "Resource": "arn:aws:kinesis:region:account:stream/video-processing-stream"
    }
  ]
}
```

### ECS Deployment (Advanced)

1. **Create ECS Cluster**
2. **Build and Push Docker Image**
3. **Create Task Definition**
4. **Deploy Service**

Detailed ECS configuration available in `infrastructure/` directory.

---

## 📊 Monitoring & Maintenance

### Health Monitoring

**Built-in Health Check:**
```bash
curl http://localhost:5000/api/health
```

**Docker Health Checks:**
```bash
docker-compose ps
docker-compose logs web
```

### Prometheus Metrics

Access metrics at: `http://localhost:9090`

**Key Metrics:**
- Request count and latency
- Processing FPS
- Memory and CPU usage
- Error rates

### Log Management

**Application Logs:**
```bash
# Docker logs
docker-compose logs -f web

# File logs (if configured)
tail -f logs/app.log
```

**Nginx Logs:**
```bash
docker-compose logs nginx
```

### Backup Strategy

**Automated Backup:**
```bash
# Run backup script
./backup.sh

# Scheduled backup (crontab)
0 2 * * * /opt/video-processing/backup.sh
```

**Manual Backup:**
```bash
# Database
docker-compose exec db pg_dump -U user video_processing > backup.sql

# Files
tar -czf uploads_backup.tar.gz uploads/
```

---

## 🛠️ Troubleshooting

### Common Issues

#### 1. Application Won't Start

**Check logs:**
```bash
docker-compose logs web
python app.py  # For direct debugging
```

**Common causes:**
- Missing environment variables
- Port conflicts
- Dependency issues

#### 2. Video Processing Not Working

**Check camera access:**
```bash
# Test camera
python -c "import cv2; print(cv2.VideoCapture(0).isOpened())"
```

**Check dependencies:**
```bash
pip list | grep opencv
```

#### 3. Cloud Features Not Working

**Verify AWS credentials:**
```bash
aws sts get-caller-identity
```

**Check S3 permissions:**
```bash
aws s3 ls s3://your-bucket-name
```

#### 4. Performance Issues

**Monitor resources:**
```bash
docker stats
htop
```

**Optimize configuration:**
- Increase worker processes
- Adjust video resolution
- Enable GPU acceleration (if available)

### Performance Optimization

#### 1. Video Processing
- Use lower resolution for real-time processing
- Implement frame skipping for heavy operations
- Enable hardware acceleration

#### 2. Server Configuration
```bash
# Increase file upload limits
# In nginx.conf
client_max_body_size 100M;

# Optimize worker processes
# In gunicorn.conf.py
workers = multiprocessing.cpu_count() * 2 + 1
```

#### 3. Database Optimization
- Use connection pooling
- Implement database indexing
- Regular maintenance tasks

### Debug Mode

**Enable debug logging:**
```env
LOG_LEVEL=DEBUG
FLASK_DEBUG=true
```

**Development debugging:**
```bash
python app.py --debug
```

---

## 🔧 Configuration Reference

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | Yes | - | Flask secret key |
| `AWS_ACCESS_KEY_ID` | No | - | AWS access key |
| `AWS_SECRET_ACCESS_KEY` | No | - | AWS secret key |
| `S3_BUCKET_NAME` | No | - | S3 bucket for uploads |
| `REDIS_URL` | No | `redis://localhost:6379/0` | Redis connection |
| `MAX_CONTENT_LENGTH` | No | `16777216` | Max upload size |

### Service Ports

| Service | Development | Production |
|---------|-------------|------------|
| Flask App | 5000 | 8000 |
| Nginx | - | 80, 443 |
| Redis | 6379 | 6379 |
| PostgreSQL | - | 5432 |
| Prometheus | 9090 | 9090 |

---

## 📞 Support

### Getting Help

1. **Check logs** for error messages
2. **Review configuration** files
3. **Test individual components** (camera, AWS, etc.)
4. **Check system resources** (CPU, memory, disk)
5. **Verify network connectivity**

### Useful Commands

```bash
# System health
df -h                    # Disk usage
free -h                  # Memory usage
docker system prune      # Clean Docker resources
docker-compose restart   # Restart services

# Application debugging
python -m flask --help   # Flask CLI
docker-compose exec web python -c "import app; print('OK')"
```

---

## 🔄 Updates & Maintenance

### Application Updates

```bash
# Pull latest code
git pull origin main

# Rebuild and deploy
docker-compose down
docker-compose up --build -d

# Or use deployment script
./deploy.sh
```

### Dependency Updates

```bash
# Update requirements
pip list --outdated
pip install -r requirements.txt --upgrade

# Update Docker images
docker-compose pull
```

### Security Updates

```bash
# System updates
sudo apt update && sudo apt upgrade

# SSL certificate renewal
sudo certbot renew

# Review logs for security issues
docker-compose logs | grep -i error
```

---

This deployment guide covers all aspects of deploying the Real-time Video Processing Platform. Choose the deployment method that best fits your needs and environment.

For additional support or custom deployment requirements, please refer to the project documentation or create an issue in the repository.
