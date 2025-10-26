#!/usr/bin/env python3
"""
Check OAuth redirect URI configuration
"""

import json
import os

def check_credentials():
    """Check credentials.json and env configuration."""
    print("=" * 60)
    print("OAuth Redirect URI Configuration Check")
    print("=" * 60)
    print()
    
    # Check credentials.json
    if os.path.exists('credentials.json'):
        print("✅ Found credentials.json")
        with open('credentials.json', 'r') as f:
            creds = json.load(f)
            
        if 'web' in creds:
            print(f"   Client ID: {creds['web'].get('client_id', 'Not found')}")
            print(f"   Project ID: {creds['web'].get('project_id', 'Not found')}")
            
            if 'redirect_uris' in creds['web']:
                print("   Registered Redirect URIs:")
                for uri in creds['web']['redirect_uris']:
                    print(f"      - {uri}")
            else:
                print("   ⚠️  No redirect_uris found in credentials.json")
                print("      This is normal - URIs are configured in Google Cloud Console")
    else:
        print("❌ credentials.json not found")
    
    print()
    print("=" * 60)
    print("Required Configuration")
    print("=" * 60)
    print()
    print("Your app expects this redirect URI:")
    print("   http://localhost:8000/auth/callback")
    print()
    print("To fix the error:")
    print("1. Go to: https://console.cloud.google.com/apis/credentials")
    print("2. Click on your OAuth 2.0 Client ID")
    print("3. Add this to 'Authorized redirect URIs':")
    print("   http://localhost:8000/auth/callback")
    print("4. Click SAVE")
    print()
    print("=" * 60)
    print()
    
    # Check if running on different port
    print("If you're running on a different port, update REDIRECT_URI in main.py")
    print("Example: If running on port 3000, change to:")
    print("   REDIRECT_URI = 'http://localhost:3000/auth/callback'")
    print()

if __name__ == '__main__':
    check_credentials()
