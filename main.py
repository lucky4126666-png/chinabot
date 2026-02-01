import os, json, asyncio
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardButton, InlineKeyboardMarkup,
    InputMediaPhoto
)
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 8572604188
DATA_FILE = "data.json"

bot = Bot(TOKEN)
dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)

# ===== DATA =====
def load():
    if not os.path.exists(DATA_FILE):
        return {}
    return json.load(open(DATA_FILE, "r", encoding="utf-8"))

def save():
    json.dump(data, open(DATA_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

data = load()

def gen_id():
    return f"k{len(data)+1}"

# ===== FSM =====
class Form(StatesGroup):
    add_kw = State()
    text = State()
    img = State()
    btn = State()

# ===== MENUS =====
def admin_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Thêm từ khóa", callback_data="add")],
        [InlineKeyboardButton(text="📌 Danh sách", callback_data="list")]
    ])

def kw_menu(kid):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✏️ Nội dung", callback_data=f"t:{kid}"),
            InlineKeyboardButton(text="🖼️ Ảnh", callback_data=f"i:{kid}")
        ],
        [
            InlineKeyboardButton(text="🔘 Nút", callback_data=f"b:{kid}"),
            InlineKeyboardButton(text="👁️ Xem", callback_data=f"p:{kid}")
        ],
        [
            InlineKeyboardButton(text="🗑️ Xóa", callback_data=f"d:{kid}")
        ],
        [
            InlineKeyboardButton(text="⬅️ Trở lại", callback_data="back")
        ]
    ])

def btns(buttons):
    rows, tmp = [], []
    for b in buttons:
        tmp.append(InlineKeyboardButton(text=b["text"], url=b["url"]))
        if len(tmp) == 2:
            rows.append(tmp)
            tmp = []
    if tmp:
        rows.append(tmp)
    return InlineKeyboardMarkup(inline_keyboard=rows)

# ===== START =====
@router.message(CommandStart())
async def start(m: Message):
    if m.from_user.id == ADMIN_ID:
        await m.answer("⚙️ Quản lý bot", reply_markup=admin_menu())

# ===== ADD KEYWORD =====
@router.callback_query(F.data == "add")
async def add(cb: CallbackQuery, state: FSMContext):
    await cb.message.edit_text("Nhập từ khóa:")
    await state.set_state(Form.add_kw)

@router.message(Form.add_kw)
async def save_kw(m: Message, state: FSMContext):
    kid = gen_id()
    data[kid] = {
        "keyword": m.text.strip(),
        "text": "",
        "images": [],
        "buttons": []
    }
    save()
    await m.answer(f"✅ Đã tạo: {m.text}", reply_markup=kw_menu(kid))
    await state.clear()

# ===== LIST =====
@router.callback_query(F.data == "list")
async def list_kw(cb: CallbackQuery):
    rows = [
        [InlineKeyboardButton(text=v["keyword"], callback_data=f"o:{k}")]
        for k, v in data.items()
    ]
    rows.append([InlineKeyboardButton(text="⬅️ Trở lại", callback_data="back")])
    await cb.message.edit_text("📌 Từ khóa", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))

@router.callback_query(F.data.startswith("o:"))
async def open_kw(cb: CallbackQuery):
    await cb.message.edit_text("⚙️ Cấu hình", reply_markup=kw_menu(cb.data[2:]))

# ===== TEXT =====
@router.callback_query(F.data.startswith("t:"))
async def set_text(cb: CallbackQuery, state: FSMContext):
    await state.update_data(id=cb.data[2:])
    await cb.message.edit_text("Gửi nội dung:")
    await state.set_state(Form.text)

@router.message(Form.text)
async def save_text(m: Message, state: FSMContext):
    kid = (await state.get_data())["id"]
    data[kid]["text"] = m.text
    save()
    await m.answer("✅ Đã lưu", reply_markup=kw_menu(kid))
    await state.clear()

# ===== IMAGE =====
@router.callback_query(F.data.startswith("i:"))
async def set_img(cb: CallbackQuery, state: FSMContext):
    await state.update_data(id=cb.data[2:])
    await cb.message.edit_text("Gửi ảnh (nhiều ảnh được)")
    await state.set_state(Form.img)

@router.message(Form.img, F.photo)
async def save_img(m: Message, state: FSMContext):
    kid = (await state.get_data())["id"]
    data[kid]["images"].append(m.photo[-1].file_id)
    save()
    await m.answer("✅ Đã thêm ảnh")

# ===== BUTTON =====
@router.callback_query(F.data.startswith("b:"))
async def set_btn(cb: CallbackQuery, state: FSMContext):
    await state.update_data(id=cb.data[2:])
    await cb.message.edit_text("Tên | https://link")
    await state.set_state(Form.btn)

@router.message(Form.btn)
async def save_btn(m: Message, state: FSMContext):
    if "|" not in m.text:
        return await m.answer("Sai định dạng")
    name, url = map(str.strip, m.text.split("|", 1))
    kid = (await state.get_data())["id"]
    data[kid]["buttons"].append({"text": name, "url": url})
    save()
    await m.answer("✅ Đã thêm nút", reply_markup=kw_menu(kid))
    await state.clear()

# ===== PREVIEW =====
@router.callback_query(F.data.startswith("p:"))
async def preview(cb: CallbackQuery):
    k = data[cb.data[2:]]
    if k["images"]:
        await cb.message.answer_photo(
            k["images"][0],
            caption=k["text"],
            reply_markup=btns(k["buttons"])
        )
    else:
        await cb.message.answer(
            k["text"],
            reply_markup=btns(k["buttons"])
        )

# ===== AUTO REPLY (GROUP) =====
@router.message()
async def auto(m: Message):
    if m.chat.type == "private" or not m.text:
        return
    for k in data.values():
        if k["keyword"] in m.text:
            if k["images"]:
                await m.reply_photo(
                    k["images"][0],
                    caption=k["text"],
                    reply_markup=btns(k["buttons"])
                )
            else:
                await m.reply(k["text"], reply_markup=btns(k["buttons"]))
            break

# ===== RUN =====
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
