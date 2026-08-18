from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.enums import ParseMode

from database import (
    get_stats, get_purchases_stats, get_account_count, get_pricing_cache,
    get_demand_stats, approve_deposit, reject_deposit, get_deposit
)
from keyboards import admin_kb, back_kb
from tg_utils import safe_answer, safe_edit, send_safe_message, escape_html
from config import ADMIN_IDS, get_all_subcats

router = Router()

@router.callback_query(F.data == "menu:admin")
async def cb_admin(callback: CallbackQuery):
    await safe_answer(callback)
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Нет доступа!", show_alert=True)
        return
    text = "⚙️ <b>Админ-панель</b>\n\nВыбери действие:"
    await safe_edit(callback.message, text, reply_markup=admin_kb())

@router.callback_query(F.data == "admin:stats")
async def cb_admin_stats(callback: CallbackQuery):
    await safe_answer(callback)
    stats = await get_stats()
    text = (
        f"📊 <b>Статистика</b>\n\n"
        f"👤 Пользователей: <b>{stats['users']}</b>\n"
        f"📦 Аккаунтов в наличии: <b>{stats['accounts']}</b>\n"
        f"🛒 Покупок: <b>{stats['purchases']}</b>\n"
        f"💰 Выручка: <b>{stats['revenue']:.2f}₽</b>"
    )
    await safe_edit(callback.message, text, reply_markup=back_kb("menu:admin"))

@router.callback_query(F.data == "admin:prices")
async def cb_admin_prices(callback: CallbackQuery):
    await safe_answer(callback)
    text = "💰 <b>Текущие цены (кэш LZT):</b>\n\n"
    for key in get_all_subcats():
        cache = await get_pricing_cache(key)
        if cache:
            text += f"• {key}: avg={cache.get('avg_price', 0):.0f}₽\n"
        else:
            text += f"• {key}: нет данных\n"
    await safe_edit(callback.message, text, reply_markup=back_kb("menu:admin"))

@router.callback_query(F.data == "admin:demand")
async def cb_admin_demand(callback: CallbackQuery):
    await safe_answer(callback)
    stats = await get_demand_stats()
    text = "📈 <b>Аналитика спроса:</b>\n\n"
    if stats:
        for s in stats[:10]:
            text += (
                f"• {s.get('subcat_key', '?')} "
                f"({s.get('country_code', '?')}) — "
                f"скорость: {s.get('sales_speed', 0):.1f}/час\n"
            )
    else:
        text += "Пока недостаточно данных."
    await safe_edit(callback.message, text, reply_markup=back_kb("menu:admin"))

@router.callback_query(F.data == "admin:stock")
async def cb_admin_stock(callback: CallbackQuery):
    await safe_answer(callback)
    text = "📦 <b>Остатки по позициям:</b>\n\n"
    for key in get_all_subcats():
        count = await get_account_count(key)
        emoji = "🔴" if count < 3 else ("🟡" if count < 8 else "🟢")
        text += f"{emoji} {key}: <b>{count}</b> шт.\n"
    await safe_edit(callback.message, text, reply_markup=back_kb("menu:admin"))

@router.callback_query(F.data == "admin:update_prices")
async def cb_admin_update(callback: CallbackQuery):
    await safe_answer(callback)
    text = (
        "🔄 <b>Обновление цен запущено!</b>\n\n"
        "В фоновом режиме цены будут пересчитаны по формуле:\n"
        "LZT_price × margin + fixed_profit"
    )
    await safe_edit(callback.message, text, reply_markup=back_kb("menu:admin"))

@router.callback_query(F.data == "admin:autobuy")
async def cb_admin_autobuy(callback: CallbackQuery):
    await safe_answer(callback)
    text = (
        "🛒 <b>Автозакупка</b>\n\n"
        "Приоритеты рассчитаны по скорости продаж.\n"
        "Топовые позиции будут закуплены в 2× объёме."
    )
    await safe_edit(callback.message, text, reply_markup=back_kb("menu:admin"))

# Обработка заявок на пополнение
@router.callback_query(F.data.startswith("dep:approve:"))
async def cb_approve_deposit(callback: CallbackQuery):
    await safe_answer(callback)
    if callback.from_user.id not in ADMIN_IDS:
        return
    dep_id = int(callback.data.split(":")[2])
    dep = await get_deposit(dep_id)
    if not dep:
        await callback.answer("❌ Заявка не найдена!", show_alert=True)
        return
    if dep.get("status") != "pending":
        await callback.answer("❌ Заявка уже обработана!", show_alert=True)
        return

    await approve_deposit(dep_id)
    await callback.answer("✅ Заявка принята!", show_alert=True)

    # Уведомляем пользователя
    user_id = dep.get("user_id")
    amount = dep.get("amount", 0)
    await send_safe_message(
        callback.bot, user_id,
        f"✅ <b>Пополнение одобрено!</b>\n\n"
        f"Зачислено: <b>{amount:.0f}₽</b>\n"
        f"Проверь баланс в профиле."
    )

    # Обновляем сообщение админу
    await safe_edit(
        callback.message,
        callback.message.caption + "\n\n✅ <b>ПРИНЯТО</b>",
        reply_markup=None
    )

@router.callback_query(F.data.startswith("dep:reject:"))
async def cb_reject_deposit(callback: CallbackQuery):
    await safe_answer(callback)
    if callback.from_user.id not in ADMIN_IDS:
        return
    dep_id = int(callback.data.split(":")[2])
    dep = await get_deposit(dep_id)
    if not dep:
        await callback.answer("❌ Заявка не найдена!", show_alert=True)
        return
    if dep.get("status") != "pending":
        await callback.answer("❌ Заявка уже обработана!", show_alert=True)
        return

    await reject_deposit(dep_id)
    await callback.answer("❌ Заявка отклонена!", show_alert=True)

    user_id = dep.get("user_id")
    amount = dep.get("amount", 0)
    await send_safe_message(
        callback.bot, user_id,
        f"❌ <b>Пополнение отклонено</b>\n\n"
        f"Сумма: {amount:.0f}₽\n"
        f"Если считаешь это ошибкой — обратись в поддержку."
    )

    await safe_edit(
        callback.message,
        callback.message.caption + "\n\n❌ <b>ОТКЛОНЕНО</b>",
        reply_markup=None
    )
