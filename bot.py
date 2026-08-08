import openpyxl
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler, ContextTypes
import os
import speech_recognition as sr
from pydub import AudioSegment

# ========== НАЛАШТУВАННЯ ==========
TOKEN = "8768269164:AAHqoOfBA0c4ng_zLoy23sfzajWsNBSJ_9g"
EXCEL_FILE = "notebook.xlsx"

CATEGORIES = ["ТЕК", "Ідеї", "Особисті", "Книги", "Фільми", "Що відвідати", "Цікаві думки"]
TASK_CATEGORIES = ["ТЕК", "Ідеї", "Особисті"]
MEDIA_CATEGORIES = ["Книги", "Фільми", "Що відвідати"]
THOUGHT_CATEGORIES = ["Цікаві думки"]

CATEGORY, DESCRIPTION, PRIORITY, RESPONSIBLE, DUE_DATE, NAME, LINK = range(7)

# ========== РОБОТА З EXCEL ==========
def save_to_excel(data):
    try:
        wb = openpyxl.load_workbook(EXCEL_FILE)
        sheet = wb.active
    except FileNotFoundError:
        wb = openpyxl.Workbook()
        sheet = wb.active
        headers = ["Категорія", "Дата", "Опис", "Пріоритет", "Хто відповідальний", 
                   "Дата виконання орієнтовна", "Назва (фільми,книги, що відвідати)", 
                   "Лінк (фільм, книги, що відвідати)"]
        sheet.append(headers)
    
    row = [
        data.get("category", ""),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        data.get("description", ""),
        data.get("priority", ""),
        data.get("responsible", ""),
        data.get("due_date", ""),
        data.get("name", ""),
        data.get("link", "")
    ]
    sheet.append(row)
    wb.save(EXCEL_FILE)

# ========== РОЗПІЗНАВАННЯ ГОЛОСУ ==========
async def transcribe_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Розпізнає голосове повідомлення в текст"""
    try:
        await update.message.reply_text("🎤 Обробляю голосове...")
        
        # Завантажуємо голосове
        voice = update.message.voice
        file = await context.bot.get_file(voice.file_id)
        
        # Створюємо папку для тимчасових файлів
        os.makedirs("temp", exist_ok=True)
        
        # Зберігаємо .ogg файл
        ogg_path = f"temp/voice_{datetime.now().strftime('%Y%m%d_%H%M%S')}.ogg"
        await file.download_to_drive(ogg_path)
        
        # Конвертуємо .ogg в .wav
        wav_path = ogg_path.replace(".ogg", ".wav")
        audio = AudioSegment.from_ogg(ogg_path)
        audio.export(wav_path, format="wav")
        
        # Розпізнаємо
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio_data = recognizer.record(source)
        
        # Пробуємо різні мови
        text = None
        for lang in ["uk-UA", "ru-RU", "en-US"]:
            try:
                text = recognizer.recognize_google(audio_data, language=lang)
                break
            except sr.UnknownValueError:
                continue
            except sr.RequestError:
                await update.message.reply_text("❌ Немає з'єднання з Google. Перевірте інтернет.")
                os.remove(ogg_path)
                os.remove(wav_path)
                return None
        
        # Видаляємо тимчасові файли
        os.remove(ogg_path)
        os.remove(wav_path)
        
        if text:
            return text
        else:
            await update.message.reply_text("❌ Не вдалося розпізнати голос. Спробуйте чіткіше.")
            return None
        
    except Exception as e:
        print(f"Помилка розпізнавання: {e}")
        await update.message.reply_text("❌ Помилка обробки голосового.")
        return None

# ========== ОКРЕМИЙ ОБРОБНИК ГОЛОСОВИХ ==========
async def voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка голосового повідомлення (окремо від ConversationHandler)"""
    
    # Перевіряємо, чи вибрано категорію
    if "category" not in context.user_data:
        await update.message.reply_text("⚠️ Спочатку оберіть категорію через /start")
        return
    
    # Розпізнаємо голос
    text = await transcribe_voice(update, context)
    if not text:
        return
    
    # Зберігаємо розпізнаний текст
    context.user_data["description"] = text
    category = context.user_data["category"]
    
    # Якщо Цікаві думки — одразу зберігаємо
    if category in THOUGHT_CATEGORIES:
        save_to_excel(context.user_data)
        await update.message.reply_text(
            f"🎤 Розпізнано: {text}\n\n"
            f"✅ Збережено!\n"
            f"📌 Категорія: {category}\n"
            f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        context.user_data.clear()
        return
    
    # Для задач — зберігаємо з пріоритетом за замовчуванням
    if "priority" not in context.user_data:
        context.user_data["priority"] = "Середній"
    
    save_to_excel(context.user_data)
    await update.message.reply_text(
        f"🎤 Розпізнано: {text}\n\n"
        f"✅ Збережено!\n"
        f"📌 Категорія: {category}\n"
        f"⚡ Пріоритет: {context.user_data.get('priority', 'Середній')}\n"
        f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    context.user_data.clear()

# ========== ФУНКЦІЇ БОТА ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton(cat, callback_data=cat)] for cat in CATEGORIES]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "📋 Оберіть категорію для нового запису:"
    
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup)
    elif update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(text, reply_markup=reply_markup)
    return CATEGORY

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await start(update, context)

async def category_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    category = query.data
    context.user_data["category"] = category
    
    if category in TASK_CATEGORIES:
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="back_category")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"📌 Вибрано: {category}\n\n✏️ Введіть ОПИС задачі\n(або надішліть голосове 🎤):",
            reply_markup=reply_markup
        )
        return DESCRIPTION
    elif category in MEDIA_CATEGORIES:
        await query.edit_message_text(
            f"📌 Вибрано: {category}\n\n📝 Введіть НАЗВУ:"
        )
        return NAME
    elif category in THOUGHT_CATEGORIES:
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="back_category")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"📌 Вибрано: {category}\n\n🧠 Напишіть думку\n(або надішліть голосове 🎤):",
            reply_markup=reply_markup
        )
        return DESCRIPTION
    else:
        await query.edit_message_text("❌ Невідома категорія.")
        return ConversationHandler.END

async def get_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Якщо кнопка "Назад"
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        if query.data == "back_category":
            keyboard = [[InlineKeyboardButton(cat, callback_data=cat)] for cat in CATEGORIES]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("📋 Оберіть категорію:", reply_markup=reply_markup)
            return CATEGORY
    
    # Текстовий опис
    context.user_data["description"] = update.message.text
    category = context.user_data["category"]
    
    if category in THOUGHT_CATEGORIES:
        save_to_excel(context.user_data)
        await update.message.reply_text(
            f"✅ Збережено!\n\n"
            f"📌 Категорія: {category}\n"
            f"📝 Опис: {context.user_data['description']}\n"
            f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        return ConversationHandler.END
    else:
        keyboard = [
            [InlineKeyboardButton("🔴 Високий", callback_data="Високий")],
            [InlineKeyboardButton("🟡 Середній", callback_data="Середній")],
            [InlineKeyboardButton("🟢 Низький", callback_data="Низький")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_priority")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("⚡ Оберіть ПРІОРИТЕТ:", reply_markup=reply_markup)
        return PRIORITY

async def get_priority(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "back_priority":
        keyboard = [[InlineKeyboardButton(cat, callback_data=cat)] for cat in CATEGORIES]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("📋 Оберіть категорію:", reply_markup=reply_markup)
        return CATEGORY
    
    context.user_data["priority"] = query.data
    keyboard = [
        [InlineKeyboardButton("⏭️ Пропустити", callback_data="skip")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_responsible")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        "👤 Хто відповідальний? (напишіть або 'Пропустити')",
        reply_markup=reply_markup
    )
    return RESPONSIBLE

async def get_responsible(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        if query.data == "back_responsible":
            keyboard = [
                [InlineKeyboardButton("🔴 Високий", callback_data="Високий")],
                [InlineKeyboardButton("🟡 Середній", callback_data="Середній")],
                [InlineKeyboardButton("🟢 Низький", callback_data="Низький")],
                [InlineKeyboardButton("⬅️ Назад", callback_data="back_priority")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("⚡ Оберіть ПРІОРИТЕТ:", reply_markup=reply_markup)
            return PRIORITY
        elif query.data == "skip":
            context.user_data["responsible"] = ""
            keyboard = [
                [InlineKeyboardButton("⏭️ Пропустити", callback_data="skip")],
                [InlineKeyboardButton("⬅️ Назад", callback_data="back_due_date")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "📅 Дата виконання (ДД.ММ.РРРР) або 'Пропустити':",
                reply_markup=reply_markup
            )
            return DUE_DATE
    else:
        text = update.message.text
        context.user_data["responsible"] = text if text.strip() else ""
        keyboard = [
            [InlineKeyboardButton("⏭️ Пропустити", callback_data="skip")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_due_date")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "📅 Дата виконання (ДД.ММ.РРРР) або 'Пропустити':",
            reply_markup=reply_markup
        )
        return DUE_DATE

async def get_due_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        if query.data == "back_due_date":
            keyboard = [
                [InlineKeyboardButton("⏭️ Пропустити", callback_data="skip")],
                [InlineKeyboardButton("⬅️ Назад", callback_data="back_responsible")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "👤 Хто відповідальний?",
                reply_markup=reply_markup
            )
            return RESPONSIBLE
        elif query.data == "skip":
            context.user_data["due_date"] = ""
            save_to_excel(context.user_data)
            data = context.user_data
            await query.edit_message_text(
                f"✅ Збережено!\n\n"
                f"📌 Категорія: {data['category']}\n"
                f"📝 Опис: {data['description']}\n"
                f"⚡ Пріоритет: {data.get('priority', '—')}\n"
                f"👤 Відповідальний: {data.get('responsible', '—') or '—'}\n"
                f"📅 Дата виконання: —\n"
                f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            return ConversationHandler.END
    else:
        context.user_data["due_date"] = update.message.text
        save_to_excel(context.user_data)
        data = context.user_data
        await update.message.reply_text(
            f"✅ Збережено!\n\n"
            f"📌 Категорія: {data['category']}\n"
            f"📝 Опис: {data['description']}\n"
            f"⚡ Пріоритет: {data.get('priority', '—')}\n"
            f"👤 Відповідальний: {data.get('responsible', '—') or '—'}\n"
            f"📅 Дата виконання: {data.get('due_date', '—')}\n"
            f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        return ConversationHandler.END

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text
    keyboard = [
        [InlineKeyboardButton("⏭️ Пропустити", callback_data="skip")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_name")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🔗 Введіть ЛІНК (або 'Пропустити'):", reply_markup=reply_markup)
    return LINK

async def get_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        if query.data == "back_name":
            await query.edit_message_text(f"📌 {context.user_data['category']}\n\n📝 Введіть НАЗВУ:")
            return NAME
        elif query.data == "skip":
            context.user_data["link"] = ""
    else:
        context.user_data["link"] = update.message.text
    
    save_to_excel(context.user_data)
    data = context.user_data
    await update.message.reply_text(
        f"✅ Збережено!\n\n"
        f"📌 Категорія: {data['category']}\n"
        f"📝 Назва: {data['name']}\n"
        f"🔗 Лінк: {data.get('link', '—') or '—'}\n"
        f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Скасовано. /start для нового запису.")
    return ConversationHandler.END

# ========== ЗАПУСК ==========
def main():
    app = Application.builder().token(TOKEN).build()
    
    # Окремий обробник голосових (ПОЗА ConversationHandler)
    app.add_handler(MessageHandler(filters.VOICE, voice_handler))
    
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text)
        ],
        states={
            CATEGORY: [CallbackQueryHandler(category_selected)],
            DESCRIPTION: [
                CallbackQueryHandler(get_description),
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_description)
            ],
            PRIORITY: [CallbackQueryHandler(get_priority)],
            RESPONSIBLE: [CallbackQueryHandler(get_responsible), MessageHandler(filters.TEXT & ~filters.COMMAND, get_responsible)],
            DUE_DATE: [CallbackQueryHandler(get_due_date), MessageHandler(filters.TEXT & ~filters.COMMAND, get_due_date)],
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            LINK: [CallbackQueryHandler(get_link), MessageHandler(filters.TEXT & ~filters.COMMAND, get_link)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    app.add_handler(conv_handler)
    
    print("🤖 Бот запущено! /start або голосове 🎤")
    app.run_polling()

if __name__ == "__main__":
    main()