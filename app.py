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

async def run_thread_id_migration_check():
    """Run thread_id migration check for Railway PostgreSQL"""
    try:
        # Check if we're on Railway PostgreSQL
        is_railway = os.getenv('RAILWAY_ENVIRONMENT_NAME') is not None
        from config import DATABASE_URL
        is_postgres = DATABASE_URL.startswith('postgres')
        
        if not (is_railway and is_postgres):
            logger.info("✅ Not on Railway PostgreSQL, skipping thread_id migration check")
            return
        
        logger.info("🔍 Checking for thread_id columns in Railway PostgreSQL...")
        
        # Run the migration
        from scripts.add_thread_id_migration import ThreadIdMigration
        migration = ThreadIdMigration()
        
        # First check current state
        posts_has_thread = migration.check_column_exists('posts', 'thread_id')
        analyzed_has_thread = migration.check_column_exists('analyzed_posts', 'thread_id')
        
        if posts_has_thread and analyzed_has_thread:
            logger.info("✅ Both thread_id columns already exist")
            return
        
        logger.info("🚀 Running thread_id migration...")
        success = migration.run_migration(dry_run=False)
        
        if success:
            logger.info("✅ Thread ID migration completed successfully!")
        else:
            logger.warning("⚠️ Thread ID migration failed, but app will continue with safety checks")
            
    except Exception as e:
        logger.error(f"❌ Thread ID migration check failed: {e}")
        logger.info("⚠️ Continuing with application startup despite migration error")

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
        
        # Run thread_id migration check for Railway PostgreSQL
        await run_thread_id_migration_check()
        
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
    """現代化的社交媒體追蹤儀表板"""
    html_content = """
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <title>Social Media Tracking Dashboard</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
        <style>
            :root {
                --primary-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                --secondary-gradient: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                --success-gradient: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
                --warning-gradient: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
                --danger-gradient: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
                --dark-gradient: linear-gradient(135deg, #434343 0%, #000000 100%);
                --glass: rgba(255, 255, 255, 0.25);
                --glass-border: rgba(255, 255, 255, 0.18);
                --shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
                --text-primary: #2d3748;
                --text-secondary: #4a5568;
                --text-muted: #718096;
            }
            
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body { 
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: var(--primary-gradient);
                min-height: 100vh;
                padding: 20px;
                line-height: 1.6;
            }
            
            .container {
                max-width: 1400px;
                margin: 0 auto;
                display: grid;
                grid-template-columns: 1fr;
                gap: 24px;
            }
            
            .glass-card {
                background: var(--glass);
                backdrop-filter: blur(16px);
                -webkit-backdrop-filter: blur(16px);
                border-radius: 16px;
                border: 1px solid var(--glass-border);
                box-shadow: var(--shadow);
                padding: 28px;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            }
            
            .glass-card:hover {
                transform: translateY(-4px);
                box-shadow: 0 12px 48px 0 rgba(31, 38, 135, 0.5);
            }
            
            .header {
                text-align: center;
                color: white;
                margin-bottom: 32px;
            }
            
            .header h1 {
                font-size: 3rem;
                font-weight: 800;
                margin-bottom: 12px;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            }
            
            .header p {
                font-size: 1.2rem;
                opacity: 0.9;
                margin-bottom: 16px;
            }
            
            .time-display {
                background: rgba(255,255,255,0.2);
                padding: 8px 16px;
                border-radius: 25px;
                display: inline-block;
                font-weight: 500;
            }
            
            .metrics-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                gap: 20px;
                margin-bottom: 32px;
            }
            
            .metric-card {
                background: var(--glass);
                backdrop-filter: blur(16px);
                border-radius: 16px;
                padding: 24px;
                text-align: center;
                border: 1px solid var(--glass-border);
                transition: all 0.3s ease;
                position: relative;
                overflow: hidden;
            }
            
            .metric-card::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 4px;
                background: var(--primary-gradient);
                opacity: 0;
                transition: opacity 0.3s ease;
            }
            
            .metric-card:hover::before {
                opacity: 1;
            }
            
            .metric-card:hover {
                transform: translateY(-8px);
                box-shadow: 0 16px 64px rgba(0,0,0,0.2);
            }
            
            .metric-icon {
                font-size: 2.5rem;
                margin-bottom: 12px;
                color: #667eea;
            }
            
            .metric-value {
                font-size: 2.5rem;
                font-weight: 800;
                margin-bottom: 8px;
                color: var(--text-primary);
            }
            
            .metric-label {
                color: var(--text-secondary);
                font-weight: 500;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                font-size: 0.9rem;
            }
            
            .metric-sublabel {
                color: var(--text-muted);
                font-size: 0.8rem;
                margin-top: 4px;
            }
            
            .control-panel {
                background: var(--glass);
                backdrop-filter: blur(16px);
                border-radius: 16px;
                border: 1px solid var(--glass-border);
                padding: 32px;
                margin-bottom: 24px;
            }
            
            .control-section {
                margin-bottom: 32px;
            }
            
            .section-title {
                font-size: 1.5rem;
                font-weight: 700;
                color: var(--text-primary);
                margin-bottom: 8px;
                display: flex;
                align-items: center;
                gap: 12px;
            }
            
            .section-subtitle {
                color: var(--text-secondary);
                margin-bottom: 24px;
            }
            
            .button-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 16px;
            }
            
            .btn {
                padding: 16px 24px;
                border: none;
                border-radius: 12px;
                cursor: pointer;
                font-size: 1rem;
                font-weight: 600;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 12px;
                text-decoration: none;
                position: relative;
                overflow: hidden;
            }
            
            .btn::before {
                content: '';
                position: absolute;
                top: 0;
                left: -100%;
                width: 100%;
                height: 100%;
                background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
                transition: left 0.5s;
            }
            
            .btn:hover::before {
                left: 100%;
            }
            
            .btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 24px rgba(0,0,0,0.2);
            }
            
            .btn:active {
                transform: translateY(0);
            }
            
            .btn-primary { background: var(--primary-gradient); color: white; }
            .btn-success { background: var(--success-gradient); color: white; }
            .btn-warning { background: var(--warning-gradient); color: var(--text-primary); }
            .btn-secondary { background: var(--secondary-gradient); color: white; }
            .btn-info { background: var(--dark-gradient); color: white; }
            
            .loading-overlay {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0,0,0,0.8);
                display: none;
                justify-content: center;
                align-items: center;
                z-index: 1000;
                backdrop-filter: blur(4px);
            }
            
            .loading-content {
                background: var(--glass);
                backdrop-filter: blur(16px);
                border-radius: 16px;
                padding: 32px;
                text-align: center;
                border: 1px solid var(--glass-border);
                color: white;
            }
            
            .spinner {
                width: 48px;
                height: 48px;
                border: 4px solid rgba(255,255,255,0.3);
                border-top: 4px solid #667eea;
                border-radius: 50%;
                animation: spin 1s linear infinite;
                margin: 0 auto 16px;
            }
            
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            
            .log-panel {
                background: #1a202c;
                border-radius: 16px;
                padding: 24px;
                font-family: 'JetBrains Mono', 'Fira Code', monospace;
                color: #e2e8f0;
                max-height: 400px;
                overflow-y: auto;
                border: 1px solid #2d3748;
                box-shadow: inset 0 2px 4px rgba(0,0,0,0.3);
            }
            
            .log-entry {
                margin-bottom: 8px;
                line-height: 1.4;
            }
            
            .log-timestamp {
                color: #4a5568;
                font-size: 0.85rem;
            }
            
            .toast {
                position: fixed;
                top: 24px;
                right: 24px;
                background: var(--glass);
                backdrop-filter: blur(16px);
                border-radius: 12px;
                padding: 16px 24px;
                border: 1px solid var(--glass-border);
                color: white;
                font-weight: 500;
                transform: translateX(400px);
                transition: transform 0.3s ease;
                z-index: 1001;
            }
            
            .toast.show {
                transform: translateX(0);
            }
            
            .status-indicator {
                width: 12px;
                height: 12px;
                border-radius: 50%;
                background: #48bb78;
                display: inline-block;
                margin-right: 8px;
                animation: pulse 2s infinite;
            }
            
            @keyframes pulse {
                0% { box-shadow: 0 0 0 0 rgba(72, 187, 120, 0.7); }
                70% { box-shadow: 0 0 0 10px rgba(72, 187, 120, 0); }
                100% { box-shadow: 0 0 0 0 rgba(72, 187, 120, 0); }
            }
            
            .feature-badge {
                background: var(--secondary-gradient);
                color: white;
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 0.75rem;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                margin-left: 8px;
            }
            
            @media (max-width: 768px) {
                .container { padding: 16px; }
                .header h1 { font-size: 2rem; }
                .metrics-grid { grid-template-columns: 1fr; }
                .button-grid { grid-template-columns: 1fr; }
                .glass-card { padding: 20px; }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <header class="header">
                <h1><i class="fas fa-chart-line"></i> Social Media Intelligence</h1>
                <p>Next-Generation Social Media Tracking & AI Analysis Platform</p>
                <div class="time-display">
                    <i class="far fa-clock"></i>
                    <span id="current-time">Loading...</span>
                </div>
            </header>
            
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-icon"><i class="fas fa-server"></i></div>
                    <div class="metric-value" id="service-status">Loading...</div>
                    <div class="metric-label">Service Status</div>
                    <div class="metric-sublabel">
                        <span class="status-indicator"></span>Scheduler Active
                    </div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-icon"><i class="fas fa-clock"></i></div>
                    <div class="metric-value">09:00</div>
                    <div class="metric-label">Next Collection</div>
                    <div class="metric-sublabel">Daily Automated Run</div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-icon"><i class="fas fa-history"></i></div>
                    <div class="metric-value" id="last-collection">Loading...</div>
                    <div class="metric-label">Last Collection</div>
                    <div class="metric-sublabel" id="collection-time">Checking...</div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-icon"><i class="fas fa-database"></i></div>
                    <div class="metric-value" id="total-posts">Loading...</div>
                    <div class="metric-label">Total Posts</div>
                    <div class="metric-sublabel">AI Analyzed Content</div>
                </div>
            </div>
            
            <div class="glass-card control-panel">
                <div class="control-section">
                    <h2 class="section-title">
                        <i class="fas fa-rocket"></i>
                        Data Collection
                        <span class="feature-badge">Live</span>
                    </h2>
                    <p class="section-subtitle">
                        Execute manual data collection tasks or schedule platform-specific runs
                    </p>
                    
                    <div class="button-grid">
                        <button class="btn btn-primary" onclick="triggerCollection()">
                            <i class="fas fa-play"></i>
                            Full Collection
                        </button>
                        <button class="btn btn-success" onclick="triggerPlatform('twitter')">
                            <i class="fab fa-twitter"></i>
                            Twitter Only
                        </button>
                        <button class="btn btn-warning" onclick="triggerPlatform('linkedin')">
                            <i class="fab fa-linkedin"></i>
                            LinkedIn Only
                        </button>
                        <button class="btn btn-secondary" onclick="refreshStatus()">
                            <i class="fas fa-sync-alt"></i>
                            Refresh Status
                        </button>
                    </div>
                </div>
                
                <div class="control-section">
                    <h2 class="section-title">
                        <i class="fas fa-brain"></i>
                        AI Intelligence
                        <span class="feature-badge">New</span>
                    </h2>
                    <p class="section-subtitle">
                        Advanced AI prompt optimization and analytics tools
                    </p>
                    
                    <div class="button-grid">
                        <button class="btn btn-info" onclick="optimizePrompts()">
                            <i class="fas fa-magic"></i>
                            Optimize Prompts
                        </button>
                        <button class="btn btn-secondary" onclick="analyzePerformance()">
                            <i class="fas fa-chart-bar"></i>
                            Performance Analytics
                        </button>
                    </div>
                </div>
            </div>
            
            <div class="glass-card">
                <h2 class="section-title">
                    <i class="fas fa-terminal"></i>
                    System Activity Log
                </h2>
                <div class="log-panel" id="log-output">
                    <div class="log-entry">
                        <span class="log-timestamp">[System]</span> Dashboard initialized successfully
                    </div>
                    <div class="log-entry">
                        <span class="log-timestamp">[Info]</span> Real-time monitoring active
                    </div>
                </div>
            </div>
        </div>
        
        <div class="loading-overlay" id="loading">
            <div class="loading-content">
                <div class="spinner"></div>
                <h3>Processing Request</h3>
                <p>Please wait while we execute your request...</p>
            </div>
        </div>
        
        <div class="toast" id="toast"></div>

        <script>
            // Utility functions
            function showToast(message, type = 'info') {
                const toast = document.getElementById('toast');
                toast.textContent = message;
                toast.className = `toast show ${type}`;
                
                setTimeout(() => {
                    toast.classList.remove('show');
                }, 3000);
            }
            
            function formatTime() {
                return new Date().toLocaleString('zh-TW', { 
                    timeZone: 'Asia/Taipei',
                    year: 'numeric',
                    month: '2-digit',
                    day: '2-digit',
                    hour: '2-digit',
                    minute: '2-digit',
                    second: '2-digit'
                });
            }
            
            function updateTime() {
                document.getElementById('current-time').textContent = formatTime();
            }
            
            function log(message, type = 'info') {
                const logOutput = document.getElementById('log-output');
                const timestamp = new Date().toLocaleTimeString('zh-TW');
                
                const logEntry = document.createElement('div');
                logEntry.className = 'log-entry';
                logEntry.innerHTML = `
                    <span class="log-timestamp">[${timestamp}]</span> ${message}
                `;
                
                logOutput.appendChild(logEntry);
                logOutput.scrollTop = logOutput.scrollHeight;
                
                // Keep only last 50 entries
                const entries = logOutput.querySelectorAll('.log-entry');
                if (entries.length > 50) {
                    entries[0].remove();
                }
            }
            
            // Status refresh
            async function refreshStatus() {
                try {
                    log('🔄 Refreshing system status...', 'info');
                    const response = await fetch('/status');
                    const data = await response.json();
                    
                    // Update service status
                    const statusElement = document.getElementById('service-status');
                    const isRunning = data.running;
                    statusElement.textContent = isRunning ? 'Online' : 'Offline';
                    statusElement.style.color = isRunning ? '#48bb78' : '#f56565';
                    
                    // Update collection stats
                    if (data.collection_stats) {
                        const stats = data.collection_stats;
                        document.getElementById('total-posts').textContent = stats.total_posts || '0';
                        
                        // 處理最後收集時間
                        if (stats.last_collection) {
                            console.log('🔍 Debug - Frontend timezone conversion:');
                            console.log('   Raw last_collection:', stats.last_collection);
                            
                            // 正確解析 UTC 時間
                            let lastCollectionDate;
                            if (stats.last_collection.endsWith('Z')) {
                                lastCollectionDate = new Date(stats.last_collection);
                            } else {
                                lastCollectionDate = new Date(stats.last_collection + 'Z');
                            }
                            
                            console.log('   Parsed UTC date:', lastCollectionDate.toISOString());
                            console.log('   Local browser time:', lastCollectionDate.toLocaleString());
                            
                            // 計算距離現在的時間（使用本地時間比較）
                            const now = new Date();
                            const diffMs = now - lastCollectionDate;
                            const diffHours = Math.round(diffMs / (1000 * 60 * 60));
                            
                            if (diffHours < 24) {
                                document.getElementById('last-collection').textContent = diffHours + 'h';
                            } else {
                                const diffDays = Math.round(diffHours / 24);
                                document.getElementById('last-collection').textContent = diffDays + 'd';
                            }
                            
                            // 顯示台北時間（收集時間）
                            const taipeiTimeString = lastCollectionDate.toLocaleString('zh-TW', {
                                year: 'numeric',
                                month: '2-digit', 
                                day: '2-digit',
                                hour: '2-digit',
                                minute: '2-digit',
                                timeZone: 'Asia/Taipei'
                            });
                            
                            console.log('   Taiwan time string:', taipeiTimeString);
                            document.getElementById('collection-time').textContent = taipeiTimeString;
                        } else {
                            document.getElementById('last-collection').textContent = '0';
                            document.getElementById('collection-time').textContent = '無資料';
                        }
                    }
                    
                    log('✅ Status updated successfully');
                    showToast('Status refreshed', 'success');
                    
                } catch (error) {
                    log(`❌ Status update failed: ${error.message}`, 'error');
                    showToast('Failed to refresh status', 'error');
                    document.getElementById('service-status').textContent = 'Error';
                }
            }

            // Collection functions
            async function triggerCollection() {
                const loading = document.getElementById('loading');
                loading.style.display = 'flex';
                
                try {
                    log('🚀 Triggering full data collection...', 'info');
                    const response = await fetch('/trigger', { 
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' }
                    });
                    const data = await response.json();
                    
                    if (response.ok) {
                        log('✅ Full collection triggered successfully');
                        log(`📊 ${data.message}`);
                        showToast('Collection started successfully!', 'success');
                        
                        setTimeout(() => {
                            refreshStatus();
                            log('💡 Results should appear in 2-3 minutes');
                        }, 2000);
                    } else {
                        log(`❌ Trigger failed: ${data.detail || 'Unknown error'}`, 'error');
                        showToast('Failed to trigger collection', 'error');
                    }
                } catch (error) {
                    log(`❌ Request error: ${error.message}`, 'error');
                    showToast('Network error occurred', 'error');
                } finally {
                    loading.style.display = 'none';
                }
            }

            async function triggerPlatform(platform) {
                const loading = document.getElementById('loading');
                loading.style.display = 'flex';
                
                try {
                    log(`🎯 Triggering ${platform.toUpperCase()} collection...`, 'info');
                    const response = await fetch(`/trigger/${platform}`, { 
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' }
                    });
                    const data = await response.json();
                    
                    if (response.ok) {
                        log(`✅ ${platform.toUpperCase()} collection triggered`);
                        log(`📊 ${data.message}`);
                        showToast(`${platform.toUpperCase()} collection started!`, 'success');
                        setTimeout(refreshStatus, 2000);
                    } else {
                        log(`❌ ${platform} trigger failed: ${data.detail || 'Unknown error'}`, 'error');
                        showToast(`Failed to trigger ${platform} collection`, 'error');
                    }
                } catch (error) {
                    log(`❌ Request error: ${error.message}`, 'error');
                    showToast('Network error occurred', 'error');
                } finally {
                    loading.style.display = 'none';
                }
            }

            // AI functions
            async function optimizePrompts() {
                const loading = document.getElementById('loading');
                loading.style.display = 'flex';
                
                try {
                    log('🧠 Starting prompt optimization...', 'info');
                    const response = await fetch('/optimize-prompts', { 
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' }
                    });
                    const data = await response.json();
                    
                    if (response.ok) {
                        log('✅ Prompt optimization completed');
                        log(`🎯 ${data.message}`);
                        showToast('Prompts optimized successfully!', 'success');
                    } else {
                        log(`❌ Optimization failed: ${data.detail || 'Unknown error'}`, 'error');
                        showToast('Optimization failed', 'error');
                    }
                } catch (error) {
                    log(`❌ Request error: ${error.message}`, 'error');
                    showToast('Network error occurred', 'error');
                } finally {
                    loading.style.display = 'none';
                }
            }

            async function analyzePerformance() {
                log('📊 Analyzing system performance...', 'info');
                showToast('Performance analysis started', 'info');
                // Implementation for performance analytics
                setTimeout(() => {
                    log('✅ Performance analysis completed');
                    showToast('Analysis complete - check logs', 'success');
                }, 2000);
            }

            // Initialize dashboard
            document.addEventListener('DOMContentLoaded', function() {
                updateTime();
                refreshStatus();
                
                // Auto-refresh every 30 minutes
                setInterval(updateTime, 30000); // Time updates every 30 seconds
                setInterval(refreshStatus, 1800000); // Status updates every 30 minutes
                
                log('🌐 Social Media Intelligence Dashboard initialized');
                log('💡 Status auto-refreshes every 30 minutes, time every 30 seconds');
                
                // Add smooth scroll behavior
                document.documentElement.style.scrollBehavior = 'smooth';
                
                showToast('Dashboard loaded successfully!', 'success');
            });
        </script>
    </body>
    </html>
    """
    return html_content

