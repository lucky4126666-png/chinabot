import os, json, re, sqlite3
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))

# ---------- DB ----------
db = sqlite3.connect("data.db", check_same_thread=False)
cur = db.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS keywords(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 keyword TEXT,
 match_type TEXT,
 text TEXT,
 photo TEXT,
 buttons TEXT,
 groups TEXT
)
""")
db.commit()

# ---------- HELPERS ----------
def owner(update):
    return update.effective_user.id == OWNER_ID

def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📌 Quản lý từ khóa", callback_data="kw_menu")],
        [InlineKeyboardButton("⚙️ Cài đặt", callback_data="settings")]
    ])

# ---------- START ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not owner(update):
        return
    await update.message.reply_text("⚙️ MENU BOT", reply_markup=menu())

# ---------- KEYWORD MENU ----------
async def kw_menu(update, context):
    q = update.callback_query; await q.answer()
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Danh sách từ khóa", callback_data="kw_list")],
        [InlineKeyboardButton("➕ Thêm từ khóa", callback_data="kw_add")],
        [InlineKeyboardButton("⬅️ Quay lại", callback_data="start")]
    ])
    await q.edit_message_text("📌 Quản lý từ khóa", reply_markup=kb)

# ---------- LIST ----------
async def kw_list(update, context):
    q = update.callback_query; await q.answer()
    rows = cur.execute("SELECT id, keyword FROM keywords").fetchall()

    if not rows:
        await q.edit_message_text("⚠️ Chưa có từ khóa")
        return

    kb = [[InlineKeyboardButton(k, callback_data=f"kw_view:{i}")]
          for i, k in rows]
    kb.append([InlineKeyboardButton("⬅️", callback_data="kw_menu")])
    await q.edit_message_text("📋 Danh sách", reply_markup=InlineKeyboardMarkup(kb))

# ---------- ADD ----------
async def kw_add(update, context):
    q = update.callback_query; await q.answer()
    context.user_data.clear()
    context.user_data["step"] = "keyword"
    await q.edit_message_text("✏️ Gửi từ khóa")

# ---------- PRIVATE FLOW ----------
async def private_msg(update, context):
    if not owner(update):
        return

    step = context.user_data.get("step")

    if step == "keyword":
        context.user_data["keyword"] = update.message.text
        context.user_data["step"] = "text"
        await update.message.reply_text("📝 Gửi nội dung trả lời")

    elif step == "text":
        context.user_data["text"] = update.message.text
        context.user_data["step"] = "photo"
        await update.message.reply_text("🖼️ Gửi ảnh (hoặc /skip)")

    elif step == "photo":
        if update.message.photo:
            context.user_data["photo"] = update.message.photo[-1].file_id
        else:
            context.user_data["photo"] = None
        context.user_data["step"] = "buttons"
        await update.message.reply_text("🔘 Gửi nút: text|url (mỗi dòng 1 nút) hoặc /skip")

    elif step == "buttons":
        btns = []
        if update.message.text != "/skip":
            for line in update.message.text.splitlines():
                t, u = line.split("|")
                btns.append({"text": t, "url": u})

        context.user_data["buttons"] = btns
        context.user_data["step"] = "preview"

        kb = None
        if btns:
            kb = InlineKeyboardMarkup([[InlineKeyboardButton(b["text"], url=b["url"])] for b in btns])

        if context.user_data["photo"]:
            await update.message.reply_photo(
                context.user_data["photo"],
                caption=context.user_data["text"],
                reply_markup=kb
            )
        else:
            await update.message.reply_text(context.user_data["text"], reply_markup=kb)

        await update.message.reply_text(
            "👀 Preview\nLưu?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Lưu", callback_data="kw_save"),
                 InlineKeyboardButton("❌ Hủy", callback_data="start")]
            ])
        )

# ---------- SAVE ----------
async def kw_save(update, context):
    q = update.callback_query; await q.answer()
    d = context.user_data

    cur.execute("""
    INSERT INTO keywords(keyword, match_type, text, photo, buttons, groups)
    VALUES (?,?,?,?,?,?)
    """, (
        d["keyword"], "exact", d["text"],
        d["photo"], json.dumps(d["buttons"]), "*"
    ))
    db.commit()
    context.user_data.clear()
    await q.edit_message_text("✅ Đã lưu")

# ---------- GROUP RESPONSE ----------
async def group_msg(update, context):
    text = update.message.text
    gid = str(update.message.chat_id)

    rows = cur.execute("SELECT * FROM keywords").fetchall()

    for _, kw, mtype, rtext, photo, btns, groups in rows:
        if groups != "*" and gid not in groups.split(","):
            continue

        ok = False
        if mtype == "exact" and text == kw: ok = True
        if mtype == "contains" and kw in text: ok = True
        if mtype == "startswith" and text.startswith(kw): ok = True
        if mtype == "regex" and re.search(kw, text): ok = True

        if ok:
            kb = None
            btns = json.loads(btns)
            if btns:
                kb = InlineKeyboardMarkup([[InlineKeyboardButton(b["text"], url=b["url"])] for b in btns])

            if photo:
                await update.message.reply_photo(photo, caption=rtext, reply_markup=kb)
            else:
                await update.message.reply_text(rtext, reply_markup=kb)
            break

# ---------- CALLBACK ----------
async def callbacks(update, context):
    d = update.callback_query.data

    if d == "start":
        await start(update, context)
    elif d == "kw_menu":
        await kw_menu(update, context)
    elif d == "kw_list":
        await kw_list(update, context)
    elif d == "kw_add":
        await kw_add(update, context)
    elif d == "kw_save":
        await kw_save(update, context)

# ---------- MAIN ----------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callbacks))
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.ALL, private_msg))
    app.add_handler(MessageHandler(filters.ChatType.GROUPS & filters.TEXT, group_msg))

    app.run_polling()

if __name__ == "__main__":
    main()
