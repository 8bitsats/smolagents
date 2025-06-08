from io import BytesIO
from time import sleep
import os
import json
import csv

import helium
from dotenv import load_dotenv
from PIL import Image
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from smolagents import CodeAgent, tool, OpenAIServerModel
from smolagents.agents import ActionStep

# Load environment variables
load_dotenv()

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

# Create the agent
agent = CodeAgent(
    tools=[go_back, close_popups, search_item_ctrl_f, extract_token_data_from_letsbonk],
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

if __name__ == "__main__":
    # Example usage
    result = extract_token_data_from_letsbonk()
    print("Extracted token data:")
    for token in result:
        print(token)
    # Export to output directory
    output_dir = os.path.join(os.getcwd(), "output")
    os.makedirs(output_dir, exist_ok=True)
    # Write JSON
    json_path = os.path.join(output_dir, "letsbonk_tokens.json")
    with open(json_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"Exported JSON to {json_path}")
    # Write CSV
    csv_path = os.path.join(output_dir, "letsbonk_tokens.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "contract_address", "market_cap", "time_posted"])
        writer.writeheader()
        for row in result:
            writer.writerow(row)
    print(f"Exported CSV to {csv_path}")
    # run_github_trending()  # Uncomment to run the GitHub trending example 