import os
import json
import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set
from pathlib import Path
from config import logger, DATA_DIR

# YouTube Data API v3
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"

# Clip settings
MAX_CLIP_DURATION_SEC = int(os.getenv("MAX_CLIP_DURATION", "120"))  # 2 min max
MIN_CLIP_DURATION_SEC = int(os.getenv("MIN_CLIP_DURATION", "15"))   # 15 sec min
MAX_CLIPS_PER_RUN = int(os.getenv("MAX_CLIPS_PER_RUN", "3"))
# Reduced to 1 category per run to stay well under YouTube API quota
# 5 runs/day × 1 search + 1 details call = 10 API calls/day (limit: 100/day)
CLIP_CATEGORIES = os.getenv("CLIP_CATEGORIES", "finance").split(",")

# API Quota tracking
QUOTA_FILE = DATA_DIR / "youtube_quota.json"
QUOTA_LIMIT = 100  # Daily search quota limit

# Channel diversity - track last N channels to avoid repetition
CHANNEL_HISTORY_FILE = DATA_DIR / "youtube_channels.json"
MAX_CHANNEL_HISTORY = 50

# Posted videos tracking
POSTED_VIDEOS_FILE = DATA_DIR / "posted_videos.json"

# Whitelist of known good finance channels (optional, for quality)
CHANNEL_WHITELIST = os.getenv("CHANNEL_WHITELIST", "").split(",") if os.getenv("CHANNEL_WHITELIST") else []


class QuotaTracker:
    """Track YouTube API usage to prevent quota exhaustion."""
    
    def __init__(self):
        self.quota_file = QUOTA_FILE
        self.usage = self._load_usage()
        
    def _load_usage(self) -> Dict:
        """Load quota usage from file."""
        if self.quota_file.exists():
            with open(self.quota_file, 'r') as f:
                return json.load(f)
        return {
            'date': datetime.utcnow().strftime('%Y-%m-%d'),
            'search_calls': 0,
            'details_calls': 0,
            'total_calls': 0,
            'history': []
        }
    
    def _save_usage(self):
        """Save quota usage."""
        with open(self.quota_file, 'w') as f:
            json.dump(self.usage, f, indent=2)
    
    def check_and_reset(self):
        """Check if it's a new day and reset quota."""
        today = datetime.utcnow().strftime('%Y-%m-%d')
        if self.usage.get('date') != today:
            # New day - reset
            self.usage = {
                'date': today,
                'search_calls': 0,
                'details_calls': 0,
                'total_calls': 0,
                'history': self.usage.get('history', [])[-30:]  # Keep last 30 days
            }
            self._save_usage()
            logger.info(f"🔄 YouTube API quota reset for {today}")
    
    def record_call(self, call_type: str = 'search'):
        """Record an API call."""
        self.check_and_reset()
        
        if call_type == 'search':
            self.usage['search_calls'] += 1
        elif call_type == 'details':
            self.usage['details_calls'] += 1
        
        self.usage['total_calls'] += 1
        self._save_usage()
    
    def can_make_call(self, call_type: str = 'search') -> bool:
        """Check if we can make another API call."""
        self.check_and_reset()
        
        # Leave 20% buffer (use max 80 calls out of 100)
        buffer_limit = int(QUOTA_LIMIT * 0.8)
        
        if self.usage['total_calls'] >= buffer_limit:
            logger.warning(f"⚠️ YouTube API quota near limit: {self.usage['total_calls']}/{buffer_limit} (buffer)")
            return False
        
        return True
    
    def get_status(self) -> str:
        """Get quota status for display."""
        self.check_and_reset()
        
        remaining = QUOTA_LIMIT - self.usage['total_calls']
        buffer_remaining = int(QUOTA_LIMIT * 0.8) - self.usage['total_calls']
        
        return f"📊 YouTube API: {self.usage['total_calls']} used, {remaining} remaining ({buffer_remaining} buffer)"


