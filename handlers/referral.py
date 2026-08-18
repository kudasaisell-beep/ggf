from aiogram import Router, F
from aiogram.types import CallbackQuery
from tg_utils import safe_edit, safe_answer
from database import get_or_create_user
from keyboards import back_to_main_kb

router = Router()


@router.callback_query(F.data == "referral")
async def referral_handler(callback: CallbackQuery):
    user = get_or_create_user(callback.from_user.id)
    ref_link = f"https://t.me/{(await callback.bot.get_me()).username}?start=ref{callback.from_user.id}"
    text = (
        f"🎁 <b>Реферальная программа</b>\n\n"
        f"Ваша ссылка:\n<code>{ref_link}</code>\n\n"
        f"👥 Рефералов: <b>{user.get('referrals', 0)}</b>\n"
        f"💵 Заработано: <b>{int(user.get('ref_earnings', 0))}₽</b>"
    )
    await safe_edit(callback, text, reply_markup=back_to_main_kb)
    await safe_answer(callback)
