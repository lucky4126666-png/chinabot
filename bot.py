from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = "8234123060:AAEtxTPA0TNBgBgQGYKY2BRRMhMOfNp3TJ4"
OWNER_ID = 8572604188


def is_owner(update: Update):
    return update.effective_user and update.effective_user.id == OWNER_ID


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        await update.message.reply_text("无权限")
        return

    keyboard = [
        [InlineKeyboardButton("反应自动回复", callback_data="auto_reply")],
        [InlineKeyboardButton("群管理设置", callback_data="group_setting")],
        [InlineKeyboardButton("系统设置", callback_data="system_setting")]
    ]

    await update.message.reply_text(
        "管理菜单",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not is_owner(update):
        await query.edit_message_text("无权限")
        return

    data = query.data

    if data == "auto_reply":
        keyboard = [
            [InlineKeyboardButton("关键词列表", callback_data="keyword_list")],
            [InlineKeyboardButton("添加关键词", callback_data="keyword_add")],
            [InlineKeyboardButton("返回", callback_data="back_main")]
        ]
        await query.edit_message_text("反应自动回复", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "keyword_list":
        keyboard = [
            [InlineKeyboardButton("关键词详情", callback_data="keyword_detail")],
            [InlineKeyboardButton("返回", callback_data="auto_reply")]
        ]
        await query.edit_message_text("关键词列表", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "keyword_detail":
        keyboard = [
            [InlineKeyboardButton("修改关键词", callback_data="kw_edit")],
            [InlineKeyboardButton("回复内容", callback_data="kw_text")],
            [InlineKeyboardButton("图片", callback_data="kw_image")],
            [InlineKeyboardButton("按钮", callback_data="kw_button")],
            [InlineKeyboardButton("预览", callback_data="kw_preview")],
            [InlineKeyboardButton("删除", callback_data="kw_delete")],
            [InlineKeyboardButton("返回", callback_data="keyword_list")]
        ]
        await query.edit_message_text("关键词详情", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "group_setting":
        keyboard = [
            [InlineKeyboardButton("已绑定群组", callback_data="group_list")],
            [InlineKeyboardButton("绑定新群", callback_data="group_bind")],
            [InlineKeyboardButton("返回", callback_data="back_main")]
        ]
        await query.edit_message_text("群管理设置", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "system_setting":
        keyboard = [
            [InlineKeyboardButton("语言设置", callback_data="lang_setting")],
            [InlineKeyboardButton("权限设置", callback_data="permission_setting")],
            [InlineKeyboardButton("返回", callback_data="back_main")]
        ]
        await query.edit_message_text("系统设置", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "back_main":
        keyboard = [
            [InlineKeyboardButton("反应自动回复", callback_data="auto_reply")],
            [InlineKeyboardButton("群管理设置", callback_data="group_setting")],
            [InlineKeyboardButton("系统设置", callback_data="system_setting")]
        ]
        await query.edit_message_text("管理菜单", reply_markup=InlineKeyboardMarkup(keyboard))


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.run_polling()


if __name__ == "__main__":
    main()
