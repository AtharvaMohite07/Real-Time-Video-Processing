#!/usr/bin/env python3
"""
Production Deployment Script for Real-time Video Processing Platform
Handles production setup, configuration, and deployment preparation.
"""

import os
import sys
import subprocess
import shutil
import json
import platform
from pathlib import Path

class ProductionDeployer:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.deployment_configs = {
            'docker': True,
            'gunicorn': True,
            'nginx': True,
            'ssl': False,
            'monitoring': True
        }
        
    def check_system_requirements(self):
        """Check system requirements for production deployment."""
        print("🔍 Checking system requirements...")
        
        requirements = {
            'python': self.check_python_version(),
            'docker': self.check_docker(),
            'git': self.check_git(),
            'ports': self.check_ports([5000, 80, 443, 6379])
        }
        
        all_good = all(requirements.values())
        if all_good:
            print("✅ All system requirements met")
        else:
            print("❌ Some requirements not met:")
            for req, status in requirements.items():
                if not status:
                    print(f"   - {req}: Not available")
        
        return all_good
    
    def check_python_version(self):
        """Check Python version."""
        version = sys.version_info
        if version.major >= 3 and version.minor >= 8:
            print(f"✅ Python {version.major}.{version.minor} (compatible)")
            return True
        else:
            print(f"❌ Python {version.major}.{version.minor} (requires >= 3.8)")
            return False
    
    def check_docker(self):
        """Check if Docker is available."""
        try:
            result = subprocess.run(['docker', '--version'], 
                                   capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ Docker available: {result.stdout.strip()}")
                return True
        except FileNotFoundError:
            pass
        
        print("❌ Docker not available")
        return False
    
    def check_git(self):
        """Check if Git is available."""
        try:
            result = subprocess.run(['git', '--version'], 
                                   capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ Git available: {result.stdout.strip()}")
                return True
        except FileNotFoundError:
            pass
        
        print("❌ Git not available")
        return False
    
    def check_ports(self, ports):
        """Check if required ports are available."""
        import socket
        
        available_ports = []
        for port in ports:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            if result != 0:  # Port is free
                available_ports.append(port)
        
        if len(available_ports) == len(ports):
            print(f"✅ All ports available: {', '.join(map(str, ports))}")
            return True
        else:
            unavailable = set(ports) - set(available_ports)
            print(f"❌ Ports in use: {', '.join(map(str, unavailable))}")
            return False
    
    def setup_production_config(self):
        """Set up production configuration files."""
        print("⚙️ Setting up production configuration...")
        
        # Create production environment file
        prod_env = self.project_root / '.env.prod'
        env_content = """
# Production Environment Configuration
FLASK_ENV=production
FLASK_DEBUG=false
SECRET_KEY=your-secret-key-here-change-this-in-production
DATABASE_URL=postgresql://user:password@db:5432/video_processing

# AWS Configuration (Required for cloud features)
AWS_ACCESS_KEY_ID=your-access-key-here
AWS_SECRET_ACCESS_KEY=your-secret-key-here
AWS_DEFAULT_REGION=us-west-2
S3_BUCKET_NAME=your-video-processing-bucket
KINESIS_STREAM_NAME=video-processing-stream

# Redis Configuration
REDIS_URL=redis://redis:6379/0

# Monitoring
ENABLE_MONITORING=true
LOG_LEVEL=INFO

# Security
CORS_ORIGINS=https://yourdomain.com
MAX_CONTENT_LENGTH=104857600  # 100MB

# Performance
WORKER_PROCESSES=4
WORKER_CONNECTIONS=1000
KEEP_ALIVE=2
""".strip()
        
        with open(prod_env, 'w') as f:
            f.write(env_content)
        
        print(f"✅ Created production config: {prod_env}")
        
        # Create Gunicorn configuration
        self.create_gunicorn_config()
        
        # Create Nginx configuration
        self.create_nginx_config()
        
        # Create systemd service file
        self.create_systemd_service()
    
    def create_gunicorn_config(self):
        """Create Gunicorn configuration for production."""
        config_content = """
# Gunicorn configuration for production
import multiprocessing

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2

# Restart workers
max_requests = 1000
max_requests_jitter = 50
preload_app = True

# Logging
accesslog = "/var/log/gunicorn/access.log"
errorlog = "/var/log/gunicorn/error.log"
loglevel = "info"

# Process naming
proc_name = "real_time_video_processing"

# Server mechanics
daemon = False
pidfile = "/var/run/gunicorn/gunicorn.pid"
user = "www-data"
group = "www-data"
tmp_upload_dir = None

# SSL (if enabled)
# keyfile = "/path/to/keyfile"
# certfile = "/path/to/certfile"
""".strip()
        
        config_file = self.project_root / 'gunicorn.conf.py'
        with open(config_file, 'w') as f:
            f.write(config_content)
        
        print(f"✅ Created Gunicorn config: {config_file}")
    
    def create_nginx_config(self):
        """Create Nginx configuration."""
        nginx_content = """
upstream video_processing_app {
    server web:8000;
}

server {
    listen 80;
    server_name localhost;
    
    client_max_body_size 100M;
    
    location / {
        proxy_pass http://video_processing_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
    
    location /static/ {
        alias /app/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    location /health {
        access_log off;
        return 200 "healthy\\n";
        add_header Content-Type text/plain;
    }
}

# SSL configuration (uncomment when SSL certificates are ready)
# server {
#     listen 443 ssl http2;
#     server_name yourdomain.com;
#     
#     ssl_certificate /etc/ssl/certs/cert.pem;
#     ssl_certificate_key /etc/ssl/private/key.pem;
#     
#     # Modern SSL configuration
#     ssl_protocols TLSv1.2 TLSv1.3;
#     ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
#     ssl_prefer_server_ciphers off;
#     
#     location / {
#         proxy_pass http://video_processing_app;
#         proxy_set_header Host $host;
#         proxy_set_header X-Real-IP $remote_addr;
#         proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
#         proxy_set_header X-Forwarded-Proto $scheme;
#     }
# }
""".strip()
        
        # Update the existing nginx.conf
        nginx_file = self.project_root / 'nginx.conf'
        with open(nginx_file, 'w') as f:
            f.write(nginx_content)
        
        print(f"✅ Updated Nginx config: {nginx_file}")
    
    def create_systemd_service(self):
        """Create systemd service file for non-Docker deployment."""
        service_content = f"""
[Unit]
Description=Real-time Video Processing Platform
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory={self.project_root}
ExecStart={sys.executable} -m gunicorn --config gunicorn.conf.py app:app
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always
RestartSec=3
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true

[Install]
WantedBy=multi-user.target
""".strip()
        
        service_file = self.project_root / 'video-processing.service'
        with open(service_file, 'w') as f:
            f.write(service_content)
        
        print(f"✅ Created systemd service: {service_file}")
        print("   To install: sudo cp video-processing.service /etc/systemd/system/")
        print("   To enable: sudo systemctl enable video-processing")
        print("   To start: sudo systemctl start video-processing")
    
    def optimize_docker_build(self):
        """Optimize Docker configuration for production."""
        print("🐳 Optimizing Docker configuration...")
        
        # Create production Dockerfile
        prod_dockerfile = """
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    ffmpeg \\
    libsm6 \\
    libxext6 \\
    libxrender-dev \\
    libglib2.0-0 \\
    libgtk-3-0 \\
    libgl1-mesa-glx \\
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Change ownership
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \\
    CMD curl -f http://localhost:8000/api/health || exit 1

# Run with Gunicorn
CMD ["gunicorn", "--config", "gunicorn.conf.py", "app:app"]
""".strip()
        
        dockerfile_prod = self.project_root / 'Dockerfile.prod'
        with open(dockerfile_prod, 'w') as f:
            f.write(prod_dockerfile)
        
        print(f"✅ Created production Dockerfile: {dockerfile_prod}")
        
        # Update docker-compose for production
        self.update_docker_compose_prod()
    
    def update_docker_compose_prod(self):
        """Update docker-compose for production."""
        compose_content = """
version: '3.8'

services:
  web:
    build:
      context: .
      dockerfile: Dockerfile.prod
    ports:
      - "8000:8000"
    env_file:
      - .env.prod
    volumes:
      - ./uploads:/app/uploads
      - ./logs:/app/logs
    depends_on:
      - redis
      - db
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf
      - ./static:/app/static:ro
    depends_on:
      - web
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: video_processing
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user -d video_processing"]
      interval: 30s
      timeout: 10s
      retries: 3

  monitoring:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
  prometheus_data:
""".strip()
        
        compose_prod = self.project_root / 'docker-compose.prod.yml'
        with open(compose_prod, 'w') as f:
            f.write(compose_content)
        
        print(f"✅ Created production docker-compose: {compose_prod}")
    
    def create_deployment_scripts(self):
        """Create deployment scripts."""
        print("📜 Creating deployment scripts...")
        
        # Deploy script
        deploy_script = """#!/bin/bash
set -e

echo "🚀 Deploying Real-time Video Processing Platform..."

# Build and deploy with Docker Compose
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d

echo "✅ Deployment complete!"
echo "🌐 Application available at: http://localhost"
echo "📊 Monitoring available at: http://localhost:9090"

# Health check
sleep 10
if curl -f http://localhost/api/health > /dev/null 2>&1; then
    echo "✅ Health check passed"
else
    echo "❌ Health check failed"
    exit 1
fi
""".strip()
        
        deploy_file = self.project_root / 'deploy.sh'
        with open(deploy_file, 'w') as f:
            f.write(deploy_script)
        
        # Make executable (on Unix systems)
        if platform.system() != 'Windows':
            os.chmod(deploy_file, 0o755)
        
        print(f"✅ Created deployment script: {deploy_file}")
        
        # Backup script
        self.create_backup_script()
    
    def create_backup_script(self):
        """Create backup script."""
        backup_script = """#!/bin/bash
set -e

BACKUP_DIR="/backup/video-processing"
DATE=$(date +%Y%m%d_%H%M%S)

echo "💾 Creating backup..."

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Backup database
docker-compose -f docker-compose.prod.yml exec -T db pg_dump -U user video_processing > "$BACKUP_DIR/db_$DATE.sql"

# Backup uploaded files
tar -czf "$BACKUP_DIR/uploads_$DATE.tar.gz" uploads/

# Backup configuration
tar -czf "$BACKUP_DIR/config_$DATE.tar.gz" .env.prod gunicorn.conf.py nginx.conf

echo "✅ Backup complete: $BACKUP_DIR"

# Clean old backups (keep last 7 days)
find "$BACKUP_DIR" -name "*.sql" -mtime +7 -delete
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +7 -delete
""".strip()
        
        backup_file = self.project_root / 'backup.sh'
        with open(backup_file, 'w') as f:
            f.write(backup_script)
        
        if platform.system() != 'Windows':
            os.chmod(backup_file, 0o755)
        
        print(f"✅ Created backup script: {backup_file}")
    
    def create_monitoring_config(self):
        """Create monitoring configuration."""
        print("📊 Setting up monitoring...")
        
        prometheus_config = """
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'video-processing-app'
    static_configs:
      - targets: ['web:8000']
    metrics_path: /metrics
    scrape_interval: 30s

  - job_name: 'nginx'
    static_configs:
      - targets: ['nginx:80']
    
  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']
""".strip()
        
        prometheus_file = self.project_root / 'prometheus.yml'
        with open(prometheus_file, 'w') as f:
            f.write(prometheus_config)
        
        print(f"✅ Created monitoring config: {prometheus_file}")
    
    def run_production_setup(self):
        """Run complete production setup."""
        print("🎯 Setting up production deployment...")
        print("=" * 50)
        
        # Check requirements
        if not self.check_system_requirements():
            print("\n❌ Please fix system requirements before continuing.")
            return False
        
        # Setup configurations
        self.setup_production_config()
        self.optimize_docker_build()
        self.create_deployment_scripts()
        self.create_monitoring_config()
        
        print("\n" + "=" * 50)
        print("🎉 Production setup complete!")
        print("\n📋 Next steps:")
        print("1. Update .env.prod with your actual configuration")
        print("2. Configure SSL certificates (if needed)")
        print("3. Run: ./deploy.sh")
        print("4. Monitor at: http://localhost:9090")
        
        print("\n🔐 Security reminders:")
        print("- Change SECRET_KEY in .env.prod")
        print("- Configure AWS credentials properly")
        print("- Set up firewall rules")
        print("- Enable SSL in production")
        print("- Review CORS_ORIGINS setting")
        
        return True

def main():
    """Main function."""
    deployer = ProductionDeployer()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "setup":
            deployer.run_production_setup()
        elif command == "check":
            deployer.check_system_requirements()
        else:
            print("Usage: python deploy_production.py [setup|check]")
    else:
        deployer.run_production_setup()

if __name__ == "__main__":
    main()
