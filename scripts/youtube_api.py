#!/usr/bin/env python3
"""YouTube Analytics CLI helper for OpenClaw — by Komputer Mechanic"""

import json
import os
import re
import sys
import webbrowser
import urllib.parse
from datetime import date, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import requests

# ── Paths ─────────────────────────────────────────────────────────────────────
API_KEY_ENV = Path.home() / ".openclaw" / "credentials" / "youtube-analytics.env"
OAUTH_FILE  = Path.home() / ".openclaw" / "credentials" / "youtube-analytics-oauth.json"

# ── Constants ─────────────────────────────────────────────────────────────────
YT_API       = "https://www.googleapis.com/youtube/v3"
YT_ANALYTICS = "https://youtubeanalytics.googleapis.com/v2"
TOKEN_URI    = "https://oauth2.googleapis.com/token"
AUTH_URI     = "https://accounts.google.com/o/oauth2/v2/auth"
REDIRECT_URI = "http://localhost:8080"
SCOPES       = " ".join([
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
    "https://www.googleapis.com/auth/yt-analytics-monetary.readonly",
])


# ── Output ────────────────────────────────────────────────────────────────────
def out(data: dict) -> None:
    print(json.dumps({"ok": True, **data}, indent=2))


def fail(msg: str, quota: bool = False) -> None:
    print(json.dumps({"ok": False, "error": msg, "quota_hint": quota}, indent=2))
    sys.exit(1)


# ── Credentials ───────────────────────────────────────────────────────────────
def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def api_key() -> str:
    load_env_file(API_KEY_ENV)
    k = os.environ.get("YOUTUBE_API_KEY")
    if not k:
        fail(f"Missing YOUTUBE_API_KEY. Expected it in {API_KEY_ENV}")
    return k


def load_oauth_creds() -> dict:
    if not OAUTH_FILE.exists():
        fail(
            f"OAuth credentials not found at {OAUTH_FILE}. "
            "Run setup-youtube-analytics.sh and choose OAuth setup."
        )
    return json.loads(OAUTH_FILE.read_text())


def get_access_token() -> str:
    creds = load_oauth_creds()
    resp = requests.post(TOKEN_URI, data={
        "client_id":     creds["client_id"],
        "client_secret": creds["client_secret"],
        "refresh_token": creds["refresh_token"],
        "grant_type":    "refresh_token",
    }, timeout=15)
    if not resp.ok:
        fail(f"Token refresh failed: {resp.text}")
    return resp.json()["access_token"]


# ── HTTP helpers ──────────────────────────────────────────────────────────────
def yt_get(path: str, params: dict) -> dict:
    params["key"] = api_key()
    resp = requests.get(f"{YT_API}{path}", params=params, timeout=15)
    if not resp.ok:
        err = resp.json().get("error", {})
        msg = err.get("message", resp.text)
        fail(msg, quota=resp.status_code == 403 and "quota" in msg.lower())
    return resp.json()


def yt_oauth_get(path: str, params: dict) -> dict:
    token = get_access_token()
    resp = requests.get(
        f"{YT_API}{path}", params=params,
        headers={"Authorization": f"Bearer {token}"}, timeout=15
    )
    if not resp.ok:
        err = resp.json().get("error", {})
        fail(err.get("message", resp.text))
    return resp.json()


def analytics_get(params: dict) -> dict:
    token = get_access_token()
    resp = requests.get(
        f"{YT_ANALYTICS}/reports", params=params,
        headers={"Authorization": f"Bearer {token}"}, timeout=15
    )
    if not resp.ok:
        err = resp.json().get("error", {})
        msg = err.get("message", resp.text)
        fail(msg, quota=resp.status_code == 403 and "quota" in msg.lower())
    return resp.json()


def parse_analytics(data: dict) -> list:
    headers = [h["name"] for h in data.get("columnHeaders", [])]
    return [dict(zip(headers, row)) for row in data.get("rows", [])]


# ── Formatting ────────────────────────────────────────────────────────────────
def fmt_num(n) -> str:
    n = int(n or 0)
    if n >= 1_000_000_000: return f"{n / 1_000_000_000:.1f}B"
    if n >= 1_000_000:     return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:         return f"{n / 1_000:.1f}K"
    return str(n)


def fmt_duration(iso: str) -> str:
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    if not m:
        return iso or "0:00"
    h, mi, s = (int(x or 0) for x in m.groups())
    return f"{h}:{mi:02d}:{s:02d}" if h else f"{mi}:{s:02d}"


def fmt_seconds(secs) -> str:
    secs = int(secs or 0)
    return fmt_duration(f"PT{secs}S")


def fmt_pct(num, den, decimals=2) -> str:
    n, d = float(num or 0), float(den or 1)
    return f"{n / d * 100:.{decimals}f}%"


def fmt_money(amount) -> str:
    return f"${float(amount or 0):.2f}"


def engagement_rate(views, likes, comments) -> str:
    v = int(views or 0)
    if v == 0:
        return "0.00%"
    return f"{(int(likes or 0) + int(comments or 0)) / v * 100:.2f}%"


