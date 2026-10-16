import json, time, os
from pathlib import Path
from camoufox.sync_api import Camoufox

PROFILE = os.path.expanduser("~/.camoufox-hf-profile")
MAP_FILE = Path("jobs/hf_tool_map.json")

TRENDING_URL = "https://huggingface.co/models?pipeline_tag=text-to-video&sort=trending"

def analyze_space_interface(page, space_url):
    print(f"\n=== ANALYZING {space_url} ===")
    page.goto(space_url, timeout=90000)
    page.wait_for_timeout(15000)

    frames = page.frames
    print(f"Found {len(frames)} frames")
    target = page
    for f in frames:
        try:
            if f.locator("text=Drop Image Here").count() > 0 or f.locator("input[type=file]").count() > 0 or "gradio" in f.url.lower():
                print(f"Using frame: {f.url}")
                target = f
                break
        except:
            pass

    js_scan = """
    () => {
        const results = {fileInputs:[], textareas:[], buttons:[], dropZones:[]};
        function deepQuery(selector, root=document){
            let els = [...root.querySelectorAll(selector)];
            root.querySelectorAll('*').forEach(el=>{
                if(el.shadowRoot){
                    els = els.concat(deepQuery(selector, el.shadowRoot));
                }
            });
            return els;
        }
        results.fileInputs = deepQuery('input[type=file]').map(el=>({
            html: el.outerHTML.slice(0,200),
            visible: el.offsetParent!==null,
            parentText: el.parentElement?.innerText?.slice(0,100)
        }));
        results.textareas = deepQuery('textarea').map(el=>({
            placeholder: el.placeholder,
            visible: el.offsetParent!==null,
            label: el.parentElement?.innerText?.slice(0,100)
        }));
        results.buttons = [...document.querySelectorAll('button')].map(b=>b.innerText).filter(t=>t.length<30);
        results.dropZones = [...document.querySelectorAll('*')].filter(el=>/Drop Image Here|Click to Upload|Drag and Drop/i.test(el.innerText)).map(el=>el.innerText.slice(0,100));
        return results;
    }
    """
    try:
        data = target.evaluate(js_scan)
    except Exception as e:
        print(f"JS scan fail {e}")
        data = {"fileInputs":[],"textareas":[],"buttons":[],"dropZones":[]}

    print(f"Scan result: {json.dumps(data, indent=2)[:1000]}")

    locators = {
        "file_input_selector": "input[type=file]",
        "drop_text_selector": "text=Drop Image Here",
        "click_upload_selector": "text=Click to Upload",
        "prompt_textarea_selector": "textarea",
        "generate_button_texts": [b for b in data.get("buttons",[]) if "generat" in b.lower() or "run" in b.lower() or "submit" in b.lower()],
        "all_buttons": data.get("buttons",[]),
        "raw_scan": data
    }

    interface_type = "unknown"
    if len(data.get("fileInputs",[]))>0 or len(data.get("dropZones",[]))>0:
        interface_type = "img2vid"
    elif len(data.get("textareas",[]))>0:
        interface_type = "text2vid"

    return {
        "url": space_url,
        "type": interface_type,
        "locators": locators,
        "working": True,
        "last_checked": int(time.time())
    }

def map_trending_tools():
    if MAP_FILE.exists():
        existing = json.loads(MAP_FILE.read_text())
    else:
        existing = []

    with Camoufox(persistent_context=True, user_data_dir=PROFILE, headless=False) as ctx:
        page = ctx.new_page()
        page.goto(TRENDING_URL, timeout=90000)
        page.wait_for_timeout(10000)
        print("Trending page loaded")

        links = page.evaluate("""
        () => {
            return [...document.querySelectorAll('a')].map(a=>a.href).filter(h=>h.includes('/spaces/') || h.includes('/models/')).slice(0,30)
        }
        """)
        print(f"Found {len(links)} links: {links[:10]}")

        spaces_to_check = [
            "https://huggingface.co/spaces/mediasynthesismuseum/stable-video-diffusion",
            "https://huggingface.co/spaces/stabilityai/stable-video-diffusion-img2vid-xt",
            "https://huggingface.co/spaces/Lightricks/LTX-Video",
            "https://huggingface.co/spaces/ali-vilab/i2vgen-xl",
            "https://huggingface.co/spaces/Wan-AI/Wan2.1-T2V-14B",
            "https://huggingface.co/spaces/Wan-AI/Wan2.2-TI2V-5B",
            "https://huggingface.co/spaces/THUDM/CogVideoX-5B",
        ] + [l for l in links if "/spaces/" in l][:10]

        spaces_to_check = list(dict.fromkeys(spaces_to_check))

        results = []
        for space_url in spaces_to_check[:8]:
            try:
                sp_page = ctx.new_page()
                info = analyze_space_interface(sp_page, space_url)
                results.append(info)
                sp_page.close()
                time.sleep(2)
            except Exception as e:
                print(f"Failed to analyze {space_url}: {e}")
                results.append({"url":space_url, "error":str(e), "working":False})

        MAP_FILE.parent.mkdir(parents=True, exist_ok=True)
        MAP_FILE.write_text(json.dumps(results, indent=2))
        print(f"\n=== MAPPING DONE SAVED TO {MAP_FILE} ===")
        print(json.dumps(results, indent=2))
        input("Mapping complete. Press Enter to close...")

if __name__=="__main__":
    map_trending_tools()