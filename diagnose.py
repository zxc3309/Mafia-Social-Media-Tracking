#!/usr/bin/env python3
"""
Railway Deployment Diagnostic Script
Run this to check the environment and dependencies
"""

import sys
import os
import importlib
import subprocess

def check_python():
    """Check Python version and basic info"""
    print("🐍 PYTHON INFORMATION")
    print("=" * 50)
    print(f"Version: {sys.version}")
    print(f"Executable: {sys.executable}")
    print(f"Platform: {sys.platform}")
    print(f"Path: {sys.path[:3]}...")  # Show first 3 paths
    print()

def check_environment():
    """Check environment variables"""
    print("🌍 ENVIRONMENT VARIABLES")
    print("=" * 50)
    
    # Key variables to check
    key_vars = ['PORT', 'PYTHONPATH', 'PATH', 'DATABASE_URL']
    
    for var in key_vars:
        value = os.getenv(var, 'Not set')
        if var == 'DATABASE_URL' and value != 'Not set':
            value = value[:20] + "..." # Hide sensitive parts
        print(f"{var}: {value}")
    
    print(f"Total environment variables: {len(os.environ)}")
    print()

def check_dependencies():
    """Check if key dependencies can be imported"""
    print("📦 DEPENDENCY CHECK")
    print("=" * 50)
    
    dependencies = [
        'fastapi',
        'uvicorn', 
        'pydantic',
        'sqlalchemy',
        'psycopg2',
        'google',
        'openai',
        'requests'
    ]
    
    for dep in dependencies:
        try:
            module = importlib.import_module(dep)
            version = getattr(module, '__version__', 'unknown')
            print(f"✅ {dep}: {version}")
        except ImportError:
            print(f"❌ {dep}: Not available")
    print()

def check_files():
    """Check if key files exist"""
    print("📁 FILE CHECK")
    print("=" * 50)
    
    key_files = [
        'app.py',
        'main.py', 
        'Procfile',
        'requirements.txt',
        'Dockerfile',
        'railway.json'
    ]
    
    for file in key_files:
        exists = "✅" if os.path.exists(file) else "❌"
        print(f"{exists} {file}")
    print()

def test_fastapi_import():
    """Test FastAPI import and basic functionality"""
    print("🚀 FASTAPI TEST")
    print("=" * 50)
    
    try:
        from fastapi import FastAPI
        import uvicorn
        
        # Create minimal app
        test_app = FastAPI()
        
        @test_app.get("/")
        def root():
            return {"status": "test success"}
        
        print("✅ FastAPI app created successfully")
        print("✅ Basic endpoint defined")
        print("✅ uvicorn imported")
        
        # Test if we can get the port
        port = int(os.getenv("PORT", 8080))
        print(f"✅ Port configuration: {port}")
        
    except Exception as e:
        print(f"❌ FastAPI test failed: {e}")
    print()

def check_working_directory():
    """Check working directory and permissions"""
    print("📂 WORKING DIRECTORY")
    print("=" * 50)
    print(f"Current directory: {os.getcwd()}")
    print(f"Directory contents:")
    
    try:
        files = os.listdir('.')
        for f in sorted(files)[:10]:  # Show first 10 files
            print(f"  - {f}")
        if len(files) > 10:
            print(f"  ... and {len(files)-10} more files")
    except Exception as e:
        print(f"❌ Cannot list directory: {e}")
    print()

def main():
    print("🔧 RAILWAY DEPLOYMENT DIAGNOSTICS")
    print("=" * 50)
    print(f"Running at: {os.getcwd()}")
    print(f"Timestamp: {__import__('datetime').datetime.now()}")
    print("\n")
    
    check_python()
    check_environment() 
    check_working_directory()
    check_files()
    check_dependencies()
    test_fastapi_import()
    
    print("🏁 DIAGNOSTIC COMPLETE")
    print("=" * 50)
    print("If all checks pass, the basic FastAPI app should work!")
    print()

if __name__ == "__main__":
    main()