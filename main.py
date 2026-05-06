import os
import asyncio
import time
from flask import Flask, jsonify
from flask_cors import CORS
from telethon import TelegramClient
from telethon.sessions import StringSession

app = Flask(__name__)
CORS(app)

# --- Config from environment variables ---
API_ID       = int(os.environ.get("API_ID", "0"))
API_HASH     = os.environ.get("API_HASH", "")
SESSION_STR  = os.environ.get("SESSION_STR", "")
BOT_USERNAME = os.environ.get("BOT_USERNAME", "Santhoshgeci_bot")
KEYWORD      = os.environ.get("KEYWORD", "Nowa")
CACHE_SECS   = int(os.environ.get("CACHE_SECS", "180"))  # 3 minutes

# --- Simple in-memory cache ---
cache = {"url": None, "ts": 0}


async def fetch_photo_from_bot():
    client = TelegramClient(StringSession(SESSION_STR), API_ID, API_HASH)
    await client.connect()

    # Send the keyword to the bot
    await client.send_message(BOT_USERNAME, KEYWORD)

    # Wait for bot to reply
    await asyncio.sleep(5)

    # Get messages ONLY from this specific bot's chat
    messages = await client.get_messages(BOT_USERNAME, limit=10)

    photo_path = None
    for msg in messages:
        # Only get photo with caption "cam a" — ignore butterfly bot messages
        if msg.photo and not msg.out and msg.message and "cam a" in msg.message.lower():
            photo_path = await client.download_media(msg.photo, file=bytes)
            break

    await client.disconnect()
    return photo_path


@app.route("/live-photo", methods=["GET"])
def live_photo():
    now = time.time()

    # Return cached URL if still valid
    if cache["url"] and (now - cache["ts"]) < CACHE_SECS:
        return jsonify({"success": True, "url": cache["url"], "cached": True})

    # Fetch fresh photo
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        photo_bytes = loop.run_until_complete(fetch_photo_from_bot())
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        loop.close()

    if not photo_bytes:
        return jsonify({"success": False, "error": "No photo received from bot"}), 404

    # Convert to base64 to send directly to browser
    import base64
    b64 = base64.b64encode(photo_bytes).decode("utf-8")
    data_url = f"data:image/jpeg;base64,{b64}"

    # Cache it
    cache["url"] = data_url
    cache["ts"]  = now

    return jsonify({"success": True, "url": data_url, "cached": False})


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
