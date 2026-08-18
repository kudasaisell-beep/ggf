from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.enums import ParseMode

from database import get_or_create_user
from keyboards import main_menu_kb
from tg_utils import safe_answer, safe_edit
from config import ADMIN_IDS

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    user = await get_or_create_user(message.from_user.id, message.from_user.username)
    is_admin = message.from_user.id in ADMIN_IDS
    text = (
        f"👋 <b>Привет, {message.from_user.full_name}!</b>\n\n"
        f"🛍 Добро пожаловать в наш магазин!\n"
        f"💰 Баланс: <b>{user.get('balance', 0):.2f}₽</b>\n\n"
        f"Выбери действие ниже:"
    )
    await message.answer(text, reply_markup=main_menu_kb(is_admin), parse_mode=ParseMode.HTML)

@router.callback_query(F.data == "menu:main")
async def cb_main(callback: CallbackQuery):
    await safe_answer(callback)
    is_admin = callback.from_user.id in ADMIN_IDS
    user = await get_or_create_user(callback.from_user.id, callback.from_user.username)
    text = (
        f"👋 <b>Главное меню</b>\n\n"
        f"💰 Баланс: <b>{user.get('balance', 0):.2f}₽</b>\n\n"
        f"Выбери действие:"
    )
    await safe_edit(callback.message, text, reply_markup=main_menu_kb(is_admin))
