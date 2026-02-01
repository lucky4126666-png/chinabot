import json
import os
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 8572604188  # ← ĐỔI ID ADMIN Ở ĐÂY
DATA_FILE = "data.json"


# ---------- DATA ----------
def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


data = load_data()


# ---------- MENUS ----------
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


# ---------- START ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == ADMIN_ID:
        await update.message.reply_text(
            "⚙️ BẢNG ĐIỀU KHIỂN BOT",
            reply_markup=admin_menu()
        )


# ---------- BUTTON HANDLER ----------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user.id
    if user != ADMIN_ID:
        return

    data_btn = query.data

    if data_btn == "add_kw":
        context.user_data["step"] = "wait_keyword"
        await query.message.reply_text("✏️ Nhập từ khóa:")

    elif data_btn == "list_kw":
        if not data:
            await query.message.reply_text("📭 Chưa có từ khóa")
            return
        for key in data:
            await query.message.reply_text(
                f"🔑 {key}",
                reply_markup=keyword_menu(key)
            )

    elif data_btn == "back":
        await query.message.reply_text(
            "⬅️ Quay lại menu",
            reply_markup=admin_menu()
        )

    elif data_btn.startswith("text:"):
        key = data_btn.split(":")[1]
        context.user_data["step"] = "wait_text"
        context.user_data["key"] = key
        await query.message.reply_text("✏️ Gửi nội dung mới:")

    elif data_btn.startswith("img:"):
        key = data_btn.split(":")[1]
        context.user_data["step"] = "wait_image"
        context.user_data["key"] = key
        await query.message.reply_text("🖼️ Gửi ảnh:")

    elif data_btn.startswith("btn:"):
        key = data_btn.split(":")[1]
        context.user_data["step"] = "wait_button"
        context.user_data["key"] = key
        await query.message.reply_text("🔘 Nhập: Tên nút | Link")

    elif data_btn.startswith("del:"):
        key = data_btn.split(":")[1]
        data.pop(key, None)
        save_data(data)
        await query.message.reply_text("🗑️ Đã xóa từ khóa")

    elif data_btn.startswith("preview:"):
        key = data_btn.split(":")[1]
        item = data[key]

        if item["text"]:
            await query.message.reply_text(item["text"])

        for img in item["images"]:
            await query.message.reply_photo(img)

        if item["buttons"]:
            kb = [[InlineKeyboardButton(b["text"], url=b["url"])] for b in item["buttons"]]
            await query.message.reply_text(
                "👇 Nút:",
                reply_markup=InlineKeyboardMarkup(kb)
            )


# ---------- TEXT HANDLER ----------
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    step = context.user_data.get("step")
    msg = update.message.text

    if step == "wait_keyword":
        key = msg.lower()
        data[key] = {"text": "", "images": [], "buttons": []}
        save_data(data)
        context.user_data.clear()
        await update.message.reply_text(
            f"✅ Đã tạo từ khóa: {key}",
            reply_markup=keyword_menu(key)
        )

    elif step == "wait_text":
        key = context.user_data["key"]
        data[key]["text"] = msg
        save_data(data)
        context.user_data.clear()
        await update.message.reply_text("✅ Đã cập nhật nội dung")


# ---------- PHOTO HANDLER ----------
async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if context.user_data.get("step") == "wait_image":
        key = context.user_data["key"]
        file_id = update.message.photo[-1].file_id
        data[key]["images"].append(file_id)
        save_data(data)
        context.user_data.clear()
        await update.message.reply_text("✅ Đã lưu ảnh")


# ---------- BUTTON TEXT ----------
async def button_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if context.user_data.get("step") == "wait_button":
        key = context.user_data["key"]
        if "|" not in update.message.text:
            await update.message.reply_text("❌ Sai định dạng")
            return
        name, link = update.message.text.split("|", 1)
        data[key]["buttons"].append({
            "text": name.strip(),
            "url": link.strip()
        })
        save_data(data)
        context.user_data.clear()
        await update.message.reply_text("✅ Đã thêm nút")


# ---------- AUTO REPLY ----------
async def auto_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    if text not in data:
        return

    item = data[text]

    if item["text"]:
        await update.message.reply_text(item["text"])

    for img in item["images"]:
        await update.message.reply_photo(img)

    if item["buttons"]:
        kb = [[InlineKeyboardButton(b["text"], url=b["url"])] for b in item["buttons"]]
        await update.message.reply_text(
            "👇 Chọn:",
            reply_markup=InlineKeyboardMarkup(kb)
        )


# ---------- MAIN ----------
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, button_text_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, auto_reply))

    print("🤖 Bot đang chạy...")
    app.run_polling()


if __name__ == "__main__":
    main()