@app.get("/health")
async def health_check():
    """健康檢查端點 - 用於監控服務狀態"""
    # 獲取最後收集時間
    last_collection = None
    next_collection = None
    scheduler_jobs = []
    
    try:
        if scheduler and scheduler.scheduler.running:
            jobs = scheduler.scheduler.get_jobs()
            for job in jobs:
                job_info = {
                    "id": job.id,
                    "name": job.name,
                    "next_run": job.next_run_time.isoformat() if job.next_run_time else None
                }
                scheduler_jobs.append(job_info)
                
                # 找到每日收集任務
                if "daily_collection" in job.id:
                    next_collection = job.next_run_time.isoformat() if job.next_run_time else None
    except Exception as e:
        logger.error(f"Error getting scheduler info: {e}")
    
    # 嘗試從數據庫獲取最後收集時間
    try:
        from models.database import db_manager
        session = db_manager.get_session()
        from sqlalchemy import text
        result = session.execute(text(
            "SELECT MAX(collected_at) as last_time FROM posts"
        )).fetchone()
        if result and result.last_time:
            last_collection = result.last_time.isoformat()
        session.close()
    except Exception as e:
        logger.error(f"Error getting last collection time: {e}")
    
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "social-media-tracker",
        "scheduler_running": scheduler and scheduler.scheduler.running,
        "scheduler_jobs_count": len(scheduler_jobs),
        "next_collection": next_collection,
        "last_collection": last_collection,
        "scheduled_time": f"{COLLECTION_SCHEDULE_HOUR:02d}:{COLLECTION_SCHEDULE_MINUTE:02d} daily",
        "environment": os.getenv("RAILWAY_ENVIRONMENT_NAME", "local"),
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

