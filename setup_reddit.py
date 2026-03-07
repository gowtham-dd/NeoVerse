#!/usr/bin/env python3
"""
Setup script for Reddit Agent
Helps configure Reddit API credentials
"""

import os
import sys
from pathlib import Path

def setup_environment():
    """Setup environment variables and check requirements"""
    
    print("🔧 Reddit Agent Setup")
    print("=" * 50)
    
    # Check if .env file exists
    env_file = Path(".env")
    
    if not env_file.exists():
        print("⚠️  No .env file found. Creating template...")
        
        env_template = """# Reddit API Credentials
# Get these from https://www.reddit.com/prefs/apps
REDDIT_CLIENT_ID=your_client_id_here
REDDIT_CLIENT_SECRET=your_client_secret_here
REDDIT_USERNAME=your_reddit_username
REDDIT_PASSWORD=your_reddit_password
REDDIT_USER_AGENT=DrugMonitoringAgent/1.0 (by /u/your_username)

# Groq API for Llama3
# Get from https://console.groq.com
GROQ_API_KEY=your_groq_api_key_here
"""
        
        with open(".env", "w") as f:
            f.write(env_template)
        
        print("✅ Created .env template")
        print("\n📝 Please edit the .env file with your credentials:")
        print("   1. Go to https://www.reddit.com/prefs/apps")
        print("   2. Create a 'script' type application")
        print("   3. Copy client ID and secret")
        print("   4. Enter your Reddit username and password")
        print("   5. Get Groq API key from https://console.groq.com")
    
    else:
        print("✅ .env file found")
    
    # Check Python version
    print(f"\n🐍 Python version: {sys.version}")
    
    # Check required packages
    print("\n📦 Checking required packages...")
    
    required_packages = [
        ("praw", "Reddit API wrapper"),
        ("sentence-transformers", "Text embeddings"),
        ("numpy", "Numerical computations"),
        ("scikit-learn", "Cosine similarity"),
        ("groq", "Llama3 API access"),
        ("python-dotenv", "Environment variables")
    ]
    
    missing_packages = []
    
    for package, description in required_packages:
        try:
            __import__(package.replace("-", "_"))
            print(f"   ✅ {package}: {description}")
        except ImportError:
            print(f"   ❌ {package}: {description} - MISSING")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️  Missing packages detected!")
        print(f"   Install with: pip install {' '.join(missing_packages)}")
        
        install = input("\nDo you want to install missing packages now? (y/n): ")
        if install.lower() == 'y':
            import subprocess
            subprocess.run([sys.executable, "-m", "pip", "install"] + missing_packages)
    
    print("\n" + "=" * 50)
    print("🎉 Setup complete!")
    print("\nNext steps:")
    print("1. Edit .env file with your credentials")
    print("2. Run: python reddit_agent.py")
    print("3. Or integrate with your main dashboard")
    
    return True


if __name__ == "__main__":
    setup_environment()