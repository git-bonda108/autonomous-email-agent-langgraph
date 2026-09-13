# 🚀 Hosted Deployment Guide for langgraph-email-agent

## 📋 Prerequisites
- ✅ Git repository: https://github.com/git-bonda108/langgraph-email-agent
- ✅ All code pushed and ready
- ✅ Gmail API credentials configured

## 🔑 Environment Variables for Hosted Deployment

When creating your LangGraph Platform deployment, add these environment variables:

### Required API Keys
```
OPENAI_API_KEY=your_openai_api_key_here

LANGSMITH_API_KEY=your_langsmith_api_key_here

LANGSMITH_PROJECT=interrupt-workshop
```

### Gmail Integration (Critical!)
```
GMAIL_SECRET=your_gmail_secrets_json_content_here

GMAIL_TOKEN=your_gmail_token_json_content_here
```

## 🚀 Deployment Steps

### 1. Create LangGraph Platform Deployment
1. Go to [LangSmith](https://smith.langchain.com/)
2. Navigate to Deployments page
3. Click "New Deployment"
4. Connect to repository: `git-bonda108/langgraph-email-agent`
5. Branch: `main`
6. Name: `langgraph-email-agent` (or your preferred name)

### 2. Add Environment Variables
Copy and paste ALL the environment variables above into the deployment configuration.

**Important**: For Gmail integration, you need to:
1. Copy the contents of `src/email_assistant/tools/gmail/.secrets/secrets.json` into `GMAIL_SECRET`
2. Copy the contents of `src/email_assistant/tools/gmail/.secrets/token.json` into `GMAIL_TOKEN`

### 3. Deploy
Click "Submit" and wait for deployment to complete.

### 4. Get Your API URL
Once deployed, copy the API URL (format: `https://your-deployment-xxx.us.langgraph.app`)

## 📧 Test Gmail Integration

After deployment, test with:

```bash
python src/email_assistant/tools/gmail/run_ingest.py \
  --email autonomous.inbox@gmail.com \
  --minutes-since 60 \
  --url https://your-deployment-xxx.us.langgraph.app
```

## 🔗 Connect to Agent Inbox

1. Go to [Agent Inbox](https://dev.agentinbox.ai/)
2. Add your deployment:
   - **Deployment URL**: `https://your-deployment-xxx.us.langgraph.app`
   - **Assistant/Graph ID**: `email_assistant_hitl_memory_gmail`
   - **Name**: `Autonomous Email Inbox`
   - **LangSmith API Key**: Your LangSmith API key from above

## ⏰ Set Up Cron Job

Automate email ingestion:

```bash
python src/email_assistant/tools/gmail/setup_cron.py \
  --email autonomous.inbox@gmail.com \
  --url https://your-deployment-xxx.us.langgraph.app \
  --schedule "*/10 * * * *" \
  --include-read
```

This will check for new emails every 10 minutes.

## 🎯 What You'll Get

- ✅ **Autonomous Email Processing**: AI-powered email triage and responses
- ✅ **Human-in-the-Loop**: Review and approve AI decisions
- ✅ **Gmail Integration**: Real-time email fetching and processing
- ✅ **Scheduled Processing**: Automated email ingestion every 10 minutes
- ✅ **LangGraph Studio**: Monitor and debug your email workflows
- ✅ **Agent Inbox**: Human oversight interface for interrupted threads

## 🚨 Important Notes

1. **Gmail Credentials**: The `GMAIL_SECRET` and `GMAIL_TOKEN` are critical for Gmail API access
2. **API Keys**: Keep your OpenAI and LangSmith keys secure
3. **Cron Jobs**: The cron job will automatically process new emails
4. **Monitoring**: Use LangGraph Studio to monitor your deployment

## 🔧 Troubleshooting

- **Gmail Connection Issues**: Verify `GMAIL_SECRET` and `GMAIL_TOKEN` are correctly set
- **API Errors**: Check that all environment variables are properly configured
- **Cron Job Failures**: Verify the deployment URL is correct and accessible

## 📁 Secret Files Location

Your Gmail credentials are stored in:
- `src/email_assistant/tools/gmail/.secrets/secrets.json` → Copy to `GMAIL_SECRET`
- `src/email_assistant/tools/gmail/.secrets/token.json` → Copy to `GMAIL_TOKEN`

---

**Repository**: https://github.com/git-bonda108/langgraph-email-agent  
**Status**: ✅ Ready for deployment
