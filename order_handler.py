from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardRemove, CallbackQuery

from config import ADMIN_CHAT_ID, CONTACT_TEXT, PRICE_CATEGORIES
from keyboards import (
    get_cancel_keyboard,
    get_company_keyboard,
    get_address_keyboard,
    get_phone_keyboard,
    get_main_menu_keyboard  # Импорт главного меню
)

order_router = Router()

class OrderForm(StatesGroup):
    waiting_for_name = State()
    waiting_for_company = State()
    waiting_for_phone = State()
    waiting_for_address = State()
    waiting_for_items = State()

@order_router.callback_query(F.data == "start_order")
async def start_order_process(callback: CallbackQuery, state: FSMContext):
    await state.set_state(OrderForm.waiting_for_name)
    await callback.message.answer(
        "📝 **Оформление заявки**\n\nШаг 1 из 5: Как к вам обращаться? *(Введите ваше имя)*",
        reply_markup=get_cancel_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

@order_router.callback_query(F.data == "cancel_order")
async def cancel_order(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    # Возвращаем Главное меню при отмене
    await callback.message.answer(
        "❌ Оформление заявки отменено.", 
        reply_markup=get_main_menu_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

@order_router.message(OrderForm.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(OrderForm.waiting_for_company)
    await message.answer(
        f"Отлично, **{message.text}**!\n\nШаг 2 из 5: Укажите название вашей компании/ИП *(или нажмите «Пропустить»)*:",
        reply_markup=get_company_keyboard(),
        parse_mode="Markdown"
    )

@order_router.callback_query(OrderForm.waiting_for_company, F.data == "skip_company")
async def skip_company(callback: CallbackQuery, state: FSMContext):
    await state.update_data(company="Не указана")
    await state.set_state(OrderForm.waiting_for_phone)
    await callback.message.answer(
        "Шаг 3 из 5: Укажите ваш **номер телефона** для связи:\n\n"
        "*(Нажмите кнопку внизу или введите номер вручную)*",
        reply_markup=get_phone_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

@order_router.message(OrderForm.waiting_for_company)
async def process_company(message: types.Message, state: FSMContext):
    await state.update_data(company=message.text)
    await state.set_state(OrderForm.waiting_for_phone)
    await message.answer(
        "Шаг 3 из 5: Укажите ваш **номер телефона** для связи:\n\n"
        "*(Нажмите кнопку внизу или введите номер вручную)*",
        reply_markup=get_phone_keyboard(),
        parse_mode="Markdown"
    )

@order_router.message(OrderForm.waiting_for_phone)
async def process_phone(message: types.Message, state: FSMContext):
    if message.contact:
        phone = message.contact.phone_number
    else:
        phone = message.text

    await state.update_data(phone=phone)
    await state.set_state(OrderForm.waiting_for_address)
    
    await message.answer(
        "Шаг 4 из 5: Укажите **адрес доставки** *(город, улица, дом/склад)*:\n\n"
        "*(Или нажмите кнопку «Самовывоз», если заберёте сами)*",
        reply_markup=get_address_keyboard(),
        parse_mode="Markdown"
    )

@order_router.callback_query(OrderForm.waiting_for_address, F.data == "pickup_delivery")
async def set_pickup_address(callback: CallbackQuery, state: FSMContext):
    await state.update_data(address="Самовывоз со склада")
    await state.set_state(OrderForm.waiting_for_items)
    await callback.message.answer(
        "Шаг 5 из 5: **Перечислите список нужных товаров**\n\n"
        "Укажите бренд, наименование, объем или количество *(например: Yacco 5W-30 4л — 2 канистры, SM106 — 10 шт)*:",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="Markdown"
    )
    await callback.answer()

@order_router.message(OrderForm.waiting_for_address)
async def process_address(message: types.Message, state: FSMContext):
    await state.update_data(address=message.text)
    await state.set_state(OrderForm.waiting_for_items)
    await message.answer(
        "Шаг 5 из 5: **Перечислите список нужных товаров**\n\n"
        "Укажите бренд, наименование, объем или количество *(например: Yacco 5W-30 4л — 2 канистры, SM106 — 10 шт)*:",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="Markdown"
    )

@order_router.message(OrderForm.waiting_for_items)
async def process_items(message: types.Message, state: FSMContext):
    raw_text = message.text.strip()
    
    # Исправляем русскую букву «В» (и «в») в вязкости на английскую «W», чтобы бот понимал «5В30» -> «5W30»
    normalized_text = (
        raw_text.replace("5В", "5W")
                .replace("10В", "10W")
                .replace("0В", "0W")
                .replace("15В", "15W")
                .replace("20В", "20W")
                .replace("5в", "5W")
                .replace("10в", "10W")
                .replace("0в", "0W")
    )
    order_lower = normalized_text.lower()
    
    # 1. Проверяем минимальную длину текста заказа
    if len(raw_text) < 3:
        await message.answer(
            "⚠️ Пожалуйста, напишите ваш заказ более подробно (укажите бренд, название товара и количество):\n\n"
            "*(Например: `Yacco 5W-30 4л — 2 канистры`)*",
            parse_mode="Markdown"
        )
        return

    # 2. Проверяем наличие цифр (цифры нужны для объема канистры или количества штук)
    has_numbers = any(char.isdigit() for char in normalized_text)
    
    if not has_numbers:
        await message.answer(
            "⚠️ В вашем заказе **отсутствуют цифры** (не указан объем или количество штук).\n\n"
            "Пожалуйста, уточните детали заказа (например: `Yacco 5W-30 4л — 2 шт`):",
            parse_mode="Markdown"
        )
        return

    # 3. Собираем все известные бренды из config.py для проверки
    all_brands = []
    for cat in PRICE_CATEGORIES.values():
        for brand_key, brand_info in cat.items():
            all_brands.append(brand_key.lower())
            if isinstance(brand_info, dict) and "name" in brand_info:
                all_brands.append(str(brand_info["name"]).lower())

    # Дополнительно разрешаем кириллическое написание бренда «якко» для Yacco
    extra_aliases = {"yacco": ["якко", "yacco"]}
    for eng_brand, rus_variants in extra_aliases.items():
        if eng_brand in all_brands:
            all_brands.extend(rus_variants)

    # Проверяем, указал ли клиент марку/бренд
    brand_found = any(brand in order_lower for brand in all_brands)

    if not brand_found:
        await message.answer(
            "⚠️ Вы указали параметры, но **забыли написать бренд** (марку масла или товара).\n\n"
            "Пожалуйста, укажите бренд (например: `Yacco 5W-30 4л — 2 шт`):",
            parse_mode="Markdown"
        )
        return

    # Сохраняем в заявку исходный текст клиента (или с исправленной буквой W, чтобы админу было привычнее)
    order_data = await state.get_data()
    user_info = message.from_user
    username = f"@{user_info.username}" if user_info.username else "нет username"

    admin_message = (
        "🚨 **НОВАЯ ЗАЯВКА С БОТА!** 🚨\n\n"
        f"👤 **Имя:** {order_data.get('name')}\n"
        f"🏢 **Компания:** {order_data.get('company')}\n"
        f"📞 **Телефон:** `{order_data.get('phone')}`\n"
        f"📍 **Адрес доставки:** {order_data.get('address')}\n"
        f"💬 **Telegram:** {username} (ID: `{user_info.id}`)\n\n"
        f"🛒 **Заказ:**\n{normalized_text}"
    )

    try:
        await message.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_message, parse_mode="Markdown")
    except Exception as e:
        print(f"❌ Ошибка отправки заявки админу: {e}")

    # Возвращаем Главное меню пользователю!
    await message.answer(
        "✅ **Ваша заявка успешно отправлена!**\n\n"
        "Наш менеджер свяжется с вами в ближайшее время для уточнения деталей и подтверждения заказа.\n\n"
        f"Для срочных вопросов:\n{CONTACT_TEXT}",
        reply_markup=get_main_menu_keyboard(),
        parse_mode="Markdown"
    )
    
    await state.clear()