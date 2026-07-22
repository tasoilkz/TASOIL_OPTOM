import asyncio
import os
import pandas as pd
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.state import default_state
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import FSInputFile, CallbackQuery
from aiogram.exceptions import TelegramBadRequest, TelegramConflictError
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import (
    BOT_TOKEN,
    PRICE_CATEGORIES, 
    PHOTOS_DIR, 
    CONTACT_TEXT
)
from gloves_handler import send_gloves_info, send_gloves_file
from promo_handler import promo_router, clean_markdown
from order_handler import order_router
from keyboards import (
    get_main_menu_keyboard,
    get_brands_keyboard,
    get_back_keyboard,
    get_brand_selected_keyboard
)

# Инициализация бота с токеном из config.py[cite: 1]
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))

# Инициализируем диспетчер с явным хранилищем состояний[cite: 1]
dp = Dispatcher(storage=MemoryStorage())

# Подключаем роутер акций Liqui Moly и роутер оформления заказов[cite: 1]
dp.include_router(promo_router)
dp.include_router(order_router)

user_selection = {}

async def safe_edit_text(callback: CallbackQuery, text: str, reply_markup=None, parse_mode="Markdown"):
    """Безопасное редактирование сообщений (предотвращает ошибки редактирования)."""[cite: 1]
    try:
        await callback.message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            pass
        else:
            try:
                await callback.message.delete()
            except Exception:
                pass
            await callback.message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except Exception:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)

def search_in_file(filepath, query, brand_key):
    """Умный поиск, который считывает персональную карту колонок бренда из config.py."""[cite: 1]
    results = []
    if not os.path.exists(filepath):
        print(f"⚠️ Файл не найден по пути: {filepath}")
        return results
    try:
        df = pd.read_excel(filepath)
        clean_query = query.lower().replace("-", "").replace(" ", "")
        
        # Находим настройки колонок для текущего бренда
        brand_cfg = None
        for cat in PRICE_CATEGORIES.values():
            if brand_key in cat:
                brand_cfg = cat[brand_key]
                break
        
        cols_map = brand_cfg.get("cols", {"art": 0, "name": 1, "vol": 2, "price": -1}) if brand_cfg else {"art": 0, "name": 1, "vol": 2, "price": -1}

        for _, row in df.iterrows():
            row_vals = [str(val).strip() for val in row.values if pd.notna(val)]
            if not row_vals:
                continue
                
            full_row_str = " ".join(row_vals)
            clean_row_str = full_row_str.lower().replace("-", "").replace(" ", "")
            
            if clean_query in clean_row_str:
                def get_val(idx, default=""):
                    try:
                        val = row_vals[idx] if idx >= 0 else row_vals[len(row_vals) + idx]
                        return val if val != "nan" else default
                    except (IndexError, TypeError):
                        return default

                art = get_val(cols_map.get("art", 0), "-")
                name = get_val(cols_map.get("name", 1), "Товар")
                vol = get_val(cols_map.get("vol", 2), "")
                price_raw = get_val(cols_map.get("price", -1), "-")

                try:
                    p_clean = price_raw.replace(" ", "").replace("₸", "").replace("тг", "")
                    price_num = int(float(p_clean))
                    formatted_price = f"{price_num:,} ₸".replace(",", " ")
                except ValueError:
                    formatted_price = price_raw if price_raw != "-" else "Уточняйте"

                results.append({
                    "art": art,
                    "name": name,
                    "vol": vol,
                    "price": formatted_price,
                    "product": name
                })
    except Exception as e:
        print(f"❌ Ошибка чтения файла {filepath}: {e}")
    return results

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    user_selection.pop(message.from_user.id, None)
    await message.answer("Привет! Я бот-помощник магазина TASOIL.\n\nЧто вы ищете?", reply_markup=get_main_menu_keyboard())

@dp.callback_query(lambda c: c.data == "back_to_categories")
async def back_to_categories(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user_selection.pop(callback.from_user.id, None)
    await safe_edit_text(callback, "Что вы ищете?", reply_markup=get_main_menu_keyboard())
    await callback.answer()

# --- РАЗДЕЛ ПЕРЧАТКИ И СПЕЦОДЕЖДА ---
@dp.callback_query(lambda c: c.data == "cat_gloves")
async def process_gloves_menu(callback: CallbackQuery):
    await send_gloves_info(callback)

@dp.callback_query(lambda c: c.data == "download_gloves_doc")
async def process_gloves_doc_download(callback: CallbackQuery):
    await send_gloves_file(callback)

# --- РАЗДЕЛЫ МАСЛА И ФИЛЬТРЫ ---
@dp.callback_query(lambda c: c.data in ["cat_oil", "cat_filter"])
async def process_category_selection(callback: CallbackQuery):
    category = "oil" if callback.data == "cat_oil" else "filter"
    cat_title = "Масла и автохимия" if category == "oil" else "Фильтра"
    example_text = "`0W-20`, `5W-30`" if category == "oil" else "`SM106`, `AF0029`"
    
    user_selection[callback.from_user.id] = {"type": "category", "value": category}
    
    await safe_edit_text(
        callback,
        f"Вы выбрали категорию: **{cat_title}** 📁\n\n"
        f"• Напишите артикул/название (например: {example_text}) для поиска по всей категории.\n"
        "• Либо выберите бренд ниже:",
        reply_markup=get_brands_keyboard(category)
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data in ["search_all_oil", "search_all_filter"])
async def process_search_all(callback: CallbackQuery):
    category = "oil" if "oil" in callback.data else "filter"
    user_selection[callback.from_user.id] = {"type": "category", "value": category}
    cat_name = "маслам" if category == "oil" else "фильтрам"
    example_text = "`0W-20`" if category == "oil" else "`SM106`"
    
    await safe_edit_text(
        callback,
        f"Режим поиска по **всему каталогу ({cat_name})** активирован 🔍\n"
        f"Напишите нужный артикул в чат (например: {example_text}).",
        reply_markup=get_back_keyboard()
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("brand_"))
async def process_brand_selection(callback: CallbackQuery):
    brand_key = callback.data.replace("brand_", "")
    user_selection[callback.from_user.id] = {"type": "brand", "value": brand_key}
    
    selected_name = brand_key
    warning_text = ""
    description_text = ""
    
    # Считываем данные из config.py
    for cat in PRICE_CATEGORIES.values():
        if brand_key in cat:
            brand_info = cat[brand_key]
            selected_name = brand_info.get("name", brand_key)
            warning_text = brand_info.get("warning", "")
            description_text = brand_info.get("desc", "")
            break
    
    desc_block = f"ℹ️ _{description_text}_\n\n" if description_text else ""
    
    await safe_edit_text(
        callback,
        f"{warning_text}Вы выбрали бренд: **{selected_name}** ✅\n\n"
        f"{desc_block}"
        "Нажмите кнопку ниже, чтобы скачать прайс, или напишите в чат артикул/вязкость для поиска товара:",
        reply_markup=get_brand_selected_keyboard(brand_key)
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("dl_price_"))
async def process_download_price(callback: CallbackQuery):
    """Обработка скачивания прайса по нажатию на кнопку."""[cite: 1]
    brand_key = callback.data.replace("dl_price_", "")
    
    cat_info = None
    for cat in PRICE_CATEGORIES.values():
        if brand_key in cat:
            cat_info = cat[brand_key]
            break

    if cat_info and os.path.exists(cat_info["file"]):
        if cat_info.get("warning"):
            await callback.message.answer(cat_info["warning"], parse_mode="Markdown")
        await callback.message.answer(f"📁 Прайс-лист бренда **{cat_info['name']}**:", parse_mode="Markdown")
        await callback.message.answer_document(
            document=FSInputFile(cat_info["file"]),
            caption=f"Для заказа:\n{CONTACT_TEXT}",
            parse_mode="Markdown"
        )
    else:
        await callback.message.answer("⚠️ Файл прайс-листа не найден на сервере.")
    
    await callback.answer()

@dp.message(Command("price"))
async def cmd_price(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_selection:
        await message.answer("Пожалуйста, сначала выберите категорию:", reply_markup=get_main_menu_keyboard())
        return

    selection = user_selection[user_id]
    brands_to_show = list(PRICE_CATEGORIES[selection["value"]].keys()) if selection["type"] == "category" else [selection["value"]]

    for brand_key in brands_to_show:
        cat_info = next((c[brand_key] for c in PRICE_CATEGORIES.values() if brand_key in c), None)
        if cat_info and os.path.exists(cat_info["file"]):
            if cat_info["warning"]:
                await message.answer(cat_info["warning"], parse_mode="Markdown")
            await message.answer(f"📁 Прайс-лист бренда **{cat_info['name']}**:", parse_mode="Markdown")
            await message.answer_document(FSInputFile(cat_info["file"]))
            
    await message.answer(f"Для заказа:\n{CONTACT_TEXT}", reply_markup=get_back_keyboard(), parse_mode="Markdown")

# --- ОБРАБОТКА ГОЛОСОВЫХ СООБЩЕНИЙ ---
@dp.message(F.voice)
async def handle_voice_warning(message: types.Message):
    await message.answer(
        "🎙 Я пока умею искать товары только по **текстовым** сообщениям.\n\n"
        "Пожалуйста, напишите артикул или название товара текстом! 😊",
        parse_mode="Markdown"
    )

# --- ОБЩИЙ ОБРАБОТЧИК ТЕКСТОВЫХ СООБЩЕНИЙ ---
@dp.message(StateFilter(default_state))
async def handle_message(message: types.Message):
    if not message.text:
        await message.answer("Пожалуйста, отправьте текстовый запрос (артикул или название товара).", reply_markup=get_back_keyboard())
        return

    text = message.text.lower()
    if "азамат" in text:
        await message.answer(f"Азамат сейчас занят. Свяжитесь с ним:\n{CONTACT_TEXT}", parse_mode="Markdown")
        return

    if any(w in text for w in ["прайс", "весь список", "каталог", "файл"]):
        await cmd_price(message)
        return

    user_id = message.from_user.id
    if user_id not in user_selection:
        await message.answer("Пожалуйста, сначала выберите категорию:", reply_markup=get_main_menu_keyboard())
        return

    selection = user_selection[user_id]
    brands_to_search = list(PRICE_CATEGORIES[selection["value"]].keys()) if selection["type"] == "category" else [selection["value"]]

    all_found_items = []
    for brand_key in brands_to_search:
        cat_info = next((c[brand_key] for c in PRICE_CATEGORIES.values() if brand_key in c), None)
        if cat_info:
            for item in search_in_file(cat_info["file"], message.text, brand_key):
                item["brand_name"] = cat_info["name"]
                all_found_items.append(item)

    if all_found_items:
        safe_query = clean_markdown(message.text)
        response = f"📋 **Результаты по запросу `{safe_query}`:**\n\n"
        
        MAX_LENGTH = 3800 
        
        for item in all_found_items:
            vol_text = f" ({clean_markdown(item['vol'])})" if item['vol'] else ""
            
            line = (
                f"🔹 **{item['brand_name']}** {clean_markdown(item['name'])}{vol_text}\n"
                f"🏷 **{item['price']}** · `Арт: {clean_markdown(item['art'])}`\n\n"
            )
            
            if len(response) + len(line) + len(CONTACT_TEXT) > MAX_LENGTH:
                response += "⚠️ *Показана только часть результатов, так как список слишком длинный.*\n\n"
                break
                
            response += line

        response += f"Для заказа:\n{CONTACT_TEXT}"
        
        await message.answer(response, reply_markup=get_back_keyboard(), parse_mode="Markdown")

        # Проверяем наличие фото
        if os.path.exists(PHOTOS_DIR):
            prod_name = str(all_found_items[0]["product"]).lower()
            photo_path = next((os.path.join(PHOTOS_DIR, f) for f in os.listdir(PHOTOS_DIR) if f.split(".")[0].lower() in prod_name), None)
            if not photo_path and os.path.exists(os.path.join(PHOTOS_DIR, "default.jpg")):
                photo_path = os.path.join(PHOTOS_DIR, "default.jpg")

            if photo_path and os.path.exists(photo_path):
                try:
                    await message.answer_photo(FSInputFile(photo_path), caption=f"Фото: {all_found_items[0]['product']}")
                except Exception:
                    pass
    else:
        await message.answer(
            f"К сожалению, по запросу ничего не нашлось.\n\n{CONTACT_TEXT}",
            reply_markup=get_back_keyboard(),
            parse_mode="Markdown"
        )

# Функция для ответа облачному серверу Render (Health Check)[cite: 1]
async def handle_ping(request):
    return web.Response(text="Bot is running!")

async def main():
    # Запускаем фоновый веб-сервер для проверки работоспособности на Render[cite: 1]
    app = web.Application()
    app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    # Основной цикл запуска бота с автопереподключением при конфликтах[cite: 1]
    while True:
        try:
            # Удаляем вебхуки и запускаем polling
            await bot.delete_webhook(drop_pending_updates=True)
            print("🚀 Бот TASOIL успешно запущен!")
            await dp.start_polling(bot)
        except TelegramConflictError:
            print("⚠️ Обнаружен конфликт сессий (старый процесс еще активен). Ждем 5 секунд и повторяем попытку...")
            await asyncio.sleep(5)
        except Exception as e:
            print(f"⚠️ Произошла ошибка: {e}. Перезапуск через 5 секунд...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("🛑 Бот остановлен.")[cite: 1]