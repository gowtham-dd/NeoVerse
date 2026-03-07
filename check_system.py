#!/usr/bin/env python3
"""
Check system readiness for real Telegram agent
"""
import os
import sys
import json

def check_system():
    print("🔍 Checking system for REAL Telegram agent...")
    print("="*60)
    
    # Check .env file
    print("\n📁 Environment Check:")
    print("-"*40)
    if os.path.exists('.env'):
        print("✅ .env file exists")
        with open('.env', 'r') as f:
            content = f.read()
            if 'TELEGRAM_API_ID' in content:
                print("✅ TELEGRAM_API_ID configured")
            else:
                print("❌ TELEGRAM_API_ID missing")
            
            if 'TELEGRAM_API_HASH' in content:
                print("✅ TELEGRAM_API_HASH configured")
            else:
                print("❌ TELEGRAM_API_HASH missing")
            
            if 'TELEGRAM_PHONE' in content:
                print("✅ TELEGRAM_PHONE configured")
            else:
                print("❌ TELEGRAM_PHONE missing")
            
            if 'GROQ_API_KEY' in content:
                print("✅ GROQ_API_KEY configured (for AI analysis)")
            else:
                print("⚠️  GROQ_API_KEY missing (will use basic keyword analysis)")
    else:
        print("❌ .env file not found!")
    
    # Check modules
    print("\n📦 Module Check:")
    print("-"*40)
    if os.path.exists('modules'):
        print("✅ modules/ directory exists")
        module_files = ['telegram_client.py', 'ai_analyzer.py', 'channel_discovery.py']
        for file in module_files:
            path = os.path.join('modules', file)
            if os.path.exists(path):
                print(f"✅ {file}")
            else:
                print(f"❌ {file} not found")
    else:
        print("❌ modules/ directory not found!")
    
    # Check telegram_agent.py
    print("\n🤖 Agent Check:")
    print("-"*40)
    if os.path.exists('telegram_agent.py'):
        print("✅ telegram_agent.py exists")
    else:
        print("❌ telegram_agent.py not found!")
    
    # Check Python packages
    print("\n🐍 Package Check:")
    print("-"*40)
    packages = ['telethon', 'groq', 'flask', 'flask_cors']
    for package in packages:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package}")
    
    print("\n" + "="*60)
    print("💡 RECOMMENDATIONS:")
    print("1. If missing .env, copy .env.example and fill in your credentials")
    print("2. If missing modules, create modules/ directory with required files")
    print("3. If missing packages, run: pip install telethon groq flask flask-cors")
    print("4. First run will ask for Telegram verification code")
    print("="*60)

if __name__ == "__main__":
    check_system()