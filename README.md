# SlinkBot Alpha v0.1.0

**Enhanced Discord Media Request Bot with Jellyseerr Integration**

SlinkBot is a sophisticated Discord bot designed to streamline media requests through Jellyseerr integration. It provides users with an intuitive interface to request movies, TV shows, and anime while maintaining comprehensive tracking and notification systems.

## ✨ Features

### 🎬 Media Request Management
- **Multi-format Support**: Request movies, TV shows, and anime
- **Smart Search**: Advanced search capabilities with auto-suggestions
- **Duplicate Detection**: Prevents duplicate requests automatically
- **Status Tracking**: Real-time status updates from pending to available
- **Request History**: Complete tracking of user request activity

### 🔧 Advanced Bot Capabilities
- **Slash Commands**: Modern Discord slash command interface
- **Permission System**: Role-based access control
- **Rate Limiting**: Built-in command cooldowns and usage limits
- **Channel Restrictions**: Commands work only in designated channels
- **Error Handling**: Comprehensive error management with retry logic

### 📊 Monitoring & Health
- **Service Health Checks**: Monitor external service availability
- **Database Integrity**: Automated database health monitoring
- **Structured Logging**: JSON-formatted logs for easy analysis
- **Performance Metrics**: Track bot performance and usage statistics
- **Automated Notifications**: Real-time status updates via Discord

### 🛠️ Technical Excellence
- **Optimized Architecture**: Eliminated code duplication across 15+ files
- **Centralized Session Management**: Efficient database operations
- **Standardized Error Handling**: Consistent error patterns throughout
- **Configuration Validation**: Comprehensive config verification
- **Background Task Scheduling**: Automated maintenance and updates

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Discord Bot Token
- Jellyseerr instance with API access
- SQLite database support

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/angryjuniper/slinkbot.git
   cd slinkbot/python
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp config/examples.env .env
   # Edit .env with your configuration
   ```

5. **Initialize database**
   ```bash
   python -c "from database.models import init_database; init_database()"
   ```

6. **Start the bot**
   ```bash
   python slinkbot.py
   ```

## ⚙️ Configuration

### Required Environment Variables

```bash
# Discord Configuration
DISCORD_BOT_TOKEN=your_discord_bot_token
DISCORD_GUILD_ID=your_server_id

# Channel IDs
CHANNEL_SLINKBOT_STATUS=123456789
CHANNEL_REQUEST_STATUS=123456789
CHANNEL_MOVIE_REQUESTS=123456789
CHANNEL_TV_REQUESTS=123456789
CHANNEL_ANIME_REQUESTS=123456789
CHANNEL_DOWNLOAD_QUEUE=123456789
CHANNEL_MEDIA_ARRIVALS=123456789
CHANNEL_CANCEL_REQUEST=123456789
CHANNEL_SERVICE_ALERTS=123456789

# Jellyseerr API
JELLYSEERR_URL=http://your-jellyseerr-instance:5055
JELLYSEERR_API_KEY=your_jellyseerr_api_key

# Optional: Additional Services
RADARR_URL=http://your-radarr-instance:7878
RADARR_API_KEY=your_radarr_api_key
SONARR_URL=http://your-sonarr-instance:8989
SONARR_API_KEY=your_sonarr_api_key

# Optional: Database Configuration
DB_PATH=data/slinkbot.db
DB_BACKUP_ENABLED=true
DB_BACKUP_INTERVAL_HOURS=24

