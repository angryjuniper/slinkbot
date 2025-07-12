# SlinkBot Alpha v0.1.0 - Comprehensive Implementation Guide

## Overview

SlinkBot is an advanced Discord media request management system that integrates with Jellyseerr, Radarr, Sonarr, and other *arr services to provide seamless media request handling, status tracking, and automated notifications. As of **Alpha v0.1.0**, SlinkBot has evolved through 5 phases of preliminary internal development, culminating in advanced command management and database consistency features.

## Current Status: Alpha v0.1.0

### Key Features
- **Advanced Command Management** - Improved command synchronization with better rate limiting and timeout handling
- **Database Consistency Monitoring** - Real-time request tracking and integrity verification
- **Enhanced Drive Space Monitoring** - Simplified, accurate storage status reporting
- **Reliable Command Syncing** - Enhanced `/sync-commands` with 60-second timeout and fallback mechanisms
- **Comprehensive Health Monitoring** - System status, service health, and database metrics
- **Enhanced User Experience** - `/my-requests` shows complete request history, improved startup notifications
- **Help System** - Built-in `/slinkbot-help` command for user guidance

## File Structure & Architecture

### Directory Layout
```
/opt/docker/slinkbot/
├── VERSION                          # Current version tracking (Alpha v0.2.0)
├── docker-compose.yml               # Complete media stack orchestration
├── .env                            # Environment configuration
├── logs/                           # Application logs
├── python/                         # Core SlinkBot application
│   ├── slinkbot.py                 # Main application (ACTIVE)
│   ├── slinkbot_phase4.py          # Phase 4 implementation (legacy)
│   ├── database/
│   │   └── models.py               # SQLAlchemy ORM models with indexing
│   ├── commands/
│   │   ├── advanced_commands.py    # Search, quick-request, stats commands
│   │   ├── request_commands.py     # Movie, TV, anime request handlers
│   │   └── base.py                 # Base command framework
│   ├── services/
│   │   ├── jellyseerr.py          # Jellyseerr API integration
│   │   └── base.py                # Base service framework
│   ├── managers/
│   │   ├── request_manager.py     # Request lifecycle management
│   │   └── health_manager.py      # Service health monitoring
│   ├── notifications/
│   │   └── enhanced_notifier.py   # Advanced notification system
│   ├── phase5/
│   │   ├── quick_sync.py          # Phase 5 command synchronization
│   │   └── __init__.py
│   ├── tasks/
│   │   ├── scheduler.py           # Background task management
│   │   └── background_tasks.py    # Task implementations
│   ├── ui/
│   │   └── enhanced_components.py # Discord UI components
│   ├── utils/
│   │   └── simple_logging.py      # Logging configuration
│   ├── config/
│   │   └── settings.py            # Configuration management
│   └── migration/
│       └── add_poster_url_column.py # Database migrations
├── roadmap/                        # Development documentation
└── simple_command_check.py         # Diagnostic utilities
```

### Core Components

#### 1. SlinkBot Alpha v0.2.0 (`python/slinkbot.py`)
**Primary application entry point** featuring:
- Advanced command registration and synchronization
- Enhanced database consistency monitoring
- Alpha v0.2.0 quick sync capabilities
- Comprehensive health checking
- Background task scheduling

#### 2. Database Models (`python/database/models.py`)
**Robust data persistence** with:
- `TrackedRequest` - Media request tracking with proper indexing
- `ServiceHealth` - Service status monitoring
- `RequestStatusHistory` - Status change tracking
- `BotConfiguration` - Bot settings storage
- Enhanced SQLAlchemy ORM with connection pooling

#### 3. Command System
**Multi-tier command architecture**:
- **Advanced Commands** (`commands/advanced_commands.py`) - Search, request-media, statistics
- **Request Commands** (`commands/request_commands.py`) - Movie, TV, anime requests
- **Alpha v0.2.0 Commands** (built-in) - sync, drive-space, database-status, system-status

#### 4. Services Integration
**External API management**:
- **Jellyseerr Service** - Media request API integration
- **Base Service** - Common API framework with retry logic
- **Health Manager** - Service availability monitoring

## Docker Stack Architecture

### Complete Media Server Stack
The `docker-compose.yml` orchestrates a comprehensive media management ecosystem:

```yaml
# Core Components
- gluetun (VPN gateway)
- cloudflared (secure tunneling)
- slinkbot_phase5 (Discord bot)

# Media Management
- jellyseerr (request management)
- jellyfin (media server)
- radarr (movie automation)
- sonarr (TV automation)
- prowlarr (indexer management)
- sabnzbd (download client)

# Infrastructure
- tailscale (secure remote access)
- netdata (monitoring)
```

