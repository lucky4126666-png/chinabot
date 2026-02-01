import json
import os
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 8572604188
DATA_FILE = "data.json"

# ================= DATA =================
def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(d):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)

data = load_data()

# ================= MENUS =================
def admin_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Thêm từ khóa", callback_data="add_kw")],
        [InlineKeyboardButton("📌 Danh sách từ khóa", callback_data="list_kw")]
    ])

def keyword_menu(key):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Sửa nội dung", callback_data=f"text:{key}")],
        [InlineKeyboardButton("🖼️ Thêm ảnh", callback_data=f"img:{key}")],
        [InlineKeyboardButton("🔘 Thêm nút", callback_data=f"btn:{key}")],
        [InlineKeyboardButton("👁️ Xem trước", callback_data=f"preview:{key}")],
        [InlineKeyboardButton("🗑️ Xóa", callback_data=f"del:{key}")],
        [InlineKeyboardButton("⬅️ Trở lại", callback_data="back")]
    ])

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type != "private":
        return

    if update.effective_user.id == ADMIN_ID:
        await update.message.reply_text(
            "⚙️ BẢNG ĐIỀU KHIỂN BOT (ADMIN)",
            reply_markup=admin_menu()
        )

# ================= BUTTON HANDLER =================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        return

    cmd = query.data

    if cmd == "add_kw":
        context.user_data["step"] = "wait_keyword"
        await query.message.reply_text("✏️ Nhập từ khóa:")

    elif cmd == "list_kw":
        if not data:
            await query.message.reply_text("📭 Chưa có từ khóa")
            return
        for k in data:
            await query.message.reply_text(f"🔑 {k}", reply_markup=keyword_menu(k))

    elif cmd == "back":
        await query.message.reply_text("⬅️ Quay lại", reply_markup=admin_menu())

    elif cmd.startswith("text:"):
        key = cmd.split(":")[1]
        context.user_data["step"] = "wait_text"
        context.user_data["key"] = key
        await query.message.reply_text("✏️ Gửi nội dung mới:")

    elif cmd.startswith("img:"):
        key = cmd.split(":")[1]
        context.user_data["step"] = "wait_image"
        context.user_data["key"] = key
        await query.message.reply_text("🖼️ Gửi ảnh:")

    elif cmd.startswith("btn:"):
        key = cmd.split(":")[1]
        context.user_data["step"] = "wait_button"
        context.user_data["key"] = key
        await query.message.reply_text("🔘 Nhập: Tên nút | Link")

    elif cmd.startswith("del:"):
        key = cmd.split(":")[1]
        data.pop(key, None)
        save_data(data)
        await query.message.reply_text("🗑️ Đã xóa từ khóa")

    elif cmd.startswith("preview:"):
        key = cmd.split(":")[1]
        await send_reply(query.message, key)

# ================= TEXT ROUTER =================
async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text.strip()
    chat_type = update.message.chat.type
    user_id = update.effective_user.id

    # ===== ADMIN SET (CHAT RIÊNG) =====
    if chat_type == "private" and user_id == ADMIN_ID:
        step = context.user_data.get("step")

        if step == "wait_keyword":
            key = msg.lower()
            data[key] = {"text": "", "images": [], "buttons": []}
            save_data(data)
            context.user_data.clear()
            await update.message.reply_text(
                f"✅ Đã tạo từ khóa: {key}",
                reply_markup=keyword_menu(key)
            )
            return

        if step == "wait_text":
            key = context.user_data["key"]
            data[key]["text"] = msg
            save_data(data)
            context.user_data.clear()
            await update.message.reply_text("✅ Đã lưu nội dung")
            return

        if step == "wait_button":
            key = context.user_data["key"]
            if "|" not in msg:
                await update.message.reply_text("❌ Sai định dạng: Tên | Link")
                return
            name, link = msg.split("|", 1)
            data[key]["buttons"].append({
                "text": name.strip(),
                "url": link.strip()
            })
            save_data(data)
            context.user_data.clear()
            await update.message.reply_text("✅ Đã thêm nút")
            return

    # ===== AUTO REPLY (PRIVATE + GROUP) =====
    key = msg.lower()
    if key in data:
        await send_reply(update.message, key)

# ================= PHOTO =================
async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if update.message.chat.type != "private":
        return

    if context.user_data.get("step") == "wait_image":
        key = context.user_data["key"]
        photo_id = update.message.photo[-1].file_id
        data[key]["images"].append(photo_id)
        save_data(data)
        context.user_data.clear()
        await update.message.reply_text("✅ Đã lưu ảnh")

# ================= SEND REPLY =================
async def send_reply(message, key):
    item = data[key]

    if item["text"]:
        await message.reply_text(item["text"])

    for img in item["images"]:
        await message.reply_photo(img)

    if item["buttons"]:
        kb = [
            [InlineKeyboardButton(b["text"], url=b["url"])]
            for b in item["buttons"]
        ]
        await message.reply_text(
            "👇 Chọn:",
            reply_markup=InlineKeyboardMarkup(kb)
        )

# ================= MAIN =================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))

    print("🤖 Bot đang chạy...")
    app.run_polling()

if __name__ == "__main__":
    main()
