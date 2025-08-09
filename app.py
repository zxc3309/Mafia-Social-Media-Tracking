#!/usr/bin/env python3
"""
完整版本的 Social Media Tracking Web Service
包含儀表板、排程器和手動觸發功能
"""

import os
import sys
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, HTMLResponse
import uvicorn

# 導入系統組件
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
    title="Social Media Tracking Dashboard",
    description="自動化社交媒體貼文收集與分析系統",
    version="2.0.0"
)

# Global variables
scheduler = None
collector = PostCollector()

@app.on_event("startup")
async def startup_event():
    """應用啟動時初始化排程器"""
    global scheduler
    try:
        logger.info("=" * 60)
        logger.info("🚀 SOCIAL MEDIA TRACKING WEB SERVICE STARTING")
        logger.info(f"Python version: {sys.version}")
        logger.info(f"PORT environment: {os.getenv('PORT', 'Not set')}")
        logger.info("=" * 60)
        
        # 初始化排程器
        logger.info("🔄 Initializing scheduler...")
        scheduler = get_scheduler(background_mode=True)
        
        # 添加每日收集任務
        scheduler.add_daily_collection_job()
        
        # 啟動排程器
        scheduler.start()
        
        logger.info(f"✅ Scheduler started! Daily collection at {COLLECTION_SCHEDULE_HOUR:02d}:{COLLECTION_SCHEDULE_MINUTE:02d}")
        logger.info("✅ Web service ready!")
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        # 不要崩潰，讓 Web 服務繼續運行
        logger.info("⚠️ Continuing without scheduler...")