# ── Channel resolution ────────────────────────────────────────────────────────
def resolve_channel(channel: str) -> str:
    """Accept a channel ID (UC...) or @handle."""
    if channel.startswith("UC"):
        return channel
    handle = channel.lstrip("@")
    data = yt_get("/channels", {"part": "id", "forHandle": handle, "maxResults": 1})
    items = data.get("items", [])
    if not items:
        fail(f"Could not resolve channel: {channel}")
    return items[0]["id"]


def my_channel_id() -> str:
    data = yt_oauth_get("/channels", {"part": "id", "mine": "true"})
    items = data.get("items", [])
    if not items:
        fail("No YouTube channel found for this account.")
    return items[0]["id"]


def date_range(days: int):
    end = date.today()
    start = end - timedelta(days=days - 1)
    return start.isoformat(), end.isoformat()


# ── Arg parser ────────────────────────────────────────────────────────────────
def parse_args(argv):
    positional, flags = [], {}
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg.startswith("--"):
            key = arg[2:]
            if i + 1 < len(argv) and not argv[i + 1].startswith("--"):
                flags[key] = argv[i + 1]
                i += 2
            else:
                flags[key] = True
                i += 1
        else:
            positional.append(arg)
            i += 1
    return positional, flags


# ── OAuth flow ────────────────────────────────────────────────────────────────
def cmd_auth(args, flags):
    if len(args) < 2:
        fail("Usage: youtube_api.py auth <client_id> <client_secret>")
    client_id, client_secret = args[0], args[1]

    params = {
        "client_id":     client_id,
        "redirect_uri":  REDIRECT_URI,
        "response_type": "code",
        "scope":         SCOPES,
        "access_type":   "offline",
        "prompt":        "consent",
    }
    auth_url = f"{AUTH_URI}?{urllib.parse.urlencode(params)}"
    auth_code: list = [None]

    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if "code" in query:
                auth_code[0] = query["code"][0]
                body = b"<h2>Authorization successful!</h2><p>You can close this tab and return to the terminal.</p>"
            else:
                body = b"<h2>Authorization failed. Please try again.</h2>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_):
            pass

    server = HTTPServer(("localhost", 8080), _Handler)
    server.timeout = 120

    print(json.dumps({
        "ok": True,
        "action": "opening_browser",
        "url": auth_url,
        "message": "Browser opened for authorization. If it did not open, visit the URL manually.",
    }, indent=2), flush=True)

    try:
        webbrowser.open(auth_url)
    except Exception:
        pass

    server.handle_request()

    if not auth_code[0]:
        fail("No authorization code received. Please try again.")

    resp = requests.post(TOKEN_URI, data={
        "code":          auth_code[0],
        "client_id":     client_id,
        "client_secret": client_secret,
        "redirect_uri":  REDIRECT_URI,
        "grant_type":    "authorization_code",
    }, timeout=15)

    if not resp.ok:
        fail(f"Token exchange failed: {resp.text}")

    token_data = resp.json()
    if "refresh_token" not in token_data:
        fail("No refresh token in response. Ensure access_type=offline and prompt=consent were set.")

    creds = {
        "client_id":     client_id,
        "client_secret": client_secret,
        "refresh_token": token_data["refresh_token"],
        "token_uri":     TOKEN_URI,
    }

    OAUTH_FILE.parent.mkdir(parents=True, exist_ok=True)
    OAUTH_FILE.write_text(json.dumps(creds, indent=2))
    OAUTH_FILE.chmod(0o600)

    out({"message": "OAuth credentials saved successfully.", "path": str(OAUTH_FILE)})


# ── Public commands ───────────────────────────────────────────────────────────
def cmd_resolve(args, flags):
    if not args:
        fail("Usage: youtube_api.py resolve <@handle>")
    out({"channel_id": resolve_channel(args[0]), "input": args[0]})


def cmd_channel(args, flags):
    if not args:
        fail("Usage: youtube_api.py channel <id|@handle>")
    channel_id = resolve_channel(args[0])
    data = yt_get("/channels", {"part": "snippet,statistics,brandingSettings", "id": channel_id})
    items = data.get("items", [])
    if not items:
        fail(f"Channel not found: {args[0]}")
    item    = items[0]
    stats   = item.get("statistics", {})
    snippet = item.get("snippet", {})
    views   = int(stats.get("viewCount", 0))
    videos  = int(stats.get("videoCount", 1))
    subs    = int(stats.get("subscriberCount", 0))

    result = {
        "channel_id":                  channel_id,
        "name":                        snippet.get("title"),
        "description":                 snippet.get("description", "")[:300],
        "country":                     snippet.get("country", "N/A"),
        "created_at":                  snippet.get("publishedAt", "")[:10],
        "subscribers":                 subs,
        "subscribers_formatted":       fmt_num(subs),
        "total_views":                 views,
        "total_views_formatted":       fmt_num(views),
        "video_count":                 int(stats.get("videoCount", 0)),
        "avg_views_per_video":         round(views / videos) if videos else 0,
        "avg_views_per_video_formatted": fmt_num(views / videos) if videos else "0",
        "hidden_subscribers":          stats.get("hiddenSubscriberCount", False),
        "url":                         f"https://youtube.com/channel/{channel_id}",
    }

    if flags.get("plain"):
        print("\n".join([
            f"Channel:          {result['name']}",
            f"URL:              {result['url']}",
            f"Subscribers:      {result['subscribers_formatted']}",
            f"Total views:      {result['total_views_formatted']}",
            f"Videos:           {result['video_count']}",
            f"Avg views/video:  {result['avg_views_per_video_formatted']}",
            f"Country:          {result['country']}",
            f"Created:          {result['created_at']}",
        ]))
        return

    out(result)


