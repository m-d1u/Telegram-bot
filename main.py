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

# تغيير مهم: استخدم set() مختلفة لكل مستخدم لمنع التكرار
user_processing = {}

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

# ========== حل مشكلة تكرار الرسائل (Instagram & TikTok) ==========
async def download_without_duplicate(url, message, platform):
    user_id = message.from_user.id
    
    # اذا المستخدم عنده طلب قيد التنفيذ، لا تكرر
    if user_processing.get(user_id):
        await message.reply_text("⏳ عندك طلب قيد التنفيذ... انتظر شوي")
        return False
    
    user_processing[user_id] = True
    
    try:
        if platform == "instagram":
            await download_instagram(url, message)
        elif platform == "tiktok":
            await download_tiktok(url, message)
    finally:
        user_processing[user_id] = False
    
    return True

# ========== حل مشكلة يوتيوب (تحسين التحميل) ==========
@app.on_callback_query(filters.regex(r"^yt_"))
async def youtube_download(client, callback):
    user_id = callback.from_user.id
    
    # منع التكرار لنفس المستخدم
    if user_processing.get(user_id):
        await callback.answer("⏳ عندك طلب قيد التشغيل...", show_alert=True)
        return
    
    user_processing[user_id] = True
    
    url = None
    # محاولة جلب الرابط من الرسالة السابقة
    async for msg in app.get_chat_history(callback.message.chat.id, limit=5):
        if msg.text and ("youtube.com" in msg.text or "youtu.be" in msg.text):
            url_match = re.search(r'https?://[^\s]+', msg.text)
            if url_match:
                url = url_match.group(0)
                break
    
    if not url:
        await callback.answer("⚠️ الرابط غير موجود", show_alert=True)
        user_processing[user_id] = False
        return
    
    quality = callback.data.replace("yt_", "")
    await callback.message.edit_text(f"⬇️ جاري تحميل {quality}... اصبر شوية")
    
    rand = int(time.time() * 1000)
    
    # تحسين: طريقة أفضل لتحميل يوتيوب
    if quality == "1080":
        cmd = f'yt-dlp -f "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]" --merge-output-format mp4 --no-check-certificate --no-warnings -o "{DOWNLOAD_DIR}/v_{rand}.mp4" "{url}"'
    elif quality == "720":
        cmd = f'yt-dlp -f "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]" --merge-output-format mp4 --no-check-certificate --no-warnings -o "{DOWNLOAD_DIR}/v_{rand}.mp4" "{url}"'
    elif quality == "480":
        cmd = f'yt-dlp -f "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]" --merge-output-format mp4 --no-check-certificate --no-warnings -o "{DOWNLOAD_DIR}/v_{rand}.mp4" "{url}"'
    elif quality == "audio":
        cmd = f'yt-dlp -x --audio-format mp3 --audio-quality 0 --no-check-certificate --no-warnings -o "{DOWNLOAD_DIR}/a_{rand}.%(ext)s" "{url}"'
    else:
        cmd = f'yt-dlp -f "best[ext=mp4]" --no-check-certificate --no-warnings -o "{DOWNLOAD_DIR}/v_{rand}.mp4" "{url}"'
    
    try:
        process = await asyncio.create_subprocess_shell(cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=300)
        
        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "خطأ غير معروف"
            # اذا فشل، جرب بدون تحديد جودة
            if "requested format" in error_msg:
                fallback_cmd = f'yt-dlp -f "best" --no-check-certificate -o "{DOWNLOAD_DIR}/v_{rand}.mp4" "{url}"'
                process2 = await asyncio.create_subprocess_shell(fallback_cmd)
                await process2.wait()
        
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
        else:
            await callback.message.edit_text("❌ فشل التحميل\nجرب رابط آخر أو جودة أقل")
    except asyncio.TimeoutError:
        await callback.message.edit_text("❌ انتهى الوقت! السيرفر بطيء، جرب رابط آخر")
    except Exception as e:
        await callback.message.edit_text(f"❌ خطأ: {str(e)[:80]}")
    finally:
        user_processing[user_id] = False

async def download_instagram(url, message):
    msg = await message.reply_text("📸 جاري التحميل...")
    rand = int(time.time() * 1000)
    cmd = f'yt-dlp -f best --no-check-certificate --no-warnings -o "{DOWNLOAD_DIR}/insta_{rand}.%(ext)s" "{url}"'
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
    cmd = f'yt-dlp -f best --no-check-certificate --no-warnings -o "{DOWNLOAD_DIR}/tt_{rand}.%(ext)s" "{clean_url}"'
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
    text = message.text.strip()
    
    if CHANNEL_LINK in text:
        return
    
    url_match = re.search(r'https?://[^\s]+', text)
    if not url_match:
        return
    
    url = url_match.group(0)
    
    # يوتيوب
    if "youtube.com" in url or "youtu.be" in url:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎬 1080p", "yt_1080"), InlineKeyboardButton("🎬 720p", "yt_720")],
            [InlineKeyboardButton("🎬 480p", "yt_480"), InlineKeyboardButton("🎵 MP3", "yt_audio")]
        ])
        await message.reply_text("🔴 رابط يوتيوب!\nاختر الجودة:", reply_markup=keyboard)
        return
    
    # انستغرام - مع منع التكرار
    if "instagram.com" in url:
        if "/reel/" in url:
            await download_without_duplicate(url, message, "instagram")
        else:
            await message.reply_text("❌ فقط ريلزات انستغرام!")
        return
    
    # تيك توك - مع منع التكرار
    if "tiktok.com" in url or "vt.tiktok.com" in url:
        await download_without_duplicate(url, message, "tiktok")
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
