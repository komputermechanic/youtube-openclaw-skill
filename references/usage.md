# Usage Examples

## Public commands

```bash
# Channel stats
scripts/youtube_api.py channel @mkbhd
scripts/youtube_api.py channel UCBcRF18a7Qf58cCRy5xuWwQ

# Recent uploads
scripts/youtube_api.py channel-videos @mkbhd --max 5

# Top videos by views
scripts/youtube_api.py channel-top @mkbhd --max 10

# Single video stats
scripts/youtube_api.py video dQw4w9WgXcQ

# Search
scripts/youtube_api.py search "iPhone 16 review" --type video --max 5
scripts/youtube_api.py search "tech channels" --type channel --max 5

# Compare channels
scripts/youtube_api.py compare @mkbhd @LinusTechTips @JerryRigEverything

# Trending (US by default)
scripts/youtube_api.py trending --region US --max 10
scripts/youtube_api.py trending --region GB

# Resolve handle to ID
scripts/youtube_api.py resolve @mkbhd

# Plain text output
scripts/youtube_api.py channel @mkbhd --plain
```

## Analytics commands (own channel)

```bash
# Overview — last 28 days
scripts/youtube_api.py analytics-overview

# Overview — last 90 days
scripts/youtube_api.py analytics-overview --days 90

# Per-video analytics
scripts/youtube_api.py analytics-video dQw4w9WgXcQ --days 28

# Traffic sources
scripts/youtube_api.py analytics-traffic --days 28

# Top countries
scripts/youtube_api.py analytics-geography --days 28 --max 10

# Device breakdown
scripts/youtube_api.py analytics-devices --days 28

# Demographics
scripts/youtube_api.py analytics-demographics --days 28

# Revenue (monetized channels only)
scripts/youtube_api.py analytics-revenue --days 28

# Last 48 hours
scripts/youtube_api.py analytics-realtime

# Top videos this month
scripts/youtube_api.py analytics-top-videos --days 30 --max 10

# Plain text for any analytics command
scripts/youtube_api.py analytics-overview --days 7 --plain
```
