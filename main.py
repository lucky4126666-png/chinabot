import json
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardButton, InlineKeyboardMarkup,
    InputMediaPhoto
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import CommandStart
from aiogram import Router
import os

TOKEN = os.getenv("BOT_TOKEN")  # Railway ENV
ADMIN_ID = 8572604188           # ID của bạn

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)

DATA_FILE = "data.json"

# ================= DATA =================
def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

data = load_data()

# ================= FSM =================
class Form(StatesGroup):
    add_kw = State()
    add_text = State()
    add_img = State()
    add_btn = State()

# ================= MENUS =================
def admin_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Thêm từ khóa", callback_data="add_kw")],
        [InlineKeyboardButton("📌 Danh sách từ khóa", callback_data="list_kw")]
    ])

def keyword_menu(key):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✏️ Sửa nội dung", callback_data=f"text:{key}"),
            InlineKeyboardButton("🖼️ Thêm ảnh", callback_data=f"img:{key}")
        ],
        [
            InlineKeyboardButton("🔘 Thêm nút", callback_data=f"btn:{key}"),
            InlineKeyboardButton("👁️ Xem trước", callback_data=f"preview:{key}")
        ],
        [
            InlineKeyboardButton("🗑️ Xóa", callback_data=f"del:{key}")
        ],
        [
            InlineKeyboardButton("⬅️ Trở lại", callback_data="back_admin")
        ]
    ])

def keyword_list_menu():
    rows = []
    for k in data:
        rows.append([InlineKeyboardButton(k, callback_data=f"open:{k}")])
    rows.append([InlineKeyboardButton("⬅️ Trở lại", callback_data="back_admin")])
    return InlineKeyboardMarkup(rows)

def build_buttons(buttons, per_row=2):
    rows, temp = [], []
    for b in buttons:
        temp.append(InlineKeyboardButton(b["text"], url=b["url"]))
        if len(temp) == per_row:
            rows.append(temp)
            temp = []
    if temp:
        rows.append(temp)
    return InlineKeyboardMarkup(rows)

# ================= START =================
@router.message(CommandStart())
async def start(msg: Message):
    if msg.chat.type == "private" and msg.from_user.id == ADMIN_ID:
        await msg.reply("⚙️ Quản lý bot", reply_markup=admin_menu())

# ================= CALLBACK =================
@router.callback_query(F.data == "add_kw")
async def add_kw(cb: CallbackQuery, state: FSMContext):
    await cb.message.edit_text("✍️ Nhập từ khóa:")
    await state.set_state(Form.add_kw)

@router.message(Form.add_kw)
async def save_kw(msg: Message, state: FSMContext):
    key = msg.text.strip()
    data[key] = {"text": "", "images": [], "buttons": []}
    save_data()
    await msg.reply(f"✅ Đã tạo từ khóa: {key}", reply_markup=keyword_menu(key))
    await state.clear()

@router.callback_query(F.data == "list_kw")
async def list_kw(cb: CallbackQuery):
    await cb.message.edit_text("📌 Danh sách từ khóa", reply_markup=keyword_list_menu())

@router.callback_query(F.data.startswith("open:"))
async def open_kw(cb: CallbackQuery):
    key = cb.data.split(":", 1)[1]
    await cb.message.edit_text(f"⚙️ Từ khóa: {key}", reply_markup=keyword_menu(key))

@router.callback_query(F.data.startswith("text:"))
async def edit_text(cb: CallbackQuery, state: FSMContext):
    key = cb.data.split(":", 1)[1]
    await state.update_data(key=key)
    await cb.message.edit_text("✏️ Gửi nội dung mới:")
    await state.set_state(Form.add_text)

@router.message(Form.add_text)
async def save_text(msg: Message, state: FSMContext):
    key = (await state.get_data())["key"]
    data[key]["text"] = msg.text
    save_data()
    await msg.reply("✅ Đã lưu nội dung", reply_markup=keyword_menu(key))
    await state.clear()

@router.callback_query(F.data.startswith("img:"))
async def add_img(cb: CallbackQuery, state: FSMContext):
    key = cb.data.split(":", 1)[1]
    await state.update_data(key=key)
    await cb.message.edit_text("🖼️ Gửi ảnh (có thể gửi nhiều ảnh)")
    await state.set_state(Form.add_img)

@router.message(Form.add_img, F.photo)
async def save_img(msg: Message, state: FSMContext):
    key = (await state.get_data())["key"]
    data[key]["images"].append(msg.photo[-1].file_id)
    save_data()
    await msg.reply("✅ Đã thêm ảnh")

@router.callback_query(F.data.startswith("btn:"))
async def add_btn(cb: CallbackQuery, state: FSMContext):
    key = cb.data.split(":", 1)[1]
    await state.update_data(key=key)
    await cb.message.edit_text("🔘 Gửi nút:\nTên | https://link")
    await state.set_state(Form.add_btn)

@router.message(Form.add_btn)
async def save_btn(msg: Message, state: FSMContext):
    key = (await state.get_data())["key"]
    if "|" not in msg.text:
        return await msg.reply("❌ Sai định dạng")
    name, url = map(str.strip, msg.text.split("|", 1))
    data[key]["buttons"].append({"text": name, "url": url})
    save_data()
    await msg.reply("✅ Đã thêm nút", reply_markup=keyword_menu(key))
    await state.clear()

@router.callback_query(F.data.startswith("preview:"))
async def preview(cb: CallbackQuery):
    key = cb.data.split(":", 1)[1]
    item = data[key]
    sent = []

    if item["images"]:
        m = await cb.message.reply_photo(
            photo=item["images"][0],
            caption=item["text"],
            reply_markup=build_buttons(item["buttons"])
        )
        sent.append(m)

        if len(item["images"]) > 1:
            media = [InputMediaPhoto(img) for img in item["images"][1:]]
            msgs = await cb.message.reply_media_group(media)
            sent.extend(msgs)
    else:
        m = await cb.message.reply_text(
            item["text"],
            reply_markup=build_buttons(item["buttons"])
        )
        sent.append(m)

    await asyncio.sleep(10)
    for m in sent:
        await m.delete()

@router.callback_query(F.data.startswith("del:"))
async def delete_kw(cb: CallbackQuery):
    key = cb.data.split(":", 1)[1]
    data.pop(key, None)
    save_data()
    await cb.message.edit_text("🗑️ Đã xóa", reply_markup=admin_menu())

@router.callback_query(F.data == "back_admin")
async def back_admin(cb: CallbackQuery):
    await cb.message.edit_text("⚙️ Quản lý bot", reply_markup=admin_menu())

# ================= AUTO REPLY =================
@router.message()
async def auto_reply(msg: Message):
    if msg.chat.type == "private":
        return
    for key in data:
        if key in msg.text:
            item = data[key]
            if item["images"]:
                await msg.reply_photo(
                    photo=item["images"][0],
                    caption=item["text"],
                    reply_markup=build_buttons(item["buttons"])
                )
            else:
                await msg.reply_text(
                    item["text"],
                    reply_markup=build_buttons(item["buttons"])
                )
            break

# ================= RUN =================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
