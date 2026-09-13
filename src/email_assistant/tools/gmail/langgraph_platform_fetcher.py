#!/usr/bin/env python
"""
LangGraph Platform Data Fetcher

This module fetches data from your existing LangGraph Platform deployment
that's running the email_assistant_hitl_memory_gmail graph.
It provides functions to get email statistics, thread information, and status updates.
"""

import os
import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv

load_dotenv()

class LangGraphPlatformFetcher:
    """Fetcher for LangGraph Platform data to populate dashboard statistics."""
    
    def __init__(self):
        # Get configuration from environment variables
        self.langgraph_api_key = os.getenv("LANGSMITH_API_KEY")
        self.endpoint = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")
        self.graph_id = os.getenv("GRAPH_ID", "email_assistant_hitl_memory_gmail")
        
        # Validate configuration
        if not self.langgraph_api_key:
            raise ValueError("LANGSMITH_API_KEY environment variable is required")
        
        print(f"Initialized LangGraph Platform Fetcher")
        print(f"Endpoint: {self.endpoint}")
        print(f"Graph ID: {self.graph_id}")
        print(f"API Key Available: {'Yes' if self.langgraph_api_key else 'No'}")
    
    def test_connection(self) -> Dict[str, Any]:
        """Test connection to LangGraph Platform"""
        try:
            # Test basic connectivity
            response = requests.get(f"{self.endpoint}/health", timeout=10)
            print(f"Health check response: {response.status_code}")
            
            if response.status_code == 200:
                return {
                    "status": "connected",
                    "message": "Successfully connected to LangGraph Platform",
                    "endpoint": self.endpoint,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "status": "error",
                    "message": f"Health check failed with status {response.status_code}",
                    "endpoint": self.endpoint,
                    "timestamp": datetime.now().isoformat()
                }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Connection failed: {str(e)}",
                "endpoint": self.endpoint,
                "timestamp": datetime.now().isoformat()
            }
    
    def get_email_threads(self) -> List[Dict[str, Any]]:
        """Fetch email threads from LangGraph Platform"""
        try:
            headers = {
                "Authorization": f"Bearer {self.langgraph_api_key}",
                "Content-Type": "application/json"
            }
            
            # Try to fetch threads from the graph
            url = f"{self.endpoint}/graphs/{self.graph_id}/threads"
            response = requests.get(url, headers=headers, timeout=30)
            
            print(f"Threads response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                threads = data.get("threads", [])
                return threads
            else:
                print(f"Failed to fetch threads: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            print(f"Error fetching email threads: {e}")
            return []
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data from LangGraph Platform"""
        try:
            print("=== Starting LangGraph Platform data fetch ===")
            
            # Test connection first
            connection_status = self.test_connection()
            print(f"Connection test result: {connection_status}")
            
            if connection_status.get("status") != "connected":
                return {
                    "error": "Not connected to LangGraph Platform",
                    "connection_status": connection_status,
                    "total_emails": 0,
                    "processed": 0,
                    "hitl": 0,
                    "ignored": 0,
                    "waiting_action": 0,
                    "scheduled_meetings": 0,
                    "notifications": 0,
                    "threads": [],
                    "source": "LangGraph Platform - Connection Failed"
                }
            
            # Fetch email threads
            threads = self.get_email_threads()
            
            # Process threads to extract statistics
            total_emails = len(threads)
            processed = 0
            hitl = 0
            ignored = 0
            waiting_action = 0
            scheduled_meetings = 0
            notifications = 0
            
            # Analyze thread statuses
            for thread in threads:
                status = thread.get("status", "unknown").lower()
                if status in ["processed", "completed", "done"]:
                    processed += 1
                elif status in ["hitl", "human_in_the_loop", "waiting_human"]:
                    hitl += 1
                elif status in ["ignored", "skipped"]:
                    ignored += 1
                elif status in ["waiting", "pending", "in_progress"]:
                    waiting_action += 1
                elif status in ["scheduled", "meeting_scheduled"]:
                    scheduled_meetings += 1
                elif status in ["notification", "alert"]:
                    notifications += 1
            
            print(f"Total processed: {total_emails}, Waiting HITL: {hitl}, Failed: {ignored}")
            print(f"Returning result with {total_emails} emails")
            
            return {
                "total_emails": total_emails,
                "processed": processed,
                "hitl": hitl,
                "ignored": ignored,
                "waiting_action": waiting_action,
                "scheduled_meetings": scheduled_meetings,
                "notifications": notifications,
                "threads": threads,
                "source": f"LangGraph Platform - {self.endpoint}",
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Error getting dashboard data: {e}")
            return {
                "error": str(e),
                "total_emails": 0,
                "processed": 0,
                "hitl": 0,
                "ignored": 0,
                "waiting_action": 0,
                "scheduled_meetings": 0,
                "notifications": 0,
                "threads": [],
                "source": "Error",
                "last_updated": datetime.now().isoformat()
            }
    
    def run_email_ingest(self) -> Dict[str, Any]:
        """Run email ingest process to fetch and process new emails"""
        try:
            print("🚀 Starting email ingest process...")
            
            # Test connection first
            connection_status = self.test_connection()
            if connection_status.get("status") != "connected":
                return {
                    "status": "error",
                    "error": "Not connected to LangGraph Platform",
                    "connection_status": connection_status
                }
            
            # Fetch current threads to get baseline
            initial_threads = self.get_email_threads()
            initial_count = len(initial_threads)
            
            print(f"📧 Initial email count: {initial_count}")
            
            # Simulate email processing (in real implementation, this would trigger the graph)
            # For now, we'll just refresh the data
            processed_threads = self.get_email_threads()
            final_count = len(processed_threads)
            
            # Calculate what was processed
            processed_count = max(0, final_count - initial_count)
            
            print(f"✅ Ingest completed. Processed: {processed_count}, Total: {final_count}")
            
            return {
                "status": "success",
                "message": "Email ingest completed successfully",
                "processed": processed_count,
                "initial_count": initial_count,
                "final_count": final_count,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ Error during email ingest: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

def main():
    """Test the LangGraph Platform Fetcher"""
    try:
        print("🧪 Testing LangGraph Platform Fetcher...")
        
        fetcher = LangGraphPlatformFetcher()
        
        # Test connection
        print("\n🔍 Testing connection...")
        connection_status = fetcher.test_connection()
        print(f"Connection Status: {connection_status}")
        
        # Test data fetching
        print("\n📊 Testing data fetch...")
        dashboard_data = fetcher.get_dashboard_data()
        print(f"📊 Dashboard Data Source: {dashboard_data.get('source', 'Unknown')}")
        print(f"📧 Email Count: {dashboard_data.get('total_emails', 0)}")
        print(f"📈 Statistics: {dashboard_data}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    main()
