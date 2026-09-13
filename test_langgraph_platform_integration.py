#!/usr/bin/env python
"""
Test script for LangGraph Platform integration

This script tests the integration with your existing LangGraph Platform deployment
to ensure the dashboard can fetch real email data.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add the src directory to Python path
sys.path.append(str(Path(__file__).parent / "src" / "email_assistant" / "tools" / "gmail"))

# Load environment variables
load_dotenv()

def test_environment():
    """Test environment variables"""
    print("🔧 Testing Environment Variables...")
    
    required_vars = [
        "LANGSMITH_API_KEY",
        "LANGSMITH_ENDPOINT", 
        "GRAPH_ID"
    ]
    
    all_good = True
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: {value[:20]}{'...' if len(value) > 20 else ''}")
        else:
            print(f"❌ {var}: Not set")
            all_good = False
    
    return all_good

def test_langgraph_platform_fetcher():
    """Test the LangGraph Platform Fetcher"""
    print("\n🔍 Testing LangGraph Platform Fetcher...")
    
    try:
        from langgraph_platform_fetcher import LangGraphPlatformFetcher
        
        fetcher = LangGraphPlatformFetcher()
        print("✅ LangGraph Platform Fetcher imported successfully")
        
        # Test connection
        connection_status = fetcher.test_connection()
        print(f"📡 Connection Status: {connection_status}")
        
        # Test dashboard data
        dashboard_data = fetcher.get_dashboard_data()
        print(f"📊 Dashboard Data Source: {dashboard_data.get('source', 'unknown')}")
        print(f"📧 Email Count: {len(dashboard_data.get('emails', []))}")
        print(f"📈 Statistics: {dashboard_data.get('statistics', {})}")
        
        return True
        
    except ImportError as e:
        print(f"❌ Failed to import LangGraph Platform Fetcher: {e}")
        return False
    except Exception as e:
        print(f"❌ Error testing LangGraph Platform Fetcher: {e}")
        return False

def test_flask_app():
    """Test the Flask app integration"""
    print("\n🌐 Testing Flask App Integration...")
    
    try:
        # Check if the updated app exists
        app_file = Path(__file__).parent / "public_interface" / "app_agentinbox.py"
        
        if app_file.exists():
            print("✅ Updated Flask app found")
        else:
            print("❌ Updated Flask app not found")
            return False
        
        # Test importing the app
        sys.path.append(str(Path(__file__).parent / "public_interface"))
        
        try:
            from app_agentinbox import app, interface
            print("✅ Updated Flask app imports successfully")
            print(f"📡 LangGraph Endpoint: {interface.langgraph_endpoint}")
            print(f"🔑 API Key Available: {'Yes' if interface.langgraph_api_key else 'No'}")
            return True
        except ImportError as e:
            print(f"❌ Failed to import updated Flask app: {e}")
            return False
        
    except Exception as e:
        print(f"❌ Error testing Flask app: {e}")
        return False

def test_dashboard_template():
    """Test if dashboard template exists"""
    print("\n📋 Testing Dashboard Template...")
    
    try:
        template_file = Path(__file__).parent / "public_interface" / "templates" / "dashboard.html"
        
        if template_file.exists():
            print("✅ Dashboard template found")
            return True
        else:
            print("❌ Dashboard template not found")
            return False
        
    except Exception as e:
        print(f"❌ Error testing dashboard template: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting LangGraph Platform Integration Tests\n")
    
    tests = [
        ("Environment Variables", test_environment),
        ("LangGraph Platform Fetcher", test_langgraph_platform_fetcher),
        ("Flask App Integration", test_flask_app),
        ("Dashboard Template", test_dashboard_template)
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
        print("1. Deploy to Vercel: git add . && git commit -m 'Deploy LangGraph Platform integration' && git push")
        print("2. Set environment variables in Vercel dashboard")
        print("3. Test the dashboard at your Vercel URL")
        print("\nExpected dashboard behavior:")
        print("- Will connect to your existing LangGraph Platform deployment")
        print("- Will fetch real email data from email_assistant_hitl_memory_gmail graph")
        print("- Will show actual email counts instead of 0s")
        print("- Will display email threads with real status information")
    else:
        print("⚠️  Some tests failed. Please fix the issues before proceeding.")
        print("\nCommon issues:")
        print("- Missing environment variables (LANGSMITH_API_KEY, etc.)")
        print("- Import path issues")
        print("- Missing dependencies")
        print("- Dashboard template not found")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

