#!/bin/bash

# ============================================
# OpenClaw YouTube Analytics Setup Script
# By Komputer Mechanic
# ============================================

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

SKILL_DIR="$HOME/.openclaw/workspace/skills/youtube-analytics"
CREDENTIALS_DIR="$HOME/.openclaw/credentials"
API_KEY_FILE="$CREDENTIALS_DIR/youtube-analytics.env"
OAUTH_FILE="$CREDENTIALS_DIR/youtube-analytics-oauth.json"
REPO_RAW="https://raw.githubusercontent.com/komputermechanic/youtube-openclaw-skill/main"

echo ""
echo -e "${CYAN}============================================${NC}"
echo -e "${CYAN}  OpenClaw YouTube Analytics Setup${NC}"
echo -e "${CYAN}  By Komputer Mechanic${NC}"
echo -e "${CYAN}============================================${NC}"
echo ""
echo -e "${YELLOW}Disclaimer:${NC}"
echo "This script was built with the assistance of AI and is provided as-is."
echo "Komputer Mechanic is not responsible for any issues, data loss, or"
echo "misconfiguration that may result from using this script."
echo "Your credentials are stored locally on your own machine only."
echo "This script does not send your data to any third-party server."
echo "Use at your own risk. For help, visit: https://komputermechanic.com/"
echo ""
read -p "Do you want to proceed? (y/n): " PROCEED_SETUP
echo ""
if [ "$PROCEED_SETUP" != "y" ]; then
  echo -e "${YELLOW}Setup cancelled.${NC}"
  exit 0
fi

# ============================================
# WHAT DO YOU WANT TO DO?
# ============================================
echo -e "${BOLD}What do you want to do?${NC}"
echo ""
echo "  1) Install          — Set up YouTube Analytics from scratch"
echo "  2) Update API key   — Replace your YouTube Data API key"
echo "  3) Re-authenticate  — Re-run OAuth2 for Analytics access"
echo "  4) Uninstall        — Remove YouTube Analytics from OpenClaw"
echo ""
read -p "Enter 1, 2, 3 or 4: " ACTION_CHOICE
echo ""

if [[ ! "$ACTION_CHOICE" =~ ^[1-4]$ ]]; then
  echo -e "${RED}❌ Invalid choice. Exiting.${NC}"
  exit 1
fi

# ============================================
# SHARED FUNCTIONS
# ============================================
LOCAL_REPO="$(cd "$(dirname "$0")" && pwd)"

fetch_skill_files() {
  mkdir -p "$SKILL_DIR/scripts" "$SKILL_DIR/references"

  if [ -f "$LOCAL_REPO/SKILL.md" ]; then
    echo -e "${YELLOW}Installing skill files from local repo...${NC}"
    cp "$LOCAL_REPO/SKILL.md" "$SKILL_DIR/SKILL.md" && echo -e "${GREEN}✅ SKILL.md${NC}"
    cp "$LOCAL_REPO/_meta.json" "$SKILL_DIR/_meta.json" && echo -e "${GREEN}✅ _meta.json${NC}"
    cp "$LOCAL_REPO/scripts/youtube_api.py" "$SKILL_DIR/scripts/youtube_api.py" && echo -e "${GREEN}✅ scripts/youtube_api.py${NC}"
    chmod +x "$SKILL_DIR/scripts/youtube_api.py"
    for REF in install.md usage.md quota.md; do
      if [ -f "$LOCAL_REPO/references/$REF" ]; then
        cp "$LOCAL_REPO/references/$REF" "$SKILL_DIR/references/$REF" && echo -e "${GREEN}✅ references/$REF${NC}"
      fi
    done
  else
    echo -e "${YELLOW}Fetching skill files from GitHub...${NC}"
    for FILE in SKILL.md _meta.json; do
      if ! wget -q -O "$SKILL_DIR/$FILE" "$REPO_RAW/$FILE"; then
        echo -e "${RED}❌ Failed to download $FILE. Check your internet connection.${NC}"
        exit 1
      fi
      echo -e "${GREEN}✅ $FILE${NC}"
    done
    if ! wget -q -O "$SKILL_DIR/scripts/youtube_api.py" "$REPO_RAW/scripts/youtube_api.py"; then
      echo -e "${RED}❌ Failed to download scripts/youtube_api.py.${NC}"
      exit 1
    fi
    chmod +x "$SKILL_DIR/scripts/youtube_api.py"
    echo -e "${GREEN}✅ scripts/youtube_api.py${NC}"
    for REF in install.md usage.md quota.md; do
      if ! wget -q -O "$SKILL_DIR/references/$REF" "$REPO_RAW/references/$REF"; then
        echo -e "${YELLOW}⚠️  Could not download references/$REF — skipping${NC}"
      else
        echo -e "${GREEN}✅ references/$REF${NC}"
      fi
    done
  fi

  echo ""
}

