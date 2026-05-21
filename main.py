from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import os
import re
import asyncio
from pathlib import Path
import time

API_ID = int(os.environ.get("TELEGRAM_API_ID", 0))
API_HASH = os.environ.get("TELEGRAM_API_HASH", "")
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

CHANNEL_LINK = "https://t.me/m_d3u"

app = Client("downloader_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)

processed = set()
yt_links = {}

@app.on_message(filters.command("start"))
async def start_command(client, message):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 قناة البوت", url=CHANNEL_LINK)]
    ])
    await message.reply_text(
        "🐼 **أهلاً بك في بوت التحميل!**\n\n"
        "✅ **يوتيوب** (فيديو MP4 / صوت MP3)\n"
        "✅ **انستغرام** (ريلزات فقط)\n"
        "✅ **تيك توك** (فيديوهات فقط)\n\n"
        "📌 **دز الرابط وهسة ينزل عندك!**",
        reply_markup=keyboard
    )

@app.on_callback_query(filters.regex(r"^yt_"))
async def youtube_download(client, callback):
    user_id = callback.from_user.id
    msg_id = f"yt_{user_id}_{callback.message.id}"
    if msg_id in processed:
        return
    processed.add(msg_id)
    
    url = yt_links.get(user_id)
    if not url:
        await callback.answer("⚠️ الرابط انتهى", show_alert=True)
        processed.discard(msg_id)
        return
    
    quality = callback.data.replace("yt_", "")
    await callback.message.edit_text(f"⬇️ جاري تحميل {quality}... اصبر شوية")
    
    rand = int(time.time() * 1000)
    
    # لكل جودة أمر مختلف
    if quality == "1080":
        cmd = f'yt-dlp -f "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]" --merge-output-format mp4 -o "{DOWNLOAD_DIR}/v_{rand}.mp4" "{url}"'
    elif quality == "720":
        cmd = f'yt-dlp -f "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]" --merge-output-format mp4 -o "{DOWNLOAD_DIR}/v_{rand}.mp4" "{url}"'
    elif quality == "480":
        cmd = f'yt-dlp -f "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]" --merge-output-format mp4 -o "{DOWNLOAD_DIR}/v_{rand}.mp4" "{url}"'
    elif quality == "audio":
        cmd = f'yt-dlp -x --audio-format mp3 --audio-quality 0 -o "{DOWNLOAD_DIR}/a_{rand}.%(ext)s" "{url}"'
    else:
        cmd = f'yt-dlp -f "best[ext=mp4]" -o "{DOWNLOAD_DIR}/v_{rand}.mp4" "{url}"'
    
    try:
        process = await asyncio.create_subprocess_shell(cmd)
        await asyncio.wait_for(process.wait(), timeout=300)
        
        files = list(DOWNLOAD_DIR.glob(f"*{rand}*"))
        files = [f for f in files if f.is_file() and f.stat().st_size > 10000]
        
        if files:
            media = files[0]
            size = media.stat().st_size / (1024 * 1024)
            
            if quality == "audio":
                await callback.message.reply_audio(audio=str(media), caption=f"🎵 صوت | {size:.1f} MB")
            else:
                await callback.message.reply_video(video=str(media), caption=f"🎬 {quality}p | {size:.1f} MB")
            
            await callback.message.delete()
            media.unlink()
            # نحذف الرابط من الذاكرة بعد التحميل
            if user_id in yt_links:
                del yt_links[user_id]
        else:
            await callback.message.edit_text("❌ فشل التحميل")
    except Exception as e:
        await callback.message.edit_text(f"❌ خطأ: {str(e)[:50]}")
    finally:
        processed.discard(msg_id)

async def download_instagram(url, message):
    msg = await message.reply_text("📸 جاري التحميل...")
    rand = int(time.time() * 1000)
    cmd = f'yt-dlp -f best -o "{DOWNLOAD_DIR}/insta_{rand}.%(ext)s" "{url}"'
    process = await asyncio.create_subprocess_shell(cmd)
    await process.wait()
    files = list(DOWNLOAD_DIR.glob(f"*{rand}*"))
    files = [f for f in files if f.is_file() and f.stat().st_size > 5000]
    if files:
        media = files[0]
        size = media.stat().st_size / (1024 * 1024)
        await message.reply_video(video=str(media), caption=f"📸 ريلز | {size:.1f} MB")
        await msg.delete()
        media.unlink()
    else:
        await msg.edit_text("❌ فشل التحميل")

async def download_tiktok(url, message):
    if "/photo/" in url:
        await message.reply_text("❌ فقط فيديوهات تيك توك!")
        return
    msg = await message.reply_text("🎵 جاري التحميل...")
    rand = int(time.time() * 1000)
    clean_url = url.split('?')[0]
    cmd = f'yt-dlp -f best -o "{DOWNLOAD_DIR}/tt_{rand}.%(ext)s" "{clean_url}"'
    process = await asyncio.create_subprocess_shell(cmd)
    await process.wait()
    files = list(DOWNLOAD_DIR.glob(f"*{rand}*"))
    files = [f for f in files if f.is_file() and f.stat().st_size > 5000]
    if files:
        media = files[0]
        size = media.stat().st_size / (1024 * 1024)
        await message.reply_video(video=str(media), caption=f"🎵 تيك توك | {size:.1f} MB")
        await msg.delete()
        media.unlink()
    else:
        await msg.edit_text("❌ فشل التحميل")

@app.on_message(filters.text & ~filters.command(["start"]))
async def handle_links(client, message):
    user_id = message.from_user.id
    msg_key = f"msg_{user_id}_{message.id}"
    if msg_key in processed:
        return
    processed.add(msg_key)
    
    text = message.text.strip()
    
    if CHANNEL_LINK in text:
        processed.discard(msg_key)
        return
    
    url_match = re.search(r'https?://[^\s]+', text)
    if not url_match:
        processed.discard(msg_key)
        return
    
    url = url_match.group(0)
    
    if "youtube.com" in url or "youtu.be" in url:
        yt_links[user_id] = url
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎬 1080p", "yt_1080"), InlineKeyboardButton("🎬 720p", "yt_720")],
            [InlineKeyboardButton("🎬 480p", "yt_480"), InlineKeyboardButton("🎵 MP3", "yt_audio")]
        ])
        await message.reply_text("🔴 رابط يوتيوب!\nاختر الجودة:", reply_markup=keyboard)
        processed.discard(msg_key)
        return
    
    if "instagram.com" in url:
        if "/reel/" in url:
            await download_instagram(url, message)
        else:
            await message.reply_text("❌ فقط ريلزات انستغرام!")
        processed.discard(msg_key)
        return
    
    if "tiktok.com" in url or "vt.tiktok.com" in url:
        await download_tiktok(url, message)
        processed.discard(msg_key)
        return
    
    await message.reply_text("❌ رابط غير مدعوم")
    processed.discard(msg_key)

def clean():
    for f in DOWNLOAD_DIR.glob("*"):
        try:
            f.unlink()
        except:
            pass

if __name__ == "__main__":
    print("🚀 تشغيل البوت...")
    clean()
    app.run()