from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from tg_utils import safe_edit, safe_answer
from database import get_reviews, get_reviews_stats, has_user_reviewed, add_review
from keyboards import reviews_kb, review_rating_kb, review_cancel_kb, back_to_main_kb

router = Router()


class ReviewState(StatesGroup):
    waiting_rating = State()
    waiting_text = State()


@router.callback_query(F.data == "reviews")
async def reviews_handler(callback: CallbackQuery):
    stats = get_reviews_stats()
    reviews = get_reviews(limit=10)
    text = f"⭐ <b>Отзывы</b> ({stats['count']}) — средняя оценка: {stats['avg']}\n\n"
    for r in reviews:
        stars = "⭐" * r["rating"]
        name = r.get("full_name") or r.get("username") or "Аноним"
        text += f"{stars} <b>{name}</b>\n{r['text'][:200]}\n\n"
    await safe_edit(callback, text, reply_markup=reviews_kb)
    await safe_answer(callback)


@router.callback_query(F.data == "leave_review")
async def leave_review(callback: CallbackQuery, state: FSMContext):
    if has_user_reviewed(callback.from_user.id):
        await safe_answer(callback, "❌ Вы уже оставляли отзыв", show_alert=True)
        return
    text = "⭐ <b>Оцените нас</b>\n\nВыберите количество звёзд:"
    await safe_edit(callback, text, reply_markup=review_rating_kb)
    await state.set_state(ReviewState.waiting_rating)
    await safe_answer(callback)


@router.callback_query(F.data.startswith("review_rate:"))
async def review_rate(callback: CallbackQuery, state: FSMContext):
    rating = int(callback.data.split(":")[1])
    await state.update_data(rating=rating)
    await state.set_state(ReviewState.waiting_text)
    text = f"⭐ Вы выбрали {rating} звёзд(ы)\n\nНапишите текст отзыва:"
    await safe_edit(callback, text, reply_markup=review_cancel_kb)
    await safe_answer(callback)


@router.message(ReviewState.waiting_text, F.text)
async def review_text(message: Message, state: FSMContext):
    data = await state.get_data()
    rating = data.get("rating", 5)
    text = message.text.strip()
    if len(text) < 5:
        await message.answer("❌ Отзыв слишком короткий (мин. 5 символов)")
        return
    add_review(message.from_user.id, rating, text)
    await state.clear()
    await message.answer("✅ Спасибо за отзыв!", reply_markup=back_to_main_kb)


@router.callback_query(F.data == "review_cancel")
async def review_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await safe_edit(callback, "❌ Отзыв отменён", reply_markup=back_to_main_kb)
    await safe_answer(callback)
