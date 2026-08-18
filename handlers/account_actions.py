from aiogram import Router, F
from aiogram.types import CallbackQuery
from tg_utils import safe_edit, safe_answer
from database import get_user_purchases
from keyboards import copy_data_kb, back_to_main_kb

router = Router()


@router.callback_query(F.data.startswith("copy_data:"))
async def copy_data_handler(callback: CallbackQuery):
    purchase_id = int(callback.data.split(":")[1])
    purchases = get_user_purchases(callback.from_user.id)
    purchase = None
    for p in purchases:
        if p["id"] == purchase_id:
            purchase = p
            break
    if not purchase:
        await safe_answer(callback, "❌ Покупка не найдена", show_alert=True)
        return
    await safe_answer(callback, "📋 Данные скопированы (в буфер обмена)")


@router.callback_query(F.data.startswith("request_code:"))
async def request_code_handler(callback: CallbackQuery):
    await safe_answer(callback, "🔑 Запрос кода отправлен админу", show_alert=True)


@router.callback_query(F.data.startswith("reset_sessions:"))
async def reset_sessions_handler(callback: CallbackQuery):
    await safe_answer(callback, "🔄 Сброс сессий в разработке", show_alert=True)


@router.callback_query(F.data.startswith("validate_acc:"))
async def validate_acc_handler(callback: CallbackQuery):
    await safe_answer(callback, "✅ Проверка валидности в разработке", show_alert=True)


@router.callback_query(F.data.startswith("ticket_from_purchase:"))
async def ticket_from_purchase_handler(callback: CallbackQuery):
    await safe_answer(callback, "🎫 Создание тикета в разработке", show_alert=True)
