import os, json, time, requests, re
from pathlib import Path
from camoufox.sync_api import Camoufox

PROFILE = os.path.expanduser("~/.camoufox-hf-profile")
MAP_FILE = Path("jobs/hf_tool_map.json")
SCREEN_DIR = Path("/tmp/hf_screenshots")
SCREEN_DIR.mkdir(exist_ok=True)

TRENDING = "https://huggingface.co/models?pipeline_tag=text-to-video&sort=trending"


def ask_qwen_with_screenshot(context, screenshot_path, hf_url):
    print(f"\n=== Asking Qwen with screenshot {screenshot_path} for {hf_url} ===")
    page = context.new_page()
    page.goto("https://www.qwen.com/", timeout=90000)
    page.wait_for_timeout(8000)

    if page.locator("text=Log in").count() > 0 and page.locator("text=Qwen3.7-Plus").count() == 0:
        print("Qwen not logged in! Please login on www.qwen.com")
        input("Login manually and press Enter...")

    try:
        page.evaluate("""
        ()=>{
            document.querySelectorAll('input[type=file]').forEach(el=>{
                el.style.display='block';
                el.style.visibility='visible';
                el.style.opacity='1';
                el.style.position='fixed';
                el.style.left='0px';
                el.style.top='0px';
                el.style.width='100px';
                el.style.height='100px';
                el.style.zIndex='9999';
            });
            const attachBtns = [...document.querySelectorAll('button')].filter(b=>b.innerHTML.includes('plus') || b.getAttribute('aria-label')?.toLowerCase().includes('attach') || b.innerText.includes('+'));
            console.log('Attach buttons', attachBtns.length);
        }
        """)

        page.wait_for_timeout(1000)

        qwen_file_input = page.locator("input[type=file]").first
        print(f"Qwen file input count: {page.locator('input[type=file]').count()}")

        if qwen_file_input.count() > 0:
            try:
                qwen_file_input.set_input_files(str(screenshot_path))
                print(f"Uploaded {screenshot_path} to Qwen")
                page.wait_for_timeout(5000)
                if page.locator("img").count() > 0:
                    print("Qwen image preview appeared")
            except Exception as e:
                print(f"Qwen upload fail {e}")
                for inp in page.locator("input[type=file]").all():
                    try:
                        inp.set_input_files(str(screenshot_path))
                        print("Fallback upload OK")
                        break
                    except:
                        pass
        else:
            print("No file input found in Qwen, trying paste via JS")
            page.evaluate("""
            async () => {
                const input = document.querySelector('textarea');
                input.focus();
                console.log('Focused textarea');
            }
            """)

        question = f"""Analyze this HuggingFace Space screenshot: {hf_url}
Where is upload? Where is Generate button? Return ONLY JSON:
{{"upload_area":"Drop Image Here","generate_button":"Generate","type":"img2vid","steps":["upload image","click Generate"]}}"""

        ta = page.locator("textarea").first
        if ta.count() > 0:
            ta.click()
            ta.fill(question)
            page.wait_for_timeout(1000)
            ta.press("Enter")
            print("Sent question to Qwen")
            page.wait_for_timeout(20000)

            body = page.locator("body").inner_text()
            print(f"Qwen body last 1500: {body[-1500:]}")
            m = re.search(r'\{.*\}', body, re.DOTALL)
            if m:
                try:
                    parsed = json.loads(m.group(0))
                    page.close()
                    return parsed
                except:
                    pass
            page.close()
            return {"upload_area": "Drop Image Here", "generate_button": "Generate", "type": "img2vid", "raw": body[-500:]}
    except Exception as e:
        print(f"Qwen ask fail {e}")
        try: page.close()
        except: pass
        return None


