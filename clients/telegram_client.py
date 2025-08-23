"""
Telegram Bot client for sending daily reports
"""

import logging
from typing import Optional
import httpx
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_ENABLED

logger = logging.getLogger(__name__)


class TelegramClient:
    """Simple Telegram Bot client for sending messages"""
    
    def __init__(self):
        self.bot_token = TELEGRAM_BOT_TOKEN
        self.chat_id = TELEGRAM_CHAT_ID
        self.enabled = TELEGRAM_ENABLED
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        
        if self.enabled and not self.bot_token:
            logger.warning("Telegram is enabled but TELEGRAM_BOT_TOKEN is not set")
            self.enabled = False
            
        if self.enabled and not self.chat_id:
            logger.warning("Telegram is enabled but TELEGRAM_CHAT_ID is not set")
            self.enabled = False
            
    def send_message(self, text: str, parse_mode: str = "Markdown") -> bool:
        """
        Send a message to the configured Telegram chat
        
        Args:
            text: Message text to send
            parse_mode: Parse mode for formatting ("Markdown" or "HTML")
            
        Returns:
            True if message was sent successfully, False otherwise
        """
        if not self.enabled:
            logger.debug("Telegram notifications are disabled")
            return False
            
        try:
            # Telegram API endpoint
            url = f"{self.base_url}/sendMessage"
            
            # Message payload
            payload = {
                "chat_id": self.chat_id,
                "text": text,
                "disable_web_page_preview": True
            }
            
            # Only add parse_mode if it's not None
            if parse_mode is not None:
                payload["parse_mode"] = parse_mode
            
            # Send request
            with httpx.Client(timeout=30.0) as client:
                response = client.post(url, json=payload)
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("ok"):
                        logger.info("Successfully sent Telegram message")
                        return True
                    else:
                        logger.error(f"Telegram API error: {result.get('description', 'Unknown error')}")
                        return False
                else:
                    logger.error(f"Failed to send Telegram message: HTTP {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")
            return False
            
    def send_long_message(self, text: str, parse_mode: str = "Markdown") -> bool:
        """
        Send a long message, splitting if necessary (Telegram has 4096 char limit)
        
        Args:
            text: Message text to send
            parse_mode: Parse mode for formatting
            
        Returns:
            True if all parts were sent successfully
        """
        if not self.enabled:
            return False
            
        # Telegram message limit
        MAX_LENGTH = 4000  # Leave some buffer
        
        if len(text) <= MAX_LENGTH:
            return self.send_message(text, parse_mode)
            
        # Split message into parts
        parts = []
        current_part = ""
        
        for line in text.split('\n'):
            if len(current_part) + len(line) + 1 > MAX_LENGTH:
                parts.append(current_part)
                current_part = line
            else:
                if current_part:
                    current_part += '\n'
                current_part += line
                
        if current_part:
            parts.append(current_part)
            
        # Send all parts
        success = True
        for i, part in enumerate(parts):
            if i > 0:
                # Add continuation marker
                part = f"... (continued {i+1}/{len(parts)})\n\n{part}"
                
            if not self.send_message(part, parse_mode):
                success = False
                
        return success
        
    def test_connection(self) -> bool:
        """
        Test the Telegram bot connection
        
        Returns:
            True if connection is successful
        """
        if not self.enabled:
            logger.info("Telegram is not enabled")
            return False
            
        try:
            # Test with getMe endpoint
            url = f"{self.base_url}/getMe"
            
            with httpx.Client(timeout=10.0) as client:
                response = client.get(url)
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("ok"):
                        bot_info = result.get("result", {})
                        logger.info(f"Connected to Telegram bot: @{bot_info.get('username', 'unknown')}")
                        return True
                        
            logger.error("Failed to connect to Telegram bot")
            return False
            
        except Exception as e:
            logger.error(f"Error testing Telegram connection: {e}")
            return False