def cmd_channel_videos(args, flags):
    if not args:
        fail("Usage: youtube_api.py channel-videos <id|@handle> [--max N]")
    channel_id  = resolve_channel(args[0])
    max_results = int(flags.get("max", 10))

    ch = yt_get("/channels", {"part": "contentDetails", "id": channel_id})
    if not ch.get("items"):
        fail(f"Channel not found: {args[0]}")
    uploads_id = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

    pl = yt_get("/playlistItems", {
        "part":       "contentDetails",
        "playlistId": uploads_id,
        "maxResults": min(max_results, 50),
    })
    video_ids = [i["contentDetails"]["videoId"] for i in pl.get("items", [])]
    if not video_ids:
        out({"videos": [], "count": 0})
        return

    vs = yt_get("/videos", {"part": "statistics,contentDetails,snippet", "id": ",".join(video_ids)})

    videos = []
    for v in vs.get("items", []):
        stats    = v.get("statistics", {})
        views    = int(stats.get("viewCount", 0))
        likes    = int(stats.get("likeCount", 0))
        comments = int(stats.get("commentCount", 0))
        videos.append({
            "video_id":          v["id"],
            "title":             v["snippet"]["title"],
            "published_at":      v["snippet"]["publishedAt"][:10],
            "duration":          fmt_duration(v["contentDetails"]["duration"]),
            "views":             views,
            "views_formatted":   fmt_num(views),
            "likes":             likes,
            "likes_formatted":   fmt_num(likes),
            "comments":          comments,
            "comments_formatted": fmt_num(comments),
            "engagement_rate":   engagement_rate(views, likes, comments),
            "url":               f"https://youtube.com/watch?v={v['id']}",
        })

    if flags.get("plain"):
        for v in videos:
            print(f"[{v['published_at']}] {v['title']}")
            print(f"  Views: {v['views_formatted']} | Likes: {v['likes_formatted']} | Comments: {v['comments_formatted']} | Engagement: {v['engagement_rate']}")
            print(f"  {v['url']}")
        return

    out({"channel_id": channel_id, "videos": videos, "count": len(videos)})


def cmd_channel_top(args, flags):
    if not args:
        fail("Usage: youtube_api.py channel-top <id|@handle> [--max N]")
    channel_id  = resolve_channel(args[0])
    max_results = int(flags.get("max", 10))

    ch = yt_get("/channels", {"part": "contentDetails", "id": channel_id})
    if not ch.get("items"):
        fail(f"Channel not found: {args[0]}")
    uploads_id = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

    pl = yt_get("/playlistItems", {"part": "contentDetails", "playlistId": uploads_id, "maxResults": 50})
    video_ids = [i["contentDetails"]["videoId"] for i in pl.get("items", [])]
    if not video_ids:
        out({"top_videos": [], "count": 0})
        return

    vs = yt_get("/videos", {"part": "statistics,contentDetails,snippet", "id": ",".join(video_ids)})

    videos = []
    for v in vs.get("items", []):
        stats    = v.get("statistics", {})
        views    = int(stats.get("viewCount", 0))
        likes    = int(stats.get("likeCount", 0))
        comments = int(stats.get("commentCount", 0))
        videos.append({
            "video_id":          v["id"],
            "title":             v["snippet"]["title"],
            "published_at":      v["snippet"]["publishedAt"][:10],
            "duration":          fmt_duration(v["contentDetails"]["duration"]),
            "views":             views,
            "views_formatted":   fmt_num(views),
            "likes":             likes,
            "likes_formatted":   fmt_num(likes),
            "comments":          comments,
            "comments_formatted": fmt_num(comments),
            "engagement_rate":   engagement_rate(views, likes, comments),
            "url":               f"https://youtube.com/watch?v={v['id']}",
        })

    videos.sort(key=lambda v: v["views"], reverse=True)
    videos = videos[:max_results]

    if flags.get("plain"):
        for i, v in enumerate(videos, 1):
            print(f"{i}. {v['title']} ({v['published_at']})")
            print(f"   Views: {v['views_formatted']} | Engagement: {v['engagement_rate']}")
            print(f"   {v['url']}")
        return

    out({"channel_id": channel_id, "top_videos": videos, "count": len(videos)})


