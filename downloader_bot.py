import asyncio
import os
import uuid
import glob
import sqlite3
import yt_dlp

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, FSInputFile
from aiogram.filters import CommandStart, Command

TOKEN = "8880888892:AAFn1gqp1pR0t2EEpnAUJULjdupIoR10v6o"
ADMIN_ID = 7768829103
BOT_USERNAME = "@DownloadMasterUzBot"

bot = Bot(token=TOKEN)
dp = Dispatcher()

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

db = sqlite3.connect("downloader.db")
cur = db.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS channels (
    chat_id TEXT PRIMARY KEY,
    link TEXT
)
""")

db.commit()


def is_admin(user_id):
    return user_id == ADMIN_ID


def chat_ref(chat_id):
    if chat_id.startswith("-100"):
        return int(chat_id)
    return chat_id


def channel_url(chat_id, link):
    if link:
        return link
    return f"https://t.me/{chat_id.replace('@', '')}"


def sub_buttons():
    cur.execute("SELECT chat_id, link FROM channels")
    channels = cur.fetchall()

    buttons = []

    for i, (chat_id, link) in enumerate(channels, start=1):
        buttons.append([
            InlineKeyboardButton(
                text=f"📢 {i}-KANAL",
                url=channel_url(chat_id, link)
            )
        ])

    buttons.append([
        InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_sub")
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def check_sub(user_id):
    cur.execute("SELECT chat_id FROM channels")
    channels = cur.fetchall()

    if not channels:
        return True

    for ch in channels:
        try:
            member = await bot.get_chat_member(chat_ref(ch[0]), user_id)
            if member.status in ["left", "kicked"]:
                return False
        except:
            return False

    return True


def download_media(url):
    file_code = str(uuid.uuid4())
    output_path = os.path.join(DOWNLOAD_DIR, f"{file_code}.%(ext)s")

    opts = {
        "outtmpl": output_path,
        "format": "best[filesize<49M]/best",
        "quiet": True,
        "noplaylist": True,
    }

    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])

    files = glob.glob(os.path.join(DOWNLOAD_DIR, f"{file_code}.*"))
    return files[0] if files else None


@dp.message(CommandStart())
async def start(message: Message):
    cur.execute("INSERT OR IGNORE INTO users VALUES (?)", (message.from_user.id,))
    db.commit()

    if not await check_sub(message.from_user.id):
        await message.answer(
            "❗ Avval quyidagi kanallarga obuna bo‘ling:",
            reply_markup=sub_buttons()
        )
        return

    name = message.from_user.first_name

    await message.answer(
        f"Salom ✋ {name}!\n\n"
        "Instagram, TikTok, YouTube, Pinterest link yuboring.\n"
        "Men video yoki rasmni yuklab beraman."
    )


@dp.callback_query(F.data == "check_sub")
async def check_button(call: CallbackQuery):
    if await check_sub(call.from_user.id):
        await call.message.answer("✅ Obuna tasdiqlandi.\n\nEndi link yuboring.")
    else:
        await call.message.answer(
            "❌ Hali hamma kanalga obuna bo‘lmagansiz.",
            reply_markup=sub_buttons()
        )


@dp.message(Command("admin"))
async def admin(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Siz admin emassiz.")
        return

    cur.execute("SELECT COUNT(*) FROM users")
    users = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM channels")
    channels = cur.fetchone()[0]

    await message.answer(
        f"👑 Admin panel\n\n"
        f"👥 Users: {users}\n"
        f"📢 Kanallar: {channels}\n\n"
        f"/addchannel @kanal\n"
        f"/addchannel -1001234567890 https://t.me/+LINK\n"
        f"/delchannel @kanal yoki ID\n"
        f"/channels\n"
        f"/stats"
    )


@dp.message(Command("addchannel"))
async def add_channel(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Siz admin emassiz.")
        return

    args = message.text.split()

    if len(args) < 2:
        await message.answer(
            "Kanal qo‘shish:\n"
            "/addchannel @kanal\n\n"
            "Private kanal:\n"
            "/addchannel -1001234567890 https://t.me/+LINK"
        )
        return

    chat_id = args[1]
    link = args[2] if len(args) >= 3 else ""

    if not chat_id.startswith("@") and not chat_id.startswith("-100"):
        await message.answer("❌ @kanal yoki -100 bilan boshlanadigan ID kiriting.")
        return

    if chat_id.startswith("-100") and not link:
        await message.answer("❌ Private kanal uchun link ham kerak.")
        return

    cur.execute(
        "INSERT OR REPLACE INTO channels (chat_id, link) VALUES (?, ?)",
        (chat_id, link)
    )
    db.commit()

    await message.answer("✅ Kanal qo‘shildi. Botda 1-KANAL, 2-KANAL bo‘lib chiqadi.")


@dp.message(Command("delchannel"))
async def del_channel(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Siz admin emassiz.")
        return

    args = message.text.split()

    if len(args) != 2:
        await message.answer("O‘chirish:\n/delchannel @kanal")
        return

    cur.execute("DELETE FROM channels WHERE chat_id=?", (args[1],))
    db.commit()

    await message.answer("🗑 Kanal o‘chirildi.")


@dp.message(Command("channels"))
async def channels(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Siz admin emassiz.")
        return

    cur.execute("SELECT chat_id, link FROM channels")
    rows = cur.fetchall()

    if not rows:
        await message.answer("❌ Kanal yo‘q.")
        return

    text = "📢 Majburiy obuna kanallari:\n\n"

    for i, (chat_id, link) in enumerate(rows, start=1):
        text += f"{i}-KANAL\nID: {chat_id}\nLink: {link if link else 'Public'}\n\n"

    await message.answer(text)


@dp.message(Command("stats"))
async def stats(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Siz admin emassiz.")
        return

    cur.execute("SELECT COUNT(*) FROM users")
    users = cur.fetchone()[0]

    await message.answer(f"📊 Statistika\n\n👥 Users: {users}")


@dp.message()
async def downloader(message: Message):
    if not await check_sub(message.from_user.id):
        await message.answer(
            "❗ Avval quyidagi kanallarga obuna bo‘ling:",
            reply_markup=sub_buttons()
        )
        return

    url = message.text.strip()

    if not url.startswith("http"):
        await message.answer("❌ Instagram, TikTok, YouTube yoki Pinterest link yuboring.")
        return

    msg = await message.answer("⏳ Yuklanmoqda...")

    try:
        file_path = download_media(url)

        if not file_path:
            await msg.edit_text("❌ Fayl topilmadi.")
            return

        size_mb = os.path.getsize(file_path) / 1024 / 1024

        if size_mb > 49:
            await msg.edit_text("❌ Fayl juda katta. 50 MB dan kichik bo‘lishi kerak.")
            os.remove(file_path)
            return

        ext = file_path.lower()

        if ext.endswith((".mp4", ".mov", ".mkv", ".webm")):
            await message.answer_video(
                video=FSInputFile(file_path),
                caption=f"✅ Tayyor!\n\n🤖 {BOT_USERNAME}"
            )
        elif ext.endswith((".jpg", ".jpeg", ".png", ".webp")):
            await message.answer_photo(
                photo=FSInputFile(file_path),
                caption=f"✅ Tayyor!\n\n🤖 {BOT_USERNAME}"
            )
        else:
            await message.answer_document(
                document=FSInputFile(file_path),
                caption=f"✅ Tayyor!\n\n🤖 {BOT_USERNAME}"
            )

        await msg.delete()
        os.remove(file_path)

    except Exception as e:
        await msg.edit_text("❌ Yuklab bo‘lmadi. Video private yoki sayt ruxsat bermagan bo‘lishi mumkin.")
        print(e)


async def main():
    print("Downloader bot ishga tushdi...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())