#!/usr/bin/env python3
"""
Migration script to convert JSON request tracking to SQLite database.
"""

import json
import os
import sys
import shutil
import asyncio
from datetime import datetime
from pathlib import Path

# Add the project root to sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database.models import TrackedRequest, init_database, get_db
from utils.simple_logging import setup_logging, logger


class JSONToSQLiteMigration:
    """Migrates existing JSON data to SQLite database."""
    
    def __init__(self, json_file_path: str, backup_dir: str = None):
        """
        Initialize migration.
        
        Args:
            json_file_path: Path to the JSON tracking file
            backup_dir: Optional backup directory
        """
        self.json_file_path = json_file_path
        self.backup_dir = backup_dir or f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Setup logging
        setup_logging()
    
    def create_backup(self) -> str:
        """
        Create backup of current data before migration.
        
        Returns:
            Path to backup directory
        """
        try:
            os.makedirs(self.backup_dir, exist_ok=True)
            
            # Backup JSON file
            if os.path.exists(self.json_file_path):
                json_backup = os.path.join(self.backup_dir, 'request_tracking.json')
                shutil.copy2(self.json_file_path, json_backup)
                logger.info(f"Backed up JSON file to {json_backup}")
            
            # Backup existing database if it exists
            db_path = os.getenv('DATABASE_PATH', 'data/slinkbot.db')
            if os.path.exists(db_path):
                db_backup = os.path.join(self.backup_dir, 'slinkbot.db')
                shutil.copy2(db_path, db_backup)
                logger.info(f"Backed up database to {db_backup}")
            
            # Backup logs
            for log_file in ['slinkbot.log', 'slinkbot.json.log']:
                if os.path.exists(log_file):
                    log_backup = os.path.join(self.backup_dir, log_file)
                    shutil.copy2(log_file, log_backup)
            
            logger.info(f"Backup created at {self.backup_dir}")
            return self.backup_dir
            
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            raise
    
    def load_json_data(self) -> list:
        """
        Load and parse JSON tracking data.
        
        Returns:
            List of tracking entries
        """
        try:
            if not os.path.exists(self.json_file_path):
                logger.warning(f"JSON file not found: {self.json_file_path}")
                return []
            
            with open(self.json_file_path, 'r') as f:
                data = json.load(f)
            
            # Handle different JSON formats
            if isinstance(data, dict):
                # Convert dictionary format to list
                entries = []
                for request_id, request_data in data.items():
                    entry = request_data.copy()
                    entry['jellyseerr_request_id'] = int(request_id)
                    entries.append(entry)
                return entries
            elif isinstance(data, list):
                return data
            else:
                logger.error(f"Unexpected JSON format: {type(data)}")
                return []
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON format: {e}")
            return []
        except Exception as e:
            logger.error(f"Failed to load JSON data: {e}")
            return []
    
    def migrate_entry(self, entry: dict) -> TrackedRequest:
        """
        Convert a JSON entry to a TrackedRequest object.
        
        Args:
            entry: JSON entry dictionary
            
        Returns:
            TrackedRequest object
        """
        # Map JSON fields to database fields
        jellyseerr_id = entry.get('jellyseerr_request_id') or entry.get('id')
        if not jellyseerr_id:
            raise ValueError("Missing jellyseerr_request_id")
        
        # Handle different field name variations
        discord_user_id = (entry.get('discord_user_id') or 
                          entry.get('requester_id') or 
                          entry.get('user_id'))
        
        discord_channel_id = (entry.get('discord_channel_id') or 
                             entry.get('channel_id') or 
                             0)  # Default to 0 if not available
        
        media_title = entry.get('media_title') or entry.get('title') or 'Unknown'
        media_year = entry.get('media_year') or entry.get('year') or 'Unknown'
        media_type = entry.get('media_type') or entry.get('type') or 'unknown'
        media_id = entry.get('media_id') or entry.get('tmdb_id') or entry.get('tvdb_id') or 0
        
        last_status = entry.get('last_status') or entry.get('status') or 1
        
        # Parse dates
        created_at = self._parse_date(entry.get('created_at') or entry.get('timestamp'))
        updated_at = self._parse_date(entry.get('updated_at')) or created_at
        
        is_active = entry.get('is_active', True)
        
        return TrackedRequest(
            jellyseerr_request_id=int(jellyseerr_id),
            discord_user_id=int(discord_user_id),
            discord_channel_id=int(discord_channel_id),
            media_title=str(media_title),
            media_year=str(media_year),
            media_type=str(media_type),
            media_id=int(media_id),
            last_status=int(last_status),
            created_at=created_at,
            updated_at=updated_at,
            is_active=bool(is_active)
        )
    
    def _parse_date(self, date_str: str) -> datetime:
        """
        Parse date string to datetime object.
        
        Args:
            date_str: Date string in various formats
            
        Returns:
            Datetime object
        """
        if not date_str:
            return datetime.utcnow()
        
        # Try different date formats
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%S.%f',
            '%Y-%m-%dT%H:%M:%S.%fZ',
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%d',
            '%Y/%m/%d %H:%M:%S',
            '%Y/%m/%d'
        ]
        
        for fmt in formats:
            try:
                # Remove timezone suffix if present
                clean_date = date_str.replace('Z', '').replace('+00:00', '')
                return datetime.strptime(clean_date, fmt)
            except ValueError:
                continue
        
        # If no format works, return current time
        logger.warning(f"Could not parse date: {date_str}, using current time")
        return datetime.utcnow()
    
    async def migrate(self) -> dict:
        """
        Perform the migration from JSON to SQLite.
        
        Returns:
            Dictionary with migration statistics
        """
        logger.info(f"Starting migration from {self.json_file_path}")
        
        stats = {
            'migrated': 0,
            'skipped': 0,
            'errors': 0,
            'total_entries': 0
        }
        
        try:
            # Initialize database
            logger.info("Initializing database")
            init_database()
            
            # Load JSON data
            logger.info("Loading JSON data")
            entries = self.load_json_data()
            stats['total_entries'] = len(entries)
            
            if not entries:
                logger.info("No entries found in JSON file")
                return stats
            
            logger.info(f"Found {len(entries)} entries to migrate")
            
            # Migrate entries
            with next(get_db()) as session:
                for i, entry in enumerate(entries):
                    try:
                        # Convert to TrackedRequest
                        tracked_request = self.migrate_entry(entry)
                        
                        # Check if already exists
                        existing = session.query(TrackedRequest).filter(
                            TrackedRequest.jellyseerr_request_id == tracked_request.jellyseerr_request_id
                        ).first()
                        
                        if existing:
                            logger.debug(f"Request {tracked_request.jellyseerr_request_id} already exists, skipping")
                            stats['skipped'] += 1
                            continue
                        
                        # Add to database
                        session.add(tracked_request)
                        stats['migrated'] += 1
                        
                        # Commit every 50 entries
                        if (i + 1) % 50 == 0:
                            session.commit()
                            logger.info(f"Migrated {i + 1}/{len(entries)} entries")
                    
                    except Exception as e:
                        logger.error(f"Error migrating entry {i}: {e}")
                        logger.debug(f"Entry data: {entry}")
                        stats['errors'] += 1
                        continue
                
                # Final commit
                session.commit()
            
            logger.info(f"Migration complete: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            raise
    
    def verify_migration(self) -> dict:
        """
        Verify the migration by checking database contents.
        
        Returns:
            Dictionary with verification results
        """
        try:
            with next(get_db()) as session:
                total_requests = session.query(TrackedRequest).count()
                active_requests = session.query(TrackedRequest).filter(
                    TrackedRequest.is_active == True
                ).count()
                
                # Status breakdown
                status_counts = {}
                for status in [1, 2, 3, 4, 5]:
                    count = session.query(TrackedRequest).filter(
                        TrackedRequest.last_status == status
                    ).count()
                    status_counts[status] = count
                
                # Media type breakdown
                type_counts = {}
                for media_type in ['movie', 'tv', 'anime']:
                    count = session.query(TrackedRequest).filter(
                        TrackedRequest.media_type == media_type
                    ).count()
                    type_counts[media_type] = count
                
                verification = {
                    'total_requests': total_requests,
                    'active_requests': active_requests,
                    'status_breakdown': status_counts,
                    'type_breakdown': type_counts
                }
                
                logger.info(f"Verification results: {verification}")
                return verification
                
        except Exception as e:
            logger.error(f"Verification failed: {e}")
            return {}


async def main():
    """Main migration script entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate JSON request tracking to SQLite')
    parser.add_argument('json_file', help='Path to JSON tracking file')
    parser.add_argument('--backup-dir', help='Backup directory (default: auto-generated)')
    parser.add_argument('--no-backup', action='store_true', help='Skip backup creation')
    parser.add_argument('--verify-only', action='store_true', help='Only verify existing database')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.json_file) and not args.verify_only:
        print(f"Error: JSON file not found: {args.json_file}")
        sys.exit(1)
    
    migration = JSONToSQLiteMigration(args.json_file, args.backup_dir)
    
    try:
        if args.verify_only:
            print("Verifying existing database...")
            verification = migration.verify_migration()
            print(f"Verification complete: {verification}")
            return
        
        # Create backup unless disabled
        if not args.no_backup:
            backup_dir = migration.create_backup()
            print(f"Backup created at: {backup_dir}")
        
        # Run migration
        print("Starting migration...")
        stats = await migration.migrate()
        
        print(f"Migration complete!")
        print(f"  Migrated: {stats['migrated']}")
        print(f"  Skipped: {stats['skipped']}")
        print(f"  Errors: {stats['errors']}")
        print(f"  Total: {stats['total_entries']}")
        
        # Verify migration
        print("Verifying migration...")
        verification = migration.verify_migration()
        print(f"Database now contains {verification['total_requests']} requests")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())