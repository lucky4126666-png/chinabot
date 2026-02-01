import logging
import sqlite3
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

API_TOKEN = "8582300335:AAFhTYOZzF7fnu6cynD0kXf0fLQkevR_W7c"

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot)

# ================== DATABASE ==================
conn = sqlite3.connect("bot.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS keywords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id INTEGER,
    keyword TEXT,
    reply_html TEXT,
    image TEXT,
    buttons TEXT
)
""")
conn.commit()


# ================== UTILS ==================
def build_keyboard(buttons_text: str):
    if not buttons_text:
        return None

    kb = InlineKeyboardMarkup(row_width=2)
    rows = buttons_text.strip().split("\n")

    for row in rows:
        btns = []
        for part in row.split("&&"):
            if "-" in part:
                text, url = part.split("-", 1)
                btns.append(
                    InlineKeyboardButton(
                        text=text.strip(),
                        url=url.strip()
                    )
                )
        if btns:
            kb.row(*btns)
    return kb


# ================== AUTO MESSAGE WHEN BOT ADDED ==================
@dp.message_handler(content_types=types.ContentTypes.NEW_CHAT_MEMBERS)
async def bot_added(msg: types.Message):
    for user in msg.new_chat_members:
        if user.id == (await bot.me).id:
            await msg.reply(
                "🤖 <b>N组防骗助手</b>\n\n"
                "我已加入群组 ✅\n"
                "发送关键词即可自动回复\n\n"
                "请管理员私聊我添加关键词",
            )


# ================== ADD KEYWORD (PRIVATE) ==================
@dp.message_handler(commands=["add"], chat_type=types.ChatType.PRIVATE)
async def add_keyword(msg: types.Message):
    """
    Format:
    /add
    GROUP_ID
    KEYWORD
    HTML_REPLY
    IMAGE(optional)
    BUTTONS(optional)
    """

    text = msg.text.split("\n")
    if len(text) < 4:
        await msg.reply("❌ 格式错误")
        return

    group_id = int(text[1].strip())
    keyword = text[2].strip()
    reply_html = text[3].strip()
    image = text[4].strip() if len(text) > 4 else ""
    buttons = text[5].strip() if len(text) > 5 else ""

    cur.execute(
        "INSERT INTO keywords (group_id, keyword, reply_html, image, buttons) VALUES (?,?,?,?,?)",
        (group_id, keyword, reply_html, image, buttons)
    )
    conn.commit()

    await msg.reply("✅ 已保存关键词")


# ================== GROUP MESSAGE HANDLER ==================
@dp.message_handler(content_types=types.ContentTypes.TEXT)
async def keyword_reply(msg: types.Message):
    if msg.chat.type not in ["group", "supergroup"]:
        return

    text = msg.text.strip()

    cur.execute(
        "SELECT keyword, reply_html, image, buttons FROM keywords WHERE group_id=?",
        (msg.chat.id,)
    )
    rows = cur.fetchall()

    for keyword, reply_html, image, buttons in rows:
        if keyword in text:
            kb = build_keyboard(buttons)

            if image:
                await bot.send_photo(
                    msg.chat.id,
                    photo=image,
                    caption=reply_html,
                    reply_markup=kb
                )
            else:
                await bot.send_message(
                    msg.chat.id,
                    reply_html,
                    reply_markup=kb
                )
            break


# ================== START ==================
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
