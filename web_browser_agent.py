from io import BytesIO
from time import sleep
import os
import json
import asyncio
import sys
import base64
import requests

import helium
from solana.rpc.api import Client as SolanaClient
from solders.keypair import Keypair
from dotenv import load_dotenv
from PIL import Image
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from smolagents import CodeAgent, tool, OpenAIServerModel
from smolagents.agents import ActionStep

# Load environment variables
load_dotenv()

# Add the project directory to Python path to import our custom modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import Jupiter swap integration
from jupiter_swap import JupiterSwap

# Custom Solana Wallet class implementation
class SolanaWallet:
    def __init__(self, client, keypair):
        self.client = client
        self.keypair = keypair
        self.pubkey = keypair.pubkey()
    
    def get_balance(self):
        """Get the SOL balance for this wallet"""
        try:
            response = self.client.get_balance(self.pubkey)
            if response and hasattr(response, 'value'):
                # Convert from lamports (10^-9 SOL) to SOL
                return response.value / 1_000_000_000
            return 0
        except Exception as e:
            print(f"Error getting balance: {e}")
            return 0
            
    def send_sol(self, recipient_address, amount_sol):
        """Send SOL to a recipient address"""
        from solana.transaction import Transaction
        from solana import system_program
        import base58
        
        try:
            # Create a transfer instruction
            transfer_instruction = system_program.transfer(
                system_program.TransferParams(
                    from_pubkey=self.pubkey,
                    to_pubkey=recipient_address,
                    lamports=int(amount_sol * 1_000_000_000)
                )
            )
            
            # Create and sign transaction
            transaction = Transaction().add(transfer_instruction)
            response = self.client.send_transaction(
                transaction, self.keypair
            )
            return response
        except Exception as e:
            print(f"Error sending SOL: {e}")
            return None

# Initialize Solana client and wallet
try:
    solana_client = SolanaClient("https://mainnet.helius-rpc.com/?api-key=c55c146c-71ef-41b9-a574-cb08f359c00c")
    wallet_path = os.path.expanduser("~/.config/solana/privy-wallet.json")
    if os.path.exists(wallet_path):
        with open(wallet_path, 'r') as f:
            keypair_data = json.loads(f.read())
            keypair = Keypair.from_bytes(bytes(keypair_data))
            solana_wallet = SolanaWallet(solana_client, keypair)
            print(f"Wallet initialized: {solana_wallet.pubkey}")
    else:
        print(f"Wallet file not found at {wallet_path}")
        solana_wallet = None
except Exception as e:
    print(f"Error initializing Solana wallet: {e}")
    solana_wallet = None

@tool
def search_item_ctrl_f(text: str, nth_result: int = 1) -> str:
    """
    Searches for text on the current page via Ctrl + F and jumps to the nth occurrence.
    Args:
        text: The text to search for
        nth_result: Which occurrence to jump to (default: 1)
    """
    elements = driver.find_elements(By.XPATH, f"//*[contains(text(), '{text}')]")
    if nth_result > len(elements):
        raise Exception(f"Match n°{nth_result} not found (only {len(elements)} matches found)")
    result = f"Found {len(elements)} matches for '{text}'."
    elem = elements[nth_result - 1]
    driver.execute_script("arguments[0].scrollIntoView(true);", elem)
    result += f"Focused on element {nth_result} of {len(elements)}"
    return result

@tool
def go_back() -> None:
    """Goes back to previous page."""
    driver.back()

@tool
def close_popups() -> str:
    """
    Closes any visible modal or pop-up on the page. Use this to dismiss pop-up windows!
    This does not work on cookie consent banners.
    """
    webdriver.ActionChains(driver).send_keys(Keys.ESCAPE).perform()
    return "Popups closed"

