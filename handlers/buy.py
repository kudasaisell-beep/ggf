from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode

from database import (
    get_available_accounts, get_account_by_id, create_purchase,
    deduct_balance, mark_account_sold, get_or_create_user, add_favorite
)
from keyboards import buy_categories_kb, subcategories_kb, account_list_kb, account_detail_kb, back_kb
from tg_utils import safe_answer, safe_edit, send_safe_message, escape_html
from lzt_api import is_blocked_origin, format_item_details
from config import get_subcat_info, ADMIN_IDS
from redis_client import acquire_item_lock, release_item_lock, set_user_cooldown, is_user_cooldown

router = Router()

class BuyState(StatesGroup):
    choosing_category = State()
    choosing_subcategory = State()
    viewing_accounts = State()
    confirming_purchase = State()

# Глобальный кэш для пагинации
_account_cache = {}

@router.callback_query(F.data == "menu:buy")
async def cb_buy_menu(callback: CallbackQuery):
    await safe_answer(callback)
    text = (
        "🛒 <b>Покупка</b>\n\n"
        "Выбери категорию товаров:\n\n"
        "💬 <b>Мессенджеры</b> — Telegram, TikTok, Discord и др.\n"
        "🎮 <b>Игры</b> — Genshin, Minecraft, Steam и др.\n"
        "🎬 <b>Сервисы</b> — Spotify, Netflix, ChatGPT и др."
    )
    await safe_edit(callback.message, text, reply_markup=buy_categories_kb())

@router.callback_query(F.data.startswith("cat:"))
async def cb_category(callback: CallbackQuery):
    await safe_answer(callback)
    cat_key = callback.data.split(":")[1]
    text = "📂 Выбери подкатегорию:"
    await safe_edit(callback.message, text, reply_markup=subcategories_kb(cat_key))

@router.callback_query(F.data.startswith("subcat:"))
async def cb_subcategory(callback: CallbackQuery):
    await safe_answer(callback)
    subcat_key = callback.data.split(":")[1]
    subcat = get_subcat_info(subcat_key)
    if not subcat:
        await safe_edit(callback.message, "❌ Категория не найдена.", reply_markup=back_kb("menu:buy"))
        return

    accounts = await get_available_accounts(subcat_key)
    # Фильтруем нелегальные источники
    filtered = []
    for acc in accounts:
        raw = acc.get("raw_lzt", "")
        if raw:
            try:
                import json
                raw_dict = json.loads(raw) if isinstance(raw, str) else raw
                if is_blocked_origin(raw_dict):
                    continue
            except Exception:
                pass
        filtered.append(acc)

    if not filtered:
        text = f"😔 Пока нет доступных товаров в категории <b>{subcat['name']}</b>.\nПопробуй позже!"
        await safe_edit(callback.message, text, reply_markup=back_kb(f"cat:{subcat_key}"))
        return

    _account_cache[callback.from_user.id] = {"accounts": filtered, "subcat": subcat_key, "page": 0}
    text = f"📋 <b>{subcat['name']}</b> — доступно {len(filtered)} шт.\n\nВыбери товар:"
    await safe_edit(callback.message, text, reply_markup=account_list_kb(filtered, page=0))

@router.callback_query(F.data.startswith("page:"))
async def cb_page(callback: CallbackQuery):
    await safe_answer(callback)
    page = int(callback.data.split(":")[1])
    cache = _account_cache.get(callback.from_user.id)
    if not cache:
        await safe_edit(callback.message, "❌ Сессия истекла. Начни заново.", reply_markup=back_kb("menu:buy"))
        return
    cache["page"] = page
    accounts = cache["accounts"]
    subcat = cache["subcat"]
    subcat_info = get_subcat_info(subcat)
    text = f"📋 <b>{subcat_info['name']}</b> — стр. {page+1}\n\nВыбери товар:"
    await safe_edit(callback.message, text, reply_markup=account_list_kb(accounts, page=page))

