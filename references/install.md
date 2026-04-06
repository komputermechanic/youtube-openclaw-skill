# Installation Reference

## Paths

| Item | Path |
|------|------|
| Skill directory | `~/.openclaw/workspace/skills/youtube-analytics/` |
| API key file | `~/.openclaw/credentials/youtube-analytics.env` |
| OAuth credentials | `~/.openclaw/credentials/youtube-analytics-oauth.json` |
| Helper script | `~/.openclaw/workspace/skills/youtube-analytics/scripts/youtube_api.py` |

## API key file format

```
YOUTUBE_API_KEY=AIza...
```

## OAuth file format

```json
{
  "client_id": "...",
  "client_secret": "...",
  "refresh_token": "...",
  "token_uri": "https://oauth2.googleapis.com/token"
}
```

## Dependencies

```
pip install requests
```

## Google Cloud setup (required for both tiers)

1. Go to https://console.cloud.google.com/
2. Create or select a project
3. Enable **YouTube Data API v3**
4. For public commands only: create an **API key** under Credentials
5. For analytics commands: also enable **YouTube Analytics API**, then create an **OAuth 2.0 Client ID** (type: Desktop app) and add `http://localhost:8080` as an authorized redirect URI
