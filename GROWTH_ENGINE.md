# FinBot Growth Engine — Phase 2 Implementation

This module adds viral mechanics, cross-promotion tools, and discoverability features
to make @apexfinanceandsecurities one of the top channels in the finance/AI/investing niche.

## Files Added
- `src/growth_engine.py` — Core growth engine with viral mechanics
- `src/analytics_tracker.py` — Subscriber and engagement analytics
- `src/cross_promo.py` — Cross-promotion network manager
- `src/news_war_coverage.py` — Real-time war/news coverage module
- `src/directory_submitter.py` — Telegram directory submission helper
- `data/growth_state.json` — Persistent growth state
- `data/cross_promo_contacts.json` — Cross-promotion contact database

## Features

### 1. Viral Mechanics (growth_engine.py)
- Forward-trigger CTAs in every post
- Engagement polls on high-relevance articles
- "Share with someone who needs this" prompts
- Exclusive content teasers for channel members

### 2. Analytics Tracking (analytics_tracker.py)
- Subscriber count monitoring via Telegram API
- Engagement rate calculation (views/forwards/reactions)
- Peak time detection for optimal posting
- Growth velocity tracking

### 3. Cross-Promotion (cross_promo.py)
- Contact database for niche channels
- Outreach message templates
- Mutual promotion tracking
- Shoutout rotation system

### 4. War/News Coverage (news_war_coverage.py)
- Real-time monitoring of geopolitical RSS feeds
- Priority queue for breaking war news
- Auto-post with BREAKING tag and urgency scoring
- US-Israel-Iran specific tracking

### 5. Directory Submission (directory_submitter.py)
- tgstat.com submission helper
- telemetr.io submission helper
- Category optimization for finance/AI/investing
- Public channel verification

## Integration

The growth engine hooks into the existing scheduler and publisher:
- `growth_engine` is initialized in `main.py`
- Analytics run hourly via scheduler
- War coverage checks every 30 minutes (faster than breaking news)
- Cross-promo outreach can be triggered manually via /crosspromo command

## Commands Added
- `/analytics` — Show growth stats
- `/crosspromo` — Trigger cross-promotion outreach
- `/viralpost` — Generate a viral-optimized post
- `/warcheck` — Manual war news check
- `/directory` — Show directory submission guide
- `/growthstats` — Full growth metrics

## Configuration (.env additions)
```
# Growth Engine
ENABLE_VIRAL_MECHANICS=true
ENABLE_ANALYTICS=true
ENABLE_CROSS_PROMO=true
ENABLE_WAR_COVERAGE=true
TARGET_SUBSCRIBER_COUNT=100000
CROSS_PROMO_OUTREACH_BATCH=5
WAR_COVERAGE_CHECK_INTERVAL=30
```

## Usage

1. Make channel public: Set @apexfinanceandsecurities to public in Telegram
2. Optimize description: Use keywords "Finance AI Investing Market Intelligence"
3. Submit to directories: Run /directorysubmit or manual submission
4. Start cross-promo: /crosspromo sends outreach to first batch
5. Monitor analytics: /analytics shows growth velocity

## Post Format for Viral Optimization

Every post now includes:
- Breaking tag when relevant
- Sentiment emoji (🟢🔴⚪)
- Ticker hashtags (#AAPL #TSLA)
- Forward CTA: "Forward this to someone who trades"
- Engagement poll on high-relevance articles
- Exclusive teaser: "More analysis in the channel..."

## War Coverage Format

Breaking war news posts:
- 🚨 BREAKING — URGENT prefix
- Auto-generated summary from multiple sources
- Impact analysis on markets (oil, gold, defense stocks)
- Timestamp for freshness
- "Developing..." tag for ongoing stories

## Directory List

Primary directories to submit:
1. tgstat.com — Analytics + directory
2. telemetr.io — Channel catalog
3. combot.org — Engagement analytics
4. tdirectory.me — General directory
5. telegramchannels.me — Category listings

## Cross-Promo Strategy

Phase 1 (0-5K subs): Mutual promos with 1K-10K channels
Phase 2 (5K-20K subs): Paid shoutouts from 20K-50K channels
Phase 3 (20K+ subs): Collaboration with 100K+ channels

## Next Steps

1. Implement all modules
2. Add to scheduler
3. Test viral post formatting
4. Submit to directories
5. Start cross-promo outreach
6. Monitor analytics daily

## Notes

- Channel must be PUBLIC for directory submissions and analytics
- Cross-promo requires manual DM sending (Telegram API limits)
- War coverage uses additional RSS feeds (see news_war_coverage.py)
- Analytics needs channel admin rights for subscriber counts
