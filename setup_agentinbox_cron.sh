#!/bin/bash

# Agent Inbox Cron Setup Script
# This script sets up a cron job to run email ingestion every 5 minutes

echo "Setting up Agent Inbox email ingestion cron job..."

# Get the current directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INGEST_SCRIPT="$SCRIPT_DIR/src/email_assistant/tools/gmail/run_ingest_agentinbox.py"

# Check if the ingest script exists
if [ ! -f "$INGEST_SCRIPT" ]; then
    echo "Error: Ingest script not found at $INGEST_SCRIPT"
    exit 1
fi

# Get email address from user
read -p "Enter the email address to monitor: " EMAIL_ADDRESS

if [ -z "$EMAIL_ADDRESS" ]; then
    echo "Error: Email address is required"
    exit 1
fi

# Create the cron command
CRON_COMMAND="*/5 * * * * cd $SCRIPT_DIR && uv run python $INGEST_SCRIPT --email $EMAIL_ADDRESS --minutes-since 5"

# Create a temporary cron file
TEMP_CRON=$(mktemp)
echo "# Agent Inbox Email Ingestion Cron Job" > "$TEMP_CRON"
echo "# This cron job runs every 5 minutes to ingest new emails" >> "$TEMP_CRON"
echo "$CRON_COMMAND" >> "$TEMP_CRON"

echo "Cron job configuration:"
echo "======================="
cat "$TEMP_CRON"
echo "======================="

# Ask for confirmation
read -p "Do you want to install this cron job? (y/N): " CONFIRM

if [[ $CONFIRM =~ ^[Yy]$ ]]; then
    # Install the cron job
    if crontab "$TEMP_CRON"; then
        echo "✅ Cron job installed successfully!"
        echo ""
        echo "Current cron jobs:"
        crontab -l
        echo ""
        echo "The email ingestion will now run every 5 minutes."
        echo "To monitor the cron job, check the logs or use: tail -f /var/log/cron"
    else
        echo "❌ Failed to install cron job"
        exit 1
    fi
else
    echo "Cron job installation cancelled."
fi

# Clean up
rm "$TEMP_CRON"

echo ""
echo "Next steps:"
echo "1. Make sure your Gmail credentials are properly configured"
echo "2. Set the AGENT_INBOX_API_KEY environment variable"
echo "3. Test the ingest script manually first:"
echo "   cd $SCRIPT_DIR"
echo "   uv run python $INGEST_SCRIPT --email $EMAIL_ADDRESS --early"
echo "4. The cron job will now run automatically every 5 minutes"

