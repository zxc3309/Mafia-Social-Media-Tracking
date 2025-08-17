# Database Migration Instructions

## Problem
The Railway PostgreSQL production database is missing `thread_id` columns that were added to the local SQLite database, causing the application to crash with:
```
(psycopg2.errors.UndefinedColumn) column posts.thread_id does not exist
```

## Solution
We've created a migration script and safety checks to fix this issue.

## Steps to Run Migration on Railway

### Option 1: Use Railway CLI (Recommended)
```bash
# In the project directory
railway run python scripts/add_thread_id_migration.py --execute
```

### Option 2: Deploy and Run on Railway
1. The migration script is already included in the latest deployment
2. SSH into Railway container or use Railway's run feature
3. Execute the migration:
```bash
python scripts/add_thread_id_migration.py --execute
```

### Option 3: Manual SQL (If migration script fails)
Connect to Railway PostgreSQL database and run these commands:
```sql
ALTER TABLE posts ADD COLUMN thread_id VARCHAR(255);
ALTER TABLE analyzed_posts ADD COLUMN thread_id VARCHAR(255);
```

## What the Migration Does
- Adds `thread_id VARCHAR(255)` column to `posts` table
- Adds `thread_id VARCHAR(255)` column to `analyzed_posts` table  
- Includes safety checks to avoid errors if columns already exist
- Provides detailed logging and verification

## Safety Features Added
The application now includes safety checks that:
- Check if `thread_id` columns exist before using them
- Log column status during database initialization
- Handle missing columns gracefully without crashing
- Continue to work even if migration hasn't been run yet

## Verification
After running the migration, check the Railway logs for these messages:
```
posts.thread_id column: ✅ exists
analyzed_posts.thread_id column: ✅ exists
Migration completed successfully!
```

## Next Steps
1. Run the migration on Railway PostgreSQL
2. Verify the application runs without thread_id column errors
3. Monitor logs to ensure thread detection is working properly

The application should now handle the missing columns gracefully until the migration is complete.