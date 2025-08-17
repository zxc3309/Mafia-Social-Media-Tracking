#!/bin/bash

echo "=========================================="
echo "Railway PostgreSQL Migration Script"
echo "=========================================="
echo ""
echo "This script will add thread_id columns to your Railway PostgreSQL database."
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Step 1: Login to Railway (if not already logged in)${NC}"
echo "Running: railway login"
railway login

echo ""
echo -e "${YELLOW}Step 2: Checking current database state (dry run)${NC}"
echo "Running: railway run python scripts/add_thread_id_migration.py"
railway run python scripts/add_thread_id_migration.py

echo ""
echo -e "${YELLOW}Do you want to execute the migration? (y/n)${NC}"
read -p "Enter your choice: " choice

if [ "$choice" = "y" ] || [ "$choice" = "Y" ]; then
    echo ""
    echo -e "${GREEN}Step 3: Executing migration${NC}"
    echo "Running: railway run python scripts/add_thread_id_migration.py --execute"
    railway run python scripts/add_thread_id_migration.py --execute
    
    echo ""
    echo -e "${GREEN}✅ Migration complete!${NC}"
    echo "Check your Railway logs to verify the application is running without errors."
else
    echo ""
    echo -e "${RED}Migration cancelled.${NC}"
    echo "You can run this script again when you're ready."
fi

echo ""
echo "=========================================="
echo "Done!"
echo "=========================================="