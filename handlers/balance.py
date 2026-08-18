from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode

from database import get_or_create_user, create_deposit
from keyboards import balance_kb, back_kb
from tg_utils import safe_answer, safe_edit, send_safe_message, send_safe_photo
from config import CARD_NUMBER, CARD_BANK, CARD_HOLDER, MIN_DEPOSIT, ADMIN_CHAT_ID

router = Router()

class CardDepositState(StatesGroup):
    waiting_amount = State()
    waiting_check = State()

@router.callback_query(F.data == "menu:balance")
async def cb_balance(callback: CallbackQuery):
    await safe_answer(callback)
    user = await get_or_create_user(callback.from_user.id)
    text = (
        f"💰 <b>Баланс</b>\n\n"
        f"Текущий баланс: <b>{user.get('balance', 0):.2f}₽</b>\n\n"
        f"Выбери способ пополнения:"
    )
    await safe_edit(callback.message, text, reply_markup=balance_kb())

@router.callback_query(F.data == "balance:card")
async def cb_card_deposit(callback: CallbackQuery, state: FSMContext):
    await safe_answer(callback)
    await state.set_state(CardDepositState.waiting_amount)
    text = (
        f"💳 <b>Пополнение через перевод на карту</b>\n\n"
        f"Введи сумму пополнения (минимум {MIN_DEPOSIT}₽):"
    )
    await safe_edit(callback.message, text, reply_markup=back_kb("menu:balance"))

@router.message(CardDepositState.waiting_amount)
async def process_deposit_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.strip())
        if amount < MIN_DEPOSIT:
            await message.answer(f"❌ Минимальная сумма — {MIN_DEPOSIT}₽. Попробуй ещё раз:")
            return
    except ValueError:
        await message.answer("❌ Введи число. Попробуй ещё раз:")
        return

    await state.update_data(amount=amount)
    await state.set_state(CardDepositState.waiting_check)

    text = (
        f"💳 <b>Реквизиты для перевода</b>\n\n"
        f"🏦 Банк: <b>{CARD_BANK}</b>\n"
        f"💳 Карта: <code>{CARD_NUMBER}</code>\n"
        f"👤 Получатель: <b>{CARD_HOLDER}</b>\n\n"
        f"💵 Сумма: <b>{amount:.0f}₽</b>\n\n"
        f"✅ Переведи указанную сумму на карту,\n"
        f"затем отправь <b>фото чека</b> сюда."
    )
    await message.answer(text)

@router.message(CardDepositState.waiting_check, F.photo)
async def process_deposit_check(message: Message, state: FSMContext):
    data = await state.get_data()
    amount = data.get("amount", 0)
    photo = message.photo[-1].file_id
    user_id = message.from_user.id

    deposit_id = await create_deposit(user_id, amount, photo)
    await state.clear()

    # Уведомляем пользователя
    await message.answer(
        f"⏳ <b>Заявка на пополнение #{deposit_id} создана!</b>\n"
        f"Сумма: {amount:.0f}₽\n\n"
        f"Ожидай подтверждения администратора."
    )

    # Пересылаем админу
    from keyboards import deposit_confirm_kb
    admin_text = (
        f"🆕 <b>Новая заявка на пополнение</b>\n\n"
        f"ID: <code>{deposit_id}</code>\n"
        f'Пользователь: <a href="tg://user?id={user_id}">{user_id}</a>\n'
        f"Сумма: <b>{amount:.0f}₽</b>\n"
        f"Юзернейм: @{message.from_user.username or 'нет'}"
    )
    await send_safe_photo(
        message.bot, ADMIN_CHAT_ID, photo=photo,
        caption=admin_text, reply_markup=deposit_confirm_kb(deposit_id)
    )

@router.message(CardDepositState.waiting_check)
async def process_deposit_check_invalid(message: Message):
    await message.answer("❌ Пожалуйста, отправь фото чека (скриншот).")
