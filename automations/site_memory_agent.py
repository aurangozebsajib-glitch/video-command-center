import json, time, os, re, requests
from pathlib import Path
from camoufox.sync_api import Camoufox

PROFILE = os.path.expanduser("~/.camoufox-hf-profile")
MEMORY_FILE = Path("jobs/site_memory.json")
SCREEN_DIR = Path("/tmp/hf_screenshots")
SCREEN_DIR.mkdir(exist_ok=True)

HF_TRENDING = "https://huggingface.co/models?pipeline_tag=text-to-video&sort=trending"
THEREISAI = "https://thereisanaiforthat.com/search?query=video%20generation"


def load_memory():
    if MEMORY_FILE.exists():
        try:
            return json.loads(MEMORY_FILE.read_text())
        except:
            return {"tools": [], "structures": {}}
    return {"tools": [], "structures": {}, "last_scan": 0}


def save_memory(mem):
    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    MEMORY_FILE.write_text(json.dumps(mem, indent=2))
    print(f"Memory saved to {MEMORY_FILE}: {len(mem['tools'])} tools")


def deep_analyze_page_structure(page, url):
    print(f"\n=== ANALYZING STRUCTURE: {url} ===")
    js = """
    () => {
        const info = {
            url: window.location.href,
            title: document.title,
            fileInputs: [],
            textareas: [],
            buttons: [],
            uploadZones: [],
            pricing: [],
            forms: []
        };
        function deepFind(selector, root=document){
            let els = [...root.querySelectorAll(selector)];
            try{
                root.querySelectorAll('*').forEach(el=>{
                    if(el.shadowRoot){
                        els = els.concat(deepFind(selector, el.shadowRoot));
                    }
                });
            }catch(e){}
            return els;
        }
        deepFind('input[type=file]').forEach(el=>{
            info.fileInputs.push({
                selector: 'input[type=file]',
                visible: el.offsetParent!==null || el.style.display!=='none',
                parentText: (el.parentElement?.innerText||'').slice(0,150),
                outer: el.outerHTML.slice(0,300)
            });
        });
        deepFind('textarea').forEach(el=>{
            info.textareas.push({
                placeholder: el.placeholder,
                visible: el.offsetParent!==null,
                label: (el.parentElement?.innerText||'').slice(0,150)
            });
        });
        deepFind('input[type=text]').forEach(el=>{
            if(el.placeholder && (el.placeholder.toLowerCase().includes('prompt') || el.placeholder.toLowerCase().includes('describe'))){
                info.textareas.push({
                    placeholder: el.placeholder,
                    type: 'prompt_input',
                    visible: el.offsetParent!==null
                });
            }
        });
        [...document.querySelectorAll('button')].forEach(b=>{
            const txt = (b.innerText||'').trim();
            if(txt.length>0 && txt.length<40){
                info.buttons.push(txt);
            }
        });
        const keywords = ['Drop Image','Click to Upload','Upload Image','Drag and Drop','Upload your','Choose File'];
        [...document.querySelectorAll('*')].forEach(el=>{
            const txt = (el.innerText||'').slice(0,100);
            if(keywords.some(k=>txt.includes(k))){
                info.uploadZones.push(txt);
            }
        });
        const bodyText = document.body.innerText.toLowerCase();
        if(bodyText.includes('free') || bodyText.includes('freemium')) info.pricing.push('freemium');
        if(bodyText.includes('pricing')) info.pricing.push('has_pricing');
        if(bodyText.includes('credits') || bodyText.includes('tokens')) info.pricing.push('credit_based');

        return info;
    }
    """
    try:
        target = page
        for frame in page.frames:
            try:
                if 'gradio' in frame.url.lower() or frame.locator('text=Drop Image Here').count()>0:
                    target = frame
                    print(f"Using gradio frame: {frame.url}")
                    break
            except:
                pass
        data = target.evaluate(js)
        print(f"Structure: {json.dumps(data, indent=2)[:2000]}")

        structure = {
            "url": url,
            "title": data.get("title",""),
            "has_upload": len(data.get("fileInputs",[]))>0 or len(data.get("uploadZones",[]))>0,
            "has_prompt": len(data.get("textareas",[]))>0,
            "generate_buttons": [b for b in data.get("buttons",[]) if any(x in b.lower() for x in ["generate","create","run","submit","convert"])],
            "all_buttons": data.get("buttons",[])[:20],
            "upload_zones": data.get("uploadZones",[]),
            "file_inputs_count": len(data.get("fileInputs",[])),
            "textareas": data.get("textareas",[])[:5],
            "pricing": data.get("pricing",[]),
            "type": "img2vid" if len(data.get("fileInputs",[]))>0 else "text2vid" if len(data.get("textareas",[]))>0 else "unknown",
            "learned_at": int(time.time()),
            "working": len(data.get("fileInputs",[]))>0 or any("generate" in b.lower() for b in data.get("buttons",[]))
        }
        return structure
    except Exception as e:
        print(f"Structure analyze fail {url}: {e}")
        return {"url":url, "error":str(e), "working":False}


