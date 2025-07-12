# SlinkBot Stack Setup Guide

## Overview
This guide will help you set up and configure the SlinkBot media management stack with Discord integration.

## Prerequisites
- Docker and Docker Compose installed
- ProtonVPN subscription
- Cloudflare account with Zero Trust
- Discord bot token
- Tailscale account (optional, for remote access)

## Initial Setup

### 1. Environment Configuration
Edit the `.env` file with your specific values:

```bash
# Update these values with your actual credentials
DISCORD_BOT_TOKEN=your_discord_bot_token
CLOUDFLARE_TUNNEL_TOKEN=your_cloudflare_tunnel_token
WIREGUARD_PRIVATE_KEY=your_protonvpn_private_key
WIREGUARD_ADDRESSES=your_protonvpn_ip_address
TAILSCALE_AUTH_KEY=your_tailscale_auth_key
```

### 2. Directory Structure
Ensure these directories exist and have proper permissions:
```bash
sudo mkdir -p /srv/media/{movies,tv,anime,downloads,downloads/complete,downloads/incomplete,incomplete-downloads}
sudo mkdir -p /etc/media/{radarr,sonarr,sabnzbd,prowlarr,jellyseerr,jellyfin}
sudo mkdir -p /var/log/media
sudo mkdir -p /opt/docker/slinkbot/{gluetun,tailscale}

# Set ownership to mediauser:media (PUID=996, PGID=1004)
sudo chown -R 996:1004 /srv/media /etc/media /var/log/media
```

## Service Configuration

### 3. Start the Stack
```bash
cd /opt/docker/slinkbot
docker-compose up -d
```

### 4. Configure Prowlarr (Indexer Management)
1. Access Prowlarr: `http://your-domain:9696`
2. Go to Settings → Indexers
3. Add your Usenet providers and torrent trackers
4. Note the API key for use in Radarr/Sonarr

### 5. Configure SABnzbd (Download Client)
1. Access SABnzbd: `http://your-domain:8080`
2. Complete the initial setup wizard
3. Go to Config → General → API Key
4. Copy the API key and add it to your `.env` file:
   ```
   SABNZBD_API_KEY=your_sabnzbd_api_key
   ```

### 6. Configure Radarr (Movies)
1. Access Radarr: `http://your-domain:7878`
2. Go to Settings → Download Clients
   - Add SABnzbd
   - Host: `sabnzbd`
   - Port: `8080`
   - API Key: (from SABnzbd)
3. Go to Settings → Indexers
   - Add Prowlarr
   - URL: `http://prowlarr:9696`
   - API Key: (from Prowlarr)
4. Go to Settings → Connect
   - Add Jellyseerr webhook
   - URL: `http://jellyseerr:5055/webhook/jellyseerr`

### 7. Configure Sonarr (TV Shows)
1. Access Sonarr: `http://your-domain:8989`
2. Same configuration as Radarr for download client and indexers
3. Add Jellyseerr webhook in Settings → Connect

### 8. Configure Jellyseerr (Request Management)
1. Access Jellyseerr: `http://your-domain:5055`
2. Go to Settings → Services
3. Add Radarr:
   - URL: `http://radarr:7878`
   - API Key: (from Radarr)
4. Add Sonarr:
   - URL: `http://sonarr:8989`
   - API Key: (from Sonarr)
5. Configure request settings and user permissions

### 9. Configure Jellyfin (Media Server)
1. Access Jellyfin: `http://your-domain:8096`
2. Complete the initial setup
3. Add your media libraries pointing to the mounted volumes

## Discord Bot Configuration

### 10. Discord Bot Setup
1. Create a Discord application at https://discord.com/developers/applications
2. Create a bot and get the token
3. Add the bot to your server with appropriate permissions
4. Update the bot token in your `.env` file

### 11. Channel Configuration
The bot is configured to work in specific channels. Ensure these channels exist in your Discord server:

- **Movie Requests**: `/request-movie <title>`
- **TV Requests**: `/request-tv <title>`
- **Anime Requests**: `/request-anime <title>`
- **Request Status**: `/request-status <title>`
- **Download Queue**: `/queued-downloads`
- **Media Arrivals**: `/recent-downloads`
- **Bot Status**: `/slinkbot-status`, `/system-status`
- **Cancel Requests**: `/cancel-request <title>`
- **Help**: `/slinkbot-help` (available in all channels)

## Volume Mapping Explanation

### SABnzbd Volume Mapping
The SABnzbd container uses these volume mappings:
- `${CONFIG_DIR}/sabnzbd:/config` - Configuration files
- `${DATA_DIR}/downloads:/downloads` - General downloads directory
- `${DATA_DIR}/downloads/complete:/config/Downloads/complete` - Completed downloads
- `${DATA_DIR}/downloads/incomplete:/config/Downloads/incomplete` - Incomplete downloads

This ensures SABnzbd can find the expected directory structure while maintaining proper file organization.

## Troubleshooting

### Common Issues

1. **VPN Connection Issues**
   - Check ProtonVPN credentials in `.env`
   - Verify WireGuard configuration
   - Check gluetun logs: `docker logs gluetun`

2. **Service Communication Issues**
   - Ensure all services are using `network_mode: "service:gluetun"`
   - Check service health: `docker-compose ps`

3. **Permission Issues**
   - Verify PUID/PGID match your system
   - Check directory ownership: `ls -la /srv/media`

4. **API Key Issues**
   - Verify all API keys are correctly set in `.env`
   - Check service logs for authentication errors

### Useful Commands
```bash
# Check service status
docker-compose ps

# View logs for a specific service
docker-compose logs -f service_name

# Restart a specific service
docker-compose restart service_name

# Update the stack
docker-compose pull
docker-compose up -d

# Check VPN status
docker exec gluetun wget -qO- http://localhost:9999/v1/healthcheck
```

## Security Considerations

1. **VPN Protection**: All download traffic goes through ProtonVPN
2. **API Keys**: Keep all API keys secure and rotate regularly
3. **Access Control**: Use Discord channel permissions to control bot access
4. **Network Isolation**: Services communicate only through the VPN network

## Next Steps

1. Test the Discord bot commands
2. Configure media quality profiles in Radarr/Sonarr
3. Set up automated media management rules
4. Configure backup strategies for your media and configuration
5. Set up monitoring and alerting

## Support

For issues specific to this setup:
1. Check the troubleshooting section above
2. Review service-specific documentation
3. Check Docker and service logs for error messages 