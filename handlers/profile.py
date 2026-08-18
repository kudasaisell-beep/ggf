from aiogram import Router, F
from aiogram.types import CallbackQuery
from tg_utils import safe_edit, safe_answer
from database import get_or_create_user, get_user_purchases
from keyboards import profile_kb, back_to_main_kb

router = Router()


@router.callback_query(F.data == "profile")
async def profile_handler(callback: CallbackQuery):
    user = get_or_create_user(
        callback.from_user.id,
        username=callback.from_user.username,
        full_name=callback.from_user.full_name
    )
    text = (
        f"👤 <b>Личный кабинет</b>\n\n"
        f"💰 Баланс: <b>{int(user.get('balance', 0))}₽</b>\n"
        f"🛍 Покупок: <b>{user.get('total_spent', 0)}</b>\n"
        f"👥 Рефералов: <b>{user.get('referrals', 0)}</b>\n"
        f"📅 Дата регистрации: {user.get('created_at', '—')[:10]}"
    )
    await safe_edit(callback, text, reply_markup=profile_kb)
    await safe_answer(callback)


@router.callback_query(F.data == "my_purchases")
async def my_purchases(callback: CallbackQuery):
    purchases = get_user_purchases(callback.from_user.id)
    if not purchases:
        text = "🛍 <b>Мои покупки</b>\n\nУ вас пока нет покупок."
        await safe_edit(callback, text, reply_markup=back_to_main_kb)
        await safe_answer(callback)
        return

    text = "🛍 <b>Мои покупки:</b>\n\n"
    for i, p in enumerate(purchases[:20], 1):
        type_label = "саморег" if p["account_type"] == "samoreg" else "авторег"
        text += (
            f"{i}. {p['country_name']} — {type_label}\n"
            f"   💰 {int(p['price'])}₽ | 📅 {p['created_at'][:10]}\n\n"
        )

    await safe_edit(callback, text, reply_markup=back_to_main_kb)
    await safe_answer(callback)


@router.callback_query(F.data == "my_stats")
async def my_stats(callback: CallbackQuery):
    user = get_or_create_user(callback.from_user.id)
    text = (
        f"📊 <b>Статистика</b>\n\n"
        f"💰 Баланс: {int(user.get('balance', 0))}₽\n"
        f"🛍 Потрачено: {int(user.get('total_spent', 0))}₽\n"
        f"👥 Рефералов: {user.get('referrals', 0)}\n"
        f"💵 Заработано с рефералов: {int(user.get('ref_earnings', 0))}₽"
    )
    await safe_edit(callback, text, reply_markup=back_to_main_kb)
    await safe_answer(callback)
