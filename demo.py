#!/usr/bin/env python3
"""
Demo script for the Email Assistant
Run this to test the email assistant with sample inputs
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from email_assistant.email_assistant import email_assistant
from email_assistant.eval.email_dataset import email_inputs
from email_assistant.utils import format_messages_string

def main():
    print("🚀 Email Assistant Demo")
    print("=" * 50)
    
    # Test with the first email from the dataset
    sample_email = email_inputs[0]
    print(f"\n📧 Processing sample email:")
    print(f"Subject: {sample_email.get('subject', 'No subject')}")
    print(f"From: {sample_email.get('from', 'Unknown sender')}")
    print(f"Content: {sample_email.get('content', 'No content')[:100]}...")
    
    print("\n🤖 Running email assistant...")
    
    try:
        # Run the email assistant
        result = email_assistant.invoke({"email_input": sample_email})
        
        print("\n✅ Email processed successfully!")
        print("\n📝 Response:")
        print(format_messages_string(result['messages']))
        
        # Show the final decision
        if 'decision' in result:
            print(f"\n🎯 Final Decision: {result['decision']}")
            
    except Exception as e:
        print(f"\n❌ Error running email assistant: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

