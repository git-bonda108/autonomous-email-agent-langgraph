#!/usr/bin/env python3
"""
LangSmith Email Ingestion Script

This script fetches emails from Gmail and creates traces in LangSmith for processing.
It will populate the dashboard with real email data.
"""

import base64
import json
import uuid
import hashlib
import os
import requests
from pathlib import Path
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

# Setup paths
_ROOT = Path(__file__).parent.absolute()
_SECRETS_DIR = _ROOT / "gmail_credentials"
TOKEN_PATH = _SECRETS_DIR / "token.json"
CREDENTIALS_PATH = _SECRETS_DIR / "credentials-gmail.json"

# LangSmith Configuration
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY", "<REDACTED-ROTATE-ME>")
LANGSMITH_ENDPOINT = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")
PROJECT_NAME = os.getenv("GRAPH_ID", "autonomous-email-inbox")

def extract_message_part(payload):
    """Extract content from a message part."""
    # If this is multipart, process with preference for text/plain
    if payload.get("parts"):
        # First try to find text/plain part
        for part in payload["parts"]:
            mime_type = part.get("mimeType", "")
            if mime_type == "text/plain" and part.get("body", {}).get("data"):
                data = part["body"]["data"]
                return base64.urlsafe_b64decode(data).decode("utf-8")
                
        # If no text/plain found, try text/html
        for part in payload["parts"]:
            mime_type = part.get("mimeType", "")
            if mime_type == "text/html" and part.get("body", {}).get("data"):
                data = part["body"]["data"]
                return base64.urlsafe_b64decode(data).decode("utf-8")
    
    # If not multipart, try to get the body directly
    if payload.get("body", {}).get("data"):
        data = payload["body"]["data"]
        return base64.urlsafe_b64decode(data).decode("utf-8")
    
    return ""

def get_gmail_service():
    """Get authenticated Gmail service."""
    if not CREDENTIALS_PATH.exists():
        raise FileNotFoundError(f"Gmail credentials not found at {CREDENTIALS_PATH}")
    
    if not TOKEN_PATH.exists():
        raise FileNotFoundError(f"Gmail token not found at {TOKEN_PATH}")
    
    # Load credentials
    with open(CREDENTIALS_PATH, 'r') as f:
        creds_data = json.load(f)
    
    # Load token
    with open(TOKEN_PATH, 'r') as f:
        token_data = json.load(f)
    
    # Create credentials object
    creds = Credentials.from_authorized_user_info(token_data, creds_data)
    
    # Build Gmail service
    service = build('gmail', 'v1', credentials=creds)
    return service

def fetch_recent_emails(service, minutes_since=5):
    """Fetch recent emails from Gmail."""
    try:
        # Calculate time threshold
        time_threshold = datetime.now() - timedelta(minutes=minutes_since)
        time_str = time_threshold.strftime('%Y/%m/%d %H:%M:%S')
        
        # Search for recent emails
        query = f'after:{time_str}'
        results = service.users().messages().list(userId='me', q=query).execute()
        
        messages = results.get('messages', [])
        print(f"Found {len(messages)} recent emails")
        
        return messages
    except Exception as e:
        print(f"Error fetching emails: {e}")
        return []

def process_email_message(service, message_id):
    """Process a single email message."""
    try:
        # Get full message details
        message = service.users().messages().get(userId='me', id=message_id).execute()
        
        # Extract headers
        headers = message['payload']['headers']
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
        sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
        recipient = next((h['value'] for h in headers if h['name'] == 'To'), 'Unknown Recipient')
        date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown Date')
        
        # Extract body
        body = extract_message_part(message['payload'])
        
        # Create email data
        email_data = {
            'id': message_id,
            'thread_id': message.get('threadId', ''),
            'subject': subject,
            'sender': sender,
            'recipient': recipient,
            'date': date,
            'body': body[:500] + '...' if len(body) > 500 else body,  # Truncate long bodies
            'snippet': message.get('snippet', ''),
            'internal_date': message.get('internalDate', ''),
            'processed_at': datetime.now().isoformat()
        }
        
        return email_data
        
    except Exception as e:
        print(f"Error processing message {message_id}: {e}")
        return None

def send_to_langsmith(email_data):
    """Send email data to LangSmith as a trace."""
    try:
        headers = {
            'Content-Type': 'application/json',
            'x-api-key': LANGSMITH_API_KEY
        }
        
        # Create a trace for this email
        trace_data = {
            "name": f"Email Processing: {email_data['subject']}",
            "project_name": PROJECT_NAME,
            "inputs": {
                "email_subject": email_data['subject'],
                "email_sender": email_data['sender'],
                "email_recipient": email_data['recipient'],
                "email_body": email_data['body'],
                "email_snippet": email_data['snippet'],
                "email_date": email_data['date'],
                "email_id": email_data['id'],
                "thread_id": email_data['thread_id']
            },
            "outputs": {
                "status": "received",
                "processing_stage": "ingestion",
                "timestamp": email_data['processed_at']
            },
            "tags": ["email", "ingestion", "gmail"],
            "metadata": {
                "source": "gmail",
                "email_id": email_data['id'],
                "thread_id": email_data['thread_id']
            }
        }
        
        # Send to LangSmith traces endpoint
        response = requests.post(
            f"{LANGSMITH_ENDPOINT}/traces",
            json=trace_data,
            headers=headers
        )
        
        if response.status_code == 200:
            trace_info = response.json()
            print(f"✅ Email sent to LangSmith: {trace_info.get('id', 'Unknown ID')}")
            return True
        else:
            print(f"❌ Failed to send to LangSmith: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error sending to LangSmith: {e}")
        return False

def main():
    """Main function to ingest emails."""
    print("🚀 Starting LangSmith Email Ingestion...")
    print(f"📧 Project: {PROJECT_NAME}")
    print(f"🔗 Endpoint: {LANGSMITH_ENDPOINT}")
    print()
    
    try:
        # Get Gmail service
        service = get_gmail_service()
        print("✅ Gmail service authenticated")
        
        # Fetch recent emails
        messages = fetch_recent_emails(service, minutes_since=60)  # Last hour
        
        if not messages:
            print("ℹ️ No recent emails found")
            return
        
        # Process each email
        successful_ingests = 0
        for message in messages:
            email_data = process_email_message(service, message['id'])
            if email_data:
                print(f"📨 Processing: {email_data['subject']}")
                if send_to_langsmith(email_data):
                    successful_ingests += 1
        
        print()
        print(f"🎉 Ingestion complete!")
        print(f"📊 Processed: {len(messages)} emails")
        print(f"✅ Successfully sent to LangSmith: {successful_ingests}")
        
    except Exception as e:
        print(f"❌ Error during ingestion: {e}")

if __name__ == "__main__":
    main()
