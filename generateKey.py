#!/usr/bin/env python3
"""
Generate a Solana keypair for use as a delegated signer
"""
from solders.keypair import Keypair

# Generate a new keypair
agent_keypair = Keypair()
agent_public_key = str(agent_keypair.pubkey())
agent_private_key = agent_keypair.secret().hex()

print(f"Public Key: {agent_public_key}")
print(f"Private Key (secret): {agent_private_key}")
print("\n===== IMPORTANT: Save this private key securely =====")
print(f"Base58 representation (for SOLANA_DELEGATED_KEY): {agent_keypair.to_base58_string()}")
