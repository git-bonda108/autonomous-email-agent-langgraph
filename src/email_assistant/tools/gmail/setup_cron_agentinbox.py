#!/usr/bin/env python
"""
Setup cron job for Agent Inbox email ingestion.

This script creates a scheduled cron job that runs the Agent Inbox ingest script
every 5 minutes to process new emails.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def setup_system_cron(email_address, script_path, schedule="*/5 * * * *"):
    """Set up a system cron job to run the ingest script."""
    
    # Get the absolute path to the script
    script_abs_path = Path(script_path).resolve()
    
    # Create the cron command
    cron_command = f"{schedule} cd {script_abs_path.parent} && uv run python {script_abs_path.name} --email {email_address} --minutes-since 5"
    
    # Create a temporary cron file
    cron_file_content = f"""# Agent Inbox Email Ingestion Cron Job
# This cron job runs every 5 minutes to ingest new emails
{cron_command}

"""
    
    # Write the cron file
    cron_file_path = Path.home() / ".agentinbox_cron"
    with open(cron_file_path, "w") as f:
        f.write(cron_file_content)
    
    print(f"Cron file created at: {cron_file_path}")
    print(f"Cron command: {cron_command}")
    
    # Install the cron job
    try:
        result = subprocess.run(
            ["crontab", str(cron_file_path)],
            capture_output=True,
            text=True,
            check=True
        )
        print("Cron job installed successfully!")
        print("Current cron jobs:")
        subprocess.run(["crontab", "-l"], check=True)
        
    except subprocess.CalledProcessError as e:
        print(f"Error installing cron job: {e}")
        print(f"Stdout: {e.stdout}")
        print(f"Stderr: {e.stderr}")
        return False
    
    return True

def setup_python_cron(email_address, script_path, schedule_minutes=5):
    """Set up a Python-based cron job using schedule library."""
    
    try:
        # Install schedule library if not available
        subprocess.run([sys.executable, "-m", "pip", "install", "schedule"], check=True)
        
        # Create a Python cron script
        cron_script_content = f'''#!/usr/bin/env python
"""
Python-based cron job for Agent Inbox email ingestion.
This script runs the ingest script every {schedule_minutes} minutes.
"""

import schedule
import time
import subprocess
import sys
from pathlib import Path

def run_ingest():
    """Run the email ingest script."""
    script_path = Path("{script_path}")
    email = "{email_address}"
    
    try:
        print(f"Running ingest script at {{time.strftime('%Y-%m-%d %H:%M:%S')}}")
        result = subprocess.run([
            "uv", "run", "python", str(script_path),
            "--email", email,
            "--minutes-since", "{schedule_minutes}"
        ], capture_output=True, text=True, check=True)
        
        print("Ingest completed successfully")
        if result.stdout:
            print("Output:", result.stdout)
            
    except subprocess.CalledProcessError as e:
        print(f"Error running ingest script: {{e}}")
        if e.stdout:
            print("Stdout:", e.stdout)
        if e.stderr:
            print("Stderr:", e.stderr)
    except Exception as e:
        print(f"Unexpected error: {{e}}")

def main():
    """Main function to run the cron job."""
    print("Starting Agent Inbox email ingestion cron job...")
    print(f"Will run every {schedule_minutes} minutes")
    print(f"Email address: {{email_address}}")
    print(f"Script path: {{script_path}}")
    
    # Schedule the job
    schedule.every({schedule_minutes}).minutes.do(run_ingest)
    
    # Run immediately on startup
    run_ingest()
    
    # Keep running
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

if __name__ == "__main__":
    main()
'''
        
        # Write the cron script
        cron_script_path = Path.home() / "agentinbox_cron.py"
        with open(cron_script_path, "w") as f:
            f.write(cron_script_content)
        
        # Make it executable
        cron_script_path.chmod(0o755)
        
        print(f"Python cron script created at: {cron_script_path}")
        print("To start the cron job, run:")
        print(f"  python {cron_script_path}")
        print("\nOr to run it in the background:")
        print(f"  nohup python {cron_script_path} > cron.log 2>&1 &")
        
        return True
        
    except Exception as e:
        print(f"Error creating Python cron script: {e}")
        return False

def main():
    """Main function to set up cron job."""
    parser = argparse.ArgumentParser(description="Setup cron job for Agent Inbox email ingestion")
    
    parser.add_argument(
        "--email",
        type=str,
        required=True,
        help="Email address to monitor for new emails"
    )
    
    parser.add_argument(
        "--script-path",
        type=str,
        default="run_ingest_agentinbox.py",
        help="Path to the ingest script"
    )
    
    parser.add_argument(
        "--schedule",
        type=str,
        default="*/5",
        help="Cron schedule in minutes (e.g., '*/5' for every 5 minutes)"
    )
    
    parser.add_argument(
        "--method",
        type=str,
        choices=["system", "python"],
        default="python",
        help="Method to use for cron job (system or python)"
    )
    
    args = parser.parse_args()
    
    # Convert schedule to cron format
    if args.method == "system":
        cron_schedule = f"*/{args.schedule} * * * *"
        success = setup_system_cron(args.email, args.script_path, cron_schedule)
    else:
        schedule_minutes = int(args.schedule.replace("*/", ""))
        success = setup_python_cron(args.email, args.script_path, schedule_minutes)
    
    if success:
        print("\n✅ Cron job setup completed successfully!")
        print("\nNext steps:")
        print("1. Make sure your Gmail credentials are properly configured")
        print("2. Set the AGENT_INBOX_API_KEY environment variable")
        print("3. Test the ingest script manually first:")
        print(f"   uv run python {args.script_path} --email {args.email} --early")
        print("4. Start the cron job to run automatically")
    else:
        print("\n❌ Cron job setup failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()