@tool
def extract_token_data_from_letsbonk() -> list:
    """
    Extracts token data from letsbonk.fun by parsing the text content of each token card. Returns a list of dicts with name, contract_address, market_cap, and time_posted.
    """
    helium.go_to('https://letsbonk.fun')
    sleep(2)
    driver = helium.get_driver()
    token_cards = driver.find_elements(By.CSS_SELECTOR, '.grid-cols-1 > div')
    if not token_cards:
        token_cards = driver.find_elements(By.CSS_SELECTOR, '[class*="grid"] > div')
    print(f"Found {len(token_cards)} token cards")
    for _ in range(3):
        helium.scroll_down(num_pixels=800)
        sleep(1)
    tokens = []
    for card in token_cards:
        try:
            text = card.text
            # Split lines and try to extract fields
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            name = None
            contract_address = None
            market_cap = None
            time_posted = None
            for line in lines:
                if line.startswith('CA:'):
                    contract_address = line
                elif line.startswith('Market Cap:'):
                    market_cap = line
                elif 'ago' in line:
                    time_posted = line
                elif not name:
                    name = line
            tokens.append({
                'name': name,
                'contract_address': contract_address,
                'market_cap': market_cap,
                'time_posted': time_posted
            })
        except Exception as e:
            print(f"Error parsing card: {e}")
    return tokens

# Configure Chrome options
chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument("--force-device-scale-factor=1")
chrome_options.add_argument("--window-size=1000,1350")
chrome_options.add_argument("--disable-pdf-viewer")
chrome_options.add_argument("--window-position=0,0")

# Initialize the browser
driver = helium.start_chrome(headless=False, options=chrome_options)

# Set up screenshot callback
def save_screenshot(memory_step: ActionStep, agent: CodeAgent) -> None:
    sleep(1.0)  # Let JavaScript animations happen before taking the screenshot
    driver = helium.get_driver()
    current_step = memory_step.step_number
    if driver is not None:
        for previous_memory_step in agent.memory.steps:  # Remove previous screenshots for lean processing
            if isinstance(previous_memory_step, ActionStep) and previous_memory_step.step_number <= current_step - 2:
                previous_memory_step.observations_images = None
        png_bytes = driver.get_screenshot_as_png()
        image = Image.open(BytesIO(png_bytes))
        print(f"Captured a browser screenshot: {image.size} pixels")
        memory_step.observations_images = [image.copy()]  # Create a copy to ensure it persists

    # Update observations with current URL
    url_info = f"Current url: {driver.current_url}"
    memory_step.observations = (
        url_info if memory_step.observations is None else memory_step.observations + "\n" + url_info
    )

# Initialize the model
model = OpenAIServerModel(
    model_id="gpt-4o",
    api_key=os.environ["OPENAI_API_KEY"]
)

# Initialize Jupiter swap if wallet is available
jupiter_swap = None
if solana_wallet:
    try:
        jupiter_swap = JupiterSwap(solana_client, solana_wallet.keypair)
        print("Jupiter swap integration initialized successfully!")
    except Exception as e:
        print(f"Error initializing Jupiter swap: {e}")
        jupiter_swap = None

# Wallet tool implementations
@tool
def check_wallet_balance() -> str:
    """Check the SOL and token balances of the connected wallet"""
    if solana_wallet is None:
        return "Wallet is not initialized"
    
    # Get SOL balance
    balance = solana_wallet.get_balance()
    return f"Wallet balance: {balance} SOL"

@tool
def send_token(recipient_address: str, amount: float, token_type: str = "SOL") -> str:
    """Send tokens to a recipient address"""
    if solana_wallet is None:
        return "Wallet is not initialized"
    
    if token_type != "SOL":
        return "Only SOL transfers are supported at this time"
    
    response = solana_wallet.send_sol(recipient_address, amount)
    if response:
        return f"Sent {amount} SOL to {recipient_address}. Response: {response}"
    else:
        return f"Failed to send {amount} SOL to {recipient_address}"

@tool
def get_token_list() -> dict:
    """
    Get list of available tokens for swapping on Jupiter
    """
    if not jupiter_swap:
        return {"error": "Jupiter swap not initialized"}
    
    try:
        tokens = jupiter_swap.get_tokens()
        # Return a subset of the most common tokens to avoid overwhelming response
        common_tokens = []
        popular_symbols = ["SOL", "USDC", "BONK", "JUP", "RAY", "MNGO", "ORCA"]
        
        for symbol in popular_symbols:
            token = jupiter_swap.get_token_info(tokens, symbol)
            if token:
                common_tokens.append({
                    "symbol": token.get("symbol"),
                    "name": token.get("name"),
                    "address": token.get("address"),
                    "decimals": token.get("decimals")
                })
        
        return {
            "available_tokens": common_tokens,
            "total_tokens_available": len(tokens)
        }
    except Exception as e:
        return {"error": f"Failed to get token list: {str(e)}"}

@tool
def get_token_quote(input_token: str, output_token: str, amount: float) -> dict:
    """
    Get a price quote for swapping tokens using Jupiter
    Args:
        input_token: Symbol of input token (e.g., "SOL", "USDC")
        output_token: Symbol of output token (e.g., "BONK", "JUP")
        amount: Amount of input token to swap
    """
    if not jupiter_swap:
        return {"error": "Jupiter swap not initialized"}
    
    try:
        # Get tokens info
        tokens = jupiter_swap.get_tokens()
        input_token_info = jupiter_swap.get_token_info(tokens, input_token)
        output_token_info = jupiter_swap.get_token_info(tokens, output_token)
        
        if not input_token_info:
            return {"error": f"Input token {input_token} not found"}
        
        if not output_token_info:
            return {"error": f"Output token {output_token} not found"}
        
        # Calculate amount in lamports/smallest unit
        decimals = input_token_info.get("decimals", 9)
        amount_in_smallest_units = int(amount * (10 ** decimals))
        
        # Get quote
        quote = jupiter_swap.get_quote(
            input_token_info["address"],
            output_token_info["address"],
            amount_in_smallest_units
        )
        
        if "error" in quote:
            return quote
        
        # Format the response to be more readable
        out_amount = int(quote.get("outAmount", 0))
        out_decimals = output_token_info.get("decimals", 9)
        human_out_amount = out_amount / (10 ** out_decimals)
        
        return {
            "input": f"{amount} {input_token}",
            "output": f"{human_out_amount} {output_token}",
            "price": f"1 {input_token} = {human_out_amount/amount} {output_token}",
            "slippage": f"{quote.get('priceImpactPct', 0) * 100:.2f}%"
        }
    except Exception as e:
        return {"error": f"Failed to get quote: {str(e)}"}

@tool
def swap_tokens(input_token: str, output_token: str, amount: float) -> dict:
    """
    Swap tokens using Jupiter
    Args:
        input_token: Symbol of input token (e.g., "SOL", "USDC")
        output_token: Symbol of output token (e.g., "BONK", "JUP")
        amount: Amount of input token to swap
    """
    if not jupiter_swap:
        return {"error": "Jupiter swap not initialized"}
    
    try:
        # Get tokens info
        tokens = jupiter_swap.get_tokens()
        input_token_info = jupiter_swap.get_token_info(tokens, input_token)
        output_token_info = jupiter_swap.get_token_info(tokens, output_token)
        
        if not input_token_info:
            return {"error": f"Input token {input_token} not found"}
        
        if not output_token_info:
            return {"error": f"Output token {output_token} not found"}
        
        # Calculate amount in lamports/smallest unit
        decimals = input_token_info.get("decimals", 9)
        amount_in_smallest_units = int(amount * (10 ** decimals))
        
        # Execute swap
        result = jupiter_swap.swap(
            input_token_info["address"],
            output_token_info["address"],
            amount_in_smallest_units
        )
        
        if "error" in result:
            return result
            
        # Get updated balance after swap
        try:
            new_balance = solana_wallet.get_balance()
            result["new_sol_balance"] = new_balance
        except:
            pass
            
        return result
    except Exception as e:
        return {"error": f"Swap failed: {str(e)}"}

# Create the agent
agent = CodeAgent(
    tools=[go_back, close_popups, search_item_ctrl_f, extract_token_data_from_letsbonk, 
           check_wallet_balance, send_token, get_token_list, get_token_quote, swap_tokens],
    model=model,
    additional_authorized_imports=["helium"],
    step_callbacks=[save_screenshot],
    max_steps=20,
    verbosity_level=2,
)

# Import helium for the agent
agent.python_executor("from helium import *")

