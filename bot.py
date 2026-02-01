import os
import sqlite3
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ====== CONFIG ======
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot)

# ====== DB ======
conn = sqlite3.connect("data.db")
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS keywords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id INTEGER,
    keyword TEXT,
    response TEXT,
    image TEXT,
    buttons TEXT
)
""")
conn.commit()

# ====== UTILS ======
def is_owner(user_id):
    return user_id == OWNER_ID

def build_buttons(raw):
    if not raw:
        return None
    kb = InlineKeyboardMarkup()
    for line in raw.split("\n"):
        if "|" in line:
            text, url = line.split("|", 1)
            kb.add(InlineKeyboardButton(text.strip(), url=url.strip()))
    return kb

# ====== START (PRIVATE ONLY) ======
@dp.message_handler(commands=["start"])
async def start(msg: types.Message):
    if msg.chat.type != "private":
        return
    if not is_owner(msg.from_user.id):
        await msg.answer("⛔ Bạn không có quyền.")
        return

    text = (
        "🤖 <b>BOT TỪ KHÓA</b>\n\n"
        "• Quản lý từ khóa tự động\n"
        "• Nội dung: văn bản / ảnh / nút\n"
        "• Phản hồi trong group\n\n"
        "<b>Lệnh:</b>\n"
        "/add – thêm từ khóa\n"
        "/list – danh sách\n"
        "/del – xóa từ khóa\n"
    )
    await msg.answer(text)

# ====== ADD KEYWORD ======
@dp.message_handler(commands=["add"])
async def add_keyword(msg: types.Message):
    if msg.chat.type != "private" or not is_owner(msg.from_user.id):
        return
    await msg.answer(
        "📌 <b>THÊM TỪ KHÓA</b>\n\n"
        "Gửi theo format:\n\n"
        "<code>GROUP_ID</code>\n"
        "<code>TỪ_KHÓA</code>\n"
        "<code>NỘI_DUNG_HTML</code>\n"
        "<code>IMAGE (có thể trống)</code>\n"
        "<code>NÚT: text|link (mỗi nút 1 dòng)</code>"
    )

@dp.message_handler(lambda m: m.chat.type=="private" and m.text and m.text.count("\n")>=4)
async def save_keyword(msg: types.Message):
    if not is_owner(msg.from_user.id):
        return

    lines = msg.text.split("\n")
    group_id = int(lines[0].strip())
    keyword = lines[1].strip()
    response = lines[2].strip()
    image = lines[3].strip() or None
    buttons = "\n".join(lines[4:]).strip() or None

    cur.execute(
        "INSERT INTO keywords (group_id, keyword, response, image, buttons) VALUES (?,?,?,?,?)",
        (group_id, keyword, response, image, buttons)
    )
    conn.commit()

    kb = build_buttons(buttons)
    if image:
        await msg.answer_photo(image, caption=response, reply_markup=kb)
    else:
        await msg.answer(response, reply_markup=kb)

    await msg.answer("✅ Đã lưu & preview ở trên")

# ====== LIST ======
@dp.message_handler(commands=["list"])
async def list_kw(msg: types.Message):
    if msg.chat.type != "private" or not is_owner(msg.from_user.id):
        return
    cur.execute("SELECT id, keyword, group_id FROM keywords")
    rows = cur.fetchall()
    if not rows:
        await msg.answer("❌ Chưa có từ khóa")
        return
    text = "📋 <b>DANH SÁCH</b>\n\n"
    for i,k,g in rows:
        text += f"#{i} | <code>{k}</code> | {g}\n"
    await msg.answer(text)

# ====== DELETE ======
@dp.message_handler(commands=["del"])
async def delete_kw(msg: types.Message):
    if msg.chat.type != "private" or not is_owner(msg.from_user.id):
        return
    try:
        kid = int(msg.get_args())
    except:
        await msg.answer("❌ /del ID")
        return
    cur.execute("DELETE FROM keywords WHERE id=?", (kid,))
    conn.commit()
    await msg.answer("🗑️ Đã xóa")

# ====== AUTO REPLY IN GROUP ======
@dp.message_handler(lambda m: m.chat.type in ["group","supergroup"], content_types=types.ContentTypes.TEXT)
async def auto_reply(msg: types.Message):
    cur.execute(
        "SELECT response, image, buttons FROM keywords WHERE group_id=? AND keyword=?",
        (msg.chat.id, msg.text.strip())
    )
    row = cur.fetchone()
    if not row:
        return

    response, image, buttons = row
    kb = build_buttons(buttons)

    if image:
        await msg.answer_photo(image, caption=response, reply_markup=kb)
    else:
        await msg.answer(response, reply_markup=kb)

# ====== BOT ADDED TO GROUP ======
@dp.message_handler(content_types=types.ContentTypes.NEW_CHAT_MEMBERS)
async def bot_added(msg: types.Message):
    for u in msg.new_chat_members:
        if u.id == (await bot.me).id:
            text = (
                "🤖 <b>Bot đã được kích hoạt</b>\n\n"
                "• Phản hồi theo từ khóa\n"
                "• Nội dung do chủ bot cài\n"
                "• Hỗ trợ HTML / ảnh / nút\n\n"
                "⚙️ Cấu hình trong chat riêng"
            )
            kb = InlineKeyboardMarkup()
            kb.add(
                InlineKeyboardButton("📢 Kênh thông báo", url="https://t.me/gonggao")
            )
            await msg.answer(text, reply_markup=kb)

# ====== RUN ======
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