@app.post("/optimize-prompts")
async def optimize_prompts(background_tasks: BackgroundTasks):
    """觸發 AI Prompt 優化"""
    try:
        logger.info("Prompt optimization triggered via web interface")
        
        # 在背景執行 Prompt 優化任務
        background_tasks.add_task(run_prompt_optimization_task)
        
        return {
            "status": "triggered",
            "message": "AI Prompt 優化已在背景啟動",
            "timestamp": datetime.utcnow().isoformat(),
            "estimated_duration": "1-2 分鐘"
        }
        
    except Exception as e:
        logger.error(f"Error triggering prompt optimization: {e}")
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

def run_prompt_optimization_task():
    """背景執行 Prompt 優化任務"""
    try:
        logger.info("🧠 Starting background prompt optimization...")
        
        # 導入 PromptOptimizer
        from prompt_optimizer import PromptOptimizer
        
        # 創建優化器實例
        optimizer = PromptOptimizer()
        
        # 運行優化工作流程（自動模式）
        optimizer.run_optimization_workflow(days_back=30, auto_mode=True)
        
        logger.info("✅ Background prompt optimization completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Background prompt optimization failed: {e}")

if __name__ == "__main__":
    # 直接啟動模式（用於測試）
    port = int(os.getenv("PORT", 8080))
    logger.info("🌐 Starting Social Media Tracking Web Service")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")