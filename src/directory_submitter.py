import json
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List
from config import logger, DATA_DIR, TELEGRAM_CHANNEL_ID

class DirectorySubmitter:
    """Helper for submitting channel to Telegram directories."""
    
    def __init__(self):
        self.state_file = DATA_DIR / "directory_submissions.json"
        self.state = self._load_state()
        
        # Directory list with submission info
        self.directories = [
            {
                'name': 'tgstat.com',
                'url': 'https://tgstat.com',
                'submission_url': 'https://tgstat.com/channel/add',
                'category': 'Finance / Cryptocurrencies',
                'requires_login': True,
                'status': 'pending',
                'notes': 'Major analytics platform. Requires account. Add @apexfinanceandsecurities'
            },
            {
                'name': 'telemetr.io',
                'url': 'https://telemetr.io',
                'submission_url': 'https://telemetr.io/en/catalog',
                'category': 'Finance / Investing',
                'requires_login': True,
                'status': 'pending',
                'notes': 'Channel catalog with analytics. Search then claim channel.'
            },
            {
                'name': 'combot.org',
                'url': 'https://combot.org',
                'submission_url': 'https://combot.org/chat',
                'category': 'Analytics',
                'requires_login': False,
                'status': 'pending',
                'notes': 'Add bot @combot to channel for analytics. Auto-listed.'
            },
            {
                'name': 'tdirectory.me',
                'url': 'https://tdirectory.me',
                'submission_url': 'https://tdirectory.me/add-channel',
                'category': 'Finance',
                'requires_login': False,
                'status': 'pending',
                'notes': 'Simple submission form. Channel must be public.'
            },
            {
                'name': 'telegramchannels.me',
                'url': 'https://telegramchannels.me',
                'submission_url': 'https://telegramchannels.me/submit',
                'category': 'Finance / Business',
                'requires_login': False,
                'status': 'pending',
                'notes': 'Category-based directory. Good for discovery.'
            },
            {
                'name': 'tchannels.me',
                'url': 'https://tchannels.me',
                'submission_url': 'https://tchannels.me/add',
                'category': 'Finance',
                'requires_login': False,
                'status': 'pending',
                'notes': 'Clean interface. Submit channel link.'
            }
        ]
    
    def _load_state(self) -> Dict:
        """Load submission state."""
        if self.state_file.exists():
            with open(self.state_file, 'r') as f:
                return json.load(f)
        return {
            'submissions': [],
            'pending': [],
            'completed': [],
            'failed': []
        }
    
    def _save_state(self):
        """Save submission state."""
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)
    
    def get_channel_info(self) -> Dict:
        """Get optimized channel info for directories."""
        return {
            'username': TELEGRAM_CHANNEL_ID,
            'name': 'Apex Finance & Securities',
            'description': (
                'Finance, AI & Investing intelligence. '
                'Market analysis, stock picks, breaking news, YouTube clips. '
                '5x daily updates. US timezone focused. '
                'Join 10K+ traders getting the edge.'
            ),
            'category': 'Finance / Investing / AI',
            'tags': ['finance', 'investing', 'stocks', 'AI', 'trading', 'market analysis', 'crypto', 'news'],
            'language': 'English',
            'posting_frequency': '5+ daily',
            'content_types': ['News', 'Analysis', 'Videos', 'Polls'],
            'target_audience': 'Traders, investors, finance professionals'
        }
    
    def get_submission_guide(self) -> str:
        """Get step-by-step submission guide."""
        info = self.get_channel_info()
        
        text = f"""📋 <b>Directory Submission Guide</b>

<b>Channel:</b> {info['username']}
<b>Name:</b> {info['name']}

<b>Optimized Description:</b>
<pre>{info['description']}</pre>

<b>Tags:</b> {', '.join(info['tags'])}

<b>Directories to Submit:</b>

"""
        
        for directory in self.directories:
            status_emoji = '⏳' if directory['status'] == 'pending' else '✅' if directory['status'] == 'completed' else '❌'
            text += f"{status_emoji} <b>{directory['name']}</b>\n"
            text += f"   URL: {directory['url']}\n"
            text += f"   Submit: {directory['submission_url']}\n"
            text += f"   Category: {directory['category']}\n"
            text += f"   Notes: {directory['notes']}\n\n"
        
        text += """<b>Submission Checklist:</b>
✅ Channel is PUBLIC
✅ Username is set (@apexfinanceandsecurities)
✅ Description has keywords (Finance, AI, Investing)
✅ Profile photo uploaded
✅ At least 10 posts (not empty)

<b>Pro Tips:</b>
• Use exact same description across all directories
• Add keywords early in description (SEO)
• Category: Finance > Investing > Stocks
• Posting frequency: "5+ daily" signals active channel
"""
        
        return text
    
    def mark_submitted(self, directory_name: str, success: bool = True):
        """Mark directory as submitted."""
        for directory in self.state['pending']:
            if directory['name'] == directory_name:
                directory['status'] = 'completed' if success else 'failed'
                directory['submitted_at'] = datetime.utcnow().isoformat()
                
                if success:
                    self.state['completed'].append(directory)
                else:
                    self.state['failed'].append(directory)
                
                self.state['pending'] = [d for d in self.state['pending'] if d['name'] != directory_name]
                self.state['submissions'].append({
                    'directory': directory_name,
                    'timestamp': datetime.utcnow().isoformat(),
                    'success': success
                })
                
                self._save_state()
                logger.info(f"Marked {directory_name} as {'completed' if success else 'failed'}")
                return True
        
        return False
    
    def get_progress(self) -> str:
        """Get submission progress."""
        total = len(self.directories)
        completed = len(self.state.get('completed', []))
        pending = len(self.state.get('pending', []))
        failed = len(self.state.get('failed', []))
        
        text = f"""📊 <b>Directory Submission Progress</b>

✅ Completed: {completed}/{total}
⏳ Pending: {pending}/{total}
❌ Failed: {failed}/{total}

<b>Submitted:</b>
"""
        
        for sub in self.state.get('submissions', []):
            emoji = '✅' if sub['success'] else '❌'
            text += f"{emoji} {sub['directory']} ({sub['timestamp'][:10]})\n"
        
        if not self.state['submissions']:
            text += "  • None yet\n"
        
        return text

# Singleton instance
directory_submitter = DirectorySubmitter()
