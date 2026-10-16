import os, json, time
from pathlib import Path
from camoufox.sync_api import Camoufox

PROFILE = os.path.expanduser("~/.camoufox-hf-profile")

def get_queue_path():
    p1 = Path("jobs/queue.json")
    p2 = Path("video-command-center/jobs/queue.json")
    return p1 if p1.exists() else p2

def get_results_path():
    p1 = Path("jobs/results.json")
    p2 = Path("video-command-center/jobs/results.json")
    return p1 if p1.exists() else p2

HF_SPACES = [
    {"name":"Stable Video Diffusion","url":"https://huggingface.co/spaces/stabilityai/stable-video-diffusion"},
    {"name":"SVD XT","url":"https://huggingface.co/spaces/stabilityai/stable-video-diffusion-img2vid-xt"},
    {"name":"LTX-Video","url":"https://huggingface.co/spaces/Lightricks/LTX-Video"},
]

def get_qwen_motion_prompt(context, topic):
    print(f"Getting Qwen motion for: {topic}")
    page = context.new_page()
    page.goto("https://chat.qwen.ai/", timeout=60000)
    page.wait_for_timeout(5000)
    try:
        box = page.locator("textarea").first
        box.fill(f"Write ONE short cinematic image-to-video motion prompt for '{topic}'. Example: slow zoom in, gentle pan right, wind, cinematic lighting. Only output prompt.")
        box.press("Enter")
        page.wait_for_timeout(10000)
        txt = page.locator("body").inner_text()[-500:]
        page.close()
        return txt[:200] if txt else f"slow zoom in, cinematic movement, {topic}"
    except Exception as e:
        print(f"Qwen fail {e}")
        page.close()
        return f"slow zoom in, camera pan, cinematic, {topic}"

def try_hf_space(context, space, image_path, motion_prompt):
    print(f"Trying {space['name']}")
    page = context.new_page()
    try:
        page.goto(space['url'], timeout=90000)
        page.wait_for_timeout(10000)
        files = page.locator("input[type=file]").all()
        if files:
            files[0].set_input_files(image_path)
            print("Image uploaded")
            page.wait_for_timeout(3000)
        # fill prompt
        for tb in page.locator("textarea").all():
            try:
                if tb.is_visible():
                    tb.fill(motion_prompt)
                    break
            except:
                pass
        # click generate
        for btn in page.locator("button").all():
            try:
                t = btn.inner_text().lower()
                if "generate" in t or "run" in t:
                    if btn.is_visible():
                        btn.click()
                        break
            except:
                pass
        # wait for video
        for i in range(60):
            page.wait_for_timeout(5000)
            if page.locator("video").count() > 0:
                print(f"Video found in {space['name']}")
                v = page.locator("video").first
                src = v.get_attribute("src")
                print(f"SRC: {src}")
                page.close()
                return {"success":True, "url":src, "space":space['name']}
        page.close()
        return {"success":False}
    except Exception as e:
        print(f"Fail {space['name']}: {e}")
        try: page.close()
        except: pass
        return {"success":False}

def run_pathway():
    qp = get_queue_path()
    rp = get_results_path()
    print(f"Queue: {qp}, Results: {rp}, Profile: {PROFILE}")
    if not qp.exists():
        print(f"No queue at {qp}")
        return
    jobs = json.loads(qp.read_text())
    for job in jobs:
        if job.get("status")!= "queued":
            continue
        topic = job.get("topic","test")
        job_id = job.get("id","test_001")
        print(f"\n=== Job {job_id}: {topic} ===")
        with Camoufox(persistent_context=True, user_data_dir=PROFILE, headless=False) as ctx:
            img_page = ctx.pages[0] if ctx.pages else ctx.new_page()
            img_url = f"https://image.pollinations.ai/prompt/{topic.replace(' ','%20')}?width=1024&height=576&nologo=true"
            img_page.goto(img_url)
            img_page.wait_for_timeout(5000)
            image_path = f"/tmp/image_{job_id}.png"
            img_page.screenshot(path=image_path)
            print(f"Image: {image_path}")
            motion = get_qwen_motion_prompt(ctx, topic)
            print(f"Motion: {motion}")
            result = None
            for space in HF_SPACES[:3]:
                res = try_hf_space(ctx, space, image_path, motion)
                if res.get("success"):
                    result = res
                    break
                print(f"Retry next space...")
            if not result:
                print("All 3 failed")
                job["status"]="failed"
                continue
            print(f"SUCCESS {result}")
            # MEGA check
            mp = ctx.new_page()
            mp.goto("https://mega.nz/fm/4M0W1R4B")
            mp.wait_for_timeout(5000)
            print(f"MEGA url: {mp.url} logged? {'fm' in mp.url}")
            mp.close()
            # save
            if not rp.exists():
                rp.write_text("[]")
            results = json.loads(rp.read_text())
            results.append({"id":job_id,"topic":topic,"video_prompt":motion,"space_used":result.get("space"),"url":result.get("url"),"status":"done"})
            rp.write_text(json.dumps(results, indent=2))
            job["status"]="done"
            input(f"Done {job_id} - Press Enter to continue...")
    qp.write_text(json.dumps(jobs, indent=2))
    print("All done")

if __name__=="__main__":
    run_pathway()
