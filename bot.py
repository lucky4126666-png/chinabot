import os
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

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = 8572604188

KEYWORDS = {}
BOUND_GROUPS = set()
SETTINGS = {"lang": "CN"}

# ================= UTILS =================
def is_owner(update: Update):
    return update.effective_user.id == OWNER_ID

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("反应自动回复", callback_data="auto")],
        [InlineKeyboardButton("群管理设置", callback_data="group")],
        [InlineKeyboardButton("系统设置", callback_data="system")]
    ])

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return
    await update.message.reply_text(
        "管理菜单",
        reply_markup=main_menu()
    )

# ================= CALLBACK =================
async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if not is_owner(update):
        return

    data = q.data

    # ===== AUTO REPLY =====
    if data == "auto":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("关键词列表", callback_data="kw_list")],
            [InlineKeyboardButton("添加关键词", callback_data="kw_add")],
            [InlineKeyboardButton("返回", callback_data="back")]
        ])
        await q.edit_message_text("反应自动回复", reply_markup=kb)

    elif data == "kw_list":
        if not KEYWORDS:
            await q.edit_message_text("暂无关键词", reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("返回", callback_data="auto")]
            ]))
            return

        kb = [[InlineKeyboardButton(k, callback_data=f"kw:{k}")] for k in KEYWORDS]
        kb.append([InlineKeyboardButton("返回", callback_data="auto")])
        await q.edit_message_text("关键词列表", reply_markup=InlineKeyboardMarkup(kb))

    elif data.startswith("kw:"):
        kw = data.split(":", 1)[1]
        context.user_data["current_kw"] = kw

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("修改关键词", callback_data="edit_kw")],
            [InlineKeyboardButton("回复内容", callback_data="edit_text")],
            [InlineKeyboardButton("图片", callback_data="edit_photo")],
            [InlineKeyboardButton("按钮", callback_data="edit_button")],
            [InlineKeyboardButton("预览", callback_data="preview")],
            [InlineKeyboardButton("删除", callback_data="delete")],
            [InlineKeyboardButton("返回", callback_data="kw_list")]
        ])
        await q.edit_message_text(f"关键词详情：{kw}", reply_markup=kb)

    elif data == "kw_add":
        context.user_data["step"] = "new_kw"
        await q.message.reply_text("请输入关键词")

    elif data == "preview":
        kw = context.user_data["current_kw"]
        d = KEYWORDS[kw]

        kb = None
        if d["buttons"]:
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton(b["text"], url=b["url"])] for b in d["buttons"]
            ])

        if d["photo"]:
            await q.message.reply_photo(d["photo"], caption=d["text"], reply_markup=kb)
        else:
            await q.message.reply_text(d["text"], reply_markup=kb)

    elif data == "delete":
        kw = context.user_data["current_kw"]
        KEYWORDS.pop(kw, None)
        await q.edit_message_text("已删除", reply_markup=main_menu())

    elif data == "group":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("已绑定群组", callback_data="group_list")],
            [InlineKeyboardButton("绑定新群", callback_data="group_bind")],
            [InlineKeyboardButton("返回", callback_data="back")]
        ])
        await q.edit_message_text("群管理设置", reply_markup=kb)

    elif data == "system":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("语言设置", callback_data="lang")],
            [InlineKeyboardButton("权限设置", callback_data="perm")],
            [InlineKeyboardButton("返回", callback_data="back")]
        ])
        await q.edit_message_text("系统设置", reply_markup=kb)

    elif data == "back":
        await q.edit_message_text("管理菜单", reply_markup=main_menu())

# ================= MESSAGE (PRIVATE SETUP) =================
async def private_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return

    step = context.user_data.get("step")
    msg = update.message.text

    if step == "new_kw":
        KEYWORDS[msg] = {"text": "", "photo": None, "buttons": []}
        context.user_data["current_kw"] = msg
        context.user_data["step"] = "new_text"
        await update.message.reply_text("请输入回复内容")
        return

    if step == "new_text":
        kw = context.user_data["current_kw"]
        KEYWORDS[kw]["text"] = msg
        context.user_data.clear()
        await update.message.reply_text("关键词创建完成")

# ================= GROUP AUTO REPLY =================
async def group_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text not in KEYWORDS:
        return

    d = KEYWORDS[text]
    kb = None
    if d["buttons"]:
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(b["text"], url=b["url"])] for b in d["buttons"]
        ])

    if d["photo"]:
        await update.message.reply_photo(d["photo"], caption=d["text"], reply_markup=kb)
    else:
        await update.message.reply_text(d["text"], reply_markup=kb)

# ================= RUN =================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.TEXT, private_handler))
    app.add_handler(MessageHandler(filters.ChatType.GROUPS & filters.TEXT, group_reply))

    print("Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
