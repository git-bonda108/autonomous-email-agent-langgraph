#!/usr/bin/env python
"""
Agent Inbox Email Ingestion Script

This script fetches emails from Gmail and sends them to Agent Inbox for processing.
It's designed to work with the Agent Inbox framework instead of direct LangGraph integration.
"""

import base64
import json
import uuid
import hashlib
import asyncio
import argparse
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
_SECRETS_DIR = _ROOT / ".secrets"
TOKEN_PATH = _SECRETS_DIR / "token.json"

# Agent Inbox Configuration
AGENT_INBOX_URL = os.getenv("AGENT_INBOX_URL", "https://dev.agentinbox.ai")
AGENT_INBOX_ID = os.getenv("AGENT_INBOX_ID", "email_assistant_hitl_memory_gmail")
AGENT_INBOX_API_KEY = os.getenv("AGENT_INBOX_API_KEY", "")

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
                
        # If we still haven't found content, recursively check for nested parts
        for part in payload["parts"]:
            content = extract_message_part(part)
            if content:
                return content
    
    # Not multipart, try to get content directly
    if payload.get("body", {}).get("data"):
        data = payload["body"]["data"]
        return base64.urlsafe_b64decode(data).decode("utf-8")

    return ""

def load_gmail_credentials():
    """
    Load Gmail credentials from token.json or environment variables.
    
    This function attempts to load credentials from multiple sources in this order:
    1. Environment variables GMAIL_TOKEN
    2. Local file at token_path (.secrets/token.json)
    
    Returns:
        Google OAuth2 Credentials object or None if credentials can't be loaded
    """
    token_data = None
    
    # 1. Try environment variable
    env_token = os.getenv("GMAIL_TOKEN")
    if env_token:
        try:
            token_data = json.loads(env_token)
            print("Using GMAIL_TOKEN environment variable")
        except Exception as e:
            print(f"Could not parse GMAIL_TOKEN environment variable: {str(e)}")
    
    # 2. Try local file as fallback
    if token_data is None:
        if TOKEN_PATH.exists():
            try:
                with open(TOKEN_PATH, "r") as f:
                    token_data = json.load(f)
                print(f"Using token from {TOKEN_PATH}")
            except Exception as e:
                print(f"Could not load token from {TOKEN_PATH}: {str(e)}")
        else:
            print(f"Token file not found at {TOKEN_PATH}")
    
    # If we couldn't get token data from any source, return None
    if token_data is None:
        print("Could not find valid token data in any location")
        return None
    
    try:
        # Create credentials object
        credentials = Credentials(
            token=token_data.get("token"),
            refresh_token=token_data.get("refresh_token"),
            token_uri=token_data.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=token_data.get("client_id"),
            client_secret=token_data.get("client_secret"),
            scopes=token_data.get("scopes", ["https://www.googleapis.com/auth/gmail.modify"])
        )
        return credentials
    except Exception as e:
        print(f"Error creating credentials object: {str(e)}")
        return None

def extract_email_data(message):
    """Extract key information from a Gmail message."""
    headers = message['payload']['headers']
    
    # Extract key headers
    subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
    from_email = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
    to_email = next((h['value'] for h in headers if h['name'] == 'To'), 'Unknown Recipient')
    date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown Date')
    
    # Extract message content
    content = extract_message_part(message['payload'])
    
    # Create email data object
    email_data = {
        "from_email": from_email,
        "to_email": to_email,
        "subject": subject,
        "page_content": content,
        "id": message['id'],
        "thread_id": message['threadId'],
        "send_time": date,
        "status": "new"  # Initial status for Agent Inbox
    }
    
    return email_data

