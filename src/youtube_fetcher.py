"""
YouTube clip sourcing module for FinBot.

Searches for investment-related clips from unique channels,
tracks posted videos to avoid duplicates, and provides
download URLs for trimming.
"""

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
CLIP_CATEGORIES = os.getenv("CLIP_CATEGORIES", "finance,investing,stock market,crypto,trading").split(",")

# Channel diversity - track last N channels to avoid repetition
CHANNEL_HISTORY_FILE = DATA_DIR / "youtube_channels.json"
MAX_CHANNEL_HISTORY = 50

# Posted videos tracking
POSTED_VIDEOS_FILE = DATA_DIR / "posted_videos.json"

# Whitelist of known good finance channels (optional, for quality)
CHANNEL_WHITELIST = os.getenv("CHANNEL_WHITELIST", "").split(",") if os.getenv("CHANNEL_WHITELIST") else []


class YouTubeClipFetcher:
    """Fetches investment-related clips from YouTube."""
    
    def __init__(self):
        self.api_key = YOUTUBE_API_KEY
        self.session = None
        self.channel_history = self._load_channel_history()
        self.posted_videos = self._load_posted_videos()
        
    def _load_channel_history(self) -> List[str]:
        """Load recently posted channel IDs."""
        if CHANNEL_HISTORY_FILE.exists():
            with open(CHANNEL_HISTORY_FILE, 'r') as f:
                data = json.load(f)
                return data.get('channels', [])
        return []
        
    def _save_channel_history(self):
        """Save channel history (keep last N)."""
        # Trim to max
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
                    data = await resp.json()
                    return self._parse_search_results(data)
                elif resp.status == 429:
                    logger.warning(f"YouTube API rate limit hit (429). Waiting 60s...")
                    await asyncio.sleep(60)
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
            except Exception as e:
                logger.error(f"Failed to get video details: {e}")
                
        return all_details
        
    def _parse_duration(self, iso_duration: str) -> int:
        """Parse ISO 8601 duration to seconds."""
        import re
        # PT1M30S -> 90
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
        
        # Search each category with delay between searches
        for i, category in enumerate(CLIP_CATEGORIES):
            # Rotate queries for variety
            queries = [
                f"{category} investing tips",
                f"{category} market analysis",
                f"{category} news today",
                f"{category} explained"
            ]
            # Pick one query per category based on day of week for variety
            day_index = datetime.utcnow().weekday()
            query = queries[day_index % len(queries)]
            
            clips = await self.search_clips(query, max_results=10)
            all_clips.extend(clips)
            
            # Rate limit between categories to avoid quota exhaustion
            if i < len(CLIP_CATEGORIES) - 1:
                await asyncio.sleep(2)
            
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
            elif len(used_channels) >= 3:  # After 3 unique channels, allow repeats
                selected.append(clip)
                
            if len(selected) >= MAX_CLIPS_PER_RUN:
                break
                
        logger.info(f"Selected {len(selected)} clips from {len(used_channels)} unique channels")
        return selected
        
    def _score_clips(self, clips: List[Dict]) -> List[Dict]:
        """Score clips by relevance, engagement, and recency."""
        now = datetime.utcnow()
        
        for clip in clips:
            score = 0
            
            # Engagement score (likes/views ratio + raw views)
            views = clip.get('view_count', 0)
            likes = clip.get('like_count', 0)
            if views > 0:
                engagement = (likes / views) * 1000  # Per 1000 views
                score += min(engagement * 10, 100)  # Cap at 100
                score += min(views / 1000, 50)  # View count bonus, capped
                
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
            
        # Sort by score descending
        return sorted(clips, key=lambda x: x['score'], reverse=True)
        
    async def close(self):
        """Close session."""
        if self.session:
            await self.session.close()


# Singleton instance
youtube_fetcher = YouTubeClipFetcher()
