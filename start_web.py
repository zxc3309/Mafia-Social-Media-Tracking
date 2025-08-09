#!/usr/bin/env python
"""
Direct web server starter - bypass main.py completely
"""
import os
import sys
import uvicorn

print("=" * 60)
print("🚀 DIRECT WEB SERVER STARTER")
print(f"Python: {sys.version}")
print(f"Port: {os.getenv('PORT', '8080')}")
print("=" * 60)

# Import and run the app directly
from app import app

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")