### Network Architecture
- **gluetun** serves as VPN gateway for all media services
- **cloudflared** provides secure external access
- **tailscale** enables secure remote administration
- **slinkbot_default** connects through gluetun for API access

## Environment Configuration

### Required Environment Variables

#### Core Discord Configuration
```bash
DISCORD_BOT_TOKEN=your_bot_token_here
DISCORD_GUILD_ID=your_guild_id_here
```

#### Service API Configuration
```bash
JELLYSEERR_API_KEY=your_jellyseerr_api_key
JELLYSEERR_URL=http://localhost:5055
RADARR_API_KEY=your_radarr_api_key
SONARR_API_KEY=your_sonarr_api_key
SABNZBD_API_KEY=your_sabnzbd_api_key
```

#### Discord Channel Configuration
```bash
CHANNEL_SLINKBOT_STATUS=channel_id_for_bot_status
CHANNEL_REQUEST_STATUS=channel_id_for_request_updates
CHANNEL_MOVIE_REQUESTS=channel_id_for_movie_requests
CHANNEL_TV_REQUESTS=channel_id_for_tv_requests
CHANNEL_ANIME_REQUESTS=channel_id_for_anime_requests
CHANNEL_DOWNLOAD_QUEUE=channel_id_for_download_status
CHANNEL_MEDIA_ARRIVALS=channel_id_for_arrival_notifications
CHANNEL_CANCEL_REQUEST=channel_id_for_cancellations
CHANNEL_SERVICE_ALERTS=channel_id_for_service_health
```

#### Infrastructure Configuration
```bash
# VPN Configuration
VPN_SERVICE_PROVIDER=your_vpn_provider
WIREGUARD_PRIVATE_KEY=your_vpn_key

# Cloudflare Tunnel
CLOUDFLARE_TUNNEL_TOKEN=your_tunnel_token

# Tailscale
TAILSCALE_AUTH_KEY=your_tailscale_key

# Monitoring
NETDATA_CLAIM_TOKEN=your_netdata_token
```

## Deployment & Usage Guide

### Initial Setup

1. **Clone Repository**
```bash
cd /opt/docker
git clone https://github.com/angryjuniper/slinkbot.git
cd slinkbot
```

2. **Configure Environment**
```bash
cp python/config/examples.env .env
# Edit .env with your specific configuration
```

3. **Start Infrastructure Services**
```bash
# NOTE: Always use 'docker compose' not 'docker-compose'
# Start VPN and basic services first
docker compose up -d gluetun cloudflared tailscale netdata

# Wait for VPN connection, then start media services
docker compose up -d jellyfin jellyseerr radarr sonarr prowlarr sabnzbd
```

4. **Deploy SlinkBot Alpha v0.2.0**
```bash
# Build and start SlinkBot
docker compose up -d slinkbot
```

### Verification & Testing

#### Check Service Status
```bash
# View all container status
docker compose ps

# Check SlinkBot logs
docker compose logs slinkbot --tail=50

# Test bot connectivity
python3 simple_command_check.py
```

#### Verify Command Registration
```bash
# Check Discord for commands:
# /bot-status - System overview
# /check-drive-space - Storage status
# /database-status - Database health
# /sync-commands - Force command sync (Admin)
```

### Command Reference

#### Administrative Commands (Require Admin Permissions)
- **`/sync-commands`** - Force immediate guild command synchronization with enhanced reliability
  - `force: bool` - Force sync even if recently synced
  - `verify: bool` - Verify commands after sync
  - Enhanced with 60-second timeout and better rate limiting

- **`/check-drive-space`** - Display server storage status
  - Shows available space, usage percentage, and warnings

- **`/system-status`** - Comprehensive system status including bot, database, and services
  - Consolidates database health, request statistics, and service monitoring

#### Media Request Commands
- **`/search`** - Search media without requesting
- **`/request-media`** - Comprehensive media requests (movies, TV shows, episodes)
  - Auto-detection for episodes (S01E01 format)
  - TV show season/episode selection
  - Movie requests

#### Status & Information
- **`/slinkbot-help`** - User-friendly help system for non-admin commands
- **`/bot-status`** - Comprehensive system status
- **`/my-requests`** - View your complete request history (active and completed)
- **`/request-stats`** - System-wide request statistics

### Database Management

#### Database Features
- **Automatic indexing** on critical fields (user_id, request_id, status)
- **Consistency monitoring** every 30 minutes
- **Request tracking** with proper foreign key relationships
- **Status history** for audit trails
- **Health monitoring** with error tracking

#### Manual Database Operations
```bash
# Access database directly
docker exec -it slinkbot_phase5 python3 -c "
from database.models import db_manager
stats = db_manager.get_stats()
print(f'Database Stats: {stats}')
"
```

### Troubleshooting

#### Common Issues