def cmd_video(args, flags):
    if not args:
        fail("Usage: youtube_api.py video <video-id>")
    video_id = args[0]
    data  = yt_get("/videos", {"part": "snippet,statistics,contentDetails", "id": video_id})
    items = data.get("items", [])
    if not items:
        fail(f"Video not found: {video_id}")
    v        = items[0]
    stats    = v["statistics"]
    snippet  = v["snippet"]
    views    = int(stats.get("viewCount", 0))
    likes    = int(stats.get("likeCount", 0))
    comments = int(stats.get("commentCount", 0))

    result = {
        "video_id":          video_id,
        "title":             snippet["title"],
        "channel":           snippet["channelTitle"],
        "channel_id":        snippet["channelId"],
        "published_at":      snippet["publishedAt"][:10],
        "duration":          fmt_duration(v["contentDetails"]["duration"]),
        "tags":              snippet.get("tags", []),
        "views":             views,
        "views_formatted":   fmt_num(views),
        "likes":             likes,
        "likes_formatted":   fmt_num(likes),
        "comments":          comments,
        "comments_formatted": fmt_num(comments),
        "engagement_rate":   engagement_rate(views, likes, comments),
        "like_ratio":        fmt_pct(likes, views) if views else "0.00%",
        "url":               f"https://youtube.com/watch?v={video_id}",
    }

    if flags.get("plain"):
        print("\n".join([
            f"Title:           {result['title']}",
            f"Channel:         {result['channel']}",
            f"Published:       {result['published_at']}",
            f"Duration:        {result['duration']}",
            f"Views:           {result['views_formatted']}",
            f"Likes:           {result['likes_formatted']} ({result['like_ratio']})",
            f"Comments:        {result['comments_formatted']}",
            f"Engagement rate: {result['engagement_rate']}",
            f"URL:             {result['url']}",
        ]))
        return

    out(result)


def cmd_search(args, flags):
    if not args:
        fail("Usage: youtube_api.py search <query> [--type video|channel] [--max N]")
    query       = " ".join(args)
    search_type = flags.get("type", "video")
    max_results = int(flags.get("max", 10))

    data  = yt_get("/search", {
        "part":       "snippet",
        "q":          query,
        "type":       search_type,
        "maxResults": min(max_results, 50),
        "order":      "relevance",
    })

    items = []
    for item in data.get("items", []):
        snippet = item["snippet"]
        entry   = {
            "title":        snippet["title"],
            "channel":      snippet["channelTitle"],
            "description":  snippet.get("description", "")[:150],
            "published_at": snippet.get("publishedAt", "")[:10],
        }
        if "videoId" in item["id"]:
            entry["video_id"] = item["id"]["videoId"]
            entry["url"]      = f"https://youtube.com/watch?v={item['id']['videoId']}"
        elif "channelId" in item["id"]:
            entry["channel_id"] = item["id"]["channelId"]
            entry["url"]        = f"https://youtube.com/channel/{item['id']['channelId']}"
        items.append(entry)

    if flags.get("plain"):
        for item in items:
            print(f"[{item.get('published_at', '')}] {item['title']} — {item['channel']}")
            print(f"  {item.get('url', '')}")
        return

    out({"query": query, "type": search_type, "results": items, "count": len(items)})


def cmd_compare(args, flags):
    if len(args) < 2:
        fail("Usage: youtube_api.py compare <id1|@handle1> <id2|@handle2> [id3|@handle3]")

    channels = []
    for handle in args[:3]:
        cid  = resolve_channel(handle)
        data = yt_get("/channels", {"part": "snippet,statistics", "id": cid})
        if not data.get("items"):
            fail(f"Channel not found: {handle}")
        item   = data["items"][0]
        stats  = item["statistics"]
        views  = int(stats.get("viewCount", 0))
        videos = int(stats.get("videoCount", 1))
        subs   = int(stats.get("subscriberCount", 0))
        channels.append({
            "channel_id":                    cid,
            "name":                          item["snippet"]["title"],
            "subscribers":                   subs,
            "subscribers_formatted":         fmt_num(subs),
            "total_views":                   views,
            "total_views_formatted":         fmt_num(views),
            "video_count":                   int(stats.get("videoCount", 0)),
            "avg_views_per_video":           round(views / videos) if videos else 0,
            "avg_views_per_video_formatted": fmt_num(views / videos) if videos else "0",
            "country":                       item["snippet"].get("country", "N/A"),
            "url":                           f"https://youtube.com/channel/{cid}",
        })

    if flags.get("plain"):
        fields = [
            ("Subscribers",      "subscribers_formatted"),
            ("Total views",      "total_views_formatted"),
            ("Videos",           "video_count"),
            ("Avg views/video",  "avg_views_per_video_formatted"),
            ("Country",          "country"),
        ]
        names = [c["name"] for c in channels]
        col_w = max(20, max(len(n) for n in names) + 2)
        header = "Metric".ljust(22) + "".join(n.ljust(col_w) for n in names)
        print(header)
        print("-" * len(header))
        for label, key in fields:
            print(label.ljust(22) + "".join(str(c[key]).ljust(col_w) for c in channels))
        return

    out({"channels": channels, "count": len(channels)})


