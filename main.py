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

# بس حطينا dictionary للروابط المؤقتة فقط، بدون أي قفل
youtube_urls = {}

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
        await message.reply_video(video=str(media))
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
        await message.reply_video(video=str(media))
        await msg.delete()
        media.unlink()
    else:
        await msg.edit_text("❌ فشل التحميل")

@app.on_callback_query(filters.regex(r"^yt_"))
async def youtube_download(client, callback):
    user_id = callback.from_user.id
    quality = callback.data.replace("yt_", "")
    
    url = youtube_urls.get(user_id)
    if not url:
        await callback.answer("⚠️ الرابط انتهى! أرسل الرابط مرة أخرى", show_alert=True)
        return
    
    await callback.message.edit_text(f"⬇️ جاري تحميل {quality}... اصبر شوية")
    
    rand = int(time.time() * 1000)
    
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
        await asyncio.wait_for(process.wait(), timeout=120)
        
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
            if user_id in youtube_urls:
                del youtube_urls[user_id]
        else:
            await callback.message.edit_text("❌ فشل التحميل\nجرب رابط آخر أو جودة أقل")
    except asyncio.TimeoutError:
        await callback.message.edit_text("❌ انتهى الوقت! السيرفر بطيء")
    except Exception as e:
        await callback.message.edit_text(f"❌ خطأ: {str(e)[:80]}")
    finally:
        # نحرر المستخدم عادي
        pass

@app.on_message(filters.text & ~filters.command(["start"]))
async def handle_links(client, message):
    text = message.text.strip()
    
    if CHANNEL_LINK in text:
        return
    
    url_match = re.search(r'https?://[^\s]+', text)
    if not url_match:
        return
    
    url = url_match.group(0)
    
    if "youtube.com" in url or "youtu.be" in url:
        youtube_urls[message.from_user.id] = url
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎬 1080p", "yt_1080"), InlineKeyboardButton("🎬 720p", "yt_720")],
            [InlineKeyboardButton("🎬 480p", "yt_480"), InlineKeyboardButton("🎵 MP3", "yt_audio")]
        ])
        await message.reply_text("🔴 رابط يوتيوب!\nاختر الجودة:", reply_markup=keyboard)
        return
    
    if "instagram.com" in url:
        if "/reel/" in url:
            await download_instagram(url, message)
        else:
            await message.reply_text("❌ فقط ريلزات انستغرام!")
        return
    
    if "tiktok.com" in url or "vt.tiktok.com" in url:
        await download_tiktok(url, message)
        return
    
    await message.reply_text("❌ رابط غير مدعوم")

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
