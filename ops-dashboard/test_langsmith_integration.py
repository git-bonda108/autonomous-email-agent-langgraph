#!/usr/bin/env python3
"""
Test LangSmith Integration

This script tests the LangSmith API integration without requiring Gmail authentication.
It will create test runs to populate the dashboard.
"""

import requests
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# LangSmith Configuration
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY", "<REDACTED-ROTATE-ME>")
LANGSMITH_ENDPOINT = "https://api.smith.langchain.com"
PROJECT_NAME = "autonomous-email-inbox"

def test_langsmith_connection():
    """Test basic connection to LangSmith"""
    headers = {
        'Content-Type': 'application/json',
        'x-api-key': LANGSMITH_API_KEY
    }
    
    print("🔍 Testing LangSmith connection...")
    
    try:
        response = requests.get(f"{LANGSMITH_ENDPOINT}/datasets", headers=headers)
        if response.status_code == 200:
            print("✅ Successfully connected to LangSmith")
            return True
        else:
            print(f"❌ Connection failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False

def create_test_runs():
    """Create test runs in LangSmith to populate the dashboard"""
    headers = {
        'Content-Type': 'application/json',
        'x-api-key': LANGSMITH_API_KEY
    }
    
    print("\n📧 Creating test email runs...")
    
    # Test email data
    test_emails = [
        {
            "subject": "Meeting Request - Project Review",
            "sender": "john.doe@company.com",
            "status": "completed",
            "body": "Hi team, I'd like to schedule a meeting to review the project progress..."
        },
        {
            "subject": "Weekly Status Update",
            "sender": "jane.smith@company.com", 
            "status": "interrupted",
            "body": "Here's our weekly status update. Please review and let me know if you need any changes..."
        },
        {
            "subject": "Invoice #12345",
            "sender": "billing@vendor.com",
            "status": "failed",
            "body": "Your invoice for services rendered is attached..."
        },
        {
            "subject": "New Feature Request",
            "sender": "product@company.com",
            "status": "running",
            "body": "We've received a new feature request from a customer..."
        }
    ]
    
    successful_runs = 0
    
    for i, email in enumerate(test_emails):
        try:
            run_data = {
                "name": f"Email Processing: {email['subject']}",
                "project_name": PROJECT_NAME,
                "inputs": {
                    "email_subject": email['subject'],
                    "email_sender": email['sender'],
                    "email_body": email['body'],
                    "email_id": f"test_email_{i+1}",
                    "thread_id": f"test_thread_{i+1}"
                },
                "outputs": {
                    "status": email['status'],
                    "processing_stage": "test_ingestion",
                    "timestamp": datetime.now().isoformat()
                },
                "tags": ["email", "test", "gmail"],
                "metadata": {
                    "source": "test_data",
                    "email_id": f"test_email_{i+1}",
                    "thread_id": f"test_thread_{i+1}"
                },
                "status": email['status']
            }
            
            # Try to create a run using the runs endpoint
            response = requests.post(
                f"{LANGSMITH_ENDPOINT}/runs",
                json=run_data,
                headers=headers
            )
            
            if response.status_code == 200:
                run_info = response.json()
                print(f"✅ Created run: {email['subject']} (ID: {run_info.get('id', 'Unknown')[:8]}...)")
                successful_runs += 1
            else:
                print(f"❌ Failed to create run: {email['subject']} - {response.status_code} - {response.text[:100]}")
                
        except Exception as e:
            print(f"❌ Error creating run for {email['subject']}: {e}")
    
    return successful_runs

def test_dashboard_data():
    """Test if the dashboard can now fetch data"""
    print("\n📊 Testing dashboard data retrieval...")
    
    try:
        from app import get_langsmith_data
        data = get_langsmith_data()
        
        print(f"✅ Dashboard data retrieved successfully!")
        print(f"📧 Total emails: {data['statistics']['total_emails']}")
        print(f"✅ Processed: {data['statistics']['processed']}")
        print(f"🔄 HITL: {data['statistics']['hitl']}")
        print(f"❌ Ignored: {data['statistics']['ignored']}")
        print(f"⏳ Waiting action: {data['statistics']['waiting_action']}")
        
        if data.get('emails'):
            print(f"📨 Email threads: {len(data['emails'])}")
            for email in data['emails'][:2]:
                print(f"   - {email['subject']} ({email['status']})")
        
        return True
        
    except Exception as e:
        print(f"❌ Dashboard data test failed: {e}")
        return False

def main():
    """Main test function"""
    print("🧪 LangSmith Integration Test")
    print("=" * 40)
    
    # Test 1: Connection
    if not test_langsmith_connection():
        print("❌ Cannot proceed without LangSmith connection")
        return
    
    # Test 2: Create test runs
    successful_runs = create_test_runs()
    print(f"\n📊 Created {successful_runs} test runs")
    
    if successful_runs > 0:
        # Test 3: Dashboard data
        print("\n⏳ Waiting 5 seconds for runs to be processed...")
        import time
        time.sleep(5)
        
        test_dashboard_data()
        
        print(f"\n🎉 Test completed! Dashboard should now show {successful_runs} emails.")
        print("🌐 Check your Vercel deployment to see the updated numbers!")
    else:
        print("❌ No runs were created. Check LangSmith API access.")

if __name__ == "__main__":
    main()
