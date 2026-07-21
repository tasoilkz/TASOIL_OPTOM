import os
import pandas as pd
from aiogram import Router, types
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.exceptions import TelegramBadRequest
from config import PROMO_LIQUI_MOLY_200K, PROMO_LIQUI_MOLY_1M, CONTACT_TEXT

promo_router = Router()

def get_promo_tiers_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 Закуп от 200 000 тг", callback_data="tier_200k")],
        [InlineKeyboardButton(text="📦 Закуп от 1 000 000 тг", callback_data="tier_1m")],
        [InlineKeyboardButton(text="⬅️ Назад в главное меню", callback_data="back_to_categories")]
    ])

def get_promo_categories_keyboard(tier):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛢 Моторные масла", callback_data=f"pcat_oil_{tier}")],
        [InlineKeyboardButton(text="⚙️ Трансмиссионные масла / ATF", callback_data=f"pcat_trans_{tier}")],
        [InlineKeyboardButton(text="🧪 Присадки и автохимия", callback_data=f"pcat_add_{tier}")],
        [InlineKeyboardButton(text="🧊 Антифризы и тормозные жидкости", callback_data=f"pcat_fluids_{tier}")],
        [InlineKeyboardButton(text="📥 Скачать весь файл прайса", callback_data=f"pcat_full_{tier}")],
        [InlineKeyboardButton(text="⬅️ Выбрать другой порог закупа", callback_data="cat_promo")]
    ])

def clean_markdown(text: str) -> str:
    """Удаляет символы, ломающие синтаксис Telegram Markdown."""
    if not text:
        return ""
    for char in ['*', '_', '`', '[', ']']:
        text = str(text).replace(char, '')
    return text

async def safe_edit_text(callback: CallbackQuery, text: str, reply_markup=None, parse_mode="Markdown"):
    """Универсальная функция: редактирует текст либо переотправляет сообщение."""
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

def parse_promo_file(filepath, category_type):
    items = []
    if not os.path.exists(filepath):
        print(f"⚠️ Файл не найден: {filepath}")
        return items
    
    try:
        df = pd.read_excel(filepath, header=None)
        
        # Сканируем структуру и динамически определяем индексы колонок
        col_code, col_name, col_qty, col_price = None, None, None, None
        
        for idx in range(min(100, len(df))):
            row_str = " ".join([str(v).upper() for v in df.iloc[idx].values if pd.notna(v)])
            if "ТОВАРЫ" in row_str or "НАИМЕНОВАНИЕ" in row_str or "АРТИКУЛ" in row_str:
                header_vals = df.iloc[idx].values
                for c_idx, val in enumerate(header_vals):
                    v_str = str(val).upper().strip()
                    if "АРТИКУЛ" in v_str and col_code is None:
                        col_code = c_idx
                    elif ("ТОВАР" in v_str or "НАИМЕНОВАНИЕ" in v_str) and col_name is None:
                        col_name = c_idx
                    elif ("КОЛИЧЕСТВО" in v_str or "ОСТАТОК" in v_str) and col_qty is None:
                        col_qty = c_idx
                    elif "ЦЕНА" in v_str and "СУММА" not in v_str and col_price is None:
                        col_price = c_idx
                break

        # Индивидуальные фоллбэки для колонок, если какие-то не распознаны
        if col_code is None: col_code = 5
        if col_name is None: col_name = 11
        if col_qty is None: col_qty = 37
        if col_price is None: col_price = 47

        def safe_get(row_series, c_idx):
            if c_idx is None or c_idx >= len(row_series):
                return ""
            val = row_series.iloc[c_idx]
            return "" if pd.isna(val) else str(val).strip()

        for idx in range(len(df)):
            row = df.iloc[idx]
            
            name = safe_get(row, col_name)
            code = safe_get(row, col_code)
            
            # Пропускаем заголовки и итоговые строки
            if not name or name.lower() in ["nan", "none", "", "товары (работы, услуги)"] or len(name) < 3:
                continue
            if "ИТОГО" in name.upper() or "ВСЕГО" in name.upper():
                continue

            raw_qty = safe_get(row, col_qty)
            raw_price = safe_get(row, col_price)
            
            if not raw_qty or raw_qty.lower() in ["nan", "-", ""]:
                continue
            if not raw_price or raw_price.lower() in ["nan", "-", ""]:
                continue

            # Очистка и форматирование количества
            try:
                qty_num = int(float(raw_qty.replace(" ", "")))
                qty_str = f"{qty_num} шт."
            except ValueError:
                qty_str = f"{raw_qty} шт."

            # Очистка и форматирование цены
            try:
                p_clean = float(raw_price.replace(" ", "").replace("₸", "").replace("тг", ""))
                price_str = f"{int(p_clean):,} ₸".replace(",", " ")
            except ValueError:
                price_str = f"{raw_price} ₸"

            name_upper = name.upper()
            is_match = False
            
            # Фильтрация по категориям
            if category_type == "oil":
                if any(k in name_upper for k in ["MOLYGEN", "LEICHTLAUF", "SYNTHOIL", "TOP TEC", "5W", "0W", "10W", "RACING", "SCOOTER", "MASLO", "МАСЛО"]):
                    if "ATF" not in name_upper and "GETRIEBE" not in name_upper and "АНТИФРИЗ" not in name_upper:
                        is_match = True
            elif category_type == "trans":
                if any(k in name_upper for k in ["ATF", "GETRIEBE", "DOPPELKUPPLUNGS", "ТРАНСМИССИОН"]):
                    is_match = True
            elif category_type == "add":
                if any(k in name_upper for k in ["ADDITIV", "VERLUST", "PROTECT", "PASTE", "PLUS", "TEC", "SAUBER", "STABIL", "ПРОМЫВКА", "РАСТВОРИТЕЛЬ", "СПРЕЙ", "FETT", "ПРИСАДКА"]):
                    is_match = True
            elif category_type == "fluids":
                if any(k in name_upper for k in ["АНТИФРИЗ", "ТОРМ", "ZENTRALHYDRAULIK", "KÜHLER"]):
                    is_match = True
            elif category_type == "full":
                is_match = True
                
            if is_match:
                safe_name = clean_markdown(name)
                safe_code = clean_markdown(code)
                items.append(
                    f"🔹 **{safe_name}**\n"
                    f"   🏷 Цена: **{price_str}** | 📦 Остаток: **{qty_str}** `(Арт: {safe_code})`\n"
                )
    except Exception as e:
        print(f"Ошибка парсинга промо-файла {filepath}: {e}")
        
    return items

@promo_router.callback_query(lambda c: c.data == "cat_promo")
async def process_promo_menu(callback: CallbackQuery):
    await safe_edit_text(
        callback,
        "🔥 **Акции и спецпредложения Liqui Moly**\n\nВыберите планируемую сумму закупа:",
        reply_markup=get_promo_tiers_keyboard()
    )
    await callback.answer()

@promo_router.callback_query(lambda c: c.data in ["tier_200k", "tier_1m"])
async def process_tier_selection(callback: CallbackQuery):
    tier = "200k" if "200k" in callback.data else "1m"
    tier_name = "от 200 000 тг" if tier == "200k" else "от 1 000 000 тг"
    
    await safe_edit_text(
        callback,
        f"📦 Выбран закуп **{tier_name}**.\n\n"
        "Выберите категорию товаров по акции, чтобы посмотреть позиции прямо в чате, либо скачайте полный файл:",
        reply_markup=get_promo_categories_keyboard(tier)
    )
    await callback.answer()

@promo_router.callback_query(lambda c: c.data.startswith("pcat_"))
async def process_promo_category(callback: CallbackQuery):
    parts = callback.data.split("_")
    cat_type = parts[1] 
    tier = parts[2] 
    
    filepath = PROMO_LIQUI_MOLY_200K if tier == "200k" else PROMO_LIQUI_MOLY_1M
    tier_label = "от 200 000 тг" if tier == "200k" else "от 1 000 000 тг"
    
    if cat_type == "full":
        if os.path.exists(filepath):
            await safe_edit_text(
                callback,
                f"📥 Полный акционный прайс **Liqui Moly ({tier_label})** в прикрепленном документе ниже:"
            )
            await callback.message.answer_document(FSInputFile(filepath))
            await callback.message.answer(
                f"Для заказа:\n{CONTACT_TEXT}", 
                reply_markup=get_promo_categories_keyboard(tier), 
                parse_mode="Markdown"
            )
        else:
            await safe_edit_text(
                callback,
                f"⚠️ Файл прайса не найден (`{filepath}`). Убедитесь, что он загружен на сервер.\n\n{CONTACT_TEXT}",
                reply_markup=get_promo_categories_keyboard(tier)
            )
    else:
        items = parse_promo_file(filepath, cat_type)
        cat_titles = {
            "oil": "Моторные масла",
            "trans": "Трансмиссионные масла / ATF",
            "add": "Присадки и автохимия",
            "fluids": "Антифризы и тормозные жидкости"
        }
        
        if items:
            response = f"🔥 **{cat_titles.get(cat_type, 'Товары')}** (Закуп {tier_label}):\n\n"
            for item in items[:15]:
                response += f"{item}\n"
            if len(items) > 15:
                response += f"\n*(Показано 15 из {len(items)} позиций. Скачайте полный файл для просмотра всего списка).* "
            
            response += f"\n\nДля заказа:\n{CONTACT_TEXT}"
            
            await safe_edit_text(
                callback,
                response,
                reply_markup=get_promo_categories_keyboard(tier)
            )
        else:
            await safe_edit_text(
                callback,
                f"ℹ️ В категории **{cat_titles.get(cat_type, '')}** по акции позиций не найдено (или проверьте наличие файла `{filepath}`).\n\n{CONTACT_TEXT}",
                reply_markup=get_promo_categories_keyboard(tier)
            )
                
    await callback.answer()