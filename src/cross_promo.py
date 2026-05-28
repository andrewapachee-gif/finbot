import json
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from config import logger, DATA_DIR

class CrossPromoManager:
    """Manage cross-promotion outreach and tracking."""
    
    def __init__(self):
        self.contacts_file = DATA_DIR / "cross_promo_contacts.json"
        self.contacts = self._load_contacts()
        
    def _load_contacts(self) -> Dict:
        """Load cross-promotion contacts."""
        if self.contacts_file.exists():
            with open(self.contacts_file, 'r') as f:
                return json.load(f)
        
        # Default contact database for finance/AI/investing niche
        return {
            'channels': [
                # Tier 1: 1K-10K (mutual promo targets)
                {'name': 'Stock Market Today', 'username': '@stockmarkettoday', 'subs': 5000, 'tier': 1, 'status': 'pending', 'niche': 'markets'},
                {'name': 'AI Trading Signals', 'username': '@aitradingsignals', 'subs': 3500, 'tier': 1, 'status': 'pending', 'niche': 'ai'},
                {'name': 'Crypto Alpha', 'username': '@cryptoalpha', 'subs': 8000, 'tier': 1, 'status': 'pending', 'niche': 'crypto'},
                {'name': 'Macro Insights', 'username': '@macroinsights', 'subs': 2000, 'tier': 1, 'status': 'pending', 'niche': 'macro'},
                {'name': 'Tech Stock Daily', 'username': '@techstockdaily', 'subs': 4500, 'tier': 1, 'status': 'pending', 'niche': 'tech'},
                
                # Tier 2: 10K-50K (paid shoutout targets)
                {'name': 'Wall Street Bets', 'username': '@wallstreetbets', 'subs': 25000, 'tier': 2, 'status': 'pending', 'niche': 'markets'},
                {'name': 'Crypto News', 'username': '@cryptonews', 'subs': 18000, 'tier': 2, 'status': 'pending', 'niche': 'crypto'},
                {'name': 'AI Daily', 'username': '@aidaily', 'subs': 12000, 'tier': 2, 'status': 'pending', 'niche': 'ai'},
                {'name': 'Market Watchers', 'username': '@marketwatchers', 'subs': 30000, 'tier': 2, 'status': 'pending', 'niche': 'markets'},
                {'name': 'Investing 101', 'username': '@investing101', 'subs': 15000, 'tier': 2, 'status': 'pending', 'niche': 'education'},
                
                # Tier 3: 50K+ (collaboration targets - future)
                {'name': 'Financial Times', 'username': '@financialtimes', 'subs': 100000, 'tier': 3, 'status': 'pending', 'niche': 'news'},
                {'name': 'Bloomberg', 'username': '@bloomberg', 'subs': 200000, 'tier': 3, 'status': 'pending', 'niche': 'news'},
            ],
            'outreach_log': [],
            'mutual_promos_completed': [],
            'paid_shoutouts': []
        }
    
    def _save_contacts(self):
        """Save contacts database."""
        with open(self.contacts_file, 'w') as f:
            json.dump(self.contacts, f, indent=2)
    
    def get_outreach_template(self, channel: Dict) -> str:
        """Generate personalized outreach message."""
        templates = {
            1: f"""Hey {channel['name']} team,

I'm running @apexfinanceandsecurities — finance, AI, and investing content. We're at [X] subscribers and growing fast.

Love your channel. Would you be open to a mutual shoutout? We promote you to our audience, you promote us. Win-win.

Our content: market analysis, AI stock picks, breaking news, YouTube clips.

Let me know if you're interested.

Best,
Apex Finance""",
            
            2: f"""Hi {channel['name']} team,

I'm the admin of @apexfinanceandsecurities — a finance/AI/investing channel. We're seeing strong engagement and I'd love to explore a paid shoutout.

What's your rate for a 24-hour shoutout post? We can provide the creative.

Our stats: [X] subscribers, [Y]% engagement rate.

Looking forward to hearing from you.

Best,
Apex Finance""",
            
            3: f"""Hi {channel['name']} team,

I'm reaching out from @apexfinanceandsecurities — a growing finance/AI/investing channel. We'd love to explore collaboration opportunities.

Ideas:
- Co-branded content series
- Guest analysis exchange
- Cross-promotion during major market events

Let me know if you're open to a conversation.

Best,
Apex Finance"""
        }
        
        return templates.get(channel['tier'], templates[1])
    
    def get_next_outreach_batch(self, batch_size: int = 5) -> List[Dict]:
        """Get next batch of channels to reach out to."""
        pending = [c for c in self.contacts['channels'] if c['status'] == 'pending']
        
        # Sort by tier (start with tier 1 for mutual promos)
        pending.sort(key=lambda x: (x['tier'], -x['subs']))
        
        return pending[:batch_size]
    
    def mark_contacted(self, username: str, method: str = 'dm'):
        """Mark channel as contacted."""
        for channel in self.contacts['channels']:
            if channel['username'] == username:
                channel['status'] = 'contacted'
                channel['contacted_at'] = datetime.utcnow().isoformat()
                channel['contact_method'] = method
                
                self.contacts['outreach_log'].append({
                    'username': username,
                    'timestamp': datetime.utcnow().isoformat(),
                    'method': method,
                    'template_tier': channel['tier']
                })
                
                self._save_contacts()
                logger.info(f"Marked {username} as contacted")
                return True
        
        return False
    
    def mark_promo_completed(self, username: str, promo_type: str = 'mutual'):
        """Mark mutual promotion as completed."""
        for channel in self.contacts['channels']:
            if channel['username'] == username:
                channel['status'] = 'completed'
                channel['promo_completed_at'] = datetime.utcnow().isoformat()
                
                self.contacts['mutual_promos_completed'].append({
                    'username': username,
                    'timestamp': datetime.utcnow().isoformat(),
                    'type': promo_type
                })
                
                self._save_contacts()
                return True
        
        return False
    
    def get_outreach_report(self) -> str:
        """Get outreach progress report."""
        total = len(self.contacts['channels'])
        pending = len([c for c in self.contacts['channels'] if c['status'] == 'pending'])
        contacted = len([c for c in self.contacts['channels'] if c['status'] == 'contacted'])
        completed = len([c for c in self.contacts['channels'] if c['status'] == 'completed'])
        
        text = f"""🤝 <b>Cross-Promotion Status</b>

📊 <b>Progress:</b>
  • Total targets: {total}
  • Pending: {pending}
  • Contacted: {contacted}
  • Completed: {completed}

✅ <b>Mutual Promos Done:</b> {len(self.contacts['mutual_promos_completed'])}
💰 <b>Paid Shoutouts:</b> {len(self.contacts['paid_shoutouts'])}

📋 <b>Next Batch (Tier 1 — Mutual):</b>
"""
        
        next_batch = self.get_next_outreach_batch(3)
        for channel in next_batch:
            text += f"  • {channel['name']} ({channel['username']}) — {channel['subs']:,} subs\n"
        
        if not next_batch:
            text += "  • All tier 1 channels contacted!\n"
        
        return text
    
    def add_contact(self, name: str, username: str, subs: int, tier: int, niche: str):
        """Add new cross-promotion contact."""
        contact = {
            'name': name,
            'username': username,
            'subs': subs,
            'tier': tier,
            'status': 'pending',
            'niche': niche,
            'added_at': datetime.utcnow().isoformat()
        }
        
        self.contacts['channels'].append(contact)
        self._save_contacts()
        logger.info(f"Added cross-promo contact: {username}")
    
    def get_templates_for_user(self) -> str:
        """Get all outreach templates for manual use."""
        text = "📝 <b>Cross-Promo Outreach Templates</b>\n\n"
        
        for tier in [1, 2, 3]:
            sample = next((c for c in self.contacts['channels'] if c['tier'] == tier), None)
            if sample:
                template = self.get_outreach_template(sample)
                text += f"<b>Tier {tier} ({['Mutual', 'Paid', 'Collab'][tier-1]}):</b>\n"
                text += f"<pre>{template}</pre>\n\n"
        
        return text

# Singleton instance
cross_promo = CrossPromoManager()