1. **Commands Not Appearing**
   - Use `/sync-commands force:True` to force synchronization (enhanced with better rate limiting)
   - Refresh Discord (Ctrl+R) or restart Discord client
   - Check bot permissions in Discord server settings
   - Enhanced sync commands now handle rate limits more effectively

2. **Database Connection Issues**
   - Check container logs: `docker compose logs slinkbot`
   - Verify database path in environment variables
   - Ensure persistent storage is properly mounted

3. **Service API Errors**
   - Verify API keys in `.env` file
   - Check service connectivity through VPN (gluetun)
   - Review service logs: `docker compose logs jellyseerr radarr sonarr`

4. **VPN Connectivity**
   - Check gluetun status: `docker compose logs gluetun`
   - Verify VPN configuration in environment variables
   - Ensure VPN provider settings are correct

#### Log Analysis
```bash
# SlinkBot application logs
docker compose logs slinkbot -f

# System-wide service logs
docker compose logs -f

# Specific service debugging
docker compose logs jellyseerr --tail=100
```

## Advanced Configuration

### Custom Channel Setup
Configure specialized Discord channels for different notification types:
- **Status Channel** - Bot startup/shutdown notifications
- **Request Channels** - Separate channels for movies, TV, anime
- **Arrival Channel** - Media availability notifications
- **Alert Channel** - Service health alerts

### Background Task Customization
Modify task intervals in `slinkbot_phase5.py`:
```python
# Status updates every 60 seconds
"status_updates" -> interval_seconds=60

# Health monitoring every 5 minutes  
"health_monitoring" -> interval_seconds=300

# Database consistency every 30 minutes
"database_consistency_check" -> interval_seconds=1800
```

### Database Schema Extensions
Add custom fields to models in `database/models.py`:
```python
# Example: Add priority field to TrackedRequest
priority = Column(Integer, default=1, nullable=False)
```

## Development & Maintenance

### Git Repository
- **GitHub**: https://github.com/angryjuniper/slinkbot
- **Current Branch**: main
- **Version**: Alpha v0.2.0
- **Active Development**: Alpha v0.2.0 enhancements

### Backup Strategy
```bash
# Database backup
docker exec slinkbot_phase5 cp /app/data/slinkbot.db /tmp/
docker cp slinkbot_phase5:/tmp/slinkbot.db ./backup-$(date +%Y%m%d).db

# Configuration backup  
cp .env .env.backup-$(date +%Y%m%d)
```

### Update Procedures
```bash
# Pull latest changes
git pull origin main

# Rebuild and restart
docker compose build --no-cache slinkbot
docker compose up -d slinkbot

# Verify deployment
docker compose logs slinkbot --tail=20
```

## Performance & Monitoring

### Resource Usage
- **SlinkBot Container**: 512MB memory limit
- **Database**: SQLite with connection pooling
- **Background Tasks**: Optimized intervals for efficiency
- **API Calls**: Rate-limited with retry logic

### Monitoring Integration
- **Netdata** - System resource monitoring
- **Discord Notifications** - Service health alerts
- **Database Health** - Automated consistency checks
- **Application Logs** - Structured JSON logging

### Performance Optimization
- Connection pooling for database access
- Async/await patterns for non-blocking operations
- Efficient Discord API usage with command batching
- Background task scheduling to minimize resource conflicts

## Security Considerations

### API Security
- All API keys stored in environment variables
- VPN tunneling for external service access
- Cloudflare secure tunneling for web access
- Tailscale for administrative access

### Discord Security
- Admin permission checks for sensitive commands
- Ephemeral responses for administrative information
- Channel-specific command restrictions
- User permission validation

### Data Protection
- Local SQLite database with no external exposure
- Encrypted VPN connections for all external APIs
- Secure token handling in environment configuration
- No sensitive data in logs or public repositories

---

## Summary

SlinkBot Alpha v0.2.0 represents a mature, production-ready Discord bot system for comprehensive media server management. The implementation provides robust request tracking, enhanced command management, and seamless integration with popular *arr stack services.

**Key Achievements:**
- ✅ Enhanced command synchronization with improved rate limiting and 60-second timeout
- ✅ Comprehensive database consistency monitoring and integrity verification
- ✅ Enhanced user experience with complete request history and startup notifications
- ✅ Robust error handling and comprehensive system health monitoring
- ✅ Complete Docker stack integration with secure networking
- ✅ Production-ready deployment with automated background tasks
- ✅ User-friendly help system with `/slinkbot-help` command
- ✅ Improved notification system with black cat startup indicator

The system is designed for reliability, scalability, and ease of maintenance, making it suitable for both personal and community media server deployments.

**Maintained by**: angryjuniper  
**Repository**: https://github.com/angryjuniper/slinkbot  
**Version**: Alpha v0.2.0  
**Last Updated**: July 12, 2025