#!/usr/bin/env python3
"""
Migration script to import existing Jellyseerr requests into SlinkBot database.
This helps preserve request history from before Phase 3 deployment.
"""

import asyncio
import os
import sys
from datetime import datetime
from typing import List, Optional

# Add the parent directory to the path so we can import our modules
sys.path.append('/app')

from database.models import TrackedRequest, get_db, init_database
from services.jellyseerr import JellyseerrService
from utils.simple_logging import logger


class RequestMigrator:
    """Migrates existing Jellyseerr requests to SlinkBot database."""
    
    def __init__(self):
        self.jellyseerr_service = JellyseerrService(
            base_url=os.getenv('JELLYSEERR_URL'),
            api_key=os.getenv('JELLYSEERR_API_KEY'),
            service_name='jellyseerr'
        )
    
    async def get_all_jellyseerr_requests(self, limit: int = 100) -> List:
        """Get all existing requests from Jellyseerr."""
        all_requests = []
        page = 1
        
        try:
            while True:
                # Get requests from Jellyseerr (we'll need to implement this method)
                logger.info(f"Fetching page {page} of Jellyseerr requests...")
                
                # Make direct API call since we don't have a get_all_requests method
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    url = f"{self.jellyseerr_service.base_url}/api/v1/request"
                    params = {
                        'take': 20,
                        'skip': (page - 1) * 20,
                        'sort': 'added',
                        'order': 'desc'
                    }
                    headers = {
                        'X-API-Key': self.jellyseerr_service.api_key,
                        'Content-Type': 'application/json'
                    }
                    
                    async with session.get(url, params=params, headers=headers) as response:
                        if response.status == 200:
                            data = await response.json()
                            requests = data.get('results', [])
                            
                            if not requests:
                                break
                            
                            all_requests.extend(requests)
                            logger.info(f"Found {len(requests)} requests on page {page}")
                            
                            # Check if we've reached the end
                            if len(requests) < 20:
                                break
                            
                            page += 1
                        else:
                            logger.error(f"Failed to fetch requests: {response.status}")
                            break
            
            logger.info(f"Total requests found: {len(all_requests)}")
            return all_requests
            
        except Exception as e:
            logger.error(f"Error fetching Jellyseerr requests: {e}")
            return []
    
    async def migrate_requests(self, user_id_override: Optional[int] = None) -> int:
        """Migrate existing Jellyseerr requests to database."""
        logger.info("Starting request migration...")
        
        # Get all existing requests from Jellyseerr
        jellyseerr_requests = await self.get_all_jellyseerr_requests()
        
        if not jellyseerr_requests:
            logger.warning("No requests found in Jellyseerr")
            return 0
        
        migrated_count = 0
        
        with next(get_db()) as session:
            for req_data in jellyseerr_requests:
                try:
                    # Check if already exists in our database
                    existing = session.query(TrackedRequest).filter(
                        TrackedRequest.jellyseerr_request_id == req_data['id']
                    ).first()
                    
                    if existing:
                        logger.debug(f"Request {req_data['id']} already exists, skipping")
                        continue
                    
                    # Extract request information
                    media_data = req_data.get('media', {})
                    media_title = media_data.get('title', 'Unknown')
                    media_year = str(media_data.get('releaseDate', '')[:4]) if media_data.get('releaseDate') else 'Unknown'
                    media_type = req_data.get('type', 'movie')
                    media_id = media_data.get('tmdbId', 0)
                    
                    # Map media type
                    if media_type == 'movie':
                        media_type = 'movie'
                    elif media_type == 'tv':
                        media_type = 'tv'
                    else:
                        media_type = 'movie'  # Default
                    
                    # Use provided user ID or try to extract from request
                    discord_user_id = user_id_override or req_data.get('requestedBy', {}).get('id', 0)
                    
                    # Create tracked request
                    tracked_request = TrackedRequest(
                        jellyseerr_request_id=req_data['id'],
                        discord_user_id=discord_user_id,
                        discord_channel_id=0,  # Unknown for migrated requests
                        media_title=media_title,
                        media_year=media_year,
                        media_type=media_type,
                        media_id=media_id,
                        last_status=req_data.get('status', 1),
                        created_at=datetime.fromisoformat(req_data['createdAt'].replace('Z', '+00:00')) if req_data.get('createdAt') else datetime.utcnow(),
                        updated_at=datetime.fromisoformat(req_data['updatedAt'].replace('Z', '+00:00')) if req_data.get('updatedAt') else datetime.utcnow(),
                        is_active=req_data.get('status', 1) not in [5]  # Not active if status is 5 (available)
                    )
                    
                    session.add(tracked_request)
                    migrated_count += 1
                    
                    logger.info(f"Migrated: {media_title} ({media_year}) - Status: {req_data.get('status', 1)}")
                    
                except Exception as e:
                    logger.error(f"Error migrating request {req_data.get('id', 'unknown')}: {e}")
                    continue
            
            # Commit all changes
            session.commit()
            
        logger.info(f"Migration complete! Migrated {migrated_count} requests")
        return migrated_count
    
    async def show_migration_preview(self, limit: int = 10) -> None:
        """Show a preview of what would be migrated."""
        logger.info("Fetching migration preview...")
        
        requests = await self.get_all_jellyseerr_requests()
        
        if not requests:
            logger.warning("No requests found for preview")
            return
        
        logger.info(f"Preview of {min(limit, len(requests))} requests to migrate:")
        
        for i, req in enumerate(requests[:limit]):
            media_data = req.get('media', {})
            title = media_data.get('title', 'Unknown')
            year = str(media_data.get('releaseDate', '')[:4]) if media_data.get('releaseDate') else 'Unknown'
            status = req.get('status', 1)
            media_type = req.get('type', 'movie')
            
            logger.info(f"  {i+1}. {title} ({year}) - {media_type} - Status: {status}")
        
        if len(requests) > limit:
            logger.info(f"  ... and {len(requests) - limit} more requests")


async def main():
    """Main CLI interface for the migration tool."""
    if len(sys.argv) < 2:
        print("Usage: python import_existing_requests.py <command> [options]")
        print("Commands:")
        print("  preview     - Show preview of requests to migrate")
        print("  migrate     - Migrate all requests")
        print("  migrate <user_id> - Migrate all requests with specific Discord user ID")
        return
    
    # Initialize database
    init_database()
    
    migrator = RequestMigrator()
    command = sys.argv[1]
    
    try:
        if command == 'preview':
            await migrator.show_migration_preview()
        elif command == 'migrate':
            user_id = int(sys.argv[2]) if len(sys.argv) > 2 else None
            count = await migrator.migrate_requests(user_id_override=user_id)
            print(f"Successfully migrated {count} requests")
        else:
            print(f"Unknown command: {command}")
            
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())