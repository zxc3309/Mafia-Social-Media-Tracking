#!/usr/bin/env python3
"""
Minimal FastAPI Test App for Railway Deployment
Testing basic web server functionality first
"""

import os
import sys
import logging
from datetime import datetime
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import uvicorn

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Social Media Tracking - Test Mode", 
    description="Minimal test version to diagnose Railway deployment"
)

@app.on_event("startup")
async def startup_event():
    """Log startup information for debugging"""
    logger.info("=" * 50)
    logger.info("🚀 MINIMAL FASTAPI APP STARTING")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"FastAPI imported successfully")
    logger.info(f"PORT environment: {os.getenv('PORT', 'Not set')}")
    logger.info(f"Current working directory: {os.getcwd()}")
    logger.info("=" * 50)

@app.get("/", response_class=HTMLResponse)
async def root():
    """Simple root endpoint with diagnostic info"""
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Railway Test - Service Running</title>
        <style>
            body {{ 
                font-family: system-ui; 
                max-width: 800px; 
                margin: 50px auto; 
                padding: 20px;
                background: #f0f2f5;
            }}
            .card {{ 
                background: white; 
                padding: 30px; 
                border-radius: 8px; 
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                text-align: center;
            }}
            .success {{ color: #28a745; }}
            .info {{ color: #17a2b8; }}
        </style>
    </head>
    <body>
        <div class="card">
            <h1 class="success">✅ FastAPI Service is Running!</h1>
            <h2>🧪 Railway Deployment Test</h2>
            <p><strong>Status:</strong> <span class="success">Healthy</span></p>
            <p><strong>Time:</strong> {datetime.utcnow().isoformat()} UTC</p>
            <p><strong>Port:</strong> {os.getenv('PORT', 'Default 8080')}</p>
            <p><strong>Python:</strong> {sys.version.split()[0]}</p>
            
            <hr>
            <h3 class="info">🎯 Next Steps:</h3>
            <p>If you can see this page, the basic web service is working!</p>
            <p>We can now safely add the full dashboard functionality.</p>
            
            <div style="margin-top: 20px;">
                <a href="/health" style="
                    display: inline-block;
                    padding: 10px 20px;
                    background: #007bff;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                ">Test Health Check</a>
            </div>
        </div>
    </body>
    </html>
    """
    return html

@app.get("/health")
async def health_check():
    """Health check endpoint for Railway"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "social-media-tracker",
        "mode": "test",
        "port": os.getenv("PORT", "8080")
    }

@app.get("/debug")
async def debug_info():
    """Debug information endpoint"""
    return {
        "python_version": sys.version,
        "port": os.getenv("PORT", "Not set"),
        "working_directory": os.getcwd(),
        "environment_variables": {
            key: value for key, value in os.environ.items() 
            if not any(secret in key.upper() for secret in ['TOKEN', 'KEY', 'SECRET', 'PASSWORD'])
        },
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    # Get port from environment (Railway provides this)
    port = int(os.getenv("PORT", 8080))
    host = "0.0.0.0"
    
    print("=" * 50)
    print("🌐 STARTING MINIMAL FASTAPI TEST SERVER")
    print(f"📍 Host: {host}")
    print(f"🔌 Port: {port}")
    print(f"🐍 Python: {sys.version.split()[0]}")
    print("=" * 50)
    
    # Run the server
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )