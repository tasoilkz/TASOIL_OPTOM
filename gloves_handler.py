import os
from aiogram.types import FSInputFile, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from aiogram.exceptions import TelegramBadRequest
from config import PROMO_GLOVES_FILE, CONTACT_TEXT

GLOVES_DIR = "перчатки"

# Список товаров с точным сопоставлением файла картинки, наименования и цены
GLOVES_CATALOG = [
    {
        "file": "glove_1.jpg",
        "caption": "🧤 **Перчатки рабочих специальностей (ХБ)**\n• В мешке: 780 шт\n• Цена с НДС: 90тг × 780 = **70 200 тг**"
    },
    {
        "file": "glove_2.jpg",
        "caption": "🧤 **Перчатки рабочие (красно-серые)**\n• В мешке: 600 шт\n• Цена с НДС: 142тг × 600 = **85 200 тг**"
    },
    {
        "file": "glove_3.jpg",
        "caption": "🧤 **Перчатки с полуобливом (300#)**\n• В мешке: 720 шт\n• Цена с НДС: 180тг × 720 = **129 600 тг**"
    },
    {
        "file": "suit.jpg",
        "caption": "🥼 **Защитный комбинезон / костюм**\n• В мешке: 100 шт\n• Цена с НДС: 1100тг × 100 = **110 000 тг**"
    },
    {
        "file": "vest.jpg",
        "caption": "🦺 **Сигнальный светоотражающий жилет**\n• Цена с НДС: **800 тг / шт**"
    },
    {
        "file": "roll.jpg",
        "caption": "📜 **Ткань / Полотно в рулонах (1.40 / 70м)**\n• Цена с НДС: **21 000 тг**"
    },
    {
        "file": "winter_glove.jpg",
        "caption": "❄️ **Перчатки утепленные (-40°C)**\n• В мешке: 420 пар\n• Цена с НДС: 880тг × 420 = **369 600 тг**"
    }
]

def get_gloves_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📥 Скачать полный прайс (docx)", callback_data="download_gloves_doc")],
        [InlineKeyboardButton(text="🔄 Главное меню", callback_data="back_to_categories")]
    ])

def get_after_download_keyboard():
    """Клавиатура, которая прикрепляется прямо к отправленному файлу прайса"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Главное меню", callback_data="back_to_categories")]
    ])

async def send_gloves_info(callback: CallbackQuery):
    # 1. Гасим нажатие кнопки МГНОВЕННО, чтобы Telegram не выдавал ошибку timeout
    try:
        await callback.answer()
    except TelegramBadRequest:
        pass

    # 2. Удаляем старое меню
    try:
        await callback.message.delete()
    except Exception:
        pass

    # 3. Собираем медиагруппу (альбом)
    media_group = []
    if os.path.exists(GLOVES_DIR):
        for item in GLOVES_CATALOG:
            photo_path = os.path.join(GLOVES_DIR, item["file"])
            if os.path.exists(photo_path):
                media_group.append(
                    InputMediaPhoto(
                        media=FSInputFile(photo_path),
                        caption=item["caption"],
                        parse_mode="Markdown"
                    )
                )

    footer_text = (
        "⚠️ **ОБРАТИТЕ ВНИМАНИЕ:** Перчатки и спецодежда отпускаются **только мешками**!\n"
        "👆 *Нажмите на любую фотографию выше, чтобы развернуть её и увидеть наименование и цену.*\n\n"
        f"Для заказа:{CONTACT_TEXT}"
    )

    # 4. Отправляем альбом и блок кнопок
    if media_group:
        await callback.message.answer_media_group(media=media_group)
        await callback.message.answer(
            text=footer_text,
            reply_markup=get_gloves_keyboard(),
            parse_mode="Markdown"
        )
    else:
        # Резервный вариант, если папки или фото нет
        await callback.message.answer(
            text=f"⚠️ Фотографии каталога временно недоступны.\n\nДля заказа:{CONTACT_TEXT}",
            reply_markup=get_gloves_keyboard(),
            parse_mode="Markdown"
        )

async def send_gloves_file(callback: CallbackQuery):
    try:
        await callback.answer()
    except TelegramBadRequest:
        pass

    # Удаляем кнопки у предыдущего сообщения, чтобы пользователь не нажимал их повторно наверх
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    # Отправляем документ С КНОПКОЙ «Главное меню» внизу
    if os.path.exists(PROMO_GLOVES_FILE):
        await callback.message.answer_document(
            document=FSInputFile(PROMO_GLOVES_FILE),
            caption=f"📋 **Прайс-лист на перчатки и спецодежду.**\n\n⚠️ *Напоминание: отпуск производится строго мешками.*\n\nДля заказа:{CONTACT_TEXT}",
            reply_markup=get_after_download_keyboard(),
            parse_mode="Markdown"
        )
    else:
        await callback.message.answer(
            text=f"⚠️ Файл с прайсом перчаток временно недоступен. Свяжитесь с менеджером.\n\nДля заказа:{CONTACT_TEXT}",
            reply_markup=get_after_download_keyboard(),
            parse_mode="Markdown"
        )