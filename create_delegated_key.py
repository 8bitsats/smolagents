#!/usr/bin/env python3
"""
Create a delegated key for Solana using Crossmint API
"""
import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
api_key = os.getenv("CROSSMINT_API_KEY")
wallet_locator = os.getenv("CROSSMINT_WALLET_USERID")
signer_public_key = input("Enter the signer public key (from generateKey.py): ")

# Set expiration time (1 year from now in milliseconds)
import time
expires_at = int((time.time() + 365 * 24 * 60 * 60) * 1000)

def create_delegated_key():
    """Create a delegated key using Crossmint API"""
    
    url = f"https://api.crossmint.com/2022-06-09/wallets/{wallet_locator}/signers"
    
    headers = {
        "Content-Type": "application/json",
        "X-API-KEY": api_key
    }
    
    # Define permissions for token swapping and transfers
    permissions = [
        {
            "type": "native-token-transfer",
            "data": {
                "allowance": "1000000000"  # 1 SOL limit
            }
        },
        {
            "type": "call-limit",
            "data": {
                "count": 100  # Limit to 100 calls
            }
        }
    ]
    
    payload = {
        "chain": "solana",
        "signer": f"solana-keypair:{signer_public_key}",
        "expiresAt": expires_at,
        "permissions": permissions
    }
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        result = response.json()
        print("Delegated key created successfully!")
        print(json.dumps(result, indent=2))
        return result
    except requests.exceptions.RequestException as e:
        print(f"Error creating delegated key: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Response: {e.response.text}")
        return None

if __name__ == "__main__":
    if not api_key:
        print("Error: CROSSMINT_API_KEY environment variable not set")
    elif not wallet_locator:
        print("Error: CROSSMINT_WALLET_USERID environment variable not set")
    else:
        create_delegated_key()