class YouTubeClipFetcher:
    """Fetches investment-related clips from YouTube."""
    
    def __init__(self):
        self.api_key = YOUTUBE_API_KEY
        self.session = None
        self.channel_history = self._load_channel_history()
        self.posted_videos = self._load_posted_videos()
        self.quota = QuotaTracker()
        
    def _load_channel_history(self) -> List[str]:
        """Load recently posted channel IDs."""
        if CHANNEL_HISTORY_FILE.exists():
            with open(CHANNEL_HISTORY_FILE, 'r') as f:
                data = json.load(f)
                return data.get('channels', [])
        return []
        
    def _save_channel_history(self):
        """Save channel history (keep last N)."""
        channels = self.channel_history[-MAX_CHANNEL_HISTORY:]
        with open(CHANNEL_HISTORY_FILE, 'w') as f:
            json.dump({'channels': channels}, f)
            
    def _load_posted_videos(self) -> Set[str]:
        """Load set of posted video IDs."""
        if POSTED_VIDEOS_FILE.exists():
            with open(POSTED_VIDEOS_FILE, 'r') as f:
                data = json.load(f)
                return set(data.get('videos', []))
        return set()
        
    def _save_posted_videos(self):
        """Save posted videos."""
        with open(POSTED_VIDEOS_FILE, 'w') as f:
            json.dump({'videos': list(self.posted_videos)}, f)
            
    def is_duplicate(self, video_id: str) -> bool:
        """Check if video was already posted."""
        return video_id in self.posted_videos
        
    def mark_posted(self, video_id: str, channel_id: str):
        """Mark video as posted and track channel."""
        self.posted_videos.add(video_id)
        self.channel_history.append(channel_id)
        self._save_posted_videos()
        self._save_channel_history()
        
    async def initialize(self):
        """Initialize aiohttp session."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={'User-Agent': 'FinBot/1.0'}
        )
        
    async def search_clips(self, query: str, max_results: int = 10) -> List[Dict]:
        """Search for clips using YouTube Data API."""
        if not self.api_key:
            logger.error("YOUTUBE_API_KEY not set")
            return []
        
        # Check quota before making call
        if not self.quota.can_make_call('search'):
            logger.warning("⛔ Skipping YouTube search - quota buffer reached")
            return []
            
        params = {
            'key': self.api_key,
            'q': query,
            'part': 'snippet,id',
            'type': 'video',
            'videoDuration': 'short',  # Under 4 minutes
            'order': 'relevance',
            'publishedAfter': (datetime.utcnow() - timedelta(days=7)).strftime('%Y-%m-%dT%H:%M:%SZ'),
            'maxResults': max_results
        }
        
        try:
            async with self.session.get(YOUTUBE_SEARCH_URL, params=params) as resp:
                if resp.status == 200:
                    self.quota.record_call('search')
                    data = await resp.json()
                    return self._parse_search_results(data)
                elif resp.status == 429:
                    logger.warning("🚫 YouTube API rate limit hit (429). Pausing searches for 1 hour.")
                    # Mark quota as exhausted
                    self.quota.usage['total_calls'] = QUOTA_LIMIT
                    self.quota._save_usage()
                    await asyncio.sleep(3600)
                    return []
                elif resp.status == 403:
                    logger.error("🚫 YouTube API quota exceeded (403). Stopping searches for today.")
                    self.quota.usage['total_calls'] = QUOTA_LIMIT
                    self.quota._save_usage()
                    return []
                else:
                    text = await resp.text()
                    logger.warning(f"YouTube API returned {resp.status}: {text[:200]}")
                    return []
        except asyncio.TimeoutError:
            logger.error(f"YouTube search timeout for query: {query}")
            return []
        except Exception as e:
            logger.error(f"YouTube search failed: {e}")
            return []
            
    def _parse_search_results(self, data: Dict) -> List[Dict]:
        """Parse search results into clip objects."""
        clips = []
        
        for item in data.get('items', []):
            if item['id']['kind'] != 'youtube#video':
                continue
                
            video_id = item['id']['videoId']
            snippet = item['snippet']
            
            clip = {
                'video_id': video_id,
                'title': snippet.get('title', ''),
                'description': snippet.get('description', ''),
                'channel_id': snippet.get('channelId', ''),
                'channel_title': snippet.get('channelTitle', ''),
                'published_at': snippet.get('publishedAt', ''),
                'thumbnail': snippet.get('thumbnails', {}).get('high', {}).get('url', 
                         snippet.get('thumbnails', {}).get('default', {}).get('url', '')),
                'url': f"https://youtube.com/shorts/{video_id}",
                'source': 'youtube',
                'type': 'clip'
            }
            clips.append(clip)
            
        return clips
        
    async def get_video_details(self, video_ids: List[str]) -> Dict[str, Dict]:
        """Get duration and stats for videos."""
        if not video_ids or not self.api_key:
            return {}
        
        # Check quota before making call
        if not self.quota.can_make_call('details'):
            logger.warning("⛔ Skipping video details - quota buffer reached")
            return {}
            
        # Batch in groups of 50 (API limit)
        all_details = {}
        
        for i in range(0, len(video_ids), 50):
            batch = video_ids[i:i+50]
            ids_str = ','.join(batch)
            
            params = {
                'key': self.api_key,
                'id': ids_str,
                'part': 'contentDetails,statistics,snippet'
            }
            
            try:
                async with self.session.get(YOUTUBE_VIDEOS_URL, params=params) as resp:
                    if resp.status == 200:
                        self.quota.record_call('details')
                        data = await resp.json()
                        for item in data.get('items', []):
                            vid = item['id']
                            details = {
                                'duration': item['contentDetails']['duration'],  # ISO 8601
                                'view_count': int(item['statistics'].get('viewCount', 0)),
                                'like_count': int(item['statistics'].get('likeCount', 0)),
                                'comment_count': int(item['statistics'].get('commentCount', 0)),
                                'channel_id': item['snippet']['channelId'],
                                'channel_title': item['snippet']['channelTitle'],
                                'tags': item['snippet'].get('tags', []),
                                'category_id': item['snippet'].get('categoryId', ''),
                            }
                            all_details[vid] = details
                    elif resp.status == 429:
                        logger.warning("🚫 YouTube API rate limit (429) on details. Pausing.")
                        self.quota.usage['total_calls'] = QUOTA_LIMIT
                        self.quota._save_usage()
                        break
                    elif resp.status == 403:
                        logger.error("🚫 YouTube API quota exceeded (403) on details.")
                        self.quota.usage['total_calls'] = QUOTA_LIMIT
                        self.quota._save_usage()
                        break
            except Exception as e:
                logger.error(f"Failed to get video details: {e}")
                
        return all_details
        
    def _parse_duration(self, iso_duration: str) -> int:
        """Parse ISO 8601 duration to seconds."""
        import re
        match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', iso_duration)
        if not match:
            return 0
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = int(match.group(3) or 0)
        return hours * 3600 + minutes * 60 + seconds
        
    async def fetch_unique_clips(self) -> List[Dict]:
        """Fetch diverse clips from multiple search queries."""
        all_clips = []
        
        # Only search 1 category per run to minimize API usage
        # 5 runs/day × 1 search + 1 details = 10 calls (limit: 100, using 80 buffer)
        categories_to_search = CLIP_CATEGORIES[:1]  # Only first category
        
        for i, category in enumerate(categories_to_search):
            # Rotate queries for variety based on hour of day
            queries = [
                f"{category} investing tips",
                f"{category} market analysis",
                f"{category} news today",
                f"{category} explained"
            ]
            hour_index = datetime.utcnow().hour
            query = queries[hour_index % len(queries)]
            
            clips = await self.search_clips(query, max_results=8)
            all_clips.extend(clips)
            
            # Rate limit between searches
            if i < len(categories_to_search) - 1:
                await asyncio.sleep(3)
            
        # Get details for all clips
        video_ids = [c['video_id'] for c in all_clips if not self.is_duplicate(c['video_id'])]
        if not video_ids:
            logger.info("No new clips found")
            return []
            
        details = await self.get_video_details(video_ids)
        
        # Enrich and filter clips
        valid_clips = []
        for clip in all_clips:
            vid = clip['video_id']
            if vid not in details:
                continue
                
            detail = details[vid]
            duration_sec = self._parse_duration(detail['duration'])
            
            # Filter by duration
            if duration_sec < MIN_CLIP_DURATION_SEC or duration_sec > MAX_CLIP_DURATION_SEC:
                continue
                
            # Filter duplicates
            if self.is_duplicate(vid):
                continue
                
            # Add details
            clip['duration_sec'] = duration_sec
            clip['view_count'] = detail['view_count']
            clip['like_count'] = detail['like_count']
            clip['channel_id'] = detail['channel_id']
            clip['channel_title'] = detail['channel_title']
            clip['tags'] = detail['tags']
            
            valid_clips.append(clip)
            
        # Score and sort by relevance + channel diversity
        scored_clips = self._score_clips(valid_clips)
        
        # Pick top N from diverse channels
        selected = []
        used_channels = set()
        
        for clip in scored_clips:
            ch = clip['channel_id']
            # Prefer channels not recently used
            if ch not in used_channels and ch not in self.channel_history[-10:]:
                selected.append(clip)
                used_channels.add(ch)
            elif len(used_channels) >= 3:
                selected.append(clip)
                
            if len(selected) >= MAX_CLIPS_PER_RUN:
                break
                
        logger.info(f"Selected {len(selected)} clips from {len(used_channels)} unique channels")
        logger.info(self.quota.get_status())
        return selected
        
    def _score_clips(self, clips: List[Dict]) -> List[Dict]:
        """Score clips by relevance, engagement, and recency."""
        now = datetime.utcnow()
        
        for clip in clips:
            score = 0
            
            # Engagement score
            views = clip.get('view_count', 0)
            likes = clip.get('like_count', 0)
            if views > 0:
                engagement = (likes / views) * 1000
                score += min(engagement * 10, 100)
                score += min(views / 1000, 50)
                
            # Recency bonus
            try:
                published = datetime.fromisoformat(clip['published_at'].replace('Z', '+00:00'))
                hours_old = (now - published.replace(tzinfo=None)).total_seconds() / 3600
                if hours_old < 24:
                    score += 50
                elif hours_old < 72:
                    score += 25
            except:
                pass
                
            # Finance keyword bonus
            finance_keywords = ['stock', 'market', 'invest', 'trade', 'crypto', 'bitcoin', 
                               'analysis', 'earnings', 'dividend', 'portfolio', 'fund']
            title_lower = clip['title'].lower()
            desc_lower = clip.get('description', '').lower()
            tags_lower = ' '.join(clip.get('tags', [])).lower()
            
            text = f"{title_lower} {desc_lower} {tags_lower}"
            keyword_matches = sum(1 for kw in finance_keywords if kw in text)
            score += keyword_matches * 5
            
            clip['score'] = score
            
        return sorted(clips, key=lambda x: x['score'], reverse=True)
        
    async def close(self):
        """Close session."""
        if self.session:
            await self.session.close()


# Singleton instance
youtube_fetcher = YouTubeClipFetcher()