check_python_deps() {
  echo -e "${YELLOW}Checking Python dependencies...${NC}"
  if ! python3 -c "import requests" 2>/dev/null; then
    echo -e "${YELLOW}Installing requests...${NC}"
    pip3 install requests --quiet
    if ! python3 -c "import requests" 2>/dev/null; then
      echo -e "${RED}❌ Could not install requests. Run: pip3 install requests${NC}"
      exit 1
    fi
  fi
  echo -e "${GREEN}✅ Python dependencies OK${NC}"
  echo ""
}

collect_api_key() {
  echo -e "${BOLD}YouTube Data API key${NC}"
  echo "This key is used for public commands (channel stats, search, trending, competitor research)."
  echo "Get yours at: https://console.cloud.google.com/ → Credentials → Create API key"
  echo "Make sure YouTube Data API v3 is enabled on your project."
  echo ""
  echo "Do not paste your key into chat. Enter it here in the terminal only."
  echo ""
  read -r -p "Paste your YouTube Data API key: " API_KEY
  echo ""
  echo ""

  if [ -z "$API_KEY" ]; then
    echo -e "${RED}❌ No key entered. Exiting.${NC}"
    exit 1
  fi

  mkdir -p "$CREDENTIALS_DIR"
  printf 'YOUTUBE_API_KEY=%s\n' "$API_KEY" > "$API_KEY_FILE"
  chmod 600 "$API_KEY_FILE"
  echo -e "${GREEN}✅ API key saved${NC}"
  echo ""
}

verify_api_key() {
  echo -e "${YELLOW}Verifying API key...${NC}"
  RESULT=$(python3 "$SKILL_DIR/scripts/youtube_api.py" channel UCQagAa6u1LBisEJTND5L42Q 2>&1)
  if echo "$RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); sys.exit(0 if d.get('ok') else 1)" 2>/dev/null; then
    echo -e "${GREEN}✅ API key verified${NC}"
    echo ""
  else
    echo -e "${RED}❌ API key verification failed.${NC}"
    echo "Check that your key is correct and YouTube Data API v3 is enabled."
    echo ""
    echo "Error: $RESULT"
    exit 1
  fi
}