def cmd_trending(args, flags):
    region      = flags.get("region", "US")
    category    = flags.get("category", "0")
    max_results = int(flags.get("max", 10))

    data = yt_get("/videos", {
        "part":            "snippet,statistics,contentDetails",
        "chart":           "mostPopular",
        "regionCode":      region,
        "videoCategoryId": category,
        "maxResults":      min(max_results, 50),
    })

    videos = []
    for v in data.get("items", []):
        stats    = v["statistics"]
        snippet  = v["snippet"]
        views    = int(stats.get("viewCount", 0))
        likes    = int(stats.get("likeCount", 0))
        comments = int(stats.get("commentCount", 0))
        videos.append({
            "video_id":          v["id"],
            "title":             snippet["title"],
            "channel":           snippet["channelTitle"],
            "published_at":      snippet["publishedAt"][:10],
            "duration":          fmt_duration(v["contentDetails"]["duration"]),
            "views":             views,
            "views_formatted":   fmt_num(views),
            "likes_formatted":   fmt_num(likes),
            "comments_formatted": fmt_num(comments),
            "engagement_rate":   engagement_rate(views, likes, comments),
            "url":               f"https://youtube.com/watch?v={v['id']}",
        })

    if flags.get("plain"):
        for i, v in enumerate(videos, 1):
            print(f"{i}. {v['title']} — {v['channel']}")
            print(f"   Views: {v['views_formatted']} | Engagement: {v['engagement_rate']}")
        return

    out({"region": region, "category": category, "trending": videos, "count": len(videos)})


# ── Analytics commands ────────────────────────────────────────────────────────
def cmd_analytics_overview(args, flags):
    days  = int(flags.get("days", 28))
    start, end = date_range(days)
    cid   = my_channel_id()

    data = analytics_get({
        "ids":       f"channel=={cid}",
        "startDate": start,
        "endDate":   end,
        "metrics":   "views,estimatedMinutesWatched,averageViewDuration,subscribersGained,subscribersLost,likes,comments,shares",
    })
    rows = parse_analytics(data)
    if not rows:
        out({"period": f"{start} to {end}", "message": "No data for this period."})
        return

    r           = rows[0]
    views       = int(r.get("views", 0))
    watch_min   = int(r.get("estimatedMinutesWatched", 0))
    gained      = int(r.get("subscribersGained", 0))
    lost        = int(r.get("subscribersLost", 0))

    result = {
        "period":                    f"{start} to {end}",
        "days":                      days,
        "views":                     views,
        "views_formatted":           fmt_num(views),
        "watch_time_minutes":        watch_min,
        "watch_time_hours":          round(watch_min / 60, 1),
        "avg_view_duration_seconds": int(r.get("averageViewDuration", 0)),
        "avg_view_duration":         fmt_seconds(r.get("averageViewDuration", 0)),
        "subscribers_gained":        gained,
        "subscribers_lost":          lost,
        "net_subscribers":           gained - lost,
        "likes":                     int(r.get("likes", 0)),
        "comments":                  int(r.get("comments", 0)),
        "shares":                    int(r.get("shares", 0)),
    }

    # Revenue — optional, only works for monetized channels
    try:
        rev = analytics_get({
            "ids":       f"channel=={cid}",
            "startDate": start,
            "endDate":   end,
            "metrics":   "estimatedRevenue,cpm,playbackBasedCpm",
        })
        rev_rows = parse_analytics(rev)
        if rev_rows:
            result["revenue"] = {
                "estimated_revenue":  fmt_money(rev_rows[0].get("estimatedRevenue", 0)),
                "cpm":                fmt_money(rev_rows[0].get("cpm", 0)),
                "playback_based_cpm": fmt_money(rev_rows[0].get("playbackBasedCpm", 0)),
            }
    except SystemExit:
        pass

    if flags.get("plain"):
        lines = [
            f"Period:              {result['period']}",
            f"Views:               {result['views_formatted']}",
            f"Watch time:          {result['watch_time_hours']}h",
            f"Avg view duration:   {result['avg_view_duration']}",
            f"Subscribers:         +{gained} gained / -{lost} lost (net {gained - lost:+d})",
            f"Likes:               {fmt_num(result['likes'])}",
            f"Comments:            {fmt_num(result['comments'])}",
            f"Shares:              {fmt_num(result['shares'])}",
        ]
        if "revenue" in result:
            r2 = result["revenue"]
            lines.append(f"Est. revenue:        {r2['estimated_revenue']} | CPM: {r2['cpm']}")
        print("\n".join(lines))
        return

    out(result)