def scan_thereisanaiforthat(context):
    print("\n=== SCANNING thereisanaiforthat.com for video tools ===")
    page = context.new_page()
    tools = []
    try:
        page.goto("https://thereisanaiforthat.com/search/video%20generation", timeout=90000)
        page.wait_for_timeout(10000)
        for _ in range(3):
            page.evaluate("()=>window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(3000)

        links = page.evaluate("""
        () => {
            const results = [];
            document.querySelectorAll('a').forEach(a=>{
                const href = a.href;
                const text = a.innerText;
                if(href && (href.includes('/ai/') || href.includes('/tool/')) && text.length>5 && text.length<100){
                    results.push({name:text.trim(), url:href});
                }
            });
            return results.slice(0,50);
        }
        """)
        print(f"Found {len(links)} potential tools from thereisanaiforthat: {links[:10]}")
        tools.extend(links)

        page.goto("https://thereisanaiforthat.com/browse?category=video", timeout=60000)
        page.wait_for_timeout(8000)
        more = page.evaluate("()=>{return [...document.querySelectorAll('a')].map(a=>({name:a.innerText.trim(), url:a.href})).filter(x=>x.name.length>5 && x.name.length<100 && x.url.includes('/ai/')).slice(0,50)}")
        tools.extend(more)

        page.close()
    except Exception as e:
        print(f"thereisanaiforthat scan fail {e}")
        try: page.close()
        except: pass

    uniq = {}
    for t in tools:
        if t['url'] not in uniq:
            uniq[t['url']] = t
    print(f"Total unique tools from thereisanaiforthat: {len(uniq)}")
    return list(uniq.values())[:30]


def scan_hf_trending(context):
    print("\n=== SCANNING HF trending video models ===")
    page = context.new_page()
    tools = []
    try:
        page.goto(HF_TRENDING, timeout=90000)
        page.wait_for_timeout(10000)
        spaces = page.evaluate("""
        () => {
            return [...document.querySelectorAll('a')].map(a=>a.href).filter(h=>h.includes('/spaces/')).slice(0,30)
        }
        """)
        print(f"HF Spaces trending: {spaces[:10]}")
        for url in spaces:
            tools.append({"name":url.split('/')[-1], "url":url, "source":"hf_trending"})
        page.close()
    except Exception as e:
        print(f"HF scan fail {e}")
        try: page.close()
        except: pass
    return tools


def run_memory_agent():
    mem = load_memory()
    print(f"Loaded memory: {len(mem['tools'])} tools already known")

    with Camoufox(persistent_context=True, user_data_dir=PROFILE, headless=False) as ctx:
        hf_tools = scan_hf_trending(ctx)
        ai_tools = scan_thereisanaiforthat(ctx)

        all_discovered = hf_tools + ai_tools
        print(f"\nTotal discovered: {len(all_discovered)} tools")

        existing_urls = set([t.get('url') for t in mem['tools']])
        new_tools = [t for t in all_discovered if t['url'] not in existing_urls]
        mem['tools'].extend(new_tools)
        print(f"New tools added: {len(new_tools)}")

        for tool in mem['tools'][-15:]:
            url = tool.get('url')
            if not url or 'thereisanaiforthat.com' in url:
                continue
            if url in mem['structures']:
                print(f"Already learned {url}, skipping")
                continue

            p = ctx.new_page()
            try:
                p.goto(url, timeout=60000)
                p.wait_for_timeout(8000)
                if p.locator("text=404").count()>0 or p.locator("text=Sorry, we can't find").count()>0:
                    print(f"404 SKIP {url}")
                    mem['structures'][url] = {"url":url, "working":False, "error":"404"}
                    save_memory(mem)
                    p.close()
                    continue

                screenshot_path = SCREEN_DIR / f"{url.replace('https://','').replace('/','_')[:50]}_{int(time.time())}.png"
                p.screenshot(path=str(screenshot_path))
                print(f"Screenshot: {screenshot_path}")

                structure = deep_analyze_page_structure(p, url)
                mem['structures'][url] = structure
                save_memory(mem)

                tool['structure_learned'] = True
                tool['type'] = structure.get('type')

                p.close()
                time.sleep(2)
            except Exception as e:
                print(f"Failed to learn {url}: {e}")
                try: p.close()
                except: pass
                mem['structures'][url] = {"url":url, "error":str(e), "working":False}
                save_memory(mem)

        print(f"\n\n=== MEMORY AGENT DONE ===")
        print(f"Total tools in memory: {len(mem['tools'])}")
        print(f"Structures learned: {len(mem['structures'])}")
        print(f"Working tools: {len([s for s in mem['structures'].values() if s.get('working')])}")
        print(json.dumps(mem['structures'], indent=2)[:5000])
        save_memory(mem)
        input("Memory agent complete. Press Enter...")


if __name__=="__main__":
    run_memory_agent()