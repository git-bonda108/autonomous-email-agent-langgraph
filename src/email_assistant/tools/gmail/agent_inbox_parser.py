#!/usr/bin/env python
"""
Agent Inbox Data Parser

This module fetches data from Agent Inbox and formats it for the dashboard.
It provides functions to get email statistics, thread information, and status updates.
"""

import os
import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv

load_dotenv()

class AgentInboxParser:
    """Parser for Agent Inbox data to populate dashboard statistics."""
    
    def __init__(self):
        self.agent_inbox_url = os.getenv("AGENT_INBOX_URL", "https://dev.agentinbox.ai")
        self.agent_inbox_id = os.getenv("AGENT_INBOX_ID", "email_assistant_hitl_memory_gmail")
        self.api_key = os.getenv("AGENT_INBOX_API_KEY", "")
        
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data from Agent Inbox."""
        try:
            # Get basic statistics
            statistics = self._get_statistics()
            
            # Get email threads
            emails = self._get_email_threads()
            
            # Get recent activity
            recent_activity = self._get_recent_activity()
            
            return {
                "statistics": statistics,
                "emails": emails,
                "recent_activity": recent_activity,
                "last_updated": datetime.now().isoformat(),
                "source": "agent_inbox"
            }
            
        except Exception as e:
            print(f"Error fetching dashboard data: {e}")
            return self._get_fallback_data()
    
    def _get_statistics(self) -> Dict[str, int]:
        """Get email statistics from Agent Inbox."""
        try:
            # Get threads count
            threads_response = requests.get(
                f"{self.agent_inbox_url}/api/threads",
                headers=self.headers
            )
            
            if threads_response.status_code == 200:
                threads_data = threads_response.json()
                total_threads = len(threads_data.get("threads", []))
                
                # Count by status
                status_counts = {
                    "processed": 0,
                    "hitl": 0,
                    "ignored": 0,
                    "waiting_action": 0
                }
                
                for thread in threads_data.get("threads", []):
                    status = thread.get("status", "unknown").lower()
                    if status in status_counts:
                        status_counts[status] += 1
                    else:
                        status_counts["waiting_action"] += 1
                
                return {
                    "total_emails": total_threads,
                    "processed": status_counts["processed"],
                    "hitl": status_counts["hitl"],
                    "ignored": status_counts["ignored"],
                    "waiting_action": status_counts["waiting_action"],
                    "scheduled_meetings": self._count_scheduled_meetings(),
                    "notifications": self._count_notifications()
                }
            
        except Exception as e:
            print(f"Error fetching statistics: {e}")
        
        # Return fallback statistics
        return {
            "total_emails": 0,
            "processed": 0,
            "hitl": 0,
            "ignored": 0,
            "waiting_action": 0,
            "scheduled_meetings": 0,
            "notifications": 0
        }
    
    def _get_email_threads(self) -> List[Dict[str, Any]]:
        """Get email threads with formatted data for dashboard."""
        try:
            threads_response = requests.get(
                f"{self.agent_inbox_url}/api/threads",
                headers=self.headers
            )
            
            if threads_response.status_code == 200:
                threads_data = threads_response.json()
                formatted_emails = []
                
                for thread in threads_data.get("threads", []):
                    # Format email data for dashboard
                    formatted_email = {
                        "id": thread.get("thread_id", ""),
                        "subject": self._format_subject(thread.get("subject", "No Subject")),
                        "from": thread.get("from", "Unknown"),
                        "to": thread.get("to", "Unknown"),
                        "timestamp": thread.get("timestamp", ""),
                        "status": thread.get("status", "unknown"),
                        "priority": self._determine_priority(thread),
                        "content_preview": self._get_content_preview(thread.get("body", "")),
                        "metadata": thread.get("metadata", {}),
                        "last_updated": thread.get("last_updated", "")
                    }
                    
                    formatted_emails.append(formatted_email)
                
                # Sort by timestamp (newest first)
                formatted_emails.sort(
                    key=lambda x: x["timestamp"], 
                    reverse=True
                )
                
                return formatted_emails[:50]  # Limit to 50 most recent
                
        except Exception as e:
            print(f"Error fetching email threads: {e}")
        
        return []
    
    def _get_recent_activity(self) -> List[Dict[str, Any]]:
        """Get recent activity from Agent Inbox."""
        try:
            # Get recent runs or actions
            activity_response = requests.get(
                f"{self.agent_inbox_url}/api/activity",
                headers=self.headers
            )
            
            if activity_response.status_code == 200:
                activity_data = activity_response.json()
                return activity_data.get("activities", [])
                
        except Exception as e:
            print(f"Error fetching recent activity: {e}")
        
        return []
    
    def _format_subject(self, subject: str) -> str:
        """Format email subject for better readability."""
        if not subject or subject == "No Subject":
            return "No Subject"
        
        # Clean up common email subject patterns
        subject = subject.strip()
        
        # Remove common prefixes
        prefixes_to_remove = ["Re:", "Fwd:", "FW:", "RE:", "FWD:"]
        for prefix in prefixes_to_remove:
            if subject.startswith(prefix):
                subject = subject[len(prefix):].strip()
        
        # Truncate long subjects
        if len(subject) > 60:
            subject = subject[:57] + "..."
        
        return subject
    
    def _determine_priority(self, thread: Dict[str, Any]) -> str:
        """Determine email priority based on content and metadata."""
        subject = thread.get("subject", "").lower()
        body = thread.get("body", "").lower()
        
        # High priority keywords
        high_priority = ["urgent", "asap", "emergency", "critical", "important", "deadline"]
        
        # Medium priority keywords
        medium_priority = ["meeting", "call", "schedule", "request", "question"]
        
        # Check for high priority
        for keyword in high_priority:
            if keyword in subject or keyword in body:
                return "high"
        
        # Check for medium priority
        for keyword in medium_priority:
            if keyword in subject or keyword in body:
                return "medium"
        
        return "low"
    
    def _get_content_preview(self, content: str, max_length: int = 100) -> str:
        """Get a preview of email content."""
        if not content:
            return "No content"
        
        # Clean up content
        content = content.replace("\n", " ").replace("\r", " ")
        content = " ".join(content.split())  # Remove extra whitespace
        
        if len(content) <= max_length:
            return content
        
        return content[:max_length] + "..."
    
    def _count_scheduled_meetings(self) -> int:
        """Count scheduled meetings from Agent Inbox data."""
        try:
            # This would depend on how meetings are stored in Agent Inbox
            # For now, return a placeholder
            return 0
        except Exception as e:
            print(f"Error counting scheduled meetings: {e}")
            return 0
    
    def _count_notifications(self) -> int:
        """Count notifications from Agent Inbox data."""
        try:
            # This would depend on how notifications are stored in Agent Inbox
            # For now, return a placeholder
            return 0
        except Exception as e:
            print(f"Error counting notifications: {e}")
            return 0
    
    def _get_fallback_data(self) -> Dict[str, Any]:
        """Get fallback data when Agent Inbox is not accessible."""
        return {
            "statistics": {
                "total_emails": 0,
                "processed": 0,
                "hitl": 0,
                "ignored": 0,
                "waiting_action": 0,
                "scheduled_meetings": 0,
                "notifications": 0
            },
            "emails": [],
            "recent_activity": [],
            "last_updated": datetime.now().isoformat(),
            "source": "fallback",
            "error": "Agent Inbox not accessible"
        }
    
    def test_connection(self) -> Dict[str, Any]:
        """Test connection to Agent Inbox."""
        try:
            response = requests.get(
                f"{self.agent_inbox_url}/api/health",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return {
                    "status": "connected",
                    "message": "Successfully connected to Agent Inbox",
                    "url": self.agent_inbox_url,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "status": "error",
                    "message": f"Agent Inbox returned status {response.status_code}",
                    "url": self.agent_inbox_url,
                    "timestamp": datetime.now().isoformat()
                }
                
        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "message": f"Connection failed: {str(e)}",
                "url": self.agent_inbox_url,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Unexpected error: {str(e)}",
                "url": self.agent_inbox_url,
                "timestamp": datetime.now().isoformat()
            }

def main():
    """Test the Agent Inbox parser."""
    parser = AgentInboxParser()
    
    print("Testing Agent Inbox connection...")
    connection_status = parser.test_connection()
    print(f"Connection status: {connection_status}")
    
    if connection_status["status"] == "connected":
        print("\nFetching dashboard data...")
        dashboard_data = parser.get_dashboard_data()
        print(f"Dashboard data source: {dashboard_data['source']}")
        print(f"Statistics: {dashboard_data['statistics']}")
        print(f"Email count: {len(dashboard_data['emails'])}")
    else:
        print("Cannot fetch dashboard data - connection failed")

if __name__ == "__main__":
    main()

