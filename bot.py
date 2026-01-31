import os
import sqlite3
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))

# ================= DB =================
conn = sqlite3.connect("data.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS keywords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword TEXT,
    reply_text TEXT,
    reply_image TEXT,
    reply_buttons TEXT
)
""")
conn.commit()

# ================= UTILS =================
def is_owner(update: Update):
    return update.effective_user.id == OWNER_ID

def build_buttons(raw: str):
    if not raw:
        return None
    keyboard = []
    for line in raw.split("\n"):
        row = []
        for part in line.split("&&"):
            if "-" not in part:
                continue
            text, url = part.split("-", 1)
            row.append(
                InlineKeyboardButton(
                    text=text.strip(),
                    url=url.strip()
                )
            )
        if row:
            keyboard.append(row)
    return InlineKeyboardMarkup(keyboard) if keyboard else None

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return

    await update.message.reply_text(
        "📌 QUẢN LÝ TỪ KHÓA\n\n"
        "1️⃣ Gửi từ khóa\n"
        "2️⃣ Gửi nội dung trả lời\n"
        "3️⃣ Gửi ảnh (hoặc /skip)\n"
        "4️⃣ Gửi nút inline (hoặc /skip)\n\n"
        "📋 /list – Danh sách từ khóa"
    )
    context.user_data.clear()
    context.user_data["step"] = "keyword"

# ================= FLOW ADD =================
async def owner_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return

    step = context.user_data.get("step")

    # STEP 1: keyword
    if step == "keyword":
        context.user_data["keyword"] = update.message.text.strip()
        context.user_data["step"] = "text"
        await update.message.reply_text("✏️ Gửi nội dung trả lời")
        return

    # STEP 2: reply text
    if step == "text":
        context.user_data["reply_text"] = update.message.text
        context.user_data["step"] = "image"
        await update.message.reply_text("🖼 Gửi ảnh (hoặc /skip)")
        return

    # STEP 3: image
    if step == "image":
        if update.message.photo:
            context.user_data["reply_image"] = update.message.photo[-1].file_id
        elif update.message.text == "/skip":
            context.user_data["reply_image"] = ""
        else:
            context.user_data["reply_image"] = update.message.text.strip()
        context.user_data["step"] = "buttons"
        await update.message.reply_text(
            "🔘 Gửi nút inline\n"
            "VD:\n"
            "Telegram - https://t.me/xxx && Website - https://abc.com\n"
            "Hoặc /skip"
        )
        return

    # STEP 4: buttons
    if step == "buttons":
        if update.message.text == "/skip":
            context.user_data["reply_buttons"] = ""
        else:
            context.user_data["reply_buttons"] = update.message.text

        cur.execute(
            "INSERT INTO keywords (keyword, reply_text, reply_image, reply_buttons) VALUES (?,?,?,?)",
            (
                context.user_data["keyword"],
                context.user_data["reply_text"],
                context.user_data.get("reply_image", ""),
                context.user_data.get("reply_buttons", "")
            )
        )
        conn.commit()

        await update.message.reply_text("✅ Đã lưu từ khóa")
        context.user_data.clear()

# ================= LIST =================
async def list_keywords(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return

    cur.execute("SELECT id, keyword FROM keywords")
    rows = cur.fetchall()

    if not rows:
        await update.message.reply_text("❌ Chưa có từ khóa")
        return

    kb = []
    for k_id, kw in rows:
        kb.append([
            InlineKeyboardButton(kw, callback_data=f"view_{k_id}"),
            InlineKeyboardButton("🗑", callback_data=f"del_{k_id}")
        ])

    await update.message.reply_text(
        "📋 Danh sách từ khóa",
        reply_markup=InlineKeyboardMarkup(kb)
    )

# ================= CALLBACK =================
async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    data = q.data

    # VIEW
    if data.startswith("view_"):
        k_id = int(data.split("_")[1])
        cur.execute(
            "SELECT reply_text, reply_image, reply_buttons FROM keywords WHERE id=?",
            (k_id,)
        )
        row = cur.fetchone()
        if not row:
            return

        text, image, buttons = row
        markup = build_buttons(buttons)

        if image:
            await q.message.reply_photo(
                photo=image,
                caption=text,
                reply_markup=markup,
                parse_mode=None
            )
        else:
            await q.message.reply_text(
                text,
                reply_markup=markup,
                parse_mode=None
            )

    # DELETE
    if data.startswith("del_"):
        k_id = int(data.split("_")[1])
        cur.execute("DELETE FROM keywords WHERE id=?", (k_id,))
        conn.commit()
        await q.message.reply_text("🗑 Đã xóa")

# ================= GROUP AUTO REPLY =================
async def group_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text

    cur.execute("SELECT keyword, reply_text, reply_image, reply_buttons FROM keywords")
    rows = cur.fetchall()

    for kw, r_text, r_img, r_btn in rows:
        if kw in text:
            markup = build_buttons(r_btn)
            if r_img:
                await update.message.reply_photo(
                    photo=r_img,
                    caption=r_text,
                    reply_markup=markup,
                    parse_mode=None
                )
            else:
                await update.message.reply_text(
                    r_text,
                    reply_markup=markup,
                    parse_mode=None
                )
            break

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("list", list_keywords))
    app.add_handler(CallbackQueryHandler(callbacks))
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE, owner_flow))
    app.add_handler(MessageHandler(filters.ChatType.GROUPS, group_reply))

    app.run_polling()

if __name__ == "__main__":
    main()
