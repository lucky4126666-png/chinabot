import os
import sqlite3
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = 8572604188   # 👈 chủ bot

# ================= DB =================
conn = sqlite3.connect("bot.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS keywords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword TEXT,
    mode TEXT,
    reply_text TEXT,
    reply_image TEXT,
    reply_buttons TEXT,
    group_id INTEGER
)
""")

cur.execute(
    "INSERT OR IGNORE INTO settings (key,value) VALUES ('lang','vi')"
)
conn.commit()

# ================= LANG =================
TEXT = {
    "vi": {
        "start": "📌 MENU CHÍNH",
        "kw_manage": "📌 Quản lý từ khóa",
        "kw_add": "➕ Thêm từ khóa",
        "kw_list": "📋 Danh sách từ khóa",
        "settings": "⚙️ Cài đặt",
        "lang": "🌐 Ngôn ngữ",
        "only_owner": "❌ Chỉ chủ bot mới dùng",
        "enter_kw": "✏️ Gửi từ khóa",
        "enter_reply": "💬 Gửi nội dung trả lời",
        "enter_buttons": "🔘 Gửi nút (hoặc /skip)",
        "saved": "✅ Đã lưu",
        "preview": "👁 Xem trước",
        "delete": "🗑 Xóa",
    },
    "zh": {
        "start": "📌 主菜单",
        "kw_manage": "📌 关键词管理",
        "kw_add": "➕ 添加关键词",
        "kw_list": "📋 关键词列表",
        "settings": "⚙️ 设置",
        "lang": "🌐 语言",
        "only_owner": "❌ 仅限机器人主人",
        "enter_kw": "✏️ 发送关键词",
        "enter_reply": "💬 发送回复内容",
        "enter_buttons": "🔘 发送按钮（或 /skip）",
        "saved": "✅ 已保存",
        "preview": "👁 预览",
        "delete": "🗑 删除",
    }
}

def get_lang():
    cur.execute("SELECT value FROM settings WHERE key='lang'")
    return cur.fetchone()[0]

def t(key):
    return TEXT[get_lang()].get(key, key)

# ================= BUTTON PARSE =================
def parse_buttons(raw: str):
    rows = []
    for line in raw.split("\n"):
        btns = []
        for part in line.split("&&"):
            if "-" in part:
                text, url = part.split("-", 1)
                btns.append(InlineKeyboardButton(text.strip(), url=url.strip()))
        if btns:
            rows.append(btns)
    return InlineKeyboardMarkup(rows) if rows else None

# ================= /START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(t("kw_manage"), callback_data="kw_menu")],
        [InlineKeyboardButton(t("settings"), callback_data="settings")]
    ])
    await update.message.reply_text(t("start"), reply_markup=kb)

# ================= CALLBACK =================
async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.from_user.id != OWNER_ID:
        await q.answer(t("only_owner"), show_alert=True)
        return

    data = q.data

    if data == "kw_menu":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(t("kw_add"), callback_data="kw_add")],
            [InlineKeyboardButton(t("kw_list"), callback_data="kw_list")]
        ])
        await q.edit_message_text(t("kw_manage"), reply_markup=kb)

    elif data == "kw_add":
        context.user_data.clear()
        context.user_data["step"] = "kw"
        await q.message.reply_text(t("enter_kw"))

    elif data == "kw_list":
        cur.execute("SELECT id,keyword FROM keywords")
        rows = cur.fetchall()
        if not rows:
            await q.message.reply_text("Empty")
            return
        kb = [
            [InlineKeyboardButton(r[1], callback_data=f"kw_{r[0]}")]
            for r in rows
        ]
        await q.message.reply_text(
            t("kw_list"),
            reply_markup=InlineKeyboardMarkup(kb)
        )

    elif data.startswith("kw_"):
        kid = int(data.split("_")[1])
        context.user_data["edit_id"] = kid
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(t("preview"), callback_data="preview")],
            [InlineKeyboardButton(t("delete"), callback_data="delete")]
        ])
        await q.message.reply_text("Keyword", reply_markup=kb)

    elif data == "delete":
        kid = context.user_data.get("edit_id")
        cur.execute("DELETE FROM keywords WHERE id=?", (kid,))
        conn.commit()
        await q.message.reply_text("Deleted")

    elif data == "preview":
        kid = context.user_data.get("edit_id")
        cur.execute(
            "SELECT reply_text,reply_image,reply_buttons FROM keywords WHERE id=?",
            (kid,)
        )
        r = cur.fetchone()
        kb = parse_buttons(r[2]) if r[2] else None
        if r[1]:
            await q.message.reply_photo(r[1], caption=r[0], reply_markup=kb)
        else:
            await q.message.reply_text(r[0], reply_markup=kb)

    elif data == "settings":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🇻🇳 Tiếng Việt", callback_data="lang_vi")],
            [InlineKeyboardButton("🇨🇳 中文", callback_data="lang_zh")]
        ])
        await q.edit_message_text(t("lang"), reply_markup=kb)

    elif data == "lang_vi":
        cur.execute("UPDATE settings SET value='vi' WHERE key='lang'")
        conn.commit()
        await q.edit_message_text("🇻🇳 OK")

    elif data == "lang_zh":
        cur.execute("UPDATE settings SET value='zh' WHERE key='lang'")
        conn.commit()
        await q.edit_message_text("🇨🇳 OK")

# ================= MESSAGE (PRIVATE) =================
async def private_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return

    text = update.message.text

    if context.user_data.get("step") == "kw":
        context.user_data["keyword"] = text
        context.user_data["step"] = "reply"
        await update.message.reply_text(t("enter_reply"))

    elif context.user_data.get("step") == "reply":
        context.user_data["reply"] = text
        context.user_data["step"] = "buttons"
        await update.message.reply_text(t("enter_buttons"))

    elif context.user_data.get("step") == "buttons":
        buttons = None if text == "/skip" else text
        cur.execute("""
        INSERT INTO keywords (keyword,mode,reply_text,reply_buttons)
        VALUES (?,?,?,?)
        """, (
            context.user_data["keyword"],
            "contains",
            context.user_data["reply"],
            buttons
        ))
        conn.commit()
        context.user_data.clear()
        await update.message.reply_text(t("saved"))

# ================= GROUP AUTO REPLY =================
async def group_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text
    gid = update.effective_chat.id

    cur.execute("SELECT keyword,mode,reply_text,reply_image,reply_buttons FROM keywords")
    for k, mode, text, img, btn in cur.fetchall():
        hit = (msg == k) if mode == "exact" else (k in msg)
        if hit:
            kb = parse_buttons(btn) if btn else None
            if img:
                await update.message.reply_photo(img, caption=text, reply_markup=kb)
            else:
                await update.message.reply_text(text, reply_markup=kb)
            break

# ================= RUN =================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.TEXT, private_msg))
    app.add_handler(MessageHandler(filters.ChatType.GROUPS & filters.TEXT, group_msg))
    app.run_polling()

if __name__ == "__main__":
    main()
