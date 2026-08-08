import sys
import os
import openpyxl
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler, ContextTypes
import speech_recognition as sr
from pydub import AudioSegment

# ========================================
# ПРИМУСОВЕ ЛОГУВАННЯ (видно в логах Koyeb)
# ========================================
print("=" * 60)
print("🤖 БОТ ЗАПУСКАЄТЬСЯ")
print(f"Python версія: {sys.version}")
print(f"Поточна папка: {os.getcwd()}")
print("=" * 60)
sys.stdout.flush()

# ========================================
# НАЛАШТУВАННЯ
# ========================================
TOKEN = "8768269164:AAHqK0lKmNSn2L80sej2_6jIb1KRsemTg3g"
EXCEL_FILE = "notebook.xlsx"

print(f"✅ Токен завантажено: {TOKEN[:10]}...")
sys.stdout.flush()

CATEGORIES = ["ТЕК", "Ідеї", "Особисті", "Книги", "Фільми", "Що відвідати", "Цікаві думки"]
TASK_CATEGORIES = ["ТЕК", "Ідеї", "Особисті"]
MEDIA_CATEGORIES = ["Книги", "Фільми", "Що відвідати"]
THOUGHT_CATEGORIES = ["Цікаві думки"]
CATEGORY, DESCRIPTION, PRIORITY, RESPONSIBLE, DUE_DATE, NAME, LINK = range(7)

print("✅ Налаштування завантажено")
sys.stdout.flush()

# ========================================
# РОБОТА З EXCEL
# ========================================
def save_to_excel(data):
    try:
        print(f"📝 Зберігаю в Excel: {data.get('description', '')[:30]}...")
        try:
            wb = openpyxl.load_workbook(EXCEL_FILE)
            sheet = wb.active
        except FileNotFoundError:
            print("📄 Створюю новий файл Excel...")
            wb = openpyxl.Workbook()
            sheet = wb.active
            headers = ["Категорія", "Дата", "Опис", "Пріоритет", "Хто відповідальний", 
                       "Дата виконання", "Назва", "Лінк"]
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
        print("✅ Excel збережено!")
        sys.stdout.flush()
        return True
    except Exception as e:
        print(f"❌ Помилка збереження Excel: {e}")
        sys.stdout.flush()
        return False

# ========================================
# ГОЛОСОВІ
# ========================================
async def transcribe_voice(update, context):
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
        sys.stdout.flush()
        await update.message.reply_text("❌ Помилка обробки голосового.")
        return None

async def voice_handler(update, context):
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
        await update.message.reply_text(f"🎤 Розпізнано: {text}\n\n✅ Збережено!")
        context.user_data.clear()
        return
    if "priority" not in context.user_data:
        context.user_data["priority"] = "Середній"
    save_to_excel(context.user_data)
    await update.message.reply_text(f"🎤 Розпізнано: {text}\n\n✅ Збережено!")
    context.user_data.clear()

# ========================================
# ОСНОВНІ ФУНКЦІЇ
# ========================================
async def start(update, context):
    print(f"📩 /start від {update.effective_user.username}")
    sys.stdout.flush()
    keyboard = [[InlineKeyboardButton(cat, callback_data=cat)] for cat in CATEGORIES]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "📋 Оберіть категорію:"
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup)
    elif update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(text, reply_markup=reply_markup)
    return CATEGORY

async def handle_text(update, context):
    return await start(update, context)

async def category_selected(update, context):
    query = update.callback_query
    await query.answer()
    category = query.data
    context.user_data["category"] = category
    print(f"📂 Вибрано: {category}")
    sys.stdout.flush()
    if category in TASK_CATEGORIES:
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="back_category")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(f"📌 {category}\n\n✏️ Введіть ОПИС:", reply_markup=reply_markup)
        return DESCRIPTION
    elif category in MEDIA_CATEGORIES:
        await query.edit_message_text(f"📌 {category}\n\n📝 Введіть НАЗВУ:")
        return NAME
    elif category in THOUGHT_CATEGORIES:
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="back_category")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(f"📌 {category}\n\n🧠 Напишіть думку:", reply_markup=reply_markup)
        return DESCRIPTION
    await query.edit_message_text("❌ Помилка.")
    return ConversationHandler.END

