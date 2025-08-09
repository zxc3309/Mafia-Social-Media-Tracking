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
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
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

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Main dashboard with web interface"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Social Media Tracking Dashboard</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                max-width: 1200px; 
                margin: 0 auto; 
                padding: 20px; 
                background: #f5f5f5;
            }
            .card { 
                background: white; 
                border-radius: 8px; 
                padding: 20px; 
                margin: 20px 0; 
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                text-align: center;
                margin: -20px -20px 20px -20px;
                padding: 30px 20px;
                border-radius: 8px 8px 0 0;
            }
            .status { 
                display: grid; 
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); 
                gap: 20px; 
            }
            .status-item { 
                padding: 15px; 
                border-radius: 6px; 
                text-align: center;
            }
            .status-good { background: #d4edda; color: #155724; }
            .status-warning { background: #fff3cd; color: #856404; }
            .status-error { background: #f8d7da; color: #721c24; }
            .btn {
                padding: 12px 24px;
                margin: 5px;
                border: none;
                border-radius: 6px;
                cursor: pointer;
                font-size: 16px;
                transition: all 0.3s;
            }
            .btn-primary { background: #007bff; color: white; }
            .btn-primary:hover { background: #0056b3; }
            .btn-success { background: #28a745; color: white; }
            .btn-success:hover { background: #1e7e34; }
            .btn-warning { background: #ffc107; color: #212529; }
            .btn-warning:hover { background: #d39e00; }
            .actions { text-align: center; margin: 20px 0; }
            .log { 
                background: #2d3748; 
                color: #e2e8f0; 
                padding: 15px; 
                border-radius: 6px; 
                font-family: 'Courier New', monospace;
                white-space: pre-wrap;
                max-height: 300px;
                overflow-y: auto;
            }
            .loading {
                display: none;
                text-align: center;
                padding: 20px;
                color: #666;
            }
        </style>
    </head>
    <body>
        <div class="card">
            <div class="header">
                <h1>📊 Social Media Tracking Dashboard</h1>
                <p>Automated Social Media Post Collection & Analysis</p>
            </div>
            
            <div class="status" id="status-grid">
                <div class="status-item status-good">
                    <h3>🚀 Service Status</h3>
                    <p id="service-status">Loading...</p>
                </div>
                <div class="status-item status-good">
                    <h3>⏰ Next Collection</h3>
                    <p id="next-collection">每日 09:00</p>
                </div>
                <div class="status-item status-warning">
                    <h3>📈 Last Collection</h3>
                    <p id="last-collection">Loading...</p>
                </div>
                <div class="status-item status-good">
                    <h3>📊 Total Posts</h3>
                    <p id="total-posts">Loading...</p>
                </div>
            </div>

            <div class="actions">
                <h3>🎯 Manual Triggers</h3>
                <button class="btn btn-primary" onclick="triggerCollection()">
                    🚀 觸發完整收集
                </button>
                <button class="btn btn-success" onclick="triggerPlatform('twitter')">
                    🐦 只收集 Twitter
                </button>
                <button class="btn btn-warning" onclick="triggerPlatform('linkedin')">
                    💼 只收集 LinkedIn
                </button>
                <button class="btn btn-primary" onclick="refreshStatus()">
                    🔄 重新整理狀態
                </button>
            </div>

            <div class="loading" id="loading">
                <h3>⏳ 執行中...</h3>
                <p>請稍候，數據收集正在進行中...</p>
            </div>

            <div class="card">
                <h3>📋 系統日誌</h3>
                <div class="log" id="log-output">點擊上方按鈕開始操作...</div>
            </div>
        </div>

        <script>
            async function refreshStatus() {
                try {
                    const response = await fetch('/status');
                    const data = await response.json();
                    
                    document.getElementById('service-status').textContent = 
                        data.running ? '✅ 運行中' : '❌ 停止';
                    
                    if (data.collection_stats) {
                        document.getElementById('total-posts').textContent = 
                            data.collection_stats.total_posts || '0';
                        document.getElementById('last-collection').textContent = 
                            data.collection_stats.last_updated || '未知';
                    }
                    
                    log('✅ 狀態更新完成');
                } catch (error) {
                    log('❌ 狀態更新失敗: ' + error.message);
                }
            }

            async function triggerCollection() {
                const loading = document.getElementById('loading');
                loading.style.display = 'block';
                
                try {
                    log('🚀 開始觸發完整收集...');
                    const response = await fetch('/trigger', { method: 'POST' });
                    const data = await response.json();
                    
                    if (response.ok) {
                        log('✅ 收集已觸發: ' + data.message);
                        setTimeout(refreshStatus, 2000);
                    } else {
                        log('❌ 觸發失敗: ' + data.detail);
                    }
                } catch (error) {
                    log('❌ 請求錯誤: ' + error.message);
                } finally {
                    loading.style.display = 'none';
                }
            }

            async function triggerPlatform(platform) {
                const loading = document.getElementById('loading');
                loading.style.display = 'block';
                
                try {
                    log(`🎯 開始觸發 ${platform} 收集...`);
                    const response = await fetch(`/trigger/${platform}`, { method: 'POST' });
                    const data = await response.json();
                    
                    if (response.ok) {
                        log(`✅ ${platform} 收集已觸發: ` + data.message);
                        setTimeout(refreshStatus, 2000);
                    } else {
                        log(`❌ ${platform} 觸發失敗: ` + data.detail);
                    }
                } catch (error) {
                    log('❌ 請求錯誤: ' + error.message);
                } finally {
                    loading.style.display = 'none';
                }
            }

            function log(message) {
                const logOutput = document.getElementById('log-output');
                const timestamp = new Date().toLocaleString('zh-TW');
                logOutput.textContent += `[${timestamp}] ${message}\\n`;
                logOutput.scrollTop = logOutput.scrollHeight;
            }

            // 初始載入
            refreshStatus();
            
            // 每30秒自動刷新狀態
            setInterval(refreshStatus, 30000);
        </script>
    </body>
    </html>
    """
    return html_content

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