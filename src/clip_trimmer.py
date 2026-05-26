"""
Clip trimming module for FinBot.

Downloads YouTube clips, trims to highlight segments,
and prepares them for Telegram upload.
"""

import os
import json
import asyncio
import subprocess
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple
from datetime import datetime
from config import logger, DATA_DIR

# Clip storage
CLIPS_DIR = DATA_DIR / "clips"
CLIPS_DIR.mkdir(exist_ok=True)

# Trim settings
TARGET_CLIP_DURATION = int(os.getenv("TARGET_CLIP_DURATION", "45"))  # Target 45s clips
MAX_CLIP_FILE_SIZE_MB = int(os.getenv("MAX_CLIP_FILE_SIZE_MB", "20"))  # Telegram limit ~50MB for bots
CLIP_QUALITY = os.getenv("CLIP_QUALITY", "720")  # 720p default


class ClipTrimmer:
    """Downloads and trims YouTube clips."""
    
    def __init__(self):
        self.clips_dir = CLIPS_DIR
        self._check_ytdlp()
        
    def _check_ytdlp(self):
        """Check if yt-dlp is installed."""
        try:
            result = subprocess.run(
                ["yt-dlp", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                logger.info(f"yt-dlp version: {result.stdout.strip()}")
            else:
                logger.warning("yt-dlp not found. Install with: pip install yt-dlp")
        except FileNotFoundError:
            logger.warning("yt-dlp not installed. Clip trimming will be disabled.")
            
    async def download_clip(self, video_id: str, title: str) -> Optional[Path]:
        """Download a YouTube clip."""
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_title = safe_title[:50]  # Limit length
        
        output_path = self.clips_dir / f"{video_id}_{safe_title}.mp4"
        
        # Skip if already downloaded
        if output_path.exists():
            logger.info(f"Clip already downloaded: {output_path}")
            return output_path
            
        url = f"https://youtube.com/shorts/{video_id}"
        
        # yt-dlp command for best quality under size limit
        cmd = [
            "yt-dlp",
            "-f", f"best[height<={CLIP_QUALITY}][filesize<{MAX_CLIP_FILE_SIZE_MB}M]/best[height<={CLIP_QUALITY}]",
            "--merge-output-format", "mp4",
            "-o", str(output_path),
            "--no-playlist",
            "--quiet",
            "--no-warnings",
            url
        ]
        
        try:
            logger.info(f"Downloading clip: {video_id}")
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
            
            if proc.returncode == 0 and output_path.exists():
                size_mb = output_path.stat().st_size / (1024 * 1024)
                logger.info(f"Downloaded: {output_path} ({size_mb:.1f} MB)")
                return output_path
            else:
                err = stderr.decode()[:500] if stderr else "Unknown error"
                logger.error(f"Download failed: {err}")
                return None
                
        except asyncio.TimeoutError:
            logger.error(f"Download timeout for {video_id}")
            return None
        except Exception as e:
            logger.error(f"Download error: {e}")
            return None
            
    async def trim_clip(self, video_path: Path, start_sec: float = 0, 
                       duration: float = None) -> Optional[Path]:
        """Trim clip to target duration."""
        if not video_path.exists():
            return None
            
        # Get video duration
        duration_sec = await self._get_duration(video_path)
        if not duration_sec:
            return video_path  # Return original if can't determine
            
        # If already short enough, return original
        if duration_sec <= TARGET_CLIP_DURATION:
            return video_path
            
        # Determine trim range
        target = duration or TARGET_CLIP_DURATION
        
        # Smart trim: skip first 3s (intros), take best segment
        start = max(start_sec, 3)  # Skip intro
        
        # Don't exceed video length
        end = min(start + target, duration_sec - 2)  # Leave 2s buffer
        
        if end - start < 10:  # Too short, return original
            return video_path
            
        # Output path
        trimmed_path = video_path.with_suffix('.trimmed.mp4')
        
        # FFmpeg trim command
        cmd = [
            "ffmpeg",
            "-y",  # Overwrite
            "-ss", str(start),
            "-t", str(end - start),
            "-i", str(video_path),
            "-c", "copy",  # Copy streams (fast)
            "-avoid_negative_ts", "make_zero",
            "-movflags", "+faststart",  # Web optimization
            str(trimmed_path)
        ]
        
        try:
            logger.info(f"Trimming: {start:.1f}s to {end:.1f}s")
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
            
            if proc.returncode == 0 and trimmed_path.exists():
                # Clean up original, keep trimmed
                video_path.unlink()
                trimmed_path.rename(video_path)
                logger.info(f"Trimmed clip saved: {video_path}")
                return video_path
            else:
                err = stderr.decode()[:500] if stderr else "Unknown"
                logger.warning(f"Trim failed, using original: {err}")
                return video_path
                
        except Exception as e:
            logger.error(f"Trim error: {e}")
            return video_path
            
    async def _get_duration(self, video_path: Path) -> Optional[float]:
        """Get video duration using ffprobe."""
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "json",
            str(video_path)
        ]
        
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
            
            if proc.returncode == 0:
                data = json.loads(stdout.decode())
                return float(data['format']['duration'])
        except:
            pass
        return None
        
    async def auto_trim(self, video_id: str, title: str) -> Optional[Path]:
        """Download and auto-trim a clip."""
        video_path = await self.download_clip(video_id, title)
        if not video_path:
            return None
            
        # Trim if needed
        trimmed = await self.trim_clip(video_path)
        return trimmed
        
    async def get_clip_info(self, video_path: Path) -> Dict:
        """Get clip file info for Telegram upload."""
        if not video_path.exists():
            return {}
            
        stat = video_path.stat()
        duration = await self._get_duration(video_path)
        
        return {
            'path': str(video_path),
            'size_mb': round(stat.st_size / (1024 * 1024), 2),
            'duration_sec': round(duration, 1) if duration else None,
            'filename': video_path.name
        }
        
    def cleanup_old_clips(self, max_age_hours: int = 48):
        """Remove clips older than max_age_hours."""
        cutoff = datetime.now().timestamp() - (max_age_hours * 3600)
        removed = 0
        
        for clip_file in self.clips_dir.glob("*.mp4"):
            if clip_file.stat().st_mtime < cutoff:
                clip_file.unlink()
                removed += 1
                
        if removed > 0:
            logger.info(f"Cleaned up {removed} old clips")


# Singleton instance
trimmer = ClipTrimmer()
