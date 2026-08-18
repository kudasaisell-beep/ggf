from aiogram import Router, F
from aiogram.types import CallbackQuery
from tg_utils import safe_edit, safe_answer
from keyboards import back_to_main_kb

router = Router()


@router.callback_query(F.data == "faq")
async def faq_handler(callback: CallbackQuery):
    from keyboards import faq_kb
    text = (
        "❓ <b>FAQ</b>\n\n"
        "Выберите вопрос:"
    )
    await safe_edit(callback, text, reply_markup=faq_kb)
    await safe_answer(callback)


@router.callback_query(F.data == "faq_how_to_buy")
async def faq_how_to_buy(callback: CallbackQuery):
    text = (
        "📦 <b>Как купить?</b>\n\n"
        "1. Пополните баланс\n"
        "2. Выберите категорию и страну\n"
        "3. Выберите тип аккаунта\n"
        "4. Нажмите 'Купить'\n"
        "5. Получите данные мгновенно"
    )
    await safe_edit(callback, text, reply_markup=back_to_main_kb)
    await safe_answer(callback)


@router.callback_query(F.data == "faq_guarantee")
async def faq_guarantee(callback: CallbackQuery):
    text = (
        "🛡 <b>Гарантия</b>\n\n"
        "• Стандарт: 24 часа\n"
        "• Со страховкой: пожизненная\n"
        "• При проблемах — замена или возврат"
    )
    await safe_edit(callback, text, reply_markup=back_to_main_kb)
    await safe_answer(callback)


@router.callback_query(F.data == "faq_payment")
async def faq_payment(callback: CallbackQuery):
    text = (
        "💰 <b>Пополнение</b>\n\n"
        "• Перевод на карту\n"
        "• QR СБП\n"
        "• Telegram Stars"
    )
    await safe_edit(callback, text, reply_markup=back_to_main_kb)
    await safe_answer(callback)


@router.callback_query(F.data == "faq_broken")
async def faq_broken(callback: CallbackQuery):
    text = (
        "⚠️ <b>Аккаунт не работает</b>\n\n"
        "1. Проверьте данные ещё раз\n"
        "2. Создайте тикет в поддержке\n"
        "3. Мы решим проблему в течение 24ч"
    )
    await safe_edit(callback, text, reply_markup=back_to_main_kb)
    await safe_answer(callback)


@router.callback_query(F.data == "faq_referral")
async def faq_referral(callback: CallbackQuery):
    text = (
        "🎁 <b>Реферальная программа</b>\n\n"
        "Приглашайте друзей и получайте % от их покупок!"
    )
    await safe_edit(callback, text, reply_markup=back_to_main_kb)
    await safe_answer(callback)