# Optional: Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=logs/slinkbot.log
JSON_LOG_FILE=logs/slinkbot.json.log
```

### Discord Bot Setup

1. Create a bot at [Discord Developer Portal](https://discord.com/developers/applications)
2. Enable the following bot permissions:
   - Send Messages
   - Use Slash Commands
   - Embed Links
   - Attach Files
   - Read Message History
   - Add Reactions
3. Invite bot to your server with appropriate permissions

## 📖 Usage

### Available Commands

#### Media Requests
- `/search <query>` - Search for available content without requesting media
- `/request-media <title> [media_type] [year] [season]` - Request movies, TV shows, or episodes (supports S01E01 format)

#### User Management
- `/my-requests [filter_type]` - View and manage your request history with optional filters
- `/request-stats [period]` - View detailed request statistics for the server

#### System Commands  
- `/slinkbot-help` - Display help information for SlinkBot commands
- `/system-status` - View comprehensive bot system health (Admin only)
- `/sync-commands [force] [verify]` - Force slash command synchronization at guild level (Admin only)
- `/check-drive-space` - Check remaining drive space on media server

### Request Workflow

1. **Search**: Use `/search` to find content
2. **Request**: Use appropriate command (`/movie`, `/tv`, `/anime`)
3. **Track**: Monitor status updates in designated channels
4. **Enjoy**: Receive notification when content is available

## 🏗️ Architecture

### Core Components

- **SlinkBot Core**: Main bot instance and command management
- **Request Manager**: Handles media request processing
- **Jellyseerr Service**: API integration for external requests
- **Database Models**: SQLite-based data persistence
- **Health Manager**: Service monitoring and health checks
- **Task Scheduler**: Background job management
- **Enhanced Notifier**: Discord notification system

### Utility Systems

- **Database Session Management**: Centralized DB operations
- **Status Manager**: Request status handling
- **Error Handling**: Comprehensive error management
- **Configuration Validation**: Settings verification
- **Embed Builder**: Discord embed creation
- **Command Validators**: Input validation and permissions

## 🔧 Development

### Project Structure

```
slinkbot/
├── python/
│   ├── commands/          # Discord slash commands
│   ├── config/           # Configuration management
│   ├── database/         # Database models and operations
│   ├── managers/         # Business logic managers
│   ├── notifications/    # Discord notification system
│   ├── services/         # External API integrations
│   ├── tasks/           # Background task scheduling
│   ├── ui/              # Discord UI components
│   ├── utils/           # Utility functions and helpers
│   ├── tests/           # Unit and integration tests
│   └── slinkbot.py      # Main application entry point
```

### Code Quality Standards

- **Type Hints**: Comprehensive type annotations
- **Error Handling**: Standardized error patterns
- **Logging**: Structured JSON logging throughout
- **Documentation**: Comprehensive docstrings
- **Testing**: Unit tests for critical components
- **Code Style**: Consistent formatting and conventions

### Running Tests

```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/test_config.py
pytest tests/test_error_handling.py
pytest tests/test_logging.py
```

## 📊 Monitoring

### Health Checks

SlinkBot includes comprehensive monitoring:

- **Database Health**: Connection and integrity checks
- **Service Availability**: External API monitoring
- **Memory Usage**: System resource tracking
- **Error Rates**: Exception monitoring and alerting
- **Performance Metrics**: Response time tracking

### Logging

- **Structured Logs**: JSON format for easy parsing
- **Log Rotation**: Automatic log file management
- **Error Tracking**: Comprehensive error reporting
- **Audit Trail**: Complete request tracking

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Setup

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

### Troubleshooting

**Bot not responding to commands?**
- Verify bot permissions in Discord
- Check bot token and guild ID configuration
- Ensure commands are synced with `/sync-commands`

**Database issues?**
- Check database file permissions
- Verify SQLite installation
- Review database health in system status

**API integration problems?**
- Validate Jellyseerr URL and API key
- Check service health status
- Review API endpoint accessibility

### Getting Help

- **Issues**: Report bugs via GitHub Issues
- **Documentation**: Check inline code documentation
- **Logs**: Review structured logs for error details

## 🏷️ Version History

See [CHANGELOG.md](CHANGELOG.md) for detailed version history.

## ⚡ Performance

SlinkBot is optimized for performance:

- **Efficient Database Operations**: Centralized session management
- **Minimal Memory Footprint**: Optimized resource usage
- **Fast Response Times**: Streamlined command processing
- **Scalable Architecture**: Designed for growth

## 🔒 Security

- **Input Validation**: Comprehensive parameter checking
- **Permission Enforcement**: Role-based access control
- **API Key Protection**: Secure credential management
- **Rate Limiting**: Protection against abuse

---

**SlinkBot Alpha v0.1.0** - Built with ❤️ for Discord communities