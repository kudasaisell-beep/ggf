from aiogram import Router, F
from aiogram.types import CallbackQuery
from tg_utils import safe_edit, safe_answer
from database import get_cart, clear_cart, remove_cart_item
from keyboards import cart_kb, back_to_main_kb

router = Router()


@router.callback_query(F.data == "cart")
async def cart_handler(callback: CallbackQuery):
    items = get_cart(callback.from_user.id)
    if not items:
        text = "🛒 <b>Корзина</b>\n\nКорзина пуста."
        await safe_edit(callback, text, reply_markup=back_to_main_kb)
        await safe_answer(callback)
        return

    total = sum(item["price"] for item in items)
    text = f"🛒 <b>Корзина</b> ({len(items)} шт)\n\n"
    for item in items:
        text += f"• {item['country_name']} — {int(item['price'])}₽\n"
    text += f"\n💰 Итого: <b>{int(total)}₽</b>"

    await safe_edit(callback, text, reply_markup=cart_kb(items))
    await safe_answer(callback)


@router.callback_query(F.data.startswith("remove_cart:"))
async def remove_cart_handler(callback: CallbackQuery):
    cart_id = int(callback.data.split(":")[1])
    remove_cart_item(cart_id)
    await safe_answer(callback, "✅ Удалено")
    await cart_handler(callback)


@router.callback_query(F.data == "clear_cart")
async def clear_cart_handler(callback: CallbackQuery):
    clear_cart(callback.from_user.id)
    await safe_answer(callback, "✅ Корзина очищена")
    await cart_handler(callback)


@router.callback_query(F.data == "checkout")
async def checkout_handler(callback: CallbackQuery):
    await safe_answer(callback, "🛠 Оформление заказа в разработке", show_alert=True)
