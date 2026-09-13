# Agent Inbox Integration for Email Dashboard

This document explains how to set up and use the Agent Inbox integration to replace the problematic LangGraph authentication in your Vercel deployment.

## Overview

Instead of trying to fix LangGraph authentication issues, we're pivoting to use **Agent Inbox** as the backend framework. This approach:

1. **Fetches emails from Gmail** every 5 minutes using a cron job
2. **Sends emails to Agent Inbox** for processing and classification
3. **Parses Agent Inbox data** to populate the dashboard statistics
4. **Provides real-time updates** without authentication issues

## Architecture

```
Gmail → Cron Job (every 5 min) → Agent Inbox → Dashboard Parser → Flask App → Vercel
```

## Prerequisites

1. **Gmail API credentials** (already configured)
2. **Agent Inbox account** and API key
3. **Python environment** with required packages

## Setup Instructions

### 1. Environment Variables

Set these environment variables in your deployment:

```bash
# Agent Inbox Configuration
AGENT_INBOX_URL=https://dev.agentinbox.ai
AGENT_INBOX_ID=email_assistant_hitl_memory_gmail
AGENT_INBOX_API_KEY=your_api_key_here

# Gmail Configuration (if not using file-based auth)
GMAIL_TOKEN=your_gmail_token_json
```

### 2. Install Dependencies

The required packages are already in your `requirements.txt`, but ensure you have:

```bash
uv run pip install requests python-dotenv google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

### 3. Test the Integration

First, test the Agent Inbox parser:

```bash
cd agents-from-scratch
uv run python src/email_assistant/tools/gmail/agent_inbox_parser.py
```

Then test the ingest script:

```bash
uv run python src/email_assistant/tools/gmail/run_ingest_agentinbox.py --email your-email@domain.com --early
```

### 4. Set Up Cron Job

Use the provided setup script:

```bash
./setup_agentinbox_cron.sh
```

Or manually create a cron job:

```bash
# Edit crontab
crontab -e

# Add this line (runs every 5 minutes)
*/5 * * * * cd /path/to/agents-from-scratch && uv run python src/email_assistant/tools/gmail/run_ingest_agentinbox.py --email your-email@domain.com --minutes-since 5
```

### 5. Deploy the New App

Replace your current `app_agentinbox.py` with the new version:

```bash
cp app_agentinbox_new.py app_agentinbox.py
```

## Files Overview

### Core Files

- **`run_ingest_agentinbox.py`** - Fetches emails from Gmail and sends to Agent Inbox
- **`agent_inbox_parser.py`** - Parses Agent Inbox data for dashboard display
- **`app_agentinbox_new.py`** - New Flask app that integrates with Agent Inbox
- **`setup_cron_agentinbox.py`** - Python-based cron setup (alternative to shell script)

### Configuration Files

- **`.env`** - Environment variables for Agent Inbox and Gmail
- **`setup_agentinbox_cron.sh`** - Shell script for cron setup

## Dashboard Data Structure

The dashboard now displays:

```json
{
  "statistics": {
    "total_emails": 0,
    "processed": 0,
    "hitl": 0,           // Human-in-the-Loop emails
    "ignored": 0,        // Ignored emails
    "waiting_action": 0, // Emails waiting for action
    "scheduled_meetings": 0,
    "notifications": 0
  },
  "emails": [
    {
      "id": "thread_id",
      "subject": "Formatted Subject",
      "from": "sender@domain.com",
      "to": "recipient@domain.com",
      "timestamp": "2025-01-11T...",
      "status": "processed|hitl|ignored|waiting_action",
      "priority": "high|medium|low",
      "content_preview": "Email content preview...",
      "metadata": {...}
    }
  ],
  "recent_activity": [...],
  "last_updated": "2025-01-11T...",
  "source": "agent_inbox"
}
```

## Email Status Classification

- **`processed`** - Emails handled autonomously by Agent Inbox
- **`hitl`** - Emails requiring human intervention
- **`ignored`** - Emails marked as not actionable
- **`waiting_action`** - Emails pending processing

## Monitoring and Troubleshooting

### Check Cron Job Status

```bash
# View current cron jobs
crontab -l

# Check cron logs
tail -f /var/log/cron

# Test cron job manually
uv run python src/email_assistant/tools/gmail/run_ingest_agentinbox.py --email your-email@domain.com --early
```

### Check Agent Inbox Connection

```bash
# Test connection
curl http://localhost:5000/api/connection-test

# Check health
curl http://localhost:5000/health
```

### Common Issues

1. **Import Error for AgentInboxParser**
   - Ensure the script path is correct in `app_agentinbox.py`
   - Check that `agent_inbox_parser.py` exists in the expected location

2. **Gmail Authentication Issues**
   - Verify your Gmail token is valid
   - Check that the `.secrets/token.json` file exists and is readable

3. **Agent Inbox API Errors**
   - Verify your API key is correct
   - Check that the Agent Inbox URL is accessible
   - Ensure you have the correct permissions

## Deployment to Vercel

1. **Update your main app file**:
   ```bash
   cp app_agentinbox_new.py app_agentinbox.py
   ```

2. **Set environment variables** in Vercel dashboard

3. **Deploy** - the new app will automatically use Agent Inbox

4. **Set up cron job** on your server (not on Vercel)

## Benefits of This Approach

✅ **No LangGraph authentication issues**  
✅ **Real-time email processing** every 5 minutes  
✅ **Clean separation of concerns** (ingest vs. display)  
✅ **Fallback data** when Agent Inbox is unavailable  
✅ **Easy to monitor and debug**  
✅ **Scalable** - can handle multiple email accounts  

## Next Steps

1. **Test locally** with the new integration
2. **Set up cron job** for email ingestion
3. **Deploy to Vercel** with the new app
4. **Monitor** email processing and dashboard updates
5. **Customize** the Agent Inbox workflow as needed

## Support

If you encounter issues:

1. Check the logs from the ingest script
2. Verify Agent Inbox connection with `/api/connection-test`
3. Test Gmail authentication manually
4. Review the cron job configuration

The integration is designed to be robust with fallbacks, so even if one component fails, the dashboard will continue to function with cached or fallback data.

