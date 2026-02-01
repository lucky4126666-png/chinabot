import logging
import sqlite3
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import os

API_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot)

# ===== DB =====
db = sqlite3.connect("data.db", check_same_thread=False)
cur = db.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS keywords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword TEXT,
    text TEXT,
    image TEXT,
    buttons TEXT
)
""")
db.commit()

# ===== TEMP DATA =====
user_state = {}

# ===== KEYBOARDS =====
def main_menu():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🔑 Quản lý từ khóa", callback_data="kw_menu"))
    kb.add(InlineKeyboardButton("⚙️ Cài đặt", callback_data="settings"))
    return kb

def kw_menu():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("➕ Thêm từ khóa", callback_data="add_kw"))
    kb.add(InlineKeyboardButton("📋 Danh sách từ khóa", callback_data="list_kw"))
    kb.add(InlineKeyboardButton("⬅️ Quay lại", callback_data="back_main"))
    return kb

def add_kw_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🔏 Từ khóa", callback_data="set_keyword"),
        InlineKeyboardButton("📝 Soạn văn bản", callback_data="set_text"),
        InlineKeyboardButton("📷 Hình ảnh", callback_data="set_image"),
        InlineKeyboardButton("🔗 Nút", callback_data="set_button"),
        InlineKeyboardButton("👀 Preview", callback_data="preview"),
        InlineKeyboardButton("💾 Lưu", callback_data="save"),
    )
    kb.add(InlineKeyboardButton("⬅️ Quay lại", callback_data="kw_menu"))
    return kb

# ===== COMMAND =====
@dp.message_handler(commands=["start"])
async def start(msg: types.Message):
    if msg.from_user.id != OWNER_ID:
        return
    await msg.answer("📌 MENU CHÍNH", reply_markup=main_menu())

# ===== CALLBACK =====
@dp.callback_query_handler(lambda c: True)
async def callbacks(call: types.CallbackQuery):
    uid = call.from_user.id
    if uid != OWNER_ID:
        await call.answer("❌ Không có quyền", show_alert=True)
        return

    data = call.data

    if data == "kw_menu":
        await call.message.edit_text("🔑 QUẢN LÝ TỪ KHÓA", reply_markup=kw_menu())

    elif data == "back_main":
        await call.message.edit_text("📌 MENU CHÍNH", reply_markup=main_menu())

    elif data == "add_kw":
        user_state[uid] = {"keyword": "", "text": "", "image": "", "buttons": ""}
        await call.message.edit_text("➕ THÊM TỪ KHÓA", reply_markup=add_kw_menu())

    elif data == "set_keyword":
        user_state[uid]["step"] = "keyword"
        await call.message.answer("🔏 Nhập TỪ KHÓA:")

    elif data == "set_text":
        user_state[uid]["step"] = "text"
        await call.message.answer(
            "📝 Nhập VĂN BẢN theo MẪU:\n\n"
            "TT66hhnGtCietkCNd4izkuUEiRFmSygqLD\n\n"
            "点击复制唯一地址 <a href=\"https://t.me/gonggao\">@gonggao</a>\n\n"
            "新币 pay 转账 ID：88888\n\n"
            "1、请 @担保 确认。"
        )

    elif data == "set_image":
        user_state[uid]["step"] = "image"
        await call.message.answer("📷 Gửi ẢNH (hoặc gõ bỏ trống):")

    elif data == "set_button":
        user_state[uid]["step"] = "button"
        await call.message.answer(
            "🔗 Nhập NÚT theo dạng:\n"
            "Tên nút | https://example.com\n"
            "(mỗi dòng 1 nút)"
        )

    elif data == "preview":
        d = user_state.get(uid)
        if not d:
            return
        kb = InlineKeyboardMarkup()
        if d["buttons"]:
            for line in d["buttons"].splitlines():
                if "|" in line:
                    t, l = line.split("|", 1)
                    kb.add(InlineKeyboardButton(t.strip(), url=l.strip()))
        if d["image"]:
            await bot.send_photo(call.message.chat.id, d["image"], caption=d["text"], reply_markup=kb)
        else:
            await bot.send_message(call.message.chat.id, d["text"], reply_markup=kb)

    elif data == "save":
        d = user_state.get(uid)
        if not d or not d["keyword"]:
            await call.answer("❌ Thiếu từ khóa", show_alert=True)
            return
        cur.execute(
            "INSERT INTO keywords (keyword,text,image,buttons) VALUES (?,?,?,?)",
            (d["keyword"], d["text"], d["image"], d["buttons"])
        )
        db.commit()
        await call.message.edit_text("✅ Đã lưu từ khóa", reply_markup=kw_menu())

    elif data == "list_kw":
        rows = cur.execute("SELECT keyword FROM keywords").fetchall()
        text = "📋 DANH SÁCH TỪ KHÓA:\n\n"
        text += "\n".join(f"• {r[0]}" for r in rows) if rows else "Chưa có"
        await call.message.edit_text(text, reply_markup=kw_menu())

# ===== INPUT =====
@dp.message_handler(content_types=types.ContentTypes.TEXT)
async def text_input(msg: types.Message):
    uid = msg.from_user.id
    if uid != OWNER_ID or uid not in user_state:
        return
    step = user_state[uid].get("step")
    if step == "keyword":
        user_state[uid]["keyword"] = msg.text.strip()
        await msg.answer("✅ Đã lưu từ khóa")
    elif step == "text":
        user_state[uid]["text"] = msg.text
        await msg.answer("✅ Đã lưu văn bản")
    elif step == "button":
        user_state[uid]["buttons"] = msg.text
        await msg.answer("✅ Đã lưu nút")

@dp.message_handler(content_types=types.ContentTypes.PHOTO)
async def photo_input(msg: types.Message):
    uid = msg.from_user.id
    if uid != OWNER_ID or uid not in user_state:
        return
    if user_state[uid].get("step") == "image":
        user_state[uid]["image"] = msg.photo[-1].file_id
        await msg.answer("✅ Đã lưu ảnh")

# ===== GROUP AUTO REPLY =====
@dp.message_handler(content_types=types.ContentTypes.TEXT, chat_type=[types.ChatType.GROUP, types.ChatType.SUPERGROUP])
async def group_reply(msg: types.Message):
    rows = cur.execute("SELECT * FROM keywords").fetchall()
    for r in rows:
        if r[1] in msg.text:
            kb = InlineKeyboardMarkup()
            if r[4]:
                for line in r[4].splitlines():
                    if "|" in line:
                        t, l = line.split("|", 1)
                        kb.add(InlineKeyboardButton(t.strip(), url=l.strip()))
            if r[3]:
                await msg.reply_photo(r[3], caption=r[2], reply_markup=kb)
            else:
                await msg.reply(r[2], reply_markup=kb)
            break

# ===== BOT ADDED TO GROUP =====
@dp.message_handler(content_types=types.ContentTypes.NEW_CHAT_MEMBERS)
async def bot_added(msg: types.Message):
    for m in msg.new_chat_members:
        if m.id == (await bot.get_me()).id:
            await msg.reply("🤖 Bot từ khóa đã sẵn sàng hoạt động!")

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
