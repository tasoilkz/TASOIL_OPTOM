from aiogram.types import (
    InlineKeyboardMarkup, 
    InlineKeyboardButton, 
    ReplyKeyboardMarkup, 
    KeyboardButton
)
from config import PRICE_CATEGORIES

# --- ГЛАВНОЕ МЕНЮ ---
def get_main_menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔥 Акции и спецпредложения (Liqui Moly)", callback_data="cat_promo")],
        [InlineKeyboardButton(text="🛢 Масла и автохимия", callback_data="cat_oil")],
        [InlineKeyboardButton(text="🔍 Фильтра", callback_data="cat_filter")],
        [InlineKeyboardButton(text="🧤 Перчатки оптом", callback_data="cat_gloves")],
        [InlineKeyboardButton(text="📝 Оформить заявку / заказ", callback_data="start_order")]
    ])

def get_brands_keyboard(category):
    keyboard_buttons = []
    if category in PRICE_CATEGORIES:
        for brand_key, info in PRICE_CATEGORIES[category].items():
            keyboard_buttons.append([InlineKeyboardButton(text=f"📌 {info['name']}", callback_data=f"brand_{brand_key}")])
            
    all_text = "🔎 Искать по ВСЕМ брендам фильтров" if category == "filter" else "🔎 Искать по ВСЕМ брендам масел"
    all_data = "search_all_filter" if category == "filter" else "search_all_oil"
    
    keyboard_buttons.insert(0, [InlineKeyboardButton(text=all_text, callback_data=all_data)])
    keyboard_buttons.append([InlineKeyboardButton(text="⬅️ Назад к категориям", callback_data="back_to_categories")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

def get_back_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Главное меню", callback_data="back_to_categories")]
    ])

def get_brand_selected_keyboard(brand_key):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📥 Скачать прайс-лист", callback_data=f"dl_price_{brand_key}")],
        [InlineKeyboardButton(text="🔄 Главное меню", callback_data="back_to_categories")]
    ])

# --- КНОПКИ ДЛЯ ФОРМЫ ЗАКАЗА ---
def get_cancel_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить оформление", callback_data="cancel_order")]
    ])

def get_company_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭ Пропустить", callback_data="skip_company")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_order")]
    ])

def get_address_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏬 Самовывоз (со склада)", callback_data="pickup_delivery")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_order")]
    ])

def get_phone_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Поделиться контактом", request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )