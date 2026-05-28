import json
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from config import logger, DATA_DIR, TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID

class AnalyticsTracker:
    """Track subscriber growth and engagement metrics."""
    
    def __init__(self):
        self.data_file = DATA_DIR / "analytics.json"
        self.data = self._load_data()
        
    def _load_data(self) -> Dict:
        """Load analytics data from file."""
        if self.data_file.exists():
            with open(self.data_file, 'r') as f:
                return json.load(f)
        return {
            'subscriber_history': [],
            'engagement_history': [],
            'post_performance': [],
            'peak_times': {},
            'growth_velocity': [],
            'last_updated': None
        }
        
    def _save_data(self):
        """Save analytics data."""
        with open(self.data_file, 'w') as f:
            json.dump(self.data, f, indent=2)
    
    async def fetch_subscriber_count(self) -> Optional[int]:
        """Fetch current subscriber count via Telegram API."""
        try:
            from telegram import Bot
            bot = Bot(token=TELEGRAM_BOT_TOKEN)
            
            # Get chat info
            chat = await bot.get_chat(TELEGRAM_CHANNEL_ID)
            count = chat.get_member_count() if hasattr(chat, 'get_member_count') else None
            
            if count:
                self.record_subscribers(count)
                return count
            
            await bot.close()
        except Exception as e:
            logger.error(f"Failed to fetch subscriber count: {e}")
        
        return None
    
    def record_subscribers(self, count: int):
        """Record subscriber count with timestamp."""
        entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'count': count
        }
        self.data['subscriber_history'].append(entry)
        
        # Calculate growth velocity
        if len(self.data['subscriber_history']) >= 2:
            prev = self.data['subscriber_history'][-2]
            prev_count = prev['count']
            growth = count - prev_count
            
            velocity_entry = {
                'timestamp': datetime.utcnow().isoformat(),
                'growth': growth,
                'growth_rate': (growth / prev_count * 100) if prev_count > 0 else 0
            }
            self.data['growth_velocity'].append(velocity_entry)
        
        self.data['last_updated'] = datetime.utcnow().isoformat()
        self._save_data()
        
        # Check for milestones
        from growth_engine import growth_engine
        milestone = growth_engine.record_milestone(count)
        if milestone:
            logger.info(f"🎉 Milestone reached: {milestone:,} subscribers!")
    
    def record_engagement(self, post_id: str, views: int, forwards: int, reactions: int = 0):
        """Record engagement metrics for a post."""
        entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'post_id': post_id,
            'views': views,
            'forwards': forwards,
            'reactions': reactions,
            'engagement_rate': (forwards / views * 100) if views > 0 else 0
        }
        self.data['engagement_history'].append(entry)
        self._save_data()
    
    def record_post_performance(self, post_type: str, views: int, forwards: int, time_posted: str):
        """Record performance by post type and time."""
        entry = {
            'timestamp': time_posted,
            'post_type': post_type,
            'views': views,
            'forwards': forwards,
            'engagement_rate': (forwards / views * 100) if views > 0 else 0
        }
        self.data['post_performance'].append(entry)
        
        # Track peak times
        hour = time_posted.split(':')[0] if ':' in str(time_posted) else 'unknown'
        if hour not in self.data['peak_times']:
            self.data['peak_times'][hour] = []
        self.data['peak_times'][hour].append(forwards)
        
        self._save_data()
    
    def get_peak_times(self) -> Dict[str, float]:
        """Get average engagement by hour."""
        peak_times = {}
        for hour, forwards in self.data['peak_times'].items():
            if forwards:
                peak_times[hour] = sum(forwards) / len(forwards)
        
        # Sort by engagement
        return dict(sorted(peak_times.items(), key=lambda x: x[1], reverse=True))
    
    def get_growth_report(self) -> Dict:
        """Get comprehensive growth report."""
        history = self.data['subscriber_history']
        velocity = self.data['growth_velocity']
        
        current_count = history[-1]['count'] if history else 0
        
        # Calculate weekly growth
        week_ago = datetime.utcnow() - timedelta(days=7)
        week_ago_count = None
        for entry in reversed(history):
            entry_time = datetime.fromisoformat(entry['timestamp'])
            if entry_time <= week_ago:
                week_ago_count = entry['count']
                break
        
        weekly_growth = current_count - week_ago_count if week_ago_count else 0
        
        # Calculate monthly growth
        month_ago = datetime.utcnow() - timedelta(days=30)
        month_ago_count = None
        for entry in reversed(history):
            entry_time = datetime.fromisoformat(entry['timestamp'])
            if entry_time <= month_ago:
                month_ago_count = entry['count']
                break
        
        monthly_growth = current_count - month_ago_count if month_ago_count else 0
        
        # Average engagement rate
        engagement = self.data['engagement_history']
        avg_engagement = sum(e['engagement_rate'] for e in engagement) / len(engagement) if engagement else 0
        
        # Best performing post type
        performance = self.data['post_performance']
        post_types = {}
        for entry in performance:
            pt = entry['post_type']
            if pt not in post_types:
                post_types[pt] = []
            post_types[pt].append(entry['engagement_rate'])
        
        best_type = None
        best_rate = 0
        for pt, rates in post_types.items():
            avg_rate = sum(rates) / len(rates)
            if avg_rate > best_rate:
                best_rate = avg_rate
                best_type = pt
        
        return {
            'current_subscribers': current_count,
            'weekly_growth': weekly_growth,
            'monthly_growth': monthly_growth,
            'avg_engagement_rate': round(avg_engagement, 2),
            'best_post_type': best_type,
            'best_engagement_rate': round(best_rate, 2),
            'peak_posting_times': self.get_peak_times(),
            'total_posts_tracked': len(performance),
            'data_points': len(history)
        }
    
    def get_analytics_summary(self) -> str:
        """Get formatted analytics summary for Telegram."""
        report = self.get_growth_report()
        
        text = f"""📊 <b>Channel Analytics</b>

👥 <b>Subscribers:</b> {report['current_subscribers']:,}
📈 <b>Weekly Growth:</b> +{report['weekly_growth']:,}
📈 <b>Monthly Growth:</b> +{report['monthly_growth']:,}

🎯 <b>Avg Engagement:</b> {report['avg_engagement_rate']:.1f}%
🏆 <b>Best Format:</b> {report['best_post_type'] or 'N/A'}
📊 <b>Posts Tracked:</b> {report['total_posts_tracked']}

⏰ <b>Peak Times (ET):</b>
"""
        
        peak_times = report['peak_posting_times']
        if peak_times:
            # Convert UTC to ET (UTC-4 for EDT)
            for hour_utc, avg_forwards in list(peak_times.items())[:3]:
                try:
                    hour_int = int(hour_utc)
                    hour_et = (hour_int - 4) % 24
                    et_time = f"{hour_et:02d}:00"
                    text += f"  • {et_time} ET — {avg_forwards:.1f} avg forwards\n"
                except:
                    text += f"  • {hour_utc} — {avg_forwards:.1f} avg forwards\n"
        else:
            text += "  • Not enough data yet\n"
        
        return text

# Singleton instance
analytics_tracker = AnalyticsTracker()
