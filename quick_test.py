#!/usr/bin/env python
"""
Quick test of Agent Inbox integration components
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the src directory to Python path
sys.path.append(str(Path(__file__).parent / "src" / "email_assistant" / "tools" / "gmail"))

def test_environment():
    """Test environment variables"""
    print("🔧 Testing Environment Variables...")
    
    required_vars = [
        "AGENT_INBOX_URL",
        "AGENT_INBOX_ID", 
        "AGENT_INBOX_API_KEY"
    ]
    
    all_good = True
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: {value}")
        else:
            print(f"❌ {var}: Not set")
            all_good = False
    
    return all_good

def test_agent_inbox_parser():
    """Test the Agent Inbox Parser"""
    print("\n🔍 Testing Agent Inbox Parser...")
    
    try:
        from agent_inbox_parser import AgentInboxParser
        
        parser = AgentInboxParser()
        print("✅ Agent Inbox Parser imported successfully")
        
        # Test connection
        connection_status = parser.test_connection()
        print(f"📡 Connection Status: {connection_status}")
        
        # Test dashboard data
        dashboard_data = parser.get_dashboard_data()
        print(f"📊 Dashboard Data Source: {dashboard_data.get('source', 'unknown')}")
        print(f"📧 Email Count: {len(dashboard_data.get('emails', []))}")
        print(f"📈 Statistics: {dashboard_data.get('statistics', {})}")
        
        return True
        
    except ImportError as e:
        print(f"❌ Failed to import Agent Inbox Parser: {e}")
        return False
    except Exception as e:
        print(f"❌ Error testing Agent Inbox Parser: {e}")
        return False

def test_ingest_script():
    """Test the email ingest script"""
    print("\n📥 Testing Email Ingest Script...")
    
    try:
        # Check if the script exists
        ingest_script = Path(__file__).parent / "src" / "email_assistant" / "tools" / "gmail" / "run_ingest_agentinbox.py"
        
        if not ingest_script.exists():
            print(f"❌ Ingest script not found at {ingest_script}")
            return False
        
        print("✅ Ingest script found")
        
        # Check if Gmail credentials are available
        gmail_token = os.getenv("GMAIL_TOKEN")
        secrets_file = Path(__file__).parent / "src" / "email_assistant" / "tools" / "gmail" / ".secrets" / "token.json"
        
        if gmail_token:
            print("✅ Gmail token found in environment variables")
        elif secrets_file.exists():
            print("✅ Gmail credentials file found")
        else:
            print("⚠️  No Gmail credentials found (set GMAIL_TOKEN env var or create .secrets/token.json)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing ingest script: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting Quick Agent Inbox Integration Tests\n")
    
    tests = [
        ("Environment Variables", test_environment),
        ("Agent Inbox Parser", test_agent_inbox_parser),
        ("Ingest Script", test_ingest_script)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*50)
    print("📋 TEST SUMMARY")
    print("="*50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The integration is ready to use.")
        print("\nNext steps:")
        print("1. Set up the cron job: ./setup_agentinbox_cron.sh")
        print("2. Deploy to Vercel (already done)")
        print("3. Test the ingest script manually")
        print("4. Set real API keys in Vercel environment variables")
    else:
        print("⚠️  Some tests failed. Please fix the issues before proceeding.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