@router.callback_query(F.data.startswith("acc:"))
async def cb_account_detail(callback: CallbackQuery):
    await safe_answer(callback)
    acc_id = int(callback.data.split(":")[1])
    account = await get_account_by_id(acc_id)
    if not account:
        await safe_edit(callback.message, "❌ Товар не найден.", reply_markup=back_kb("menu:buy"))
        return

    subcat = get_subcat_info(account.get("subcat_key", ""))
    subcat_name = subcat["name"] if subcat else "Товар"

    text = (
        f"📦 <b>{subcat_name}</b>\n"
        f"🌍 Страна: {escape_html(account.get('country_name', 'Не указана'))}\n"
        f"📌 Тип: {escape_html(account.get('account_type', 'Стандарт'))}\n"
        f"💰 Цена: <b>{account.get('price', 0)}₽</b>\n\n"
    )

    # Добавляем raw данные из LZT
    raw = account.get("raw_lzt", "")
    if raw:
        try:
            import json
            raw_dict = json.loads(raw) if isinstance(raw, str) else raw
            text += "📄 <b>Данные из LZT:</b>\n<pre>"
            raw_text = json.dumps(raw_dict, ensure_ascii=False, indent=2)
            if len(raw_text) > 3000:
                raw_text = raw_text[:3000] + "\n... (обрезано)"
            text += escape_html(raw_text)
            text += "</pre>"
        except Exception:
            text += f"📄 <b>Данные:</b>\n<pre>{escape_html(str(raw)[:3000])}</pre>"

    seller = account.get("seller_info", "")
    if seller:
        text += f"\n\n👤 {escape_html(seller)}"

    await safe_edit(callback.message, text, reply_markup=account_detail_kb(acc_id, account.get("subcat_key", "")))

@router.callback_query(F.data.startswith("buy:"))
async def cb_buy_account(callback: CallbackQuery):
    await safe_answer(callback)
    acc_id = int(callback.data.split(":")[1])
    user_id = callback.from_user.id

    if await is_user_cooldown(user_id):
        await callback.answer("⏳ Подожди немного перед следующей покупкой!", show_alert=True)
        return

    account = await get_account_by_id(acc_id)
    if not account or account.get("status") != "available":
        await callback.answer("❌ Товар уже продан!", show_alert=True)
        return

    user = await get_or_create_user(user_id)
    price = account.get("price", 0)
    if user.get("balance", 0) < price:
        await callback.answer(f"❌ Недостаточно средств! Нужно {price}₽", show_alert=True)
        return

    # Блокировка товара
    if not await acquire_item_lock(str(acc_id), ttl=60):
        await callback.answer("❌ Кто-то уже покупает этот товар!", show_alert=True)
        return

    try:
        ok = await deduct_balance(user_id, price)
        if not ok:
            await callback.answer("❌ Ошибка списания средств!", show_alert=True)
            return

        await mark_account_sold(acc_id)
        data = account.get("data", "")
        await create_purchase(user_id, acc_id, account.get("subcat_key", ""), price, account.get("cost_price", 0), data)
        await set_user_cooldown(user_id, ttl=5)

        # Отправляем данные покупателю
        text = (
            f"✅ <b>Покупка совершена!</b>\n\n"
            f"📦 Товар: {escape_html(account.get('subcat_key', ''))}\n"
            f"🌍 Страна: {escape_html(account.get('country_name', ''))}\n"
            f"💰 Списано: {price}₽\n\n"
            f"📄 <b>Данные аккаунта:</b>\n<pre>{escape_html(data)}</pre>"
        )
        await send_safe_message(callback.bot, user_id, text)

        # Уведомление админу
        for admin_id in ADMIN_IDS:
            admin_text = (
                f"🛒 <b>Новая покупка!</b>\n"
                f'Пользователь: <a href="tg://user?id={user_id}">{user_id}</a>\n'
                f"Товар: {escape_html(account.get('subcat_key', ''))}\n"
                f"Цена: {price}₽"
            )
            await send_safe_message(callback.bot, admin_id, admin_text)

        await safe_edit(callback.message, "✅ Покупка успешна! Данные отправлены в личные сообщения.", reply_markup=back_kb("menu:main"))

    finally:
        await release_item_lock(str(acc_id))
