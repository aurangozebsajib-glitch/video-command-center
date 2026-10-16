import os
from camoufox.sync_api import Camoufox

def create_hf_account():
    profile_dir = os.path.expanduser("~/.camoufox-hf-profile")
    os.makedirs(profile_dir, exist_ok=True)

    print(f"Using persistent profile: {profile_dir}")

    with Camoufox(
        headless=False,
        persistent_context=True,
        user_data_dir=profile_dir,
    ) as driver:
        # Open HF join page in first tab
        driver.get("https://huggingface.co/join")

        # Open Gmail in second tab
        driver.execute_script("window.open('https://mail.google.com','_blank');")

        print("\n" + "="*60)
        print("BROWSER OPENED WITH 2 TABS:")
        print("Tab 0: HuggingFace Join - https://huggingface.co/join")
        print("Tab 1: Gmail - https://mail.google.com")
        print("="*60)
        print("\nINSTRUCTIONS:")
        print("1. In Tab 0 (HF), enter username, email, password, click Sign Up")
        print("2. Switch to Tab 1 (Gmail) to get verification code")
        print("3. Copy code and paste back in HF tab")
        print("4. After verified, you are logged in forever in this profile")
        print("\nKeeping browser open... Complete the signup manually.")
        input("\nPress Enter AFTER you finish creating HF account to close browser...")

        print("Profile saved! Future runs will be auto-logged in.")

if __name__=="__main__":
    create_hf_account()