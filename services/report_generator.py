"""
Report generator service for creating daily summaries
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from models.database import db_manager, AnalyzedPost
from clients.telegram_client import TelegramClient
from clients.ai_client import AIClient
from clients.google_sheets_client import GoogleSheetsClient
from config import IMPORTANCE_THRESHOLD

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generate and send daily reports via Telegram"""
    
    def __init__(self):
        self.telegram = TelegramClient()
        self.ai_client = AIClient()
        self.sheets_client = GoogleSheetsClient()
        
    def generate_daily_report(self, results: Dict[str, Any]) -> Optional[str]:
        """
        Generate a daily report based on collection results
        
        Args:
            results: Collection results from post_collector
            
        Returns:
            Generated report text or None if no important posts
        """
        try:
            # Get today's important posts
            important_posts = self._get_todays_important_posts()
            
            if not important_posts:
                logger.info("No important posts found for today's report")
                return None
                
            # Generate statistics header (using code, not AI)
            header = self._generate_header(results, len(important_posts))
            
            # Generate AI summary of important posts
            summary = self._generate_ai_summary(important_posts)
            
            # Generate footer
            footer = self._generate_footer(results)
            
            # Combine all parts
            full_report = header + summary + footer
            
            return full_report
            
        except Exception as e:
            logger.error(f"Error generating daily report: {e}")
            return None
            
    def _get_todays_important_posts(self) -> List[AnalyzedPost]:
        """Get today's important posts from database"""
        try:
            # Get last 24 hours (more flexible than strict "today")
            now = datetime.utcnow()
            last_24h = now - timedelta(hours=24)
            
            # Query important posts from last 24 hours
            session = db_manager.get_session()
            try:
                posts = session.query(AnalyzedPost).filter(
                    AnalyzedPost.importance_score >= IMPORTANCE_THRESHOLD,
                    AnalyzedPost.analyzed_at >= last_24h
                ).order_by(
                    AnalyzedPost.author_username,
                    AnalyzedPost.importance_score.desc()
                ).all()
                
                # If no posts in last 24h, get recent important posts for reporting
                if not posts:
                    logger.info("No important posts in last 24h, getting recent important posts")
                    posts = session.query(AnalyzedPost).filter(
                        AnalyzedPost.importance_score >= IMPORTANCE_THRESHOLD
                    ).order_by(
                        AnalyzedPost.analyzed_at.desc()
                    ).limit(10).all()
                
                return posts
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Error fetching today's important posts: {e}")
            return []
            
    def _generate_header(self, results: Dict[str, Any], important_count: int) -> str:
        """Generate report header with statistics (no AI needed)"""
        current_date = datetime.utcnow().strftime("%Y-%m-%d")
        
        header = f"""🤖 Daily Social Media Tracking Report
📅 Date: {current_date}

📊 Summary Statistics:
• Total Posts Analyzed: {results.get('total_posts_analyzed', 0)}
• Important Posts: {important_count}
• Tracked Accounts: {results.get('total_accounts', 0)}
• Collection Success Rate: {self._calculate_success_rate(results)}%

"""
        return header
        
    def _generate_ai_summary(self, posts: List[AnalyzedPost]) -> str:
        """Generate AI summary of important posts"""
        try:
            # Format posts for AI input
            posts_text = self._format_posts_for_ai(posts)
            
            # Try to get prompt from Google Sheets first
            prompt_template = self._get_telegram_prompt()
            
            # Replace placeholder with posts
            prompt = prompt_template.replace("{posts_list}", posts_text)
            
            # Generate summary using AI (follow AIClient pattern)
            if self.ai_client.api_type == "openai":
                summary = self.ai_client._call_openai(prompt, max_tokens=500)
            elif self.ai_client.api_type == "anthropic":
                summary = self.ai_client._call_anthropic(prompt, max_tokens=500)
            else:
                logger.error(f"Unsupported API type: {self.ai_client.api_type}")
                summary = None
            
            if summary:
                return f"📝 Key Highlights:\n\n{summary}\n\n"
            else:
                # Fallback to simple listing if AI fails
                return self._generate_simple_summary(posts)
                
        except Exception as e:
            logger.error(f"Error generating AI summary: {e}")
            # Fallback to simple listing
            return self._generate_simple_summary(posts)
            
    def _format_posts_for_ai(self, posts: List[AnalyzedPost]) -> str:
        """Format posts as simple list for AI input"""
        posts_list = []

        for post in posts:
            # Use summary if available, otherwise use original content (truncated)
            content = post.summary if post.summary else post.original_content[:200]

            # Use post_url if available, otherwise fallback to user profile
            link_url = post.post_url if post.post_url else f"https://x.com/{post.author_username}"
            # Make the content itself a clickable link
            posts_list.append(f"@{post.author_username}: <a href=\"{link_url}\">{content}</a>")

        return "\n".join(posts_list)
        
    def _generate_simple_summary(self, posts: List[AnalyzedPost]) -> str:
        """Generate simple summary without AI (fallback)"""
        summary = "📝 Key Highlights:\n\n"
        
        # Group posts by author
        posts_by_author = {}
        for post in posts:
            author = post.author_username
            if author not in posts_by_author:
                posts_by_author[author] = []
            posts_by_author[author].append(post)
            
        # Format by author
        for author, author_posts in posts_by_author.items():
            summary += f"【<a href=\"https://x.com/{author}\">@{author}</a>】\n"
            for post in author_posts[:3]:  # Limit to 3 posts per author
                content = post.summary if post.summary else post.original_content[:100]
                
                # Use post_url if available, otherwise fallback to user profile
                link_url = post.post_url if post.post_url else f"https://x.com/{post.author_username}"
                summary += f"• <a href=\"{link_url}\">{content}...</a>\n"
            summary += "\n"
            
        return summary
        
    def _generate_footer(self, results: Dict[str, Any]) -> str:
        """Generate report footer"""
        start_time = results.get('start_time', 'N/A')
        end_time = results.get('end_time', 'N/A')
        
        # Convert ISO format to readable time
        try:
            if start_time != 'N/A':
                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                start_time = start_dt.strftime("%H:%M")
            if end_time != 'N/A':
                end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                end_time = end_dt.strftime("%H:%M")
        except:
            pass
            
        footer = f"""⏱️ Collection Time: {start_time} - {end_time} UTC

Use /help for more commands"""
        
        return footer
        
    def _calculate_success_rate(self, results: Dict[str, Any]) -> int:
        """Calculate collection success rate"""
        total = results.get('total_posts_collected', 0)
        analyzed = results.get('total_posts_analyzed', 0)
        
        if total == 0:
            return 0
            
        return int((analyzed / total) * 100)
        
    def _get_telegram_prompt(self) -> str:
        """Get Telegram summary prompt from Google Sheets or use default"""
        try:
            # Try to get from Google Sheets "AI Prompts" worksheet
            prompt = self.sheets_client.get_prompt_by_name("TELEGRAM_SUMMARY")
            if prompt:
                return prompt
        except Exception as e:
            logger.debug(f"Could not get prompt from sheets: {e}")
            
        # Default prompt if not found in sheets
        return """Summarize these important social media posts from the past day:

{posts_list}

IMPORTANT: You MUST preserve all HTML hyperlinks exactly as they appear (e.g., <a href="...">text</a>).
Group by account if needed. Keep it brief and highlight key information.
Output format: For each important topic, write a brief summary with the clickable link preserved."""
        
    def send_daily_report(self, results: Dict[str, Any]) -> bool:
        """
        Generate and send daily report via Telegram
        
        Args:
            results: Collection results from post_collector
            
        Returns:
            True if report was sent successfully
        """
        try:
            # Generate report
            report = self.generate_daily_report(results)
            
            if not report:
                logger.info("No report to send (no important posts)")
                return False
                
            # Send via Telegram (use HTML mode to enable clickable links)
            if self.telegram.send_long_message(report, parse_mode="HTML"):
                logger.info("Daily report sent successfully via Telegram")
                return True
            else:
                logger.error("Failed to send daily report via Telegram")
                return False
                
        except Exception as e:
            logger.error(f"Error sending daily report: {e}")
            return False