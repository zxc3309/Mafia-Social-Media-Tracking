#!/usr/bin/env python3
"""
One-time migration runner for Railway deployment
This script will run automatically on Railway and add the thread_id columns
"""
import os
import sys
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    # Check if we're running on Railway
    if not os.getenv('RAILWAY_ENVIRONMENT_NAME'):
        logger.info("Not running on Railway, skipping migration")
        return
    
    # Check if migration has already been run (using a marker file)
    marker_file = '/tmp/thread_id_migration_complete.marker'
    if os.path.exists(marker_file):
        logger.info("Migration already completed (marker file exists)")
        return
    
    logger.info("="*60)
    logger.info("Running thread_id migration on Railway")
    logger.info("="*60)
    
    try:
        # Import and run the migration
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from scripts.add_thread_id_migration import ThreadIdMigration
        
        migration = ThreadIdMigration()
        success = migration.run_migration(dry_run=False)
        
        if success:
            # Create marker file to prevent re-running
            with open(marker_file, 'w') as f:
                f.write('Migration completed successfully')
            logger.info("Migration completed and marked as done")
        else:
            logger.error("Migration failed - will retry on next deployment")
            
    except Exception as e:
        logger.error(f"Failed to run migration: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()