async def send_email_to_agent_inbox(email_data):
    """Send an email to Agent Inbox for processing."""
    try:
        # Prepare the email data for Agent Inbox
        agent_inbox_payload = {
            "email_id": email_data["id"],
            "thread_id": email_data["thread_id"],
            "from": email_data["from_email"],
            "to": email_data["to_email"],
            "subject": email_data["subject"],
            "body": email_data["page_content"],
            "timestamp": email_data["send_time"],
            "status": email_data["status"],
            "metadata": {
                "source": "gmail",
                "ingested_at": datetime.now().isoformat(),
                "gmail_message_id": email_data["id"]
            }
        }
        
        # Send to Agent Inbox
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {AGENT_INBOX_API_KEY}'
        }
        
        # Create a new thread in Agent Inbox
        thread_url = f"{AGENT_INBOX_URL}/api/threads"
        response = requests.post(
            thread_url,
            json=agent_inbox_payload,
            headers=headers
        )
        
        if response.status_code == 200 or response.status_code == 201:
            print(f"Successfully sent email {email_data['id']} to Agent Inbox")
            return True
        else:
            print(f"Failed to send email to Agent Inbox: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"Error sending email to Agent Inbox: {str(e)}")
        return False

async def fetch_and_process_emails(args):
    """Fetch emails from Gmail and process them through Agent Inbox."""
    # Load Gmail credentials
    credentials = load_gmail_credentials()
    if not credentials:
        print("Failed to load Gmail credentials")
        return 1
        
    # Build Gmail service
    service = build("gmail", "v1", credentials=credentials)
    
    # Process emails
    processed_count = 0
    failed_count = 0
    
    try:
        # Get messages from the specified email address
        email_address = args.email
        
        # Construct Gmail search query
        query = f"to:{email_address} OR from:{email_address}"
        
        # Add time constraint if specified
        if args.minutes_since > 0:
            # Calculate timestamp for filtering
            after = int((datetime.now() - timedelta(minutes=args.minutes_since)).timestamp())
            query += f" after:{after}"
            
        # Only include unread emails unless include_read is True
        if not args.include_read:
            query += " is:unread"
            
        print(f"Gmail search query: {query}")
        
        # Execute the search
        results = service.users().messages().list(userId="me", q=query).execute()
        messages = results.get("messages", [])
        
        if not messages:
            print("No emails found matching the criteria")
            return 0
            
        print(f"Found {len(messages)} emails")
        
        # Process each email
        for i, message_info in enumerate(messages):
            # Stop early if requested
            if args.early and i > 0:
                print(f"Early stop after processing {i} emails")
                break
                
            # Check if we should reprocess this email
            if not args.rerun:
                # TODO: Add check for already processed emails
                pass
                
            # Get the full message
            message = service.users().messages().get(userId="me", id=message_info["id"]).execute()
            
            # Extract email data
            email_data = extract_email_data(message)
            
            print(f"\nProcessing email {i+1}/{len(messages)}:")
            print(f"From: {email_data['from_email']}")
            print(f"Subject: {email_data['subject']}")
            
            # Send to Agent Inbox
            success = await send_email_to_agent_inbox(email_data)
            
            if success:
                processed_count += 1
            else:
                failed_count += 1
            
        print(f"\nProcessed {processed_count} emails successfully")
        if failed_count > 0:
            print(f"Failed to process {failed_count} emails")
        return 0
        
    except Exception as e:
        print(f"Error processing emails: {str(e)}")
        return 1

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Gmail ingestion for Agent Inbox")
    
    parser.add_argument(
        "--email", 
        type=str, 
        required=True,
        help="Email address to fetch messages for"
    )
    parser.add_argument(
        "--minutes-since", 
        type=int, 
        default=5,  # Default to 5 minutes for cron job
        help="Only retrieve emails newer than this many minutes"
    )
    parser.add_argument(
        "--early", 
        action="store_true",
        help="Early stop after processing one email"
    )
    parser.add_argument(
        "--include-read",
        action="store_true",
        help="Include emails that have already been read"
    )
    parser.add_argument(
        "--rerun", 
        action="store_true",
        help="Process the same emails again even if already processed"
    )
    return parser.parse_args()

if __name__ == "__main__":
    # Get command line arguments
    args = parse_args()
    
    # Run the script
    exit(asyncio.run(fetch_and_process_emails(args)))

