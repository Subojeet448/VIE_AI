from flask import Flask, request, jsonify, Response
from io import BytesIO
import requests
import json
import time
import secrets
from urllib.parse import urlparse

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False

# ============================================================
#  HOME - All endpoints listed
# ============================================================

@app.route("/")
def home():
    return jsonify({
        "service": "AB DEVS - All-in-One API",
        "developer": "@ab_devs",
        "endpoints": {
            "AI Assistant": "/ai?prompt=hello",
            "Image to Prompt": "/img2txt?url=IMAGE_URL",
            "Image Enhancer": "/enhance?url=IMAGE_URL",
            "Image Generator": "/generate?prompt=your+text",
            "Text to Video": "/video?prompt=your+text"
        },
        "status": "running"
    })


# ============================================================
#  1. AI ASSISTANT  (replaces old AI GF)
# ============================================================

AI_API_URL = "https://api.deepai.org/hacking_is_a_serious_crime"
BASE_API_KEY = "tryit-71209460785-0d83ccc5af9bd7a408f4328b4"

def generate_api_key():
    return BASE_API_KEY + secrets.token_hex(3)

def get_headers():
    return {
        "User-Agent": "Mozilla/5.0",
        "Accept": "*/*",
        "api-key": generate_api_key(),
        "Origin": "https://deepai.org"
    }

SYSTEM_PROMPT = (
    "You are ARIA, a smart and helpful AI assistant. "
    "You answer questions clearly and concisely. "
    "You are friendly, professional, and always try to give the best answer. "
    "Reply in the same language the user uses. "
    "Keep replies short and to the point — max 3-4 sentences."
)

@app.route("/ai", methods=["GET"])
def ai_assistant():
    user_input = request.args.get("prompt")
    if not user_input:
        return jsonify({
            "prompt": "",
            "response": "Please provide a prompt. Example: /ai?prompt=hello",
            "status": "error"
        }), 400

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_input}
    ]

    payload = {
        "chat_style": "chat",
        "chatHistory": json.dumps(messages),
        "model": "standard"
    }

    try:
        res = requests.post(AI_API_URL, data=payload, headers=get_headers(), timeout=30)
        raw = res.text.strip()
        try:
            data = res.json()
            reply = data.get("output") or data.get("response") or raw
        except Exception:
            reply = raw
    except Exception as e:
        return jsonify({
            "prompt": user_input,
            "response": str(e),
            "status": "error"
        }), 500

    reply = reply.replace("\n", " ")[:500]

    return jsonify({
        "prompt": user_input,
        "response": reply,
        "status": "success"
    })


# ============================================================
#  2. IMAGE TO PROMPT
# ============================================================

IMG2TXT_URL = "https://api.deepai.org/analyze-image-for-ads"

@app.route("/img2txt")
def img2txt():
    image_url = request.args.get("url")
    if not image_url:
        return jsonify({"success": False, "error": "Missing 'url' parameter. Usage: /img2txt?url=IMAGE_URL"})

    try:
        img = requests.get(image_url, timeout=20)
        if img.status_code != 200:
            return jsonify({"success": False, "error": "Failed to download image"})

        files = {"image": ("image.jpg", BytesIO(img.content))}
        data = {
            "tool_name": "IMAGE TO PROMPT",
            "tool_description": "Get Image to Prompt by AI."
        }
        headers = {"User-Agent": "Mozilla/5.0"}

        r = requests.post(IMG2TXT_URL, files=files, data=data, headers=headers, timeout=60)
        if r.status_code != 200:
            return jsonify({"success": False, "error": r.text})

        result = r.json()
        prompt = None
        if result.get("descriptions"):
            prompt = result["descriptions"][0]

        return jsonify({"success": True, "prompt": prompt})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


# ============================================================
#  3. IMAGE ENHANCER
# ============================================================

MAX_RETRIES = 30
RETRY_DELAY = 3

def enhance_image(image_url):
    try:
        img_response = requests.get(image_url, timeout=15)
        img_response.raise_for_status()
        image_data = BytesIO(img_response.content)

        upload_url = "https://photoai.imglarger.com/api/PhoAi/Upload"
        files = {"file": ("image.jpg", image_data, "image/jpeg")}
        data = {"type": "2", "scaleRadio": "2"}
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Origin": "https://image-enhancer-snowy.vercel.app",
            "Referer": "https://image-enhancer-snowy.vercel.app/"
        }

        upload_response = requests.post(upload_url, data=data, files=files, headers=headers, timeout=30)

        try:
            upload_json = upload_response.json()
        except Exception:
            return {"error": "Invalid upload response", "raw": upload_response.text}, 500

        if not upload_json.get("data"):
            return {"error": "Upload failed", "response": upload_json}, 500

        code = upload_json["data"].get("code")
        if not code:
            return {"error": "No code received", "response": upload_json}, 500

        status_url = "https://photoai.imglarger.com/api/PhoAi/CheckStatus"
        status_headers = {
            "User-Agent": "Mozilla/5.0",
            "Content-Type": "application/json",
            "Origin": "https://abbasbio.netlify.app/",
            "Referer": "https://abbasbio.netlify.app/"
        }

        for _ in range(MAX_RETRIES):
            payload = {"type": "2", "code": code}
            status_response = requests.post(status_url, json=payload, headers=status_headers, timeout=30)

            try:
                status_json = status_response.json()
            except Exception:
                return {"error": "Invalid status response", "raw": status_response.text}, 500

            s_data = status_json.get("data", {})
            status = s_data.get("status")

            if status == "success":
                urls = s_data.get("downloadUrls", [])
                if urls:
                    return {"success": True, "image": urls[0], "code": code}, 200

            if status == "failed":
                return {"error": "Enhancement failed"}, 500

            time.sleep(RETRY_DELAY)

        return {"error": "Timeout"}, 408

    except Exception as e:
        return {"error": str(e)}, 500


@app.route("/enhance", methods=["GET"])
def enhance():
    image_url = request.args.get("url")
    if not image_url:
        return jsonify({"error": "Missing 'url' parameter", "usage": "/enhance?url=IMAGE_URL"}), 400
    if not image_url.startswith(("http://", "https://")):
        return jsonify({"error": "Invalid URL"}), 400

    result, status = enhance_image(image_url)
    return jsonify(result), status


# ============================================================
#  4. IMAGE GENERATOR (Magic Studio)
# ============================================================

MAGIC_URL = "https://ai-api.magicstudio.com/api/ai-art-generator"
MAGIC_HEADERS = {
    "user-agent": "Mozilla/5.0",
    "accept": "application/json, text/plain, */*",
    "origin": "https://magicstudio.com",
    "referer": "https://magicstudio.com/ai-art-generator/"
}

@app.route("/generate")
def generate_image():
    prompt = request.args.get("prompt")
    if not prompt:
        return jsonify({"error": "Missing 'prompt' parameter. Usage: /generate?prompt=your+text"}), 400

    magic_data = {
        "prompt": prompt,
        "output_format": "bytes",
        "user_profile_id": "null",
        "anonymous_user_id": "8c8fe58b-f1dd-40b8-86ac-a91ea7d7b4c2",
        "user_is_subscribed": "false",
        "client_id": "pSgX7WgjukXCBoYwDM8G8GLnRRkvAoJlqa5eAVvj95o"
    }

    try:
        magic_response = requests.post(MAGIC_URL, data=magic_data, headers=MAGIC_HEADERS, timeout=60)
    except Exception as e:
        return jsonify({"error": "Request failed", "details": str(e)}), 500

    if magic_response.status_code != 200:
        return jsonify({"error": "API failed", "status": magic_response.status_code}), magic_response.status_code

    return Response(magic_response.content, mimetype="image/png")


# ============================================================
#  5. TEXT TO VIDEO
# ============================================================

VIDEO_HEADERS = {
    'User-Agent': "okhttp/5.1.0",
    'Accept-Encoding': "gzip",
    'authorization': "eyJzdWIiwsdeOiIyMzQyZmczNHJ0MzR0weMzQiLCJuYW1lIjorwiSm9objJif4md3kbnG",
    'sign': "68d6165b72a7f2d8d17b0dc6fe9691abdf77c583",
    'pt': "",
    'v': "72",
    'deviceid': "1b5336ed0297604a"
}
DEVICE_ID = "1b5336ed0297604a"

@app.route("/video")
def generate_video():
    prompt = request.args.get("prompt")
    if not prompt:
        return jsonify({"error": "Prompt is required. Usage: /video?prompt=your+text"}), 400

    # NSFW check
    nsfw_url = "https://text2video.aritek.app/nsfw"
    nsfw_payload = {
        'prompt': prompt,
        'ctry_target': 'others',
        'versionCode': '72',
        'deviceID': DEVICE_ID,
        'isPremium': '0'
    }

    try:
        nsfw_res = requests.post(nsfw_url, data=nsfw_payload, headers=VIDEO_HEADERS, timeout=20)
        nsfw_data = nsfw_res.json()
        if nsfw_data.get('code') != 0 or not nsfw_data.get('success'):
            return jsonify({"error": "NSFW check failed"}), 400
        if nsfw_data['data'][0].get('nsfw'):
            return jsonify({"error": "Prompt flagged as NSFW"}), 400
    except Exception as e:
        return jsonify({"error": f"NSFW error: {str(e)}"}), 500

    # Generate key
    txt2video_url = "https://text2video.aritek.app/txt2videov3"
    payload = {
        "ai_sound": 1,
        "aspect_ratio": "auto",
        "ctry_target": "others",
        "deviceID": DEVICE_ID,
        "isPremium": 0,
        "prompt": prompt,
        "used": [],
        "versionCode": 72
    }
    headers_json = VIDEO_HEADERS.copy()
    headers_json['content-type'] = "application/json; charset=utf-8"

    try:
        res = requests.post(txt2video_url, data=json.dumps(payload), headers=headers_json, timeout=30)
        data = res.json()
        if data.get('code') != 0:
            return jsonify({"error": "Video generation failed"}), 400
        video_key = data.get("key")
        if not video_key:
            return jsonify({"error": "No video key"}), 400
    except Exception as e:
        return jsonify({"error": f"Key error: {str(e)}"}), 500

    # Fetch video
    video_url_api = "https://text2video.aritek.app/video"
    video_payload = {"keys": [video_key]}

    for _ in range(10):
        try:
            res = requests.post(video_url_api, data=json.dumps(video_payload), headers=headers_json, timeout=30)
            data = res.json()
            if data.get("code") == 0 and data.get("datas"):
                video_info = data["datas"][0]
                url = video_info.get("url")
                if url:
                    filename = urlparse(url).path.split("/")[-1]
                    return jsonify({
                        "status": "success",
                        "url": url,
                        "filename": filename,
                        "safe": video_info.get("safe", "unknown")
                    })
            time.sleep(3)
        except Exception as e:
            return jsonify({"error": f"Fetch error: {str(e)}"}), 500

    return jsonify({"error": "Timeout - try again"}), 500


# ============================================================
#  Health check
# ============================================================

@app.route("/health")
def health():
    return jsonify({"status": "ok", "developer": "@ab_devs"})


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
