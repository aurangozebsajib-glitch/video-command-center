import json, sys, os
from camoufox.sync_api import Camoufox

def run_automation(site_name, category):
    # This is a generic runner shell. 
    # In a real scenario, this would load custom scripts from a mapping file.
    file_path = f"data/free_{category}_sites.json"
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found")
        return
    with open(file_path) as f:
        data = json.load(f)
    site = next((s for s in data if s["name"] == site_name), None)
    if not site:
        print(f"Site {site_name} not found in {category}")
        return
    
    print(f"Launching {site_name} at {site['url']}...")
    with Camoufox(headless=False) as driver:
        driver.get(site['url'])
        input("Press Enter to close browser...")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python camoufox_runner.py [site_name] [category]")
    else:
        run_automation(sys.argv[1], sys.argv[2])
