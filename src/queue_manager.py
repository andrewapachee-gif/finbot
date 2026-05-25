import json
import asyncio
from datetime import datetime
from typing import List, Dict, Optional
from config import QUEUE_FILE, POSTED_FILE, POSTING_MODE, logger

class QueueManager:
    """Manages content queue for review before posting."""
    
    def __init__(self):
        self.queue = self._load_queue()
        
    def _load_queue(self) -> List[Dict]:
        """Load queue from file."""
        if QUEUE_FILE.exists():
            with open(QUEUE_FILE, 'r') as f:
                return json.load(f)
        return []
        
    def _save_queue(self):
        """Save queue to file."""
        with open(QUEUE_FILE, 'w') as f:
            json.dump(self.queue, f, indent=2)
            
    def add_to_queue(self, article: Dict) -> bool:
        """Add article to queue."""
        # Check not already in queue
        for item in self.queue:
            if item['id'] == article['id']:
                return False
                
        article['queued_at'] = datetime.utcnow().isoformat()
        article['status'] = 'pending'
        self.queue.append(article)
        self._save_queue()
        
        logger.info(f"Added to queue: {article['title'][:50]}...")
        return True
        
    def approve(self, article_id: str) -> Optional[Dict]:
        """Approve article for posting."""
        for item in self.queue:
            if item['id'] == article_id:
                item['status'] = 'approved'
                self._save_queue()
                logger.info(f"Approved: {item['title'][:50]}...")
                return item
        return None
        
    def reject(self, article_id: str) -> bool:
        """Reject article from queue."""
        for i, item in enumerate(self.queue):
            if item['id'] == article_id:
                self.queue.pop(i)
                self._save_queue()
                logger.info(f"Rejected: {item['title'][:50]}...")
                return True
        return False
        
    def get_pending(self) -> List[Dict]:
        """Get all pending articles."""
        return [item for item in self.queue if item['status'] == 'pending']
        
    def get_all(self) -> List[Dict]:
        """Get all queue items."""
        return self.queue
        
    def clear(self):
        """Clear entire queue."""
        self.queue = []
        self._save_queue()
        logger.info("Queue cleared")

# Singleton instance
queue_manager = QueueManager()