def cmd_analytics_video(args, flags):
    if not args:
        fail("Usage: youtube_api.py analytics-video <video-id> [--days N]")
    video_id    = args[0]
    days        = int(flags.get("days", 28))
    start, end  = date_range(days)
    cid         = my_channel_id()

    data = analytics_get({
        "ids":       f"channel=={cid}",
        "startDate": start,
        "endDate":   end,
        "filters":   f"video=={video_id}",
        "metrics":   "views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,likes,comments,shares,subscribersGained,subscribersLost",
    })
    rows = parse_analytics(data)
    if not rows:
        out({"video_id": video_id, "period": f"{start} to {end}", "message": "No data for this period."})
        return

    r         = rows[0]
    views     = int(r.get("views", 0))
    watch_min = int(r.get("estimatedMinutesWatched", 0))
    gained    = int(r.get("subscribersGained", 0))
    lost      = int(r.get("subscribersLost", 0))

    result = {
        "video_id":                  video_id,
        "period":                    f"{start} to {end}",
        "views":                     views,
        "views_formatted":           fmt_num(views),
        "watch_time_hours":          round(watch_min / 60, 1),
        "avg_view_duration_seconds": int(r.get("averageViewDuration", 0)),
        "avg_view_duration":         fmt_seconds(r.get("averageViewDuration", 0)),
        "avg_view_percentage":       f"{float(r.get('averageViewPercentage', 0)):.1f}%",
        "likes":                     int(r.get("likes", 0)),
        "comments":                  int(r.get("comments", 0)),
        "shares":                    int(r.get("shares", 0)),
        "subscribers_gained":        gained,
        "subscribers_lost":          lost,
    }

    # Impressions + CTR — requires additional permission
    try:
        imp = analytics_get({
            "ids":       f"channel=={cid}",
            "startDate": start,
            "endDate":   end,
            "filters":   f"video=={video_id}",
            "metrics":   "impressions,impressionClickThroughRate",
        })
        imp_rows = parse_analytics(imp)
        if imp_rows:
            result["impressions"] = {
                "count":     int(imp_rows[0].get("impressions", 0)),
                "formatted": fmt_num(imp_rows[0].get("impressions", 0)),
                "ctr":       f"{float(imp_rows[0].get('impressionClickThroughRate', 0)):.2f}%",
            }
    except SystemExit:
        pass

    if flags.get("plain"):
        lines = [
            f"Video ID:          {video_id}",
            f"Period:            {result['period']}",
            f"Views:             {result['views_formatted']}",
            f"Watch time:        {result['watch_time_hours']}h",
            f"Avg duration:      {result['avg_view_duration']} ({result['avg_view_percentage']} watched)",
            f"Likes:             {fmt_num(result['likes'])}",
            f"Comments:          {fmt_num(result['comments'])}",
            f"Shares:            {fmt_num(result['shares'])}",
            f"Subscribers:       +{gained} / -{lost}",
        ]
        if "impressions" in result:
            imp = result["impressions"]
            lines.append(f"Impressions:       {imp['formatted']} | CTR: {imp['ctr']}")
        print("\n".join(lines))
        return

    out(result)


def cmd_analytics_traffic(args, flags):
    days        = int(flags.get("days", 28))
    start, end  = date_range(days)
    cid         = my_channel_id()

    data = analytics_get({
        "ids":        f"channel=={cid}",
        "startDate":  start,
        "endDate":    end,
        "dimensions": "insightTrafficSourceType",
        "metrics":    "views,estimatedMinutesWatched",
        "sort":       "-views",
    })
    rows        = parse_analytics(data)
    total_views = sum(int(r.get("views", 0)) for r in rows)

    sources = []
    for r in rows:
        views = int(r.get("views", 0))
        sources.append({
            "source":            r.get("insightTrafficSourceType", "UNKNOWN"),
            "views":             views,
            "views_formatted":   fmt_num(views),
            "share":             fmt_pct(views, total_views, 1) if total_views else "0%",
            "watch_time_hours":  round(int(r.get("estimatedMinutesWatched", 0)) / 60, 1),
        })

    if flags.get("plain"):
        print(f"Traffic sources ({start} to {end}):")
        for s in sources:
            print(f"  {s['source']}: {s['views_formatted']} views ({s['share']}) — {s['watch_time_hours']}h watch time")
        return

    out({"period": f"{start} to {end}", "total_views": total_views, "sources": sources})


def cmd_analytics_geography(args, flags):
    days        = int(flags.get("days", 28))
    max_results = int(flags.get("max", 10))
    start, end  = date_range(days)
    cid         = my_channel_id()

    data = analytics_get({
        "ids":        f"channel=={cid}",
        "startDate":  start,
        "endDate":    end,
        "dimensions": "country",
        "metrics":    "views,estimatedMinutesWatched,subscribersGained",
        "sort":       "-views",
        "maxResults": min(max_results, 25),
    })
    rows  = parse_analytics(data)
    total = sum(int(r.get("views", 0)) for r in rows)

    countries = []
    for r in rows:
        views = int(r.get("views", 0))
        countries.append({
            "country":            r.get("country"),
            "views":              views,
            "views_formatted":    fmt_num(views),
            "share":              fmt_pct(views, total, 1) if total else "0%",
            "watch_time_hours":   round(int(r.get("estimatedMinutesWatched", 0)) / 60, 1),
            "subscribers_gained": int(r.get("subscribersGained", 0)),
        })

    if flags.get("plain"):
        print(f"Top countries ({start} to {end}):")
        for c in countries:
            print(f"  {c['country']}: {c['views_formatted']} ({c['share']}) | +{c['subscribers_gained']} subs | {c['watch_time_hours']}h watch time")
        return

    out({"period": f"{start} to {end}", "countries": countries})