@app.on_event("shutdown")
async def shutdown_event():
    """應用關閉時清理排程器"""
    global scheduler
    if scheduler:
        try:
            scheduler.stop()
            logger.info("✅ Scheduler stopped")
        except Exception as e:
            logger.error(f"❌ Error stopping scheduler: {e}")

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """完整的社交媒體追蹤儀表板"""
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
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
            }
            .card { 
                background: white; 
                border-radius: 12px; 
                padding: 25px; 
                margin: 20px 0; 
                box-shadow: 0 8px 32px rgba(0,0,0,0.1);
                backdrop-filter: blur(10px);
            }
            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                text-align: center;
                margin: -25px -25px 25px -25px;
                padding: 40px 25px;
                border-radius: 12px 12px 0 0;
            }
            .status { 
                display: grid; 
                grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); 
                gap: 20px; 
                margin: 25px 0;
            }
            .status-item { 
                padding: 20px; 
                border-radius: 8px; 
                text-align: center;
                transition: transform 0.2s;
            }
            .status-item:hover {
                transform: translateY(-2px);
            }
            .status-good { background: linear-gradient(135deg, #d4edda, #c3e6cb); color: #155724; }
            .status-warning { background: linear-gradient(135deg, #fff3cd, #ffeaa7); color: #856404; }
            .status-error { background: linear-gradient(135deg, #f8d7da, #f5c6cb); color: #721c24; }
            .status-info { background: linear-gradient(135deg, #d1ecf1, #bee5eb); color: #0c5460; }
            
            .btn {
                padding: 14px 28px;
                margin: 8px;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                font-size: 16px;
                font-weight: 500;
                transition: all 0.3s;
                text-decoration: none;
                display: inline-block;
            }
            .btn:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(0,0,0,0.15); }
            .btn-primary { background: linear-gradient(135deg, #007bff, #0056b3); color: white; }
            .btn-success { background: linear-gradient(135deg, #28a745, #1e7e34); color: white; }
            .btn-warning { background: linear-gradient(135deg, #ffc107, #d39e00); color: #212529; }
            .btn-info { background: linear-gradient(135deg, #17a2b8, #138496); color: white; }
            
            .actions { 
                text-align: center; 
                margin: 30px 0;
                padding: 25px;
                background: #f8f9fa;
                border-radius: 8px;
            }
            .log { 
                background: #2d3748; 
                color: #e2e8f0; 
                padding: 20px; 
                border-radius: 8px; 
                font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Fira Code', monospace;
                white-space: pre-wrap;
                max-height: 400px;
                overflow-y: auto;
                line-height: 1.5;
            }
            .loading {
                display: none;
                text-align: center;
                padding: 30px;
                color: #666;
            }
            .spinner {
                border: 4px solid #f3f3f3;
                border-top: 4px solid #007bff;
                border-radius: 50%;
                width: 30px;
                height: 30px;
                animation: spin 1s linear infinite;
                display: inline-block;
                margin-right: 10px;
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            .metric-number {
                font-size: 2em;
                font-weight: bold;
                margin: 10px 0;
            }
            .last-update {
                font-size: 0.9em;
                opacity: 0.8;
                margin-top: 10px;
            }
        </style>
    </head>
    <body>
        <div class="card">
            <div class="header">
                <h1>📊 Social Media Tracking Dashboard</h1>
                <p>自動化社交媒體貼文收集與 AI 分析系統</p>
                <div class="last-update">
                    <span id="current-time">Loading...</span>
                </div>
            </div>
            
            <div class="status" id="status-grid">
                <div class="status-item status-good">
                    <h3>🚀 服務狀態</h3>
                    <div class="metric-number" id="service-status">Loading...</div>
                    <div>排程器運行中</div>
                </div>
                <div class="status-item status-info">
                    <h3>⏰ 下次收集</h3>
                    <div class="metric-number">09:00</div>
                    <div>每日自動執行</div>
                </div>
                <div class="status-item status-warning">
                    <h3>📈 上次收集</h3>
                    <div class="metric-number" id="last-collection">Loading...</div>
                    <div class="last-update" id="collection-time">檢查中...</div>
                </div>
                <div class="status-item status-success">
                    <h3>📊 總貼文數</h3>
                    <div class="metric-number" id="total-posts">Loading...</div>
                    <div>已分析貼文</div>
                </div>
            </div>

            <div class="actions">
                <h3>🎯 手動操作</h3>
                <p>點擊按鈕手動觸發數據收集或查看系統狀態</p>
                
                <button class="btn btn-primary" onclick="triggerCollection()">
                    🚀 觸發完整收集
                </button>
                <button class="btn btn-success" onclick="triggerPlatform('twitter')">
                    🐦 只收集 Twitter
                </button>
                <button class="btn btn-info" onclick="triggerPlatform('linkedin')">
                    💼 只收集 LinkedIn  
                </button>
                <button class="btn btn-warning" onclick="refreshStatus()">
                    🔄 重新整理狀態
                </button>
            </div>

            <div class="loading" id="loading">
                <div class="spinner"></div>
                <h3>⏳ 執行中...</h3>
                <p>請稍候，數據收集正在進行中...</p>
            </div>

            <div class="card">
                <h3>📋 系統活動日誌</h3>
                <div class="log" id="log-output">系統已就緒，點擊上方按鈕開始操作...</div>
            </div>
        </div>

        <script>
            // 更新當前時間
            function updateTime() {
                document.getElementById('current-time').textContent = 
                    new Date().toLocaleString('zh-TW', { timeZone: 'Asia/Taipei' });
            }
            
            // 刷新狀態
            async function refreshStatus() {
                try {
                    log('🔄 正在刷新系統狀態...');
                    const response = await fetch('/status');
                    const data = await response.json();
                    
                    // 更新服務狀態
                    document.getElementById('service-status').textContent = 
                        data.running ? '運行中' : '停止';
                    
                    // 更新統計數據
                    if (data.collection_stats) {
                        const stats = data.collection_stats;
                        document.getElementById('total-posts').textContent = 
                            stats.total_posts || '0';
                        document.getElementById('last-collection').textContent = 
                            stats.today_posts || '0';
                        document.getElementById('collection-time').textContent = 
                            stats.last_updated || '未知';
                    }
                    
                    log('✅ 狀態更新完成');
                } catch (error) {
                    log('❌ 狀態更新失敗: ' + error.message);
                    document.getElementById('service-status').textContent = '錯誤';
                }
            }

            // 觸發完整收集
            async function triggerCollection() {
                const loading = document.getElementById('loading');
                loading.style.display = 'block';
                
                try {
                    log('🚀 開始觸發完整數據收集...');
                    const response = await fetch('/trigger', { 
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' }
                    });
                    const data = await response.json();
                    
                    if (response.ok) {
                        log('✅ 收集已成功觸發！');
                        log('📊 ' + data.message);
                        setTimeout(() => {
                            refreshStatus();
                            log('💡 建議等待 2-3 分鐘查看結果');
                        }, 2000);
                    } else {
                        log('❌ 觸發失敗: ' + (data.detail || '未知錯誤'));
                    }
                } catch (error) {
                    log('❌ 請求錯誤: ' + error.message);
                } finally {
                    loading.style.display = 'none';
                }
            }

            // 觸發平台收集
            async function triggerPlatform(platform) {
                const loading = document.getElementById('loading');
                loading.style.display = 'block';
                
                try {
                    log(`🎯 開始觸發 ${platform.toUpperCase()} 數據收集...`);
                    const response = await fetch(`/trigger/${platform}`, { 
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' }
                    });
                    const data = await response.json();
                    
                    if (response.ok) {
                        log(`✅ ${platform.toUpperCase()} 收集已觸發！`);
                        log('📊 ' + data.message);
                        setTimeout(refreshStatus, 2000);
                    } else {
                        log(`❌ ${platform} 觸發失敗: ` + (data.detail || '未知錯誤'));
                    }
                } catch (error) {
                    log('❌ 請求錯誤: ' + error.message);
                } finally {
                    loading.style.display = 'none';
                }
            }

            // 記錄日誌
            function log(message) {
                const logOutput = document.getElementById('log-output');
                const timestamp = new Date().toLocaleString('zh-TW');
                const newMessage = `[${timestamp}] ${message}\\n`;
                logOutput.textContent += newMessage;
                logOutput.scrollTop = logOutput.scrollHeight;
            }

            // 初始化
            document.addEventListener('DOMContentLoaded', function() {
                updateTime();
                refreshStatus();
                
                // 每30秒更新時間和狀態
                setInterval(updateTime, 30000);
                setInterval(refreshStatus, 30000);
                
                log('🌐 儀表板已載入完成');
                log('💡 系統每 30 秒自動刷新狀態');
            });
        </script>
    </body>
    </html>
    """
    return html_content

@app.get("/health")
async def health_check():
    """健康檢查端點"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "social-media-tracker",
        "mode": "full",
        "scheduler": "active" if scheduler and scheduler.scheduler.running else "inactive",
        "port": os.getenv("PORT", "8080")
    }

@app.get("/status")
async def get_status():
    """獲取詳細系統狀態"""
    try:
        result = {
            "running": True,
            "timestamp": datetime.utcnow().isoformat(),
            "scheduler_active": scheduler and scheduler.scheduler.running,
            "next_collection": f"{COLLECTION_SCHEDULE_HOUR:02d}:{COLLECTION_SCHEDULE_MINUTE:02d} daily"
        }
        
        # 添加排程器狀態
        if scheduler:
            try:
                scheduler_status = scheduler.get_job_status()
                result.update(scheduler_status)
            except Exception as e:
                logger.error(f"Error getting scheduler status: {e}")
                result["scheduler_error"] = str(e)
        
        # 添加收集統計
        try:
            stats = collector.get_collection_stats()
            if 'error' not in stats:
                result['collection_stats'] = stats
            else:
                result['collection_stats'] = {"error": stats['error']}
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            result['collection_stats'] = {"error": str(e)}
        
        return result
        
    except Exception as e:
        logger.error(f"Error in get_status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/trigger")
async def trigger_collection(background_tasks: BackgroundTasks):
    """手動觸發完整收集"""
    try:
        logger.info("Manual collection triggered via web interface")
        
        # 在背景執行收集任務
        background_tasks.add_task(run_collection_task)
        
        return {
            "status": "triggered",
            "message": "完整數據收集已在背景啟動",
            "timestamp": datetime.utcnow().isoformat(),
            "estimated_duration": "2-5 分鐘"
        }
        
    except Exception as e:
        logger.error(f"Error triggering collection: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/trigger/{platform}")
async def trigger_platform_collection(platform: str, background_tasks: BackgroundTasks):
    """觸發特定平台的收集"""
    if platform not in ['twitter', 'linkedin']:
        raise HTTPException(status_code=400, detail="無效的平台。請使用 'twitter' 或 'linkedin'")
    
    try:
        logger.info(f"Platform collection triggered for {platform}")
        
        # 在背景執行平台收集
        background_tasks.add_task(run_platform_collection_task, platform)
        
        return {
            "status": "triggered",
            "platform": platform,
            "message": f"{platform.upper()} 數據收集已在背景啟動",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error triggering {platform} collection: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 背景任務函數
def run_collection_task():
    """背景執行完整收集任務"""
    try:
        logger.info("🚀 Starting background full collection...")
        results = collector.collect_all_posts()
        logger.info(f"✅ Background collection completed: {results}")
    except Exception as e:
        logger.error(f"❌ Background collection failed: {e}")

def run_platform_collection_task(platform: str):
    """背景執行平台收集任務"""
    try:
        logger.info(f"🚀 Starting background {platform} collection...")
        results = collector.collect_posts_by_platform(platform)
        logger.info(f"✅ Background {platform} collection completed: {results}")
    except Exception as e:
        logger.error(f"❌ Background {platform} collection failed: {e}")

if __name__ == "__main__":
    # 直接啟動模式（用於測試）
    port = int(os.getenv("PORT", 8080))
    logger.info("🌐 Starting Social Media Tracking Web Service")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")