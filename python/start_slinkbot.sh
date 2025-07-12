#!/bin/bash

# SlinkBot Phase 3 Startup Script

echo "🚀 Starting SlinkBot Phase 3 Deployment"
echo "========================================"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run:"
    echo "   python3 -m venv venv"
    echo "   source venv/bin/activate"
    echo "   pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment
echo "📦 Activating virtual environment..."
source venv/bin/activate

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  No .env file found. Please create one from .env.example"
    echo "   cp .env.example .env"
    echo "   # Edit .env with your actual values"
    exit 1
fi

# Load environment variables
echo "🔧 Loading environment variables..."
export $(cat .env | grep -v '^#' | xargs)

# Check required environment variables
required_vars=("JELLYSEERR_URL" "JELLYSEERR_API_KEY" "DISCORD_BOT_TOKEN" "CHANNEL_SLINKBOT_STATUS")
missing_vars=()

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -ne 0 ]; then
    echo "❌ Missing required environment variables:"
    printf '   %s\n' "${missing_vars[@]}"
    echo "Please update your .env file."
    exit 1
fi

# Create data directory if it doesn't exist
echo "📁 Creating data directory..."
mkdir -p data

# Check if migration is needed
if [ -f "request_tracking.json" ] && [ ! -f "data/slinkbot.db" ]; then
    echo "🔄 JSON tracking file found. Migration recommended."
    echo "Run: python migration/migrate_json_to_sqlite.py request_tracking.json"
    echo "Continue anyway? (y/N)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        echo "Migration cancelled. Please run migration first."
        exit 1
    fi
fi

# Start the bot
echo "🤖 Starting SlinkBot Phase 3..."
echo "Press Ctrl+C to stop the bot"
echo "========================================"

python slinkbot_phase3.py