async def get_description(update, context):
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
        await update.message.reply_text(f"✅ Збережено!")
        return ConversationHandler.END
    keyboard = [
        [InlineKeyboardButton("🔴 Високий", callback_data="Високий")],
        [InlineKeyboardButton("🟡 Середній", callback_data="Середній")],
        [InlineKeyboardButton("🟢 Низький", callback_data="Низький")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_priority")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("⚡ Пріоритет:", reply_markup=reply_markup)
    return PRIORITY

async def get_priority(update, context):
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
    await query.edit_message_text("👤 Відповідальний:", reply_markup=reply_markup)
    return RESPONSIBLE

async def get_responsible(update, context):
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
            await query.edit_message_text("⚡ Пріоритет:", reply_markup=reply_markup)
            return PRIORITY
        elif query.data == "skip":
            context.user_data["responsible"] = ""
            keyboard = [
                [InlineKeyboardButton("⏭️ Пропустити", callback_data="skip")],
                [InlineKeyboardButton("⬅️ Назад", callback_data="back_due_date")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("📅 Дата виконання:", reply_markup=reply_markup)
            return DUE_DATE
    else:
        text = update.message.text
        context.user_data["responsible"] = text if text.strip() else ""
        keyboard = [
            [InlineKeyboardButton("⏭️ Пропустити", callback_data="skip")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_due_date")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("📅 Дата виконання:", reply_markup=reply_markup)
        return DUE_DATE

async def get_due_date(update, context):
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        if query.data == "back_due_date":
            keyboard = [
                [InlineKeyboardButton("⏭️ Пропустити", callback_data="skip")],
                [InlineKeyboardButton("⬅️ Назад", callback_data="back_responsible")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("👤 Відповідальний:", reply_markup=reply_markup)
            return RESPONSIBLE
        elif query.data == "skip":
            context.user_data["due_date"] = ""
            save_to_excel(context.user_data)
            await query.edit_message_text("✅ Збережено!")
            return ConversationHandler.END
    else:
        context.user_data["due_date"] = update.message.text
        save_to_excel(context.user_data)
        await update.message.reply_text("✅ Збережено!")
        return ConversationHandler.END

async def get_name(update, context):
    context.user_data["name"] = update.message.text
    keyboard = [
        [InlineKeyboardButton("⏭️ Пропустити", callback_data="skip")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_name")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🔗 Лінк:", reply_markup=reply_markup)
    return LINK

async def get_link(update, context):
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
    await update.message.reply_text("✅ Збережено!")
    return ConversationHandler.END

async def cancel(update, context):
    await update.message.reply_text("❌ Скасовано.")
    return ConversationHandler.END

# ========================================
# ЗАПУСК
# ========================================
def main():
    try:
        print("📦 Створення додатку...")
        sys.stdout.flush()
        app = Application.builder().token(TOKEN).build()
        print("✅ Додаток створено")
        sys.stdout.flush()
        
        app.add_handler(MessageHandler(filters.VOICE, voice_handler))
        print("✅ Обробник голосових додано")
        sys.stdout.flush()
        
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
        sys.stdout.flush()
        
        print("=" * 60)
        print("🤖 БОТ УСПІШНО ЗАПУЩЕНО!")
        print("📌 Напишіть /start у Telegram")
        print("=" * 60)
        sys.stdout.flush()
        
        app.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        print(f"❌ КРИТИЧНА ПОМИЛКА: {e}")
        import traceback
        traceback.print_exc()
        sys.stdout.flush()

if __name__ == "__main__":
    main()
    print("⚠️ Бот завершив роботу")
    sys.stdout.flush()
