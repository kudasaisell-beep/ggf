from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from tg_utils import safe_edit, safe_answer, send_safe_message
from database import create_ticket, get_user_tickets, get_open_tickets
from keyboards import support_menu_kb, ticket_type_kb, back_to_main_kb, back_to_support_kb
from config import ADMIN_CHAT_ID

router = Router()


class TicketState(StatesGroup):
    waiting_message = State()


@router.callback_query(F.data == "support_menu")
async def support_menu_handler(callback: CallbackQuery):
    text = (
        "📞 <b>Поддержка</b>\n\n"
        "Выберите действие:"
    )
    await safe_edit(callback, text, reply_markup=support_menu_kb)
    await safe_answer(callback)


@router.callback_query(F.data == "create_ticket")
async def create_ticket_handler(callback: CallbackQuery, state: FSMContext):
    text = "🎫 <b>Создание тикета</b>\n\nВыберите тип:"
    await safe_edit(callback, text, reply_markup=ticket_type_kb)
    await safe_answer(callback)


@router.callback_query(F.data.startswith("ticket_type:"))
async def ticket_type_handler(callback: CallbackQuery, state: FSMContext):
    ticket_type = callback.data.split(":")[1]
    await state.update_data(ticket_type=ticket_type)
    await state.set_state(TicketState.waiting_message)
    text = "📝 Опишите вашу проблему:"
    await callback.message.answer(text)
    await safe_answer(callback)


@router.message(TicketState.waiting_message, F.text)
async def ticket_message(message: Message, state: FSMContext):
    data = await state.get_data()
    ticket_type = data.get("ticket_type", "other")
    ticket_id = create_ticket(
        message.from_user.id,
        message.from_user.username,
        message.from_user.full_name,
        ticket_type,
        message.text
    )
    await state.clear()
    await message.answer(
        f"✅ <b>Тикет #{ticket_id} создан!</b>\n\n"
        f"Мы ответим вам в ближайшее время.",
        reply_markup=back_to_main_kb
    )
    if ADMIN_CHAT_ID:
        await send_safe_message(
            message.bot,
            f"🎫 <b>Новый тикет #{ticket_id}</b>\n"
            f"Тип: {ticket_type}\n"
            f"User: {message.from_user.id}\n"
            f"Сообщение: {message.text[:200]}",
            chat_id=ADMIN_CHAT_ID
        )


@router.callback_query(F.data == "my_tickets")
async def my_tickets_handler(callback: CallbackQuery):
    tickets = get_user_tickets(callback.from_user.id)
    if not tickets:
        text = "📋 <b>Мои тикеты</b>\n\nУ вас пока нет тикетов."
        await safe_edit(callback, text, reply_markup=back_to_support_kb)
        await safe_answer(callback)
        return
    text = "📋 <b>Мои тикеты:</b>\n\n"
    for t in tickets:
        status = "✅" if t["status"] == "closed" else "⏳"
        text += f"{status} #{t['id']} — {t['type']} — {t['created_at'][:10]}\n"
    await safe_edit(callback, text, reply_markup=back_to_support_kb)
    await safe_answer(callback)