def cmd_analytics_devices(args, flags):
    days       = int(flags.get("days", 28))
    start, end = date_range(days)
    cid        = my_channel_id()

    data = analytics_get({
        "ids":        f"channel=={cid}",
        "startDate":  start,
        "endDate":    end,
        "dimensions": "deviceType",
        "metrics":    "views,estimatedMinutesWatched",
        "sort":       "-views",
    })
    rows  = parse_analytics(data)
    total = sum(int(r.get("views", 0)) for r in rows)

    devices = []
    for r in rows:
        views = int(r.get("views", 0))
        devices.append({
            "device":           r.get("deviceType"),
            "views":            views,
            "views_formatted":  fmt_num(views),
            "share":            fmt_pct(views, total, 1) if total else "0%",
            "watch_time_hours": round(int(r.get("estimatedMinutesWatched", 0)) / 60, 1),
        })

    if flags.get("plain"):
        print(f"Device breakdown ({start} to {end}):")
        for d in devices:
            print(f"  {d['device']}: {d['views_formatted']} ({d['share']}) — {d['watch_time_hours']}h watch time")
        return

    out({"period": f"{start} to {end}", "total_views": total, "devices": devices})


def cmd_analytics_demographics(args, flags):
    days       = int(flags.get("days", 28))
    start, end = date_range(days)
    cid        = my_channel_id()

    data = analytics_get({
        "ids":        f"channel=={cid}",
        "startDate":  start,
        "endDate":    end,
        "dimensions": "ageGroup,gender",
        "metrics":    "viewerPercentage",
        "sort":       "-viewerPercentage",
    })
    rows = parse_analytics(data)

    breakdown = [{"age_group": r.get("ageGroup"), "gender": r.get("gender"),
                  "viewer_percentage": f"{float(r.get('viewerPercentage', 0)):.1f}%"} for r in rows]

    age_summary    = {}
    gender_summary = {}
    for r in rows:
        age    = r.get("ageGroup", "UNKNOWN")
        gender = r.get("gender", "UNKNOWN")
        pct    = float(r.get("viewerPercentage", 0))
        age_summary[age]       = age_summary.get(age, 0) + pct
        gender_summary[gender] = gender_summary.get(gender, 0) + pct

    if flags.get("plain"):
        print(f"Demographics ({start} to {end}):")
        print("Gender:")
        for g, pct in sorted(gender_summary.items(), key=lambda x: -x[1]):
            print(f"  {g}: {pct:.1f}%")
        print("Age groups:")
        for a, pct in sorted(age_summary.items(), key=lambda x: -x[1]):
            print(f"  {a}: {pct:.1f}%")
        return

    out({
        "period":          f"{start} to {end}",
        "by_age_gender":   breakdown,
        "age_summary":     {k: f"{v:.1f}%" for k, v in age_summary.items()},
        "gender_summary":  {k: f"{v:.1f}%" for k, v in gender_summary.items()},
    })


def cmd_analytics_revenue(args, flags):
    days       = int(flags.get("days", 28))
    start, end = date_range(days)
    cid        = my_channel_id()

    data = analytics_get({
        "ids":       f"channel=={cid}",
        "startDate": start,
        "endDate":   end,
        "metrics":   "estimatedRevenue,estimatedAdRevenue,estimatedRedPartnerRevenue,grossRevenue,cpm,playbackBasedCpm,adImpressions",
    })
    rows = parse_analytics(data)
    if not rows:
        out({"period": f"{start} to {end}", "message": "No revenue data. Channel may not be monetized."})
        return

    r      = rows[0]
    result = {
        "period":                             f"{start} to {end}",
        "estimated_revenue":                  fmt_money(r.get("estimatedRevenue", 0)),
        "estimated_ad_revenue":               fmt_money(r.get("estimatedAdRevenue", 0)),
        "estimated_youtube_premium_revenue":  fmt_money(r.get("estimatedRedPartnerRevenue", 0)),
        "gross_revenue":                      fmt_money(r.get("grossRevenue", 0)),
        "cpm":                                fmt_money(r.get("cpm", 0)),
        "playback_based_cpm":                 fmt_money(r.get("playbackBasedCpm", 0)),
        "ad_impressions":                     int(r.get("adImpressions", 0)),
        "ad_impressions_formatted":           fmt_num(r.get("adImpressions", 0)),
    }

    if flags.get("plain"):
        print("\n".join([
            f"Revenue ({result['period']}):",
            f"  Estimated revenue:          {result['estimated_revenue']}",
            f"  Ad revenue:                 {result['estimated_ad_revenue']}",
            f"  YouTube Premium revenue:    {result['estimated_youtube_premium_revenue']}",
            f"  Gross revenue:              {result['gross_revenue']}",
            f"  CPM:                        {result['cpm']}",
            f"  Playback-based CPM:         {result['playback_based_cpm']}",
            f"  Ad impressions:             {result['ad_impressions_formatted']}",
        ]))
        return

    out(result)


