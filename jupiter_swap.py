#!/usr/bin/env python3
"""
Jupiter Swap Integration for Solana
This module provides a simple interface to perform token swaps using Jupiter on Solana
"""
import os
import json
import time
import base64
import requests
from typing import Dict, Any, Optional, Union, List
from solana.rpc.api import Client as SolanaClient
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.transaction import Transaction

class JupiterSwap:
    """Jupiter swap integration for Solana"""
    
    JUPITER_API_BASE = "https://quote-api.jup.ag/v6"
    
    def __init__(self, client: SolanaClient, keypair: Keypair):
        """
        Initialize Jupiter Swap with a Solana client and keypair
        
        Args:
            client: SolanaClient instance
            keypair: Keypair for signing transactions
        """
        self.client = client
        self.keypair = keypair
        self.pubkey = keypair.pubkey()
    
    def get_tokens(self) -> List[Dict[str, Any]]:
        """
        Get list of supported tokens on Jupiter
        
        Returns:
            List of token information dictionaries
        """
        try:
            response = requests.get(f"{self.JUPITER_API_BASE}/tokens")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error getting tokens: {e}")
            return []
    
    def get_quote(
        self,
        input_mint: str,
        output_mint: str,
        amount: int,
        slippage_bps: int = 50  # 0.5% slippage by default
    ) -> Dict[str, Any]:
        """
        Get a quote for swapping tokens
        
        Args:
            input_mint: Input token mint address
            output_mint: Output token mint address
            amount: Amount of input tokens (in smallest units)
            slippage_bps: Slippage tolerance in basis points (1% = 100)
            
        Returns:
            Quote information
        """
        try:
            params = {
                "inputMint": input_mint,
                "outputMint": output_mint,
                "amount": str(amount),
                "slippageBps": slippage_bps
            }
            
            response = requests.get(f"{self.JUPITER_API_BASE}/quote", params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error getting quote: {e}")
            return {"error": str(e)}
    
    def swap(
        self,
        input_mint: str,
        output_mint: str,
        amount: int,
        slippage_bps: int = 50
    ) -> Dict[str, Any]:
        """
        Swap tokens using Jupiter
        
        Args:
            input_mint: Input token mint address
            output_mint: Output token mint address
            amount: Amount of input tokens (in smallest units)
            slippage_bps: Slippage tolerance in basis points (1% = 100)
            
        Returns:
            Dictionary with transaction result
        """
        try:
            # 1. Get quote
            quote = self.get_quote(input_mint, output_mint, amount, slippage_bps)
            if "error" in quote:
                return quote
                
            # 2. Get transaction data
            swap_data = {
                "quoteResponse": quote,
                "userPublicKey": str(self.pubkey),
                "wrapUnwrapSOL": True
            }
            
            response = requests.post(
                f"{self.JUPITER_API_BASE}/swap",
                json=swap_data
            )
            response.raise_for_status()
            swap_response = response.json()
            
            # 3. Submit transaction
            tx_data = swap_response.get('swapTransaction')
            if not tx_data:
                return {"error": "No swap transaction in response"}
                
            # 4. Decode and sign transaction
            tx_bytes = base64.b64decode(tx_data)
            transaction = Transaction.deserialize(tx_bytes)
            
            result = self.client.send_transaction(transaction, self.keypair)
            
            return {
                "status": "success",
                "signature": str(result.value) if result and hasattr(result, 'value') else None,
                "quote": quote
            }
        except Exception as e:
            print(f"Error executing swap: {e}")
            return {"error": str(e)}
    
    @staticmethod
    def get_token_info(tokens_list: List[Dict[str, Any]], symbol: str) -> Optional[Dict[str, Any]]:
        """Get token info by symbol from tokens list"""
        for token in tokens_list:
            if token.get('symbol', '').upper() == symbol.upper():
                return token
        return None

    def get_sol_equivalent(self, token_amount: float, token_symbol: str) -> Optional[float]:
        """Get SOL equivalent value of token amount"""
        try:
            tokens = self.get_tokens()
            token = self.get_token_info(tokens, token_symbol)
            sol_token = self.get_token_info(tokens, "SOL")
            
            if not token or not sol_token:
                return None
                
            # Get quote for token -> SOL
            decimals = token.get('decimals', 9)
            amount_in_smallest_units = int(token_amount * (10 ** decimals))
            
            quote = self.get_quote(
                token['address'], 
                sol_token['address'],
                amount_in_smallest_units
            )
            
            if "error" in quote:
                return None
                
            out_amount = int(quote.get('outAmount', 0))
            sol_value = out_amount / (10 ** 9)  # SOL has 9 decimals
            
            return sol_value
        except Exception as e:
            print(f"Error getting SOL equivalent: {e}")
            return None
