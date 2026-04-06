# OpenClaw YouTube Analytics

By **Komputer Mechanic** — [komputermechanic.com](https://komputermechanic.com/)

Pull rich YouTube analytics directly into your OpenClaw workspace. No need to open YouTube Studio — everything is available through your agent.

## What it does

**Public tier** (any channel, API key only):
- Channel stats — subscribers, views, video count, engagement
- Video performance — views, likes, comments, duration, engagement rate
- Competitor comparison — side-by-side stats for up to 3 channels
- Search — find videos or channels by keyword
- Trending — top videos by region and category
- Top videos — best performing uploads from any channel

**Analytics tier** (your channel only, OAuth2):
- Overview — views, watch time, subscribers gained/lost, shares
- Per-video analytics — impressions, CTR, avg view duration, avg view %
- Traffic sources — search, suggested, browse, external, notifications
- Geography — top countries by views and watch time
- Devices — mobile, desktop, TV, tablet breakdown
- Demographics — age groups and gender split
- Revenue — estimated revenue, CPM, ad impressions (monetized channels)
- Last 48 hours — most recent data window available

Your data flows directly from YouTube to your machine. Nothing is stored on third-party servers.

## Install

```bash
bash <(curl -s https://raw.githubusercontent.com/komputermechanic/youtube-openclaw-skill/main/setup-youtube-analytics.sh)
```

Or clone and run locally:

```bash
git clone https://github.com/komputermechanic/youtube-openclaw-skill
cd youtube-openclaw-skill
bash setup-youtube-analytics.sh
```

## Requirements

- Python 3.8+
- `pip install requests`
- A Google Cloud project with **YouTube Data API v3** enabled
- For analytics: also enable **YouTube Analytics API** + an OAuth 2.0 Client ID (Desktop app type)

## Usage

See `references/usage.md` for full examples.

```bash
# Any channel
scripts/youtube_api.py channel @mkbhd
scripts/youtube_api.py compare @mkbhd @LinusTechTips @JerryRigEverything
scripts/youtube_api.py trending --region US

# Your channel
scripts/youtube_api.py analytics-overview --days 28
scripts/youtube_api.py analytics-traffic --days 28
scripts/youtube_api.py analytics-revenue --days 28 --plain
```

## Quota

YouTube Data API v3 free tier: 10,000 units/day. See `references/quota.md` for per-command costs.