def cmd_analytics_realtime(args, flags):
    """Last 48 hours. YouTube Analytics API has a ~24-72h delay — this is as close to real-time as possible."""
    start, end = date_range(2)
    cid        = my_channel_id()

    data = analytics_get({
        "ids":       f"channel=={cid}",
        "startDate": start,
        "endDate":   end,
        "metrics":   "views,estimatedMinutesWatched,subscribersGained,subscribersLost,likes,shares",
    })
    rows = parse_analytics(data)
    if not rows:
        out({"period": "last 48 hours", "message": "No data yet for this window."})
        return

    r         = rows[0]
    views     = int(r.get("views", 0))
    watch_min = int(r.get("estimatedMinutesWatched", 0))
    gained    = int(r.get("subscribersGained", 0))
    lost      = int(r.get("subscribersLost", 0))

    result = {
        "period":               "last 48 hours",
        "start_date":           start,
        "end_date":             end,
        "views":                views,
        "views_formatted":      fmt_num(views),
        "watch_time_minutes":   watch_min,
        "watch_time_hours":     round(watch_min / 60, 1),
        "subscribers_gained":   gained,
        "subscribers_lost":     lost,
        "net_subscribers":      gained - lost,
        "likes":                int(r.get("likes", 0)),
        "shares":               int(r.get("shares", 0)),
        "note":                 "Analytics data has a 24-72 hour processing delay. This reflects recent but not live data.",
    }

    if flags.get("plain"):
        print("\n".join([
            "Last 48 hours:",
            f"  Views:        {result['views_formatted']}",
            f"  Watch time:   {result['watch_time_hours']}h",
            f"  Subscribers:  +{gained} / -{lost} (net {gained - lost:+d})",
            f"  Likes:        {fmt_num(result['likes'])}",
            f"  Shares:       {fmt_num(result['shares'])}",
            f"  Note:         {result['note']}",
        ]))
        return

    out(result)


def cmd_analytics_top_videos(args, flags):
    days        = int(flags.get("days", 28))
    max_results = int(flags.get("max", 10))
    start, end  = date_range(days)
    cid         = my_channel_id()

    data = analytics_get({
        "ids":        f"channel=={cid}",
        "startDate":  start,
        "endDate":    end,
        "dimensions": "video",
        "metrics":    "views,estimatedMinutesWatched,averageViewPercentage,likes,comments,subscribersGained",
        "sort":       "-views",
        "maxResults": min(max_results, 200),
    })
    rows   = parse_analytics(data)
    videos = []
    for r in rows:
        views = int(r.get("views", 0))
        videos.append({
            "video_id":             r.get("video"),
            "views":                views,
            "views_formatted":      fmt_num(views),
            "watch_time_hours":     round(int(r.get("estimatedMinutesWatched", 0)) / 60, 1),
            "avg_view_percentage":  f"{float(r.get('averageViewPercentage', 0)):.1f}%",
            "likes":                int(r.get("likes", 0)),
            "comments":             int(r.get("comments", 0)),
            "subscribers_gained":   int(r.get("subscribersGained", 0)),
            "url":                  f"https://youtube.com/watch?v={r.get('video')}",
        })

    if flags.get("plain"):
        print(f"Top {len(videos)} videos ({start} to {end}):")
        for i, v in enumerate(videos, 1):
            print(f"  {i}. {v['video_id']}: {v['views_formatted']} views | {v['avg_view_percentage']} watched | +{v['subscribers_gained']} subs")
            print(f"     {v['url']}")
        return

    out({"period": f"{start} to {end}", "top_videos": videos, "count": len(videos)})


# ── Dispatcher ────────────────────────────────────────────────────────────────
COMMANDS = {
    "auth":                   cmd_auth,
    "resolve":                cmd_resolve,
    "channel":                cmd_channel,
    "channel-videos":         cmd_channel_videos,
    "channel-top":            cmd_channel_top,
    "video":                  cmd_video,
    "search":                 cmd_search,
    "compare":                cmd_compare,
    "trending":               cmd_trending,
    "analytics-overview":     cmd_analytics_overview,
    "analytics-video":        cmd_analytics_video,
    "analytics-traffic":      cmd_analytics_traffic,
    "analytics-geography":    cmd_analytics_geography,
    "analytics-devices":      cmd_analytics_devices,
    "analytics-demographics": cmd_analytics_demographics,
    "analytics-revenue":      cmd_analytics_revenue,
    "analytics-realtime":     cmd_analytics_realtime,
    "analytics-top-videos":   cmd_analytics_top_videos,
}


def main():
    if len(sys.argv) < 2:
        print(
            f"Usage: youtube_api.py <command> [args] [--flags]\n"
            f"Commands: {', '.join(COMMANDS)}",
            file=sys.stderr,
        )
        sys.exit(2)

    cmd = sys.argv[1]
    if cmd not in COMMANDS:
        print(f"Unknown command: {cmd}\nAvailable: {', '.join(COMMANDS)}", file=sys.stderr)
        sys.exit(2)

    positional, flags = parse_args(sys.argv[2:])
    COMMANDS[cmd](positional, flags)


if __name__ == "__main__":
    main()
