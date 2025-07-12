from sqlalchemy import create_engine, text
import os

def add_reason_column():
    db_path = '/opt/docker/slinkbot/python/data/slinkbot.db'
    engine = create_engine(f'sqlite:///{db_path}')
    with engine.connect() as conn:
        # Check if the column already exists
        result = conn.execute(text("PRAGMA table_info(request_status_history);"))
        columns = [row[1] for row in result]
        if 'reason' not in columns:
            print("Adding 'reason' column to request_status_history...")
            conn.execute(text("ALTER TABLE request_status_history ADD COLUMN reason TEXT;"))
            print("Column added.")
        else:
            print("'reason' column already exists. No action taken.")

if __name__ == '__main__':
    add_reason_column() 