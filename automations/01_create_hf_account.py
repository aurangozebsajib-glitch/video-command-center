from camoufox.sync_api import Camoufox

def create_hf_account():
    with Camoufox(headless=False, persistent_context=True) as driver:
        # Open 2 tabs
        driver.get("https://huggingface.co/join")
        # Use driver.switch_to.new_tab() logic to open gmail second tab
        driver.execute_script("window.open('https://mail.google.com','_blank');")
        tabs = driver.window_handles
        # Tab 0 = HuggingFace join page, Tab 1 = Gmail
        print("INSTRUCTIONS FOR SAJIB:")
        print("1. In Tab 0 (HF), enter username, email, password and click Sign Up")
        print("2. Switch to Tab 1 (Gmail) to get verification code")
        print("3. Copy code and paste back in HF tab")
        print("4. After verified, login and keep profile saved in Camoufox persistent profile")
        print("Keeping browser open for manual creation...")
        input("Press Enter after you finish creating HF account...")

if __name__=="__main__":
    create_hf_account()