collect_oauth_credentials() {
  echo -e "${BOLD}OAuth2 setup — YouTube Analytics API${NC}"
  echo ""
  echo "This unlocks your private dashboard: impressions, CTR, watch time,"
  echo "traffic sources, demographics, revenue, and more."
  echo ""
  echo -e "${CYAN}--- Step 1: Create a Google Cloud Project (if you don't have one) ---${NC}"
  echo ""
  echo "  1. Go to https://console.cloud.google.com/"
  echo "  2. Click the project dropdown at the top → 'New Project'"
  echo "  3. Give it any name (e.g. 'OpenClaw') and click Create"
  echo ""
  echo -e "${CYAN}--- Step 2: Enable the required APIs ---${NC}"
  echo ""
  echo "  1. In your project go to: APIs & Services → Library"
  echo "  2. Search for and enable: 'YouTube Data API v3'"
  echo "  3. Search for and enable: 'YouTube Analytics API'"
  echo ""
  echo -e "${CYAN}--- Step 3: Configure the OAuth consent screen ---${NC}"
  echo ""
  echo "  1. Go to: APIs & Services → OAuth consent screen"
  echo "  2. Choose 'External' → Create"
  echo "  3. Fill in App name (e.g. 'OpenClaw'), your email, and developer email"
  echo "  4. Click Save and Continue through the Scopes and Optional Info steps"
  echo "  5. On the Test Users step → click 'Add Users' → add your Google/YouTube email"
  echo "     (This is required or Google will block the login)"
  echo "  6. Click Save and Continue → Back to Dashboard"
  echo ""
  echo -e "${CYAN}--- Step 4: Create OAuth credentials ---${NC}"
  echo ""
  echo "  1. Go to: APIs & Services → Credentials"
  echo "  2. Click 'Create Credentials' → 'OAuth 2.0 Client ID'"
  echo "  3. Application type: Desktop app"
  echo "  4. Give it a name (e.g. 'OpenClaw Desktop') → Create"
  echo "  5. Copy the Client ID and Client Secret shown on screen"
  echo ""
  echo -e "${CYAN}--- Step 5: Authorize ---${NC}"
  echo ""
  echo "  When you open the Google login URL, you may see a warning:"
  echo "  'This app isn't verified' — this is normal for self-hosted setups."
  echo "  Click 'Advanced' → 'Go to [app name] (unsafe)' to continue."
  echo "  Your data stays private — nothing is sent to third-party servers."
  echo ""
  echo -e "${YELLOW}⚠️  Do not paste credentials into chat. Enter them here in the terminal only.${NC}"
  echo ""
  read -r -p "Paste your OAuth Client ID:     " OAUTH_CLIENT_ID
  echo ""
  read -r -p "Paste your OAuth Client Secret: " OAUTH_CLIENT_SECRET
  echo ""
  echo ""

  if [ -z "$OAUTH_CLIENT_ID" ] || [ -z "$OAUTH_CLIENT_SECRET" ]; then
    echo -e "${RED}❌ Client ID or Client Secret missing. Exiting.${NC}"
    exit 1
  fi

  echo -e "${YELLOW}Starting authorization...${NC}"
  echo "The authorization URL will be printed below. Open it in your browser."
  echo "Sign in with the YouTube channel account you added as a test user."
  echo ""
  echo "After authorizing, your browser will redirect to localhost:8080."
  echo "If you get a connection error (common on remote servers), copy the full"
  echo "URL from your browser bar and paste it back here when prompted."
  echo ""

  if python3 "$SKILL_DIR/scripts/youtube_api.py" auth "$OAUTH_CLIENT_ID" "$OAUTH_CLIENT_SECRET"; then
    echo -e "${GREEN}✅ OAuth credentials saved${NC}"
    echo ""
  else
    echo -e "${RED}❌ OAuth authentication failed.${NC}"
    exit 1
  fi
}

verify_oauth() {
  echo -e "${YELLOW}Verifying Analytics access...${NC}"
  RESULT=$(python3 "$SKILL_DIR/scripts/youtube_api.py" analytics-overview --days 7 2>&1)
  if echo "$RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); sys.exit(0 if d.get('ok') else 1)" 2>/dev/null; then
    echo -e "${GREEN}✅ Analytics access verified${NC}"
    echo ""
  else
    echo -e "${RED}❌ Analytics verification failed.${NC}"
    echo "Make sure you authorized the correct account and YouTube Analytics API is enabled."
    echo ""
    echo "Error: $RESULT"
    exit 1
  fi
}

print_agent_prompt() {
  echo -e "${CYAN}============================================${NC}"
  echo -e "${CYAN}  Copy and send this to your agent:${NC}"
  echo -e "${CYAN}============================================${NC}"
  echo ""
  echo "YouTube Analytics is configured in this workspace."
  echo ""
  echo "The skill is located at:"
  echo "  $SKILL_DIR"
  echo ""
  echo "Credentials are stored at:"
  echo "  API key:  $API_KEY_FILE"
  if [ -f "$OAUTH_FILE" ]; then
    echo "  OAuth:    $OAUTH_FILE"
  fi
  echo ""
  echo "When I ask about YouTube channels, videos, analytics, competitors,"
  echo "or anything YouTube-related, use this skill and its helper script."
  echo ""
  echo "Main helper script:"
  echo "  $SKILL_DIR/scripts/youtube_api.py"
  echo ""
  if [ -f "$OAUTH_FILE" ]; then
    echo "Run a quick smoke test:"
    echo "  scripts/youtube_api.py analytics-overview --days 7 --plain"
  else
    echo "Run a quick smoke test:"
    echo "  scripts/youtube_api.py channel @YouTube --plain"
  fi
  echo ""
  echo -e "${CYAN}============================================${NC}"
  echo ""
}

