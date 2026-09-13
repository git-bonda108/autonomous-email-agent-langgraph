#!/usr/bin/env python
"""
Test script for LangSmith integration

This script tests the LangSmith integration components:
1. LangSmith Parser
2. Environment Variables
3. API Connection
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
        "GRAPH_ID"
    ]
    
    optional_vars = [
        "LANGSMITH_ENDPOINT"
    ]
    
    all_good = True
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: {value[:20]}{'...' if len(value) > 20 else ''}")
        else:
            print(f"❌ {var}: Not set")
            all_good = False
    
    for var in optional_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: {value}")
        else:
            print(f"⚠️  {var}: Not set (using default)")
    
    return all_good

def test_langsmith_parser():
    """Test the LangSmith Parser"""
    print("\n🔍 Testing LangSmith Parser...")
    
    try:
        from langsmith_parser import LangSmithParser
        
        parser = LangSmithParser()
        print("✅ LangSmith Parser imported successfully")
        
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
        print(f"❌ Failed to import LangSmith Parser: {e}")
        return False
    except Exception as e:
        print(f"❌ Error testing LangSmith Parser: {e}")
        return False

def test_api_connection():
    """Test direct API connection to LangSmith"""
    print("\n🌐 Testing LangSmith API Connection...")
    
    try:
        import requests
        
        api_key = os.getenv("LANGSMITH_API_KEY")
        endpoint = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")
        
        if not api_key:
            print("❌ No LangSmith API key found")
            return False
        
        headers = {
            'Content-Type': 'application/json',
            'x-api-key': api_key
        }
        
        # Test projects endpoint
        response = requests.get(
            f"{endpoint}/projects",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            print(f"✅ Successfully connected to LangSmith API")
            print(f"📡 Endpoint: {endpoint}")
            print(f"🔑 API Key: {api_key[:20]}...")
            return True
        else:
            print(f"❌ API connection failed: {response.status_code}")
            print(f"📄 Response: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing API connection: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting LangSmith Integration Tests\n")
    
    tests = [
        ("Environment Variables", test_environment),
        ("LangSmith Parser", test_langsmith_parser),
        ("API Connection", test_api_connection)
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
        print("🎉 All tests passed! The LangSmith integration is ready to use.")
        print("\nNext steps:")
        print("1. Deploy the new app: cp app_langsmith.py app_agentinbox.py")
        print("2. Set environment variables in Vercel")
        print("3. Test the dashboard")
    else:
        print("⚠️  Some tests failed. Please fix the issues before proceeding.")
        print("\nCommon issues:")
        print("- Missing LANGSMITH_API_KEY environment variable")
        print("- Incorrect API key format")
        print("- Network connectivity issues")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
