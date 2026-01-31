import os
import re
import sqlite3
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))

# ================== DB ==================
conn = sqlite3.connect("bot.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS keywords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword TEXT,
    mode TEXT,
    reply_text TEXT,
    image TEXT,
    buttons TEXT,
    group_id INTEGER
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS settings (
    user_id INTEGER PRIMARY KEY,
    lang TEXT
)
""")
conn.commit()

# ================== LANG ==================
LANG = {
    "vi": {
        "start": "🤖 Bot phản hồi từ khóa\nChọn chức năng:",
        "add": "➕ Thêm từ khóa",
        "list": "📋 Danh sách từ khóa",
        "send_kw": "Gửi từ khóa",
        "send_reply": "Gửi nội dung trả lời (HTML)",
        "send_img": "Gửi ảnh (hoặc /skip)",
    },
    "zh": {
        "start": "🤖 关键词自动回复\n请选择：",
        "add": "➕ 添加关键词",
        "list": "📋 关键词列表",
        "send_kw": "发送关键词",
        "send_reply": "发送回复内容 (HTML)",
        "send_img": "发送图片 (或 /skip)",
    }
}

def get_lang(uid):
    cur.execute("SELECT lang FROM settings WHERE user_id=?", (uid,))
    r = cur.fetchone()
    return r[0] if r else "vi"

# ================== START ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid != OWNER_ID:
        return

    lang = get_lang(uid)
    kb = [
        [InlineKeyboardButton(LANG[lang]["add"], callback_data="add_kw")],
        [InlineKeyboardButton(LANG[lang]["list"], callback_data="list_kw")],
        [
            InlineKeyboardButton("🇻🇳 VI", callback_data="lang_vi"),
            InlineKeyboardButton("🇨🇳 中文", callback_data="lang_zh"),
        ]
    ]
    await update.message.reply_text(
        LANG[lang]["start"],
        reply_markup=InlineKeyboardMarkup(kb)
    )

# ================== ADD KEYWORD FLOW ==================
USER_STATE = {}

async def cb_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id

    if uid != OWNER_ID:
        return

    if q.data.startswith("lang_"):
        cur.execute(
            "REPLACE INTO settings VALUES (?,?)",
            (uid, q.data.split("_")[1])
        )
        conn.commit()
        await q.edit_message_text("✅ OK")
        return

    if q.data == "add_kw":
        USER_STATE[uid] = {"step": "kw"}
        await q.message.reply_text("Gửi từ khóa:")
        return

    if q.data == "list_kw":
        cur.execute("SELECT id, keyword FROM keywords")
        rows = cur.fetchall()
        if not rows:
            await q.message.reply_text("Trống")
            return

        for r in rows:
            kb = [
                [
                    InlineKeyboardButton("👁 Preview", callback_data=f"pv_{r[0]}"),
                    InlineKeyboardButton("🗑 Xóa", callback_data=f"del_{r[0]}")
                ]
            ]
            await q.message.reply_text(
                f"🔑 {r[1]}",
                reply_markup=InlineKeyboardMarkup(kb)
            )

    if q.data.startswith("del_"):
        cur.execute("DELETE FROM keywords WHERE id=?", (q.data[4:],))
        conn.commit()
        await q.message.reply_text("🗑 Đã xóa")

    if q.data.startswith("pv_"):
        cur.execute(
            "SELECT reply_text,image,buttons FROM keywords WHERE id=?",
            (q.data[3:],)
        )
        t, img, btn = cur.fetchone()

        kb = []
        if btn:
            kb.append([InlineKeyboardButton("🔗 Link", url=btn)])

        if img:
            await q.message.reply_photo(
                img, caption=t, parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(kb) if kb else None
            )
        else:
            await q.message.reply_text(
                t, parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(kb) if kb else None
            )

# ================== MESSAGE HANDLER ==================
async def msg_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    # ===== ADD FLOW =====
    if uid in USER_STATE:
        st = USER_STATE[uid]

        if st["step"] == "kw":
            st["keyword"] = update.message.text
            st["step"] = "reply"
            await update.message.reply_text("Gửi nội dung trả lời (HTML)")
            return

        if st["step"] == "reply":
            st["reply"] = update.message.text
            st["step"] = "img"
            await update.message.reply_text("Gửi ảnh hoặc /skip")
            return

        if st["step"] == "img":
            st["image"] = update.message.photo[-1].file_id if update.message.photo else None
            st["step"] = "btn"
            await update.message.reply_text("Gửi link nút hoặc /skip")
            return

        if st["step"] == "btn":
            btn = update.message.text if update.message.text != "/skip" else None

            cur.execute("""
            INSERT INTO keywords
            (keyword,mode,reply_text,image,buttons,group_id)
            VALUES (?,?,?,?,?,?)
            """, (
                st["keyword"], "contains",
                st["reply"], st["image"], btn, None
            ))
            conn.commit()
            USER_STATE.pop(uid)

            await update.message.reply_text("✅ Đã lưu")
            return

    # ===== GROUP AUTO REPLY =====
    if update.message.chat.type in ["group", "supergroup"]:
        text = update.message.text or ""
        gid = update.message.chat.id

        cur.execute("SELECT keyword,reply_text,image,buttons FROM keywords")
        for k, r, img, btn in cur.fetchall():
            if k in text:
                kb = []
                if btn:
                    kb.append([InlineKeyboardButton("🔗 Link", url=btn)])

                if img:
                    await update.message.reply_photo(
                        img, caption=r, parse_mode="HTML",
                        reply_markup=InlineKeyboardMarkup(kb) if kb else None
                    )
                else:
                    await update.message.reply_text(
                        r, parse_mode="HTML",
                        reply_markup=InlineKeyboardMarkup(kb) if kb else None
                    )
                break

# ================== BOT ADDED TO GROUP ==================
async def added(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.new_chat_members:
        for u in update.message.new_chat_members:
            if u.id == context.bot.id:
                await update.message.reply_text(
                    "🤖 N组防骗助手为您服务\n我正在初始化配置，请稍后"
                )

# ================== MAIN ==================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(cb_handler))
app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, added))
app.add_handler(MessageHandler(filters.ALL, msg_handler))

app.run_polling()
