#!/usr/bin/env python3
"""
Migration script to convert credentials.json and token.json to environment variables.
Run this once to migrate from file-based to environment-based configuration.
"""

import json
import os
from pathlib import Path

def read_json_file(filename):
    """Read and return JSON content from a file."""
    if not os.path.exists(filename):
        return None
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading {filename}: {e}")
        return None

def json_to_single_line(data):
    """Convert JSON dict to single-line string."""
    return json.dumps(data, separators=(',', ':'))

def main():
    print("=" * 80)
    print("GPlanner Migration Script")
    print("Converting credentials.json and token.json to environment variables")
    print("=" * 80)
    print()

    # Read existing files
    credentials = read_json_file('credentials.json')
    token = read_json_file('token.json')

    if not credentials and not token:
        print("❌ No credentials.json or token.json found.")
        print("   If you've already migrated, you can ignore this.")
        return

    # Prepare environment variables
    env_lines = []
    
    # Read existing env file
    if os.path.exists('env'):
        with open('env', 'r') as f:
            existing_lines = f.readlines()
            for line in existing_lines:
                # Keep lines that are not the ones we're updating
                if not any(key in line for key in [
                    'GOOGLE_APPLICATION_CREDENTIALS_JSON',
                    'GOOGLE_TOKEN_JSON'
                ]):
                    env_lines.append(line.rstrip())

    # Add credentials if found
    if credentials:
        print("✅ Found credentials.json")
        credentials_str = json_to_single_line(credentials)
        env_lines.append(f"GOOGLE_APPLICATION_CREDENTIALS_JSON={credentials_str}")
    else:
        print("⚠️  No credentials.json found")

    # Add token if found
    if token:
        print("✅ Found token.json")
        token_str = json_to_single_line(token)
        env_lines.append(f"GOOGLE_TOKEN_JSON={token_str}")
    else:
        print("⚠️  No token.json found (you'll need to authenticate again)")

    # Write updated env file
    if credentials or token:
        print()
        print("Writing to 'env' file...")
        with open('env', 'w') as f:
            f.write('\n'.join(env_lines) + '\n')
        print("✅ Environment file updated successfully!")
        
        print()
        print("=" * 80)
        print("Migration Complete!")
        print("=" * 80)
        print()
        print("You can now:")
        print("1. Delete credentials.json and token.json (they're no longer needed)")
        print("2. Restart your application")
        print("3. The app will now use environment variables from the 'env' file")
        print()
        print("To delete the old files, run:")
        print("  rm credentials.json token.json")
        print()
    else:
        print()
        print("No files to migrate. Your env file remains unchanged.")

if __name__ == '__main__':
    main()
