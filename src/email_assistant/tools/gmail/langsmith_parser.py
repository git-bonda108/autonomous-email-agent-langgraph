#!/usr/bin/env python
"""
LangSmith Data Parser

This module fetches data from LangSmith and formats it for the dashboard.
It provides functions to get email statistics, thread information, and status updates.
"""

import os
import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv

load_dotenv()

class LangSmithParser:
    """Parser for LangSmith data to populate dashboard statistics."""
    
    def __init__(self):
        self.langsmith_api_key = os.getenv("LANGSMITH_API_KEY", "<REDACTED-ROTATE-ME>")
        self.langsmith_endpoint = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")
        self.graph_id = os.getenv("GRAPH_ID", "email_assistant_hitl_memory_gmail")
        
        # LangSmith uses x-api-key header instead of Authorization
        self.headers = {
            'Content-Type': 'application/json',
            'x-api-key': self.langsmith_api_key
        }
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data from LangSmith."""
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
                "source": "langsmith"
            }
            
        except Exception as e:
            print(f"Error fetching dashboard data: {e}")
            return self._get_fallback_data()
    
    def _get_statistics(self) -> Dict[str, int]:
        """Get email statistics from LangSmith."""
        try:
            # Try to get runs using POST method (LangSmith often requires POST for queries)
            runs_response = requests.post(
                f"{self.langsmith_endpoint}/runs/search",
                headers=self.headers,
                json={
                    "project": self.graph_id,
                    "limit": 100
                }
            )
            
            if runs_response.status_code == 200:
                runs_data = runs_response.json()
                runs = runs_data.get("runs", [])
                
                # Count by status
                status_counts = {
                    "processed": 0,
                    "hitl": 0,
                    "ignored": 0,
                    "waiting_action": 0
                }
                
                for run in runs:
                    status = run.get("status", "unknown").lower()
                    if status == "completed":
                        status_counts["processed"] += 1
                    elif status == "interrupted":
                        status_counts["hitl"] += 1
                    elif status == "failed":
                        status_counts["ignored"] += 1
                    else:
                        status_counts["waiting_action"] += 1
                
                return {
                    "total_emails": len(runs),
                    "processed": status_counts["processed"],
                    "hitl": status_counts["hitl"],
                    "ignored": status_counts["ignored"],
                    "waiting_action": status_counts["waiting_action"],
                    "scheduled_meetings": self._count_scheduled_meetings(runs),
                    "notifications": len(runs)
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
            # Get runs from the graph using POST method
            runs_response = requests.post(
                f"{self.langsmith_endpoint}/runs/search",
                headers=self.headers,
                json={
                    "project": self.graph_id,
                    "limit": 50
                }
            )
            
            if runs_response.status_code == 200:
                runs_data = runs_response.json()
                runs = runs_data.get("runs", [])
                formatted_emails = []
                
                for run in runs:
                    # Extract email data from run
                    run_input = run.get("inputs", {})
                    run_output = run.get("outputs", {})
                    
                    # Try to get email content from various possible fields
                    email_content = (
                        run_input.get("email_input", {}).get("body") or
                        run_input.get("body") or
                        run_input.get("content") or
                        run_output.get("email_content") or
                        "No content available"
                    )
                    
                    subject = (
                        run_input.get("email_input", {}).get("subject") or
                        run_input.get("subject") or
                        "No Subject"
                    )
                    
                    sender = (
                        run_input.get("email_input", {}).get("from") or
                        run_input.get("from") or
                        "Unknown Sender"
                    )
                    
                    recipient = (
                        run_input.get("email_input", {}).get("to") or
                        run_input.get("to") or
                        "Unknown Recipient"
                    )
                    
                    # Format email data for dashboard
                    formatted_email = {
                        "id": run.get("id", ""),
                        "subject": self._format_subject(subject),
                        "from": sender,
                        "to": recipient,
                        "timestamp": run.get("start_time", ""),
                        "status": self._map_run_status(run.get("status", "unknown")),
                        "priority": self._determine_priority(subject, email_content),
                        "content_preview": self._get_content_preview(email_content),
                        "metadata": {
                            "run_id": run.get("id"),
                            "graph_id": self.graph_id,
                            "execution_time": run.get("execution_time"),
                            "latency": run.get("latency")
                        },
                        "last_updated": run.get("end_time", run.get("start_time", ""))
                    }
                    
                    formatted_emails.append(formatted_email)
                
                # Sort by timestamp (newest first)
                formatted_emails.sort(
                    key=lambda x: x["timestamp"], 
                    reverse=True
                )
                
                return formatted_emails
                
        except Exception as e:
            print(f"Error fetching email threads: {e}")
        
        return []
    
    def _get_recent_activity(self) -> List[Dict[str, Any]]:
        """Get recent activity from LangSmith."""
        try:
            # Get recent runs using POST method
            runs_response = requests.post(
                f"{self.langsmith_endpoint}/runs/search",
                headers=self.headers,
                json={
                    "project": self.graph_id,
                    "limit": 20
                }
            )
            
            if runs_response.status_code == 200:
                runs_data = runs_response.json()
                runs = runs_data.get("runs", [])
                
                activities = []
                for run in runs:
                    activity = {
                        "id": run.get("id"),
                        "type": "email_processing",
                        "status": run.get("status"),
                        "timestamp": run.get("start_time"),
                        "duration": run.get("execution_time"),
                        "graph_id": self.graph_id
                    }
                    activities.append(activity)
                
                return activities
                
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
    
    def _map_run_status(self, run_status: str) -> str:
        """Map LangSmith run status to dashboard status."""
        status_mapping = {
            "completed": "processed",
            "interrupted": "hitl",
            "failed": "ignored",
            "running": "waiting_action",
            "pending": "waiting_action"
        }
        
        return status_mapping.get(run_status.lower(), "waiting_action")
    
    def _determine_priority(self, subject: str, content: str) -> str:
        """Determine email priority based on content and metadata."""
        subject_lower = subject.lower()
        content_lower = content.lower()
        
        # High priority keywords
        high_priority = ["urgent", "asap", "emergency", "critical", "important", "deadline"]
        
        # Medium priority keywords
        medium_priority = ["meeting", "call", "schedule", "request", "question"]
        
        # Check for high priority
        for keyword in high_priority:
            if keyword in subject_lower or keyword in content_lower:
                return "high"
        
        # Check for medium priority
        for keyword in medium_priority:
            if keyword in subject_lower or keyword in content_lower:
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
    
    def _count_scheduled_meetings(self, runs: List[Dict]) -> int:
        """Count scheduled meetings from run data."""
        try:
            meeting_count = 0
            for run in runs:
                run_input = run.get("inputs", {})
                subject = run_input.get("email_input", {}).get("subject", "").lower()
                content = run_input.get("email_input", {}).get("body", "").lower()
                
                if "meeting" in subject or "meeting" in content:
                    meeting_count += 1
            
            return meeting_count
        except Exception as e:
            print(f"Error counting scheduled meetings: {e}")
            return 0
    
    def _get_fallback_data(self) -> Dict[str, Any]:
        """Get fallback data when LangSmith is not accessible."""
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
            "error": "LangSmith not accessible"
        }
    
    def test_connection(self) -> Dict[str, Any]:
        """Test connection to LangSmith."""
        try:
            # Try different endpoints to find the correct one
            endpoints_to_try = [
                f"{self.langsmith_endpoint}/runs",
                f"{self.langsmith_endpoint}/projects",
                f"{self.langsmith_endpoint}/traces",
                f"{self.langsmith_endpoint}/datasets"
            ]
            
            for endpoint in endpoints_to_try:
                try:
                    response = requests.get(
                        endpoint,
                        headers=self.headers,
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        return {
                            "status": "connected",
                            "message": f"Successfully connected to LangSmith at {endpoint}",
                            "endpoint": endpoint,
                            "graph_id": self.graph_id,
                            "timestamp": datetime.now().isoformat()
                        }
                    elif response.status_code == 401:
                        return {
                            "status": "error",
                            "message": "Authentication failed - check API key",
                            "endpoint": endpoint,
                            "timestamp": datetime.now().isoformat()
                        }
                    elif response.status_code == 403:
                        return {
                            "status": "error",
                            "message": "Access forbidden - check API key permissions",
                            "endpoint": endpoint,
                            "timestamp": datetime.now().isoformat()
                        }
                    elif response.status_code == 404:
                        continue  # Try next endpoint
                    else:
                        print(f"Endpoint {endpoint} returned {response.status_code}")
                        continue
                        
                except Exception as e:
                    print(f"Error testing endpoint {endpoint}: {e}")
                    continue
            
            # If we get here, none of the endpoints worked
            return {
                "status": "error",
                "message": "Could not connect to any LangSmith endpoints",
                "endpoint": self.langsmith_endpoint,
                "timestamp": datetime.now().isoformat()
            }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"Unexpected error: {str(e)}",
                "endpoint": self.langsmith_endpoint,
                "timestamp": datetime.now().isoformat()
            }

def main():
    """Test the LangSmith parser."""
    parser = LangSmithParser()
    
    print("Testing LangSmith connection...")
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
