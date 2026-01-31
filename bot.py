import logging
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

# ================== CONFIG ==================
BOT_TOKEN = "8582300335:AAHWQjiBrWXYn-xsJ6TIhXxCrihKg-AEHfw"
OWNER_ID = 8572604188

# Chủ bot tự set dữ liệu tại đây
KEYWORD_DATA = {
    "hello": {
        "text": "👋 Xin chào! Đây là nội dung do chủ bot cài đặt.",
        "image": None,  # hoặc link ảnh
    },
    "test": {
        "text": "✅ Đây là tin nhắn test",
        "image": "https://picsum.photos/400/300",
    },
}

# ================== LOG ==================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# ================== MENU ==================
def start_menu():
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("反应自动回复", callback_data="auto_reply")],
            [InlineKeyboardButton("群管理设置", callback_data="group_setting")],
            [InlineKeyboardButton("系统设置", callback_data="system_setting")],
        ]
    )

def auto_reply_menu():
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("关键词列表", callback_data="keyword_list")],
            [InlineKeyboardButton("添加关键词", callback_data="keyword_add")],
            [InlineKeyboardButton("⬅ 返回", callback_data="back_start")],
        ]
    )

# ================== HANDLERS ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ Bạn không có quyền sử dụng bot này.")
        return

    await update.message.reply_text(
        "🤖 Bot quản lý phản hồi tự động",
        reply_markup=start_menu(),
    )

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "auto_reply":
        await query.edit_message_text(
            "⚙️ Phản hồi tự động",
            reply_markup=auto_reply_menu(),
        )

    elif query.data == "keyword_list":
        text = "📄 **Danh sách từ khóa:**\n\n"
        for k in KEYWORD_DATA.keys():
            text += f"- `{k}`\n"
        await query.edit_message_text(text, parse_mode="Markdown")

    elif query.data == "group_setting":
        await query.edit_message_text("👥 Cài đặt quản lý nhóm (đang phát triển)")

    elif query.data == "system_setting":
        await query.edit_message_text("⚙️ Cài đặt hệ thống (đang phát triển)")

    elif query.data == "back_start":
        await query.edit_message_text(
            "🤖 Bot quản lý phản hồi tự động",
            reply_markup=start_menu(),
        )

# ================== AUTO REPLY ==================
async def keyword_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text.lower()

    for keyword, data in KEYWORD_DATA.items():
        if keyword in text:
            if data["image"]:
                await update.message.reply_photo(
                    photo=data["image"],
                    caption=data["text"],
                )
            else:
                await update.message.reply_text(data["text"])
            break

# ================== MAIN ==================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(menu_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, keyword_reply))

    print("🤖 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