def learn_space(context, space_url):
    print(f"\n\n{'='*60}\nLEARNING SPACE: {space_url}\n{'='*60}")
    page = context.new_page()
    page.goto(space_url, timeout=90000)
    page.wait_for_timeout(8000)
    if page.locator("text=404").count() > 0 or page.locator("text=Sorry, we can't find").count() > 0:
        print(f"SKIP 404 {space_url}")
        return {"url": space_url, "working": False, "error": "404", "learned_at": int(time.time())}
    page.wait_for_timeout(4000)

    screenshot_path = SCREEN_DIR / f"{space_url.split('/')[-1]}_{int(time.time())}.png"
    page.screenshot(path=str(screenshot_path))
    print(f"Screenshot saved: {screenshot_path}")

    analysis = ask_qwen_with_screenshot(context, screenshot_path, space_url)

    if not analysis:
        print("Qwen analysis failed, using fallback")
        analysis = {"upload_area": "Drop Image Here", "generate_button": "Generate", "type": "img2vid", "steps": ["upload", "generate"]}

    test_image = "/tmp/test_learn.png"
    if not Path(test_image).exists():
        r = requests.get("https://image.pollinations.ai/prompt/cinematic%20cat%20close%20up?width=512&height=512", timeout=20)
        open(test_image, 'wb').write(r.content)

    try:
        page.evaluate("()=>{document.querySelectorAll('input[type=file]').forEach(el=>{el.style.display='block'; el.style.visibility='visible'; el.style.opacity='1';})}")
        page.wait_for_timeout(2000)

        inputs = page.locator("input[type=file]").all()
        if len(inputs) == 0:
            for frame in page.frames:
                try:
                    if frame.locator("input[type=file]").count() > 0:
                        print(f"Found file input in frame {frame.url}")
                        page = frame
                        inputs = frame.locator("input[type=file]").all()
                        break
                except:
                    pass

        print(f"Found {len(inputs)} file inputs to try")
        uploaded = False
        for inp in inputs:
            try:
                inp.set_input_files(test_image)
                uploaded = True
                print("Upload success!")
                break
            except Exception as e:
                print(f"Upload try fail {e}")

        if not uploaded:
            try:
                drop = page.locator(f"text={analysis.get('upload_area', 'Drop Image Here')}").first
                if drop.count() > 0:
                    drop.click()
                    page.wait_for_timeout(1000)
                    page.evaluate("()=>{document.querySelectorAll('input[type=file]').forEach(el=>{el.style.display='block'})}")
                    inputs = page.locator("input[type=file]").all()
                    if inputs:
                        inputs[0].set_input_files(test_image)
                        uploaded = True
            except Exception as e:
                print(f"Drop click fail {e}")

        page.wait_for_timeout(5000)
        has_image = page.locator("img").count() > 2
        print(f"Image uploaded? {has_image}, uploaded flag {uploaded}")

        gen_text = analysis.get("generate_button", "Generate")
        gen_btn = page.locator(f"button:has-text('{gen_text}')").first
        if gen_btn.count() == 0:
            gen_btn = page.locator("button:has-text('Generate')").first
        if gen_btn.count() == 0:
            gen_btn = page.locator("button:has-text('Run')").first

        if gen_btn.count() > 0:
            gen_btn.scroll_into_view_if_needed()
            gen_btn.click()
            print(f"Clicked Generate button: {gen_text}")
            for i in range(30):
                page.wait_for_timeout(5000)
                if page.locator("video").count() > 0:
                    print(f"SUCCESS! Video generated in {space_url}")
                    page.close()
                    return {
                        "url": space_url,
                        "type": analysis.get("type", "img2vid"),
                        "upload_selector": "input[type=file]",
                        "generate_selector": f"button:has-text('{gen_text}')",
                        "qwen_analysis": analysis,
                        "working": True,
                        "learned_at": int(time.time())
                    }
                print(f"Waiting video {i*5}s...")
            print(f"No video after 150s for {space_url}")
        else:
            print(f"No Generate button found for {space_url}")

        page.close()
        return {
            "url": space_url,
            "type": analysis.get("type", "img2vid"),
            "qwen_analysis": analysis,
            "working": False,
            "learned_at": int(time.time())
        }

    except Exception as e:
        print(f"Learn error {space_url}: {e}")
        try: page.close()
        except: pass
        return {"url": space_url, "error": str(e), "working": False}


def run_self_learning():
    trending_spaces = [
        "https://huggingface.co/spaces/mediasynthesismuseum/stable-video-diffusion",
        "https://huggingface.co/spaces/Wan-AI/Wan2.1-I2V-14B-720P",
        "https://huggingface.co/spaces/THUDM/CogVideoX-5B",
        "https://huggingface.co/spaces/huggingface-projects/AnimateDiff",
        "https://huggingface.co/spaces/damo-vilab/modelscope-text-to-video-synthesis",
    ]

    try:
        with Camoufox(persistent_context=True, user_data_dir=PROFILE, headless=False) as ctx:
            p = ctx.new_page()
            p.goto(TRENDING, timeout=60000)
            p.wait_for_timeout(8000)
            links = p.evaluate("()=>{return [...document.querySelectorAll('a')].map(a=>a.href).filter(h=>h.includes('/spaces/')).slice(0,15)}")
            print(f"Trending spaces: {links}")
            p.close()
            for l in links:
                if l not in trending_spaces:
                    trending_spaces.append(l)

            learned = []
            if MAP_FILE.exists():
                try:
                    learned = json.loads(MAP_FILE.read_text())
                except:
                    learned = []

            for space_url in trending_spaces[:6]:
                result = learn_space(ctx, space_url)
                learned.append(result)
                MAP_FILE.parent.mkdir(parents=True, exist_ok=True)
                MAP_FILE.write_text(json.dumps(learned, indent=2))
                print(f"\nSaved progress to {MAP_FILE}")
                time.sleep(3)

            print(f"\n\n=== SELF LEARNING COMPLETE ===")
            print(f"Learned {len([x for x in learned if x.get('working')])} working tools out of {len(learned)}")
            print(json.dumps(learned, indent=2))
            input("Done. Press Enter...")
    except Exception as e:
        print(f"Self learning failed: {e}")


if __name__ == "__main__":
    run_self_learning()
