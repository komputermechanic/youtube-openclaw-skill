---
name: youtube-analytics
description: Pull YouTube analytics for any channel or your own. Use when the user wants channel stats, video performance, traffic sources, watch time, demographics, revenue, competitor research, or trending videos. Covers both public data (any channel, API key) and private dashboard analytics (own channel, OAuth2).
---

# YouTube Analytics

Created by **Komputer Mechanic** — <https://komputermechanic.com/>

Use the bundled helper script for all YouTube interactions. Two tiers of data are available depending on setup.

## Tiers

| Tier | Requires | Works on |
|------|----------|----------|
| Public | API key | Any channel |
| Analytics | OAuth2 | Your channel only |

---

## Public commands — any channel

| Command | Description | Quota cost |
|---------|-------------|------------|
| `scripts/youtube_api.py channel <id\|@handle>` | Full channel profile and stats | ~5 units |
| `scripts/youtube_api.py channel-videos <id\|@handle> [--max N]` | Recent uploads with engagement metrics | ~5 units |
| `scripts/youtube_api.py channel-top <id\|@handle> [--max N]` | Top videos by view count | ~5 units |
| `scripts/youtube_api.py video <video-id>` | Single video stats and engagement | ~1 unit |
| `scripts/youtube_api.py search <query> [--type video\|channel] [--max N]` | Search YouTube | ~100 units |
| `scripts/youtube_api.py compare <id1> <id2> [id3]` | Side-by-side channel comparison | ~15 units |
| `scripts/youtube_api.py trending [--region US] [--max N]` | Trending videos by region | ~1 unit |
| `scripts/youtube_api.py resolve <@handle>` | Resolve @handle to channel ID | ~1 unit |

---

## Analytics commands — own channel only

All analytics commands accept `--days N` (default: 28). Use `--plain` on any command for a readable summary instead of JSON.

| Command | Description |
|---------|-------------|
| `scripts/youtube_api.py analytics-overview [--days N]` | Views, watch time, subscribers, engagement, revenue for the period |
| `scripts/youtube_api.py analytics-video <video-id> [--days N]` | Per-video: views, watch time, avg view %, CTR, impressions, subs gained |
| `scripts/youtube_api.py analytics-traffic [--days N]` | Traffic sources breakdown (search, suggested, browse, external, etc.) |
| `scripts/youtube_api.py analytics-geography [--days N] [--max N]` | Top countries by views and watch time |
| `scripts/youtube_api.py analytics-devices [--days N]` | Device breakdown (mobile, desktop, TV, tablet) |
| `scripts/youtube_api.py analytics-demographics [--days N]` | Age group and gender split |
| `scripts/youtube_api.py analytics-revenue [--days N]` | Revenue, CPM, ad impressions (monetized channels only) |
| `scripts/youtube_api.py analytics-realtime` | Last 48 hours snapshot |
| `scripts/youtube_api.py analytics-top-videos [--days N] [--max N]` | Best performing videos in the period |

---

## Workflow

1. For competitor or public channel research — use public commands with `channel`, `compare`, or `search`
2. For own channel analytics — use `analytics-overview` first, then drill down with `analytics-video`, `analytics-traffic`, etc.
3. Use `--plain` when the user wants to read the result directly rather than see raw JSON

---

## Credential handling

- API key is stored at `~/.openclaw/credentials/youtube-analytics.env` as `YOUTUBE_API_KEY=...`
- OAuth credentials are stored at `~/.openclaw/credentials/youtube-analytics-oauth.json`
- Do not ask the user to paste keys into chat
- Do not print credentials back to the user
- If a key appeared in chat, treat it as exposed and recommend immediate rotation

---

## Quota awareness

YouTube Data API v3 free tier: **10,000 units/day**. Analytics API has separate limits.

- `search` costs 100 units — use sparingly
- Most other public commands cost 1-5 units
- If you hit quota, `quota_hint: true` will appear in the error response
- Tell the user if a planned sequence of searches may exhaust daily quota

---

## References

- `references/install.md` — installation paths and credential locations
- `references/usage.md` — command examples
- `references/quota.md` — full quota cost breakdown
