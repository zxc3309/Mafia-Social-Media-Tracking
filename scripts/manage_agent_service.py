#!/usr/bin/env python3
"""
管理 Twitter Agent Service (Node.js)
提供安裝、啟動、停止、狀態檢查等功能
"""

import os
import sys
import subprocess
import time
import signal
import json
import argparse
import requests
from pathlib import Path

# 添加專案根目錄到 Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import AGENT_CLIENT_CONFIG


class AgentServiceManager:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.service_dir = self.project_root / 'node_service'
        self.pid_file = self.service_dir / '.agent_service.pid'
        self.log_file = self.service_dir / 'agent_service.log'
        self.port = AGENT_CLIENT_CONFIG.get('service_port', 3456)
        self.service_url = f"http://localhost:{self.port}"
    
    def install(self):
        """安裝 Node.js 依賴"""
        print("🔧 Installing dependencies...")
        
        # 檢查 Node.js 是否安裝
        try:
            result = subprocess.run(['node', '--version'], 
                                  capture_output=True, 
                                  text=True,
                                  check=True)
            print(f"✓ Node.js version: {result.stdout.strip()}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("❌ Node.js is not installed. Please install Node.js v18+ first.")
            print("   Visit: https://nodejs.org/")
            return False
        
        # 檢查 npm 是否安裝
        try:
            result = subprocess.run(['npm', '--version'], 
                                  capture_output=True, 
                                  text=True,
                                  check=True)
            print(f"✓ npm version: {result.stdout.strip()}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("❌ npm is not installed.")
            return False
        
        # 安裝 node_service 依賴
        print("\n📦 Installing service dependencies...")
        try:
            subprocess.run(['npm', 'install'], 
                         cwd=self.service_dir,
                         check=True)
            print("✓ Service dependencies installed")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install service dependencies: {e}")
            return False
        
        # 安裝並編譯 agent-twitter-client
        print("\n📦 Building agent-twitter-client...")
        agent_dir = self.service_dir / 'agent-twitter-client'
        
        if not agent_dir.exists():
            print("❌ agent-twitter-client not found. Please ensure it's copied to node_service/")
            return False
        
        try:
            # 安裝依賴
            print("  Installing agent-twitter-client dependencies...")
            subprocess.run(['npm', 'install'], 
                         cwd=agent_dir,
                         check=True)
            
            # 編譯 TypeScript
            print("  Building TypeScript...")
            subprocess.run(['npm', 'run', 'build'], 
                         cwd=agent_dir,
                         check=True)
            
            print("✓ agent-twitter-client built successfully")
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to build agent-twitter-client: {e}")
            return False
        
        print("\n✅ Installation complete!")
        return True
    
    def start(self):
        """啟動服務"""
        # 檢查是否已經在運行
        if self.is_running():
            print(f"⚠️  Service is already running on port {self.port}")
            return True
        
        # 檢查依賴是否已安裝
        if not (self.service_dir / 'node_modules').exists():
            print("📦 Dependencies not installed. Running installation...")
            if not self.install():
                return False
        
        print(f"🚀 Starting Twitter Agent Service on port {self.port}...")
        
        # 準備環境變數
        env = os.environ.copy()
        env['AGENT_SERVICE_PORT'] = str(self.port)
        
        # 啟動服務
        with open(self.log_file, 'a') as log:
            process = subprocess.Popen(
                ['node', 'twitter_service.js'],
                cwd=self.service_dir,
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True
            )
        
        # 保存 PID
        with open(self.pid_file, 'w') as f:
            f.write(str(process.pid))
        
        # 等待服務啟動
        print("⏳ Waiting for service to start...")
        for i in range(30):
            time.sleep(1)
            if self.is_running():
                print(f"✅ Service started successfully on port {self.port}")
                print(f"   PID: {process.pid}")
                print(f"   Logs: {self.log_file}")
                return True
        
        print("❌ Failed to start service within timeout")
        return False
    
    def stop(self):
        """停止服務"""
        if not self.pid_file.exists():
            print("⚠️  No PID file found. Service may not be running.")
            return True
        
        try:
            with open(self.pid_file, 'r') as f:
                pid = int(f.read().strip())
            
            print(f"🛑 Stopping service (PID: {pid})...")
            
            # 發送 SIGTERM
            os.kill(pid, signal.SIGTERM)
            
            # 等待進程結束
            for i in range(10):
                time.sleep(0.5)
                try:
                    os.kill(pid, 0)  # 檢查進程是否還在
                except ProcessLookupError:
                    # 進程已結束
                    self.pid_file.unlink()
                    print("✅ Service stopped successfully")
                    return True
            
            # 如果還沒停止，使用 SIGKILL
            print("⚠️  Service not responding, forcing stop...")
            os.kill(pid, signal.SIGKILL)
            self.pid_file.unlink()
            print("✅ Service force stopped")
            return True
            
        except Exception as e:
            print(f"❌ Error stopping service: {e}")
            return False
    
    def restart(self):
        """重啟服務"""
        print("🔄 Restarting service...")
        if self.is_running():
            self.stop()
            time.sleep(2)
        return self.start()
    
    def status(self):
        """檢查服務狀態"""
        print("📊 Service Status")
        print("-" * 40)
        
        # 檢查 PID 文件
        if self.pid_file.exists():
            with open(self.pid_file, 'r') as f:
                pid = f.read().strip()
            print(f"PID file: {pid}")
        else:
            print("PID file: Not found")
        
        # 檢查服務健康狀態
        if self.is_running():
            try:
                response = requests.get(f"{self.service_url}/health", timeout=2)
                if response.status_code == 200:
                    health = response.json()
                    print(f"Status: ✅ Running")
                    print(f"Port: {self.port}")
                    print(f"Logged in: {health.get('isLoggedIn', False)}")
                    print(f"Last login: {health.get('lastLoginTime', 'Never')}")
                    print(f"Uptime: {health.get('uptime', 0):.0f} seconds")
            except Exception as e:
                print(f"Status: ⚠️  Running but not responding")
                print(f"Error: {e}")
        else:
            print(f"Status: ❌ Not running")
        
        # 檢查環境變數
        print("\n📝 Configuration:")
        print(f"Username: {'✓ Set' if os.getenv('TWITTER_USERNAME') else '✗ Not set'}")
        print(f"Password: {'✓ Set' if os.getenv('TWITTER_PASSWORD') else '✗ Not set'}")
        print(f"Email: {'✓ Set' if os.getenv('TWITTER_EMAIL') else '✗ Not set'}")
        print(f"2FA Secret: {'✓ Set' if os.getenv('TWITTER_2FA_SECRET') else '✗ Not set'}")
        
        # 顯示最近的日誌
        if self.log_file.exists():
            print(f"\n📄 Recent logs from {self.log_file}:")
            print("-" * 40)
            try:
                with open(self.log_file, 'r') as f:
                    lines = f.readlines()
                    recent = lines[-10:] if len(lines) > 10 else lines
                    for line in recent:
                        print(line.rstrip())
            except Exception as e:
                print(f"Error reading logs: {e}")
    
    def logs(self, lines=50, follow=False):
        """查看服務日誌"""
        if not self.log_file.exists():
            print("❌ Log file not found")
            return
        
        if follow:
            # 使用 tail -f
            print(f"📄 Following logs from {self.log_file} (Ctrl+C to stop)...")
            try:
                subprocess.run(['tail', '-f', str(self.log_file)])
            except KeyboardInterrupt:
                print("\n✅ Stopped following logs")
        else:
            # 顯示最近的日誌
            print(f"📄 Last {lines} lines from {self.log_file}:")
            print("-" * 40)
            try:
                with open(self.log_file, 'r') as f:
                    all_lines = f.readlines()
                    recent = all_lines[-lines:] if len(all_lines) > lines else all_lines
                    for line in recent:
                        print(line.rstrip())
            except Exception as e:
                print(f"Error reading logs: {e}")
    
    def test(self):
        """測試服務連接"""
        print("🧪 Testing service connection...")
        
        if not self.is_running():
            print("❌ Service is not running")
            return False
        
        try:
            response = requests.get(f"{self.service_url}/test", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    print("✅ Service test successful")
                    print(f"   Message: {data.get('message')}")
                    print(f"   Logged in: {data.get('isLoggedIn')}")
                    return True
                else:
                    print(f"❌ Service test failed: {data.get('error')}")
                    return False
            else:
                print(f"❌ Service returned status code: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Connection test failed: {e}")
            return False
    
    def is_running(self):
        """檢查服務是否在運行"""
        try:
            response = requests.get(f"{self.service_url}/health", timeout=2)
            return response.status_code == 200
        except:
            return False


def main():
    parser = argparse.ArgumentParser(description='Manage Twitter Agent Service')
    parser.add_argument('command', 
                       choices=['install', 'start', 'stop', 'restart', 
                               'status', 'logs', 'test'],
                       help='Command to execute')
    parser.add_argument('--lines', '-n', 
                       type=int, 
                       default=50,
                       help='Number of log lines to show (for logs command)')
    parser.add_argument('--follow', '-f',
                       action='store_true',
                       help='Follow log output (for logs command)')
    
    args = parser.parse_args()
    
    manager = AgentServiceManager()
    
    if args.command == 'install':
        manager.install()
    elif args.command == 'start':
        manager.start()
    elif args.command == 'stop':
        manager.stop()
    elif args.command == 'restart':
        manager.restart()
    elif args.command == 'status':
        manager.status()
    elif args.command == 'logs':
        manager.logs(lines=args.lines, follow=args.follow)
    elif args.command == 'test':
        manager.test()


if __name__ == '__main__':
    main()