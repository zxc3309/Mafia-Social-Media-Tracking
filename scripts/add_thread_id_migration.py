#!/usr/bin/env python3
"""
Database Migration Script: Add thread_id columns to posts and analyzed_posts tables

This script adds the thread_id column to both posts and analyzed_posts tables
in the production PostgreSQL database on Railway.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from sqlalchemy import create_engine, text, inspect
from config import DATABASE_URL

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ThreadIdMigration:
    def __init__(self):
        self.database_url = DATABASE_URL
        self.engine = None
        self._initialize_connection()
    
    def _initialize_connection(self):
        """Initialize database connection"""
        try:
            self.engine = create_engine(
                self.database_url,
                echo=True,  # Show SQL statements for debugging
                pool_pre_ping=True
            )
            logger.info("Database connection initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database connection: {e}")
            raise
    
    def check_column_exists(self, table_name: str, column_name: str) -> bool:
        """Check if a column exists in a table"""
        try:
            inspector = inspect(self.engine)
            columns = [col['name'] for col in inspector.get_columns(table_name)]
            exists = column_name in columns
            logger.info(f"Column {column_name} in table {table_name}: {'exists' if exists else 'missing'}")
            return exists
        except Exception as e:
            logger.error(f"Error checking column existence: {e}")
            return False
    
    def add_thread_id_column(self, table_name: str) -> bool:
        """Add thread_id column to specified table"""
        try:
            # Check if column already exists
            if self.check_column_exists(table_name, 'thread_id'):
                logger.info(f"Column thread_id already exists in {table_name}, skipping")
                return True
            
            # Add the column
            sql = f"ALTER TABLE {table_name} ADD COLUMN thread_id VARCHAR(255)"
            
            with self.engine.connect() as conn:
                conn.execute(text(sql))
                conn.commit()
                logger.info(f"Successfully added thread_id column to {table_name}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to add thread_id column to {table_name}: {e}")
            return False
    
    def verify_migration(self) -> bool:
        """Verify that the migration was successful"""
        try:
            tables_to_check = ['posts', 'analyzed_posts']
            all_success = True
            
            for table in tables_to_check:
                if not self.check_column_exists(table, 'thread_id'):
                    logger.error(f"Migration verification failed: thread_id column missing from {table}")
                    all_success = False
                else:
                    logger.info(f"✅ Migration verified: thread_id column exists in {table}")
            
            return all_success
            
        except Exception as e:
            logger.error(f"Error during migration verification: {e}")
            return False
    
    def get_database_info(self):
        """Get database information for logging"""
        try:
            with self.engine.connect() as conn:
                # Get database type and version
                if 'postgresql' in self.database_url:
                    result = conn.execute(text("SELECT version()"))
                    version = result.fetchone()[0]
                    logger.info(f"PostgreSQL version: {version}")
                elif 'sqlite' in self.database_url:
                    result = conn.execute(text("SELECT sqlite_version()"))
                    version = result.fetchone()[0]
                    logger.info(f"SQLite version: {version}")
                
                # List existing tables
                inspector = inspect(self.engine)
                tables = inspector.get_table_names()
                logger.info(f"Existing tables: {tables}")
                
        except Exception as e:
            logger.error(f"Error getting database info: {e}")
    
    def run_migration(self, dry_run=True):
        """Run the complete migration process"""
        logger.info("="*60)
        logger.info("Starting Thread ID Migration")
        logger.info(f"Mode: {'DRY RUN' if dry_run else 'EXECUTE'}")
        logger.info("="*60)
        
        # Get database information
        self.get_database_info()
        
        # Check current state
        logger.info("\n" + "-"*40)
        logger.info("Checking current database state...")
        logger.info("-"*40)
        
        posts_has_thread_id = self.check_column_exists('posts', 'thread_id')
        analyzed_posts_has_thread_id = self.check_column_exists('analyzed_posts', 'thread_id')
        
        # Determine what needs to be done
        migrations_needed = []
        if not posts_has_thread_id:
            migrations_needed.append('posts')
        if not analyzed_posts_has_thread_id:
            migrations_needed.append('analyzed_posts')
        
        if not migrations_needed:
            logger.info("🎉 No migration needed - all thread_id columns already exist!")
            return True
        
        logger.info(f"Tables needing thread_id column: {migrations_needed}")
        
        if dry_run:
            logger.info("\n" + "-"*40)
            logger.info("DRY RUN - Would execute the following:")
            logger.info("-"*40)
            for table in migrations_needed:
                logger.info(f"  ALTER TABLE {table} ADD COLUMN thread_id VARCHAR(255)")
            logger.info("\nTo execute the migration, run with --execute flag")
            return True
        
        # Execute migrations
        logger.info("\n" + "-"*40)
        logger.info("Executing migrations...")
        logger.info("-"*40)
        
        success = True
        for table in migrations_needed:
            if not self.add_thread_id_column(table):
                success = False
        
        if success:
            # Verify migration
            logger.info("\n" + "-"*40)
            logger.info("Verifying migration...")
            logger.info("-"*40)
            
            if self.verify_migration():
                logger.info("\n🎉 Migration completed successfully!")
                return True
            else:
                logger.error("\n❌ Migration verification failed!")
                return False
        else:
            logger.error("\n❌ Migration failed!")
            return False

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Add thread_id columns to database tables')
    parser.add_argument('--execute', action='store_true', 
                       help='Execute the migration (default is dry run)')
    args = parser.parse_args()
    
    try:
        migration = ThreadIdMigration()
        success = migration.run_migration(dry_run=not args.execute)
        
        if not args.execute:
            print("\n" + "="*60)
            print("This was a dry run. No changes were made.")
            print("To execute the migration, run:")
            print("  python scripts/add_thread_id_migration.py --execute")
            print("="*60)
        
        sys.exit(0 if success else 1)
        
    except Exception as e:
        logger.error(f"Migration script failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()