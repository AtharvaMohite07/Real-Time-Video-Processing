#!/usr/bin/env python3
"""
GitHub Upload Validation Script
Ensures the project is ready for safe public upload
"""

import os
import sys
from pathlib import Path

def check_file_exists(filepath, description):
    """Check if a file exists and print status"""
    if os.path.exists(filepath):
        print(f"✅ {description}: {filepath}")
        return True
    else:
        print(f"❌ {description}: {filepath}")
        return False

def check_gitignore():
    """Verify .gitignore protects sensitive files"""
    gitignore_path = ".gitignore"
    if not os.path.exists(gitignore_path):
        print("❌ .gitignore file missing!")
        return False
    
    with open(gitignore_path, 'r') as f:
        content = f.read()
    
    required_patterns = ['.env', '__pycache__/', '*.pyc', 'models/', 'saved_frames/']
    missing_patterns = []
    
    for pattern in required_patterns:
        if pattern not in content:
            missing_patterns.append(pattern)
    
    if missing_patterns:
        print(f"❌ .gitignore missing patterns: {missing_patterns}")
        return False
    else:
        print("✅ .gitignore properly configured")
        return True

def check_env_files():
    """Check environment file configuration"""
    env_exists = os.path.exists('.env')
    env_example_exists = os.path.exists('.env.example')
    
    if env_exists:
        print("⚠️  .env file exists - ensure it's in .gitignore!")
    else:
        print("✅ .env file not present (good for GitHub)")
    
    if env_example_exists:
        print("✅ .env.example template exists")
    else:
        print("❌ .env.example template missing")
    
    return env_example_exists

def scan_for_secrets():
    """Scan Python files for potential hardcoded secrets"""
    secret_patterns = ['aws_access_key_id="', 'aws_secret_access_key="', 'secret_key="']
    found_secrets = []
    
    for root, dirs, files in os.walk('.'):
        # Skip hidden directories and __pycache__
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
        
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read().lower()
                    
                    for pattern in secret_patterns:
                        if pattern in content and 'os.getenv' not in content:
                            found_secrets.append(f"{filepath}: {pattern}")
                except Exception as e:
                    print(f"⚠️  Could not scan {filepath}: {e}")
    
    if found_secrets:
        print("❌ Potential hardcoded secrets found:")
        for secret in found_secrets:
            print(f"   {secret}")
        return False
    else:
        print("✅ No hardcoded secrets detected")
        return True

def main():
    """Run all validation checks"""
    print("🔍 GitHub Upload Validation\n")
    
    # Required files check
    required_files = [
        ('README.md', 'Main documentation'),
        ('requirements.txt', 'Python dependencies'),
        ('app.py', 'Main application'),
        ('.env.example', 'Environment template'),
        ('LICENSE', 'License file'),
        ('.gitignore', 'Git ignore rules'),
        ('quick_setup.py', 'Setup script'),
        ('CONTRIBUTING.md', 'Contributing guidelines'),
        ('docs/AWS_FREE_SETUP_GUIDE.md', 'AWS setup guide'),
        ('docs/DEPLOYMENT.md', 'Deployment guide'),
        ('docs/PROJECT_SUMMARY.md', 'Project summary'),
        ('docs/README_DETAILED.md', 'Detailed documentation')
    ]
    
    files_ok = True
    for filepath, description in required_files:
        if not check_file_exists(filepath, description):
            files_ok = False
    
    print()
    
    # Security checks
    gitignore_ok = check_gitignore()
    print()
    
    env_ok = check_env_files()
    print()
    
    secrets_ok = scan_for_secrets()
    print()
    
    # Final assessment
    all_checks_passed = files_ok and gitignore_ok and env_ok and secrets_ok
    
    if all_checks_passed:
        print("🎉 ALL CHECKS PASSED! Ready for GitHub upload!")
        print("\nNext steps:")
        print("1. git init")
        print("2. git add .")
        print("3. git commit -m 'Initial commit: Real-Time Video Processing Platform'")
        print("4. Create repository on GitHub")
        print("5. git remote add origin <your-repo-url>")
        print("6. git push -u origin main")
        return 0
    else:
        print("❌ Some checks failed. Please fix the issues above before uploading.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
