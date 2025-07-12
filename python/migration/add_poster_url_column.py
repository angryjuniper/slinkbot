#!/usr/bin/env python3
"""
Migration script to add poster_url column to tracked_requests table.
This should be run when upgrading to Alpha v0.1.1 or later.
"""

import sqlite3
import os
import sys
from pathlib import Path

# Add parent directory to path to import database models
sys.path.append(str(Path(__file__).parent.parent))

from utils.simple_logging import logger

def add_poster_url_column():
    """Add poster_url column to tracked_requests table if it doesn't exist."""
    
    # Get database path
    db_path = os.getenv('DATABASE_PATH', '/opt/docker/slinkbot/python/data/slinkbot.db')
    
    if not os.path.exists(db_path):
        logger.error(f"Database not found at {db_path}")
        return False
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Check if poster_url column already exists
            cursor.execute("PRAGMA table_info(tracked_requests)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'poster_url' in columns:
                logger.info("poster_url column already exists, skipping migration")
                return True
            
            # Add the poster_url column
            logger.info("Adding poster_url column to tracked_requests table...")
            cursor.execute("ALTER TABLE tracked_requests ADD COLUMN poster_url VARCHAR(500)")
            
            conn.commit()
            logger.info("Successfully added poster_url column")
            return True
            
    except Exception as e:
        logger.error(f"Failed to add poster_url column: {e}")
        return False

if __name__ == "__main__":
    print("Running poster_url column migration...")
    success = add_poster_url_column()
    if success:
        print("Migration completed successfully!")
        sys.exit(0)
    else:
        print("Migration failed!")
        sys.exit(1)