# Helium instructions for the agent
helium_instructions = """
You can use helium to access websites. Don't bother about the helium driver, it's already managed.
We've already ran "from helium import *"
Then you can go to pages!
Code:
```py
go_to('github.com/trending')
```<end_code>

You can directly click clickable elements by inputting the text that appears on them.
Code:
```py
click("Top products")
```<end_code>

If it's a link:
Code:
```py
click(Link("Top products"))
```<end_code>

If you try to interact with an element and it's not found, you'll get a LookupError.
In general stop your action after each button click to see what happens on your screenshot.
Never try to login in a page.

To scroll up or down, use scroll_down or scroll_up with as an argument the number of pixels to scroll from.
Code:
```py
scroll_down(num_pixels=1200) # This will scroll one viewport down
```<end_code>

When you have pop-ups with a cross icon to close, don't try to click the close icon by finding its element or targeting an 'X' element (this most often fails).
Just use your built-in tool `close_popups` to close them:
Code:
```py
close_popups()
```<end_code>

You can use .exists() to check for the existence of an element. For example:
Code:
```py
if Text('Accept cookies?').exists():
    click('I accept')
```<end_code>

To type text in input fields, use write() function:
Code:
```py
write("your text here")
```<end_code>

To press Enter key, use press(ENTER):
Code:
```py
press(ENTER)
```<end_code>
"""

def run_letsbonk_fun_tokens():
    search_request = """
    Please navigate to https://letsbonk.fun and find 25 tokens. List them in the order you would buy the tokens in, including their name, their price, and their contract address on Solana. Output a list of these tokens with all requested details.
    """
    agent_output = agent.run(search_request + helium_instructions)
    print("Final output:")
    print(agent_output)

def run_github_trending():
    github_request = """
    I'm trying to find how hard I have to work to get a repo in github.com/trending.
    Can you navigate to the profile for the top author of the top trending repo, and give me their total number of commits over the last year?
    """
    agent_output = agent.run(github_request + helium_instructions)
    print("Final output:")
    print(agent_output)

def run_mcpweb3_voice_agent():
    """
    Navigate to about.mcpweb3.fun and interact with the voice agent
    """
    mcpweb3_request = """
    Please navigate to about.mcpweb3.fun and perform the following actions:
    1. Click the "initialize" button
    2. Wait for the page to load, then click the voice agent button on the bottom right
    3. When terms appear, click "accept" to accept the terms
    4. When a text input box pops up, type "what is solana?" and press Enter
    
    Let me know what response you get from the voice agent.
    """
    agent_output = agent.run(mcpweb3_request + helium_instructions)
    print("Final output:")
    print(agent_output)

# This version is removed to avoid duplication

# This version is removed to avoid duplication

def run_wallet_demo():
    """Run a demo of the wallet functionality"""
    if solana_wallet is None:
        print("Wallet not initialized. Cannot run demo.")
        return
    
    print("\n=== Wallet Demo ===\n")
    
    # Step 1: Check balance
    balance_result = check_wallet_balance()
    print(f"Balance check: {balance_result}")
    
    # Step 2: Show available tokens for swapping
    if jupiter_swap:
        print("\n--- Available Tokens for Swapping ---")
        tokens_result = get_token_list()
        if "error" not in tokens_result:
            for token in tokens_result.get("available_tokens", []):
                print(f"- {token['symbol']}: {token['name']} ({token['address']})")
        
        # Step 3: Get a quote for SOL to BONK (without executing)
        print("\n--- Sample Quote: SOL to BONK ---")
        quote_result = get_token_quote("SOL", "BONK", 0.01)
        print(f"Quote: {quote_result}")
    
    print("\n=== Demo Complete ===\n")


if __name__ == "__main__":
    # Print wallet status
    if solana_wallet:
        print("Solana wallet initialized successfully!")
        try:
            balance = solana_wallet.get_balance()
            print(f"Wallet SOL balance: {balance} SOL")
        except Exception as e:
            print(f"Error checking wallet balance: {e}")
    else:
        print("Failed to initialize Solana wallet.")
    
    # Set environment variable to determine which demo to run
    if os.environ.get("RUN_TYPE") == "WALLET_DEMO":
        # Run the wallet demo
        print("Running wallet demo")
        run_wallet_demo()
    elif os.environ.get("RUN_TYPE") == "BONK":
        # Run the BONK demo - if available
        if "run_bonk_agent" in globals():
            asyncio.run(run_bonk_agent())
        else:
            print("BONK agent functionality not available")
            run_wallet_demo()
    else:
        # Default to running wallet demo
        run_wallet_demo()