from aiogram import Router, F
from aiogram.types import CallbackQuery
from tg_utils import safe_edit, safe_answer
from keyboards import legal_kb, legal_back_kb, back_to_main_kb

router = Router()


@router.callback_query(F.data == "legal_menu")
async def legal_menu_handler(callback: CallbackQuery):
    text = "📜 <b>Документы</b>\n\nВыберите документ:"
    await safe_edit(callback, text, reply_markup=legal_kb)
    await safe_answer(callback)


@router.callback_query(F.data == "privacy_policy")
async def privacy_policy_handler(callback: CallbackQuery):
    text = (
        "🔐 <b>Политика конфиденциальности</b>\n\n"
        "1. Мы не передаём данные третьим лицам\n"
        "2. Данные хранятся в зашифрованном виде\n"
        "3. Вы можете запросить удаление данных"
    )
    await safe_edit(callback, text, reply_markup=legal_back_kb)
    await safe_answer(callback)


@router.callback_query(F.data == "terms_of_service")
async def terms_handler(callback: CallbackQuery):
    text = (
        "📄 <b>Пользовательское соглашение</b>\n\n"
        "1. Аккаунты предоставляются как есть\n"
        "2. Гарантия действует в течение указанного срока\n"
        "3. Возврат средств возможен только по решению администрации"
    )
    await safe_edit(callback, text, reply_markup=legal_back_kb)
    await safe_answer(callback)