# ============================================
# INSTALL FLOW
# ============================================
if [ "$ACTION_CHOICE" = "1" ]; then

  # Skill files
  if [ -d "$SKILL_DIR" ]; then
    echo -e "${YELLOW}⚠️  YouTube Analytics skill is already installed at $SKILL_DIR${NC}"
    read -p "Reinstall skill files? (y/n): " REINSTALL
    echo ""
    if [ "$REINSTALL" = "y" ]; then
      fetch_skill_files
    else
      echo "Keeping existing skill files."
      echo ""
    fi
  else
    fetch_skill_files
  fi

  check_python_deps

  # Which tiers to set up?
  echo -e "${BOLD}Which access tiers do you want to set up?${NC}"
  echo ""
  echo "  1) API key only    — Public data (any channel, competitor research)"
  echo "  2) OAuth2 only     — Private analytics (own channel dashboard)"
  echo "  3) Both            — Recommended: full public + private access"
  echo ""
  read -p "Enter 1, 2 or 3: " TIER_CHOICE
  echo ""

  if [[ ! "$TIER_CHOICE" =~ ^[1-3]$ ]]; then
    echo -e "${RED}❌ Invalid choice. Exiting.${NC}"
    exit 1
  fi

  SETUP_API_KEY=false
  SETUP_OAUTH=false
  [ "$TIER_CHOICE" = "1" ] && SETUP_API_KEY=true
  [ "$TIER_CHOICE" = "2" ] && SETUP_OAUTH=true
  [ "$TIER_CHOICE" = "3" ] && SETUP_API_KEY=true && SETUP_OAUTH=true

  # API key
  if [ "$SETUP_API_KEY" = true ]; then
    if [ -f "$API_KEY_FILE" ]; then
      echo -e "${YELLOW}⚠️  An existing API key was found.${NC}"
      read -p "Do you want to replace it? (y/n): " REPLACE_KEY
      echo ""
      if [ "$REPLACE_KEY" = "y" ]; then
        collect_api_key
      else
        echo "Keeping existing API key."
        echo ""
      fi
    else
      collect_api_key
    fi
    verify_api_key
  fi

  # OAuth
  if [ "$SETUP_OAUTH" = true ]; then
    if [ -f "$OAUTH_FILE" ]; then
      echo -e "${YELLOW}⚠️  Existing OAuth credentials found.${NC}"
      read -p "Re-authenticate? (y/n): " REAUTH
      echo ""
      if [ "$REAUTH" = "y" ]; then
        collect_oauth_credentials
      else
        echo "Keeping existing OAuth credentials."
        echo ""
      fi
    else
      collect_oauth_credentials
    fi
    verify_oauth
  fi

  echo -e "${GREEN}============================================${NC}"
  echo -e "${GREEN}  Installation complete!${NC}"
  echo -e "${GREEN}============================================${NC}"
  echo ""
  if [ -f "$OAUTH_FILE" ]; then
    echo -e "${CYAN}--- Your channel ---${NC}"
    python3 "$SKILL_DIR/scripts/youtube_api.py" whoami --plain
    echo ""
    echo -e "${CYAN}--- Last 7 days ---${NC}"
    python3 "$SKILL_DIR/scripts/youtube_api.py" analytics-overview --days 7 --plain
    echo ""
  elif [ -f "$API_KEY_FILE" ]; then
    read -p "Enter your YouTube channel handle or ID to preview your stats (e.g. @yourchannel): " PREVIEW_CHANNEL
    echo ""
    if [ -n "$PREVIEW_CHANNEL" ]; then
      echo -e "${CYAN}--- Your channel ---${NC}"
      python3 "$SKILL_DIR/scripts/youtube_api.py" channel "$PREVIEW_CHANNEL" --plain
      echo ""
    fi
  fi
  print_agent_prompt
  exit 0
