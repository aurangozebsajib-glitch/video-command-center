
def run_pathway():
    if not QUEUE.exists():
        print("No queue.json")
        return

    jobs = json.loads(QUEUE.read_text())
    for job in jobs:
        if job.get("status")!= "queued":
            continue

        topic = job.get("topic","test video")
        job_id = job.get("id", str(int(time.time())))
        print(f"\n=== Processing job {job_id}: {topic} ===")

        with Camoufox(persistent_context=True, user_data_dir=PROFILE, headless=False) as ctx:
            img_page = ctx.pages[0] if ctx.pages else ctx.new_page()
            img_url = f"https://image.pollinations.ai/prompt/{topic.replace(' ','%20')}?width=1024&height=576&nologo=true"
            img_page.goto(img_url)
            img_page.wait_for_timeout(5000)
            image_path = f"/tmp/image_{job_id}.png"
            img_page.screenshot(path=image_path)
            print(f"Image saved: {image_path}")

            motion_prompt = get_qwen_motion_prompt(ctx, topic)
            print(f"Motion prompt: {motion_prompt}")

            result = None
            for space in HF_SPACES[:3]:
                res = try_hf_space(ctx, space, image_path, motion_prompt)
                if res.get("success"):
                    result = res
                    break
                print(f"Failed {space['name']}, trying next...")
                time.sleep(3)

            if not result:
                print(f"All 3 spaces failed for job {job_id}")
                job["status"] = "failed"
                continue

            print(f"SUCCESS: {result}")

            mega_page = ctx.new_page()
            mega_page.goto("https://mega.nz/fm/4M0W1R4B")
            mega_page.wait_for_timeout(5000)
            is_logged = "login" not in mega_page.url.lower() or "fm" in mega_page.url
            print(f"MEGA logged in: {is_logged}, url: {mega_page.url}")
            mega_page.close()

            if not RESULTS.exists():
                RESULTS.write_text("[]")
            results = json.loads(RESULTS.read_text())
            results.append({
                "id": job_id,
                "topic": topic,
                "video_prompt": motion_prompt,
                "space_used": result.get("space"),
                "url": result.get("url"),
                "status":"done"
            })
            RESULTS.write_text(json.dumps(results, indent=2))
            job["status"] = "done"

            input(f"Job {job_id} done. Video: {result.get('url')}. Press Enter to continue to next job...")

    QUEUE.write_text(json.dumps(jobs, indent=2))
    print("All jobs processed")

if __name__=="__main__":
    run_pathway()

def get_qwen_motion_prompt(context, topic):
    print(f"Getting Qwen motion prompt for: {topic}")
    page = context.new_page()
    page.goto("https://www.qwen.com/")
    time.sleep(5)
    try:
        input_box = page.locator("textarea").first
        prompt = f"Write ONE short cinematic image-to-video motion prompt for topic '{topic}'. Example: 'slow zoom in, gentle pan right, wind blowing, cinematic lighting, 4k'. Only output the motion prompt, no explanation."
        input_box.fill(prompt)
        input_box.press("Enter")
        time.sleep(10)
        messages = page.locator("[data-role='assistant']").all()
        if messages:
            text = messages[-1].inner_text()
            page.close()
            return text[:200]
        text = page.content()
        page.close()
        return f"slow zoom in, cinematic movement, topic {topic}"
    except Exception as e:
        print(f"Qwen error: {e}")
        page.close()
        return f"slow zoom in, camera pan, cinematic, {topic}"

def try_hf_space(context, space, image_path, motion_prompt):
    print(f"Trying space: {space['name']} - {space['url']}")
    page = context.new_page()
    try:
        page.goto(space['url'], timeout=60000)
        page.wait_for_timeout(8000)
        file_inputs = page.locator("input[type=file]").all()
        if file_inputs:
            file_inputs[0].set_input_files(image_path)
            print("Uploaded image")
            page.wait_for_timeout(3000)

        textboxes = page.locator("textarea").all()
        for tb in textboxes:
            try:
                if tb.is_visible():
                    tb.fill(motion_prompt)
                    print(f"Pasted motion prompt: {motion_prompt}")
                    break
            except:
                continue

        buttons = page.locator("button").all()
        for btn in buttons:
            try:
                txt = btn.inner_text().lower()
                if "generate" in txt or "run" in txt or "submit" in txt:
                    if btn.is_visible() and btn.is_enabled():
                        btn.click()
                        print(f"Clicked {txt}")
                        break
            except:
                continue

        for i in range(60):
            page.wait_for_timeout(5000)
            videos = page.locator("video").all()
            if videos:
                print(f"Video found in {space['name']}")
                src = videos[0].get_attribute("src")
                if src:
                    print(f"Video src: {src[:100]}")
                    page.close()
                    return {"success":True, "url":src, "space":space['name']}
            download_btns = page.locator("a[download]").all()
            if download_btns:
                href = download_btns[0].get_attribute("href")
                if href:
                    page.close()
                    return {"success":True, "url":href, "space":space['name']}

        page.close()
        return {"success":False, "error":"timeout no video"}
    except Exception as e:
        print(f"Space {space['name']} failed: {e}")
        try:
            page.close()
        except:
            pass
        return {"success":False, "error":str(e)}

import os, json, time
from pathlib import Path
from camoufox.sync_api import Camoufox

PROFILE = os.path.expanduser("~/.camoufox-hf-profile")
QUEUE = Path("jobs/queue.json")
RESULTS = Path("jobs/results.json")

HF_SPACES = [
    {"name":"Stable Video Diffusion","url":"https://huggingface.co/spaces/stabilityai/stable-video-diffusion","type":"i2v","retry":1},
    {"name":"SVD XT","url":"https://huggingface.co/spaces/stabilityai/stable-video-diffusion-img2vid-xt","type":"i2v","retry":2},
    {"name":"LTX-Video","url":"https://huggingface.co/spaces/Lightricks/LTX-Video","type":"i2v","retry":3},
    {"name":"CogVideoX-5B","url":"https://huggingface.co/spaces/THUDM/CogVideoX-5B","type":"i2v","retry":4},
    {"name":"I2VGen-XL","url":"https://huggingface.co/spaces/ali-vilab/i2vgen-xl","type":"i2v","retry":5},
]