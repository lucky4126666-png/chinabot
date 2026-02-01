import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

API_TOKEN = "8582300335:AAFhTYOZzF7fnu6cynD0kXf0fLQkevR_W7c"
OWNER_ID = 8572604188  # ID Telegram của bạn

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot)

KEYWORDS = {}

# Khi bot được thêm vào group
@dp.message_handler(content_types=types.ContentType.NEW_CHAT_MEMBERS)
async def on_added(msg: types.Message):
    for u in msg.new_chat_members:
        if u.id == (await bot.me).id:
            await msg.reply(
                "🤖 Bot đã được kích hoạt\n"
                "✅ Nhắn từ khóa → bot trả lời\n"
                "⚠️ Nhớ tắt Privacy Mode"
            )

# Thêm từ khóa
@dp.message_handler(commands=["add"])
async def add_keyword(msg: types.Message):
    if msg.from_user.id != OWNER_ID:
        return

    await msg.reply(
        "Gửi theo format:\n\n"
        "TUKHOA\n"
        "NOI_DUNG_HTML\n"
        "IMAGE (có thể bỏ trống)\n"
        "NÚT|LINK (mỗi dòng 1 nút)"
    )

    state = {}

    @dp.message_handler(lambda m: m.from_user.id == OWNER_ID, content_types=types.ContentType.TEXT)
    async def save(m: types.Message):
        lines = m.text.splitlines()
        if len(lines) < 2:
            await m.reply("❌ Sai format")
            return

        keyword = lines[0].strip().lower()
        text = lines[1]
        image = None
        buttons = []

        for line in lines[2:]:
            if "|" in line:
                t, l = line.split("|", 1)
                buttons.append((t.strip(), l.strip()))
            elif line.startswith("http"):
                image = line.strip()

        KEYWORDS[keyword] = {
            "text": text,
            "image": image,
            "buttons": buttons
        }

        await m.reply(f"✅ Đã lưu từ khóa: <b>{keyword}</b>")

        dp.message_handlers.unregister(save)

# Bắt từ khóa trong group
@dp.message_handler(content_types=types.ContentType.TEXT)
async def keyword_reply(msg: types.Message):
    text = msg.text.lower()

    for k, v in KEYWORDS.items():
        if k in text:
            kb = InlineKeyboardMarkup()
            for t, l in v["buttons"]:
                kb.add(InlineKeyboardButton(t, url=l))

            if v["image"]:
                await msg.reply_photo(v["image"], caption=v["text"], reply_markup=kb)
            else:
                await msg.reply(v["text"], reply_markup=kb)
            break

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
