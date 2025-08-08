#!/usr/bin/env python3
"""
FastAPI Web Server for Social Media Tracking System

This server runs continuously on Railway and handles:
1. Built-in scheduling for daily collections at 9:00 AM
2. Webhook endpoints for manual triggers
3. Health checks and status monitoring
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
import uvicorn

from services.scheduler import get_scheduler
from services.post_collector import PostCollector
from config import COLLECTION_SCHEDULE_HOUR, COLLECTION_SCHEDULE_MINUTE

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Social Media Tracking API",
    description="Automated social media post collection and analysis system",
    version="1.0.0"
)

# Global scheduler instance
scheduler = None
collector = PostCollector()

@app.on_event("startup")
async def startup_event():
    """Initialize scheduler on startup"""
    global scheduler
    try:
        logger.info("Starting web server and initializing scheduler...")
        
        # Get scheduler in background mode
        scheduler = get_scheduler(background_mode=True)
        
        # Add daily collection job
        scheduler.add_daily_collection_job()
        
        # Start the scheduler
        scheduler.start()
        
        logger.info(f"✅ Scheduler started! Daily collection scheduled at {COLLECTION_SCHEDULE_HOUR:02d}:{COLLECTION_SCHEDULE_MINUTE:02d}")
        logger.info("✅ Web server ready to accept requests")
        
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global scheduler
    if scheduler:
        scheduler.stop()
        logger.info("Scheduler stopped")

@app.get("/")
async def root():
    """Root endpoint - health check and basic info"""
    return {
        "status": "running",
        "service": "Social Media Tracking System",
        "time": datetime.utcnow().isoformat(),
        "scheduler": "active" if scheduler and scheduler.scheduler.running else "inactive",
        "next_collection": f"{COLLECTION_SCHEDULE_HOUR:02d}:{COLLECTION_SCHEDULE_MINUTE:02d} daily"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for Railway"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.get("/status")
async def get_status():
    """Get detailed system status"""
    try:
        if not scheduler:
            return {"error": "Scheduler not initialized"}
        
        status = scheduler.get_job_status()
        
        # Add collection statistics
        try:
            stats = collector.get_collection_stats()
            status['collection_stats'] = stats
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            status['collection_stats'] = {"error": str(e)}
        
        return status
        
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/trigger")
async def trigger_collection(background_tasks: BackgroundTasks):
    """Manually trigger a collection"""
    try:
        logger.info("Manual collection triggered via API")
        
        # Run collection in background to avoid timeout
        background_tasks.add_task(run_collection_task)
        
        return {
            "status": "triggered",
            "message": "Collection started in background",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error triggering collection: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/trigger-sync")
async def trigger_collection_sync():
    """Manually trigger a collection (synchronous - waits for completion)"""
    try:
        logger.info("Synchronous collection triggered via API")
        
        start_time = datetime.utcnow()
        results = collector.collect_all_posts()
        end_time = datetime.utcnow()
        
        duration = (end_time - start_time).total_seconds()
        
        return {
            "status": "completed",
            "duration_seconds": duration,
            "results": results,
            "timestamp": end_time.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in synchronous collection: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/trigger/{platform}")
async def trigger_platform_collection(platform: str, background_tasks: BackgroundTasks):
    """Trigger collection for a specific platform"""
    if platform not in ['twitter', 'linkedin']:
        raise HTTPException(status_code=400, detail="Invalid platform. Use 'twitter' or 'linkedin'")
    
    try:
        logger.info(f"Platform collection triggered for {platform}")
        
        background_tasks.add_task(run_platform_collection_task, platform)
        
        return {
            "status": "triggered",
            "platform": platform,
            "message": f"{platform} collection started in background",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error triggering {platform} collection: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/logs/recent")
async def get_recent_logs(limit: int = 50):
    """Get recent processing logs"""
    try:
        # This would fetch from database
        return {
            "message": "Log fetching not yet implemented",
            "limit": limit
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def run_collection_task():
    """Background task to run collection"""
    try:
        logger.info("Starting background collection task...")
        results = collector.collect_all_posts()
        logger.info(f"Background collection completed: {results}")
    except Exception as e:
        logger.error(f"Background collection failed: {e}")

def run_platform_collection_task(platform: str):
    """Background task to run platform-specific collection"""
    try:
        logger.info(f"Starting background {platform} collection...")
        results = collector.collect_posts_by_platform(platform)
        logger.info(f"Background {platform} collection completed: {results}")
    except Exception as e:
        logger.error(f"Background {platform} collection failed: {e}")

if __name__ == "__main__":
    # Get port from environment (Railway provides this)
    port = int(os.getenv("PORT", 8080))
    host = "0.0.0.0"  # Listen on all interfaces
    
    logger.info(f"Starting server on {host}:{port}")
    
    # Run the server
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )