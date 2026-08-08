import openpyxl
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler, ContextTypes
import os
import sys
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

print("=" * 50)
print("🤖 Бот запускається...")
print(f"Python версія: {sys.version}")
print("=" * 50)

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
    print(f"✅ Записано в Excel: {data.get('description', '')[:50]}")

# ========== РОЗПІЗНАВАННЯ ГОЛОСУ ==========
async def transcribe_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.reply_text("🎤 Обробляю голосове...")
        voice = update.message.voice
        file = await context.bot.get_file(voice.file_id)
        os.makedirs("temp", exist_ok=True)
        ogg_path = f"temp/voice_{datetime.now().strftime('%Y%m%d_%H%M%S')}.ogg"
        await file.download_to_drive(ogg_path)
        wav_path = ogg_path.replace(".ogg", ".wav")
        audio = AudioSegment.from_ogg(ogg_path)
        audio.export(wav_path, format="wav")
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio_data = recognizer.record(source)
        text = None
        for lang in ["uk-UA", "ru-RU", "en-US"]:
            try:
                text = recognizer.recognize_google(audio_data, language=lang)
                break
            except:
                continue
        os.remove(ogg_path)
        os.remove(wav_path)
        if text:
            return text
        await update.message.reply_text("❌ Не вдалося розпізнати голос.")
        return None
    except Exception as e:
        print(f"❌ Помилка розпізнавання: {e}")
        await update.message.reply_text("❌ Помилка обробки голосового.")
        return None

async def voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "category" not in context.user_data:
        await update.message.reply_text("⚠️ Спочатку оберіть категорію через /start")
        return
    text = await transcribe_voice(update, context)
    if not text:
        return
    context.user_data["description"] = text
    category = context.user_data["category"]
    if category in THOUGHT_CATEGORIES:
        save_to_excel(context.user_data)
        await update.message.reply_text(f"🎤 Розпізнано: {text}\n\n✅ Збережено!\n📌 Категорія: {category}")
        context.user_data.clear()
        return
    if "priority" not in context.user_data:
        context.user_data["priority"] = "Середній"
    save_to_excel(context.user_data)
    await update.message.reply_text(f"🎤 Розпізнано: {text}\n\n✅ Збережено!\n📌 Категорія: {category}")
    context.user_data.clear()

# ========== ОСНОВНІ ФУНКЦІЇ ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"📩 Команда /start від {update.effective_user.username}")
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
    print(f"📂 Вибрано категорію: {category}")
    if category in TASK_CATEGORIES:
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="back_category")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(f"📌 Вибрано: {category}\n\n✏️ Введіть ОПИС задачі:", reply_markup=reply_markup)
        return DESCRIPTION
    elif category in MEDIA_CATEGORIES:
        await query.edit_message_text(f"📌 Вибрано: {category}\n\n📝 Введіть НАЗВУ:")
        return NAME
    elif category in THOUGHT_CATEGORIES:
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="back_category")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(f"📌 Вибрано: {category}\n\n🧠 Напишіть думку:", reply_markup=reply_markup)
        return DESCRIPTION
    await query.edit_message_text("❌ Невідома категорія.")
    return ConversationHandler.END

async def get_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        if query.data == "back_category":
            keyboard = [[InlineKeyboardButton(cat, callback_data=cat)] for cat in CATEGORIES]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("📋 Оберіть категорію:", reply_markup=reply_markup)
            return CATEGORY
    context.user_data["description"] = update.message.text
    category = context.user_data["category"]
    if category in THOUGHT_CATEGORIES:
        save_to_excel(context.user_data)
        await update.message.reply_text(f"✅ Збережено!\n📌 Категорія: {category}\n📝 Опис: {context.user_data['description']}")
        return ConversationHandler.END
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
    await query.edit_message_text("👤 Хто відповідальний? (напишіть або 'Пропустити')", reply_markup=reply_markup)
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
            await query.edit_message_text("📅 Дата виконання (ДД.ММ.РРРР) або 'Пропустити':", reply_markup=reply_markup)
            return DUE_DATE
    else:
        text = update.message.text
        context.user_data["responsible"] = text if text.strip() else ""
        keyboard = [
            [InlineKeyboardButton("⏭️ Пропустити", callback_data="skip")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_due_date")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("📅 Дата виконання (ДД.ММ.РРРР) або 'Пропустити':", reply_markup=reply_markup)
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
            await query.edit_message_text("👤 Хто відповідальний?", reply_markup=reply_markup)
            return RESPONSIBLE
        elif query.data == "skip":
            context.user_data["due_date"] = ""
            save_to_excel(context.user_data)
            data = context.user_data
            await query.edit_message_text(f"✅ Збережено!\n📌 Категорія: {data['category']}\n📝 Опис: {data['description']}")
            return ConversationHandler.END
    else:
        context.user_data["due_date"] = update.message.text
        save_to_excel(context.user_data)
        data = context.user_data
        await update.message.reply_text(f"✅ Збережено!\n📌 Категорія: {data['category']}\n📝 Опис: {data['description']}")
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
    await update.message.reply_text(f"✅ Збережено!\n📌 Категорія: {data['category']}\n📝 Назва: {data['name']}")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Скасовано. /start для нового запису.")
    return ConversationHandler.END

# ========== ЗАПУСК ==========
def main():
    try:
        print("📦 Створення додатку...")
        app = Application.builder().token(TOKEN).build()
        print("✅ Додаток створено")
        
        # Окремий обробник голосових
        app.add_handler(MessageHandler(filters.VOICE, voice_handler))
        print("✅ Обробник голосових додано")
        
        # Основний ConversationHandler
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
                RESPONSIBLE: [
                    CallbackQueryHandler(get_responsible),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, get_responsible)
                ],
                DUE_DATE: [
                    CallbackQueryHandler(get_due_date),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, get_due_date)
                ],
                NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
                LINK: [
                    CallbackQueryHandler(get_link),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, get_link)
                ],
            },
            fallbacks=[CommandHandler("cancel", cancel)],
        )
        app.add_handler(conv_handler)
        print("✅ ConversationHandler додано")
        
        print("=" * 50)
        print("🤖 Бот запущено! /start або голосове 🎤")
        print("=" * 50)
        
        # Запуск з polling
        app.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        print(f"❌ КРИТИЧНА ПОМИЛКА: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
