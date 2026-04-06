# YouTube API Quota Reference

## YouTube Data API v3

Free daily quota: **10,000 units**. Resets at midnight Pacific Time.

| Command | API call(s) | Quota cost |
|---------|-------------|------------|
| `resolve` | channels.list | ~1 unit |
| `channel` | channels.list | ~5 units |
| `channel-videos` | channels.list + playlistItems.list + videos.list | ~7 units |
| `channel-top` | channels.list + playlistItems.list + videos.list | ~7 units |
| `video` | videos.list | ~1 unit |
| `search` | search.list | **100 units** |
| `compare` (2 channels) | channels.list x2 | ~10 units |
| `compare` (3 channels) | channels.list x3 | ~15 units |
| `trending` | videos.list | ~1 unit |

## YouTube Analytics API

Quota is tracked separately from the Data API. Default limit is generous for normal use.

| Command | Notes |
|---------|-------|
| `analytics-overview` | 1 query (2 if monetized — revenue is a separate call) |
| `analytics-video` | 1-2 queries (impressions/CTR is a separate call) |
| `analytics-traffic` | 1 query |
| `analytics-geography` | 1 query |
| `analytics-devices` | 1 query |
| `analytics-demographics` | 1 query |
| `analytics-revenue` | 1 query — returns empty if not monetized |
| `analytics-realtime` | 1 query |
| `analytics-top-videos` | 1 query |

## Quota tips

- **Avoid chaining multiple `search` calls** — 100 units each adds up fast
- Use `channel` (5 units) instead of `search` when you already know the handle
- `analytics-overview` with revenue tries two API calls — if channel is not monetized, the second call fails silently
- If `quota_hint: true` appears in an error response, the daily limit has been reached — wait until midnight PT to reset
- For heavy usage, request a quota increase in Google Cloud Console