fi

# ============================================
# UPDATE API KEY FLOW
# ============================================
if [ "$ACTION_CHOICE" = "2" ]; then

  if [ ! -f "$SKILL_DIR/scripts/youtube_api.py" ]; then
    echo -e "${RED}❌ Skill is not installed yet. Run this script again and choose option 1.${NC}"
    exit 1
  fi

  echo -e "${BOLD}Replacing YouTube Data API key...${NC}"
  echo ""
  collect_api_key
  verify_api_key

  echo -e "${GREEN}============================================${NC}"
  echo -e "${GREEN}  API key updated successfully!${NC}"
  echo -e "${GREEN}============================================${NC}"
  echo ""
  print_agent_prompt
  exit 0
fi

# ============================================
# RE-AUTHENTICATE OAUTH FLOW
# ============================================
if [ "$ACTION_CHOICE" = "3" ]; then

  if [ ! -f "$SKILL_DIR/scripts/youtube_api.py" ]; then
    echo -e "${RED}❌ Skill is not installed yet. Run this script again and choose option 1.${NC}"
    exit 1
  fi

  echo -e "${BOLD}Re-running OAuth2 authentication...${NC}"
  echo ""
  collect_oauth_credentials
  verify_oauth

  echo -e "${GREEN}============================================${NC}"
  echo -e "${GREEN}  Re-authentication complete!${NC}"
  echo -e "${GREEN}============================================${NC}"
  echo ""
  echo -e "${YELLOW}Authenticated channel:${NC}"
  python3 "$SKILL_DIR/scripts/youtube_api.py" whoami --plain
  echo ""
  print_agent_prompt
  exit 0
fi

# ============================================
# UNINSTALL FLOW
# ============================================
if [ "$ACTION_CHOICE" = "4" ]; then

  echo -e "${YELLOW}This will remove:${NC}"
  echo "  - YouTube Analytics skill folder at $SKILL_DIR"
  [ -f "$API_KEY_FILE" ] && echo "  - Optionally your API key at $API_KEY_FILE"
  [ -f "$OAUTH_FILE"   ] && echo "  - Optionally your OAuth credentials at $OAUTH_FILE"
  echo ""
  read -p "Are you sure you want to uninstall? (y/n): " CONFIRM
  echo ""
  if [ "$CONFIRM" != "y" ]; then
    echo -e "${YELLOW}Uninstall cancelled.${NC}"
    exit 0
  fi

  if [ -d "$SKILL_DIR" ]; then
    rm -rf "$SKILL_DIR"
    echo -e "${GREEN}✅ Removed skill folder${NC}"
  else
    echo -e "${YELLOW}⚠️  Skill folder not found — skipping${NC}"
  fi

  if [ -f "$API_KEY_FILE" ]; then
    read -p "Remove your YouTube API key? (y/n): " REMOVE_KEY
    echo ""
    if [ "$REMOVE_KEY" = "y" ]; then
      rm -f "$API_KEY_FILE"
      echo -e "${GREEN}✅ API key removed${NC}"
    fi
  fi

  if [ -f "$OAUTH_FILE" ]; then
    read -p "Remove your OAuth credentials? (y/n): " REMOVE_OAUTH
    echo ""
    if [ "$REMOVE_OAUTH" = "y" ]; then
      rm -f "$OAUTH_FILE"
      echo -e "${GREEN}✅ OAuth credentials removed${NC}"
    fi
  fi

  echo ""
  echo -e "${GREEN}============================================${NC}"
  echo -e "${GREEN}  Uninstall complete!${NC}"
  echo -e "${GREEN}============================================${NC}"
  echo ""
  echo "YouTube Analytics has been removed from your OpenClaw setup."
  echo "Run this script again anytime to reinstall."
  echo ""
  exit 0
fi
