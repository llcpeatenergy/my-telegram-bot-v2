import sys
import os
import openpyxl
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler, ContextTypes
import speech_recognition as sr
from pydub import AudioSegment
import traceback

# ========================================
# ПРИМУСОВЕ ЛОГУВАННЯ
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
TOKEN = os.environ.get("TOKEN")
if not TOKEN:
    print("❌ ПОМИЛКА: Токен не знайдено в змінних середовища!")
    print("Додайте змінну TOKEN у налаштуваннях Koyeb")
    sys.exit(1)

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
# ДОПОМІЖНІ ФУНКЦІЇ ДЛЯ КНОПОК
# ========================================
def get_back_button(step):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Назад", callback_data=f"back_{step}")]
    ])

def get_skip_and_back_buttons(step):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⏭️ Пропустити", callback_data=f"skip_{step}")],
        [InlineKeyboardButton("⬅️ Назад", callback_data=f"back_{step}")]
    ])

def get_category_keyboard():
    """Повертає клавіатуру з категоріями"""
    keyboard = [[InlineKeyboardButton(cat, callback_data=cat)] for cat in CATEGORIES]
    return InlineKeyboardMarkup(keyboard)

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
# КОМАНДА ЗАВАНТАЖЕННЯ EXCEL
# ========================================
async def download_excel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if os.path.exists(EXCEL_FILE):
            await update.message.reply_document(
                document=open(EXCEL_FILE, 'rb'),
                filename="notebook.xlsx",
                caption="📊 Ось ваш файл з нотатками!"
            )
        else:
            await update.message.reply_text("❌ Файл ще не створено. Зробіть хоча б один запис.")
    except Exception as e:
        await update.message.reply_text(f"❌ Помилка: {e}")

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
    await update.message.reply_text(
        "📋 Оберіть категорію:",
        reply_markup=get_category_keyboard()
    )
    return CATEGORY

async def handle_text(update, context):
    # Якщо користувач надіслав текст, але категорії немає
    if "category" not in context.user_data:
        await update.message.reply_text(
            "⚠️ Спочатку оберіть категорію за допомогою кнопок.",
            reply_markup=get_category_keyboard()
        )
        return CATEGORY
    return await start(update, context)

async def category_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    category = query.data
    context.user_data["category"] = category
    print(f"📂 Вибрано: {category}")
    sys.stdout.flush()
    
    if category in TASK_CATEGORIES:
        await query.edit_message_text(
            f"📌 {category}\n\n✏️ Введіть ОПИС:",
            reply_markup=get_back_button("category")
        )
        return DESCRIPTION
        
    elif category in MEDIA_CATEGORIES:
        await query.edit_message_text(
            f"📌 {category}\n\n📝 Введіть НАЗВУ:",
            reply_markup=get_back_button("category")
        )
        return NAME
        
    elif category in THOUGHT_CATEGORIES:
        await query.edit_message_text(
            f"📌 {category}\n\n🧠 Напишіть думку:",
            reply_markup=get_back_button("category")
        )
        return DESCRIPTION
        
    await query.edit_message_text("❌ Помилка.")
    return ConversationHandler.END

async def get_description(update, context):
    # Перевіряємо наявність категорії
    if "category" not in context.user_data:
        await update.message.reply_text(
            "⚠️ Спочатку оберіть категорію за допомогою кнопок.",
            reply_markup=get_category_keyboard()
        )
        return CATEGORY
    
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        if query.data == "back_category":
            await query.edit_message_text(
                "📋 Оберіть категорію:",
                reply_markup=get_category_keyboard()
            )
            return CATEGORY
        return DESCRIPTION
    
    # Зберігаємо опис
    context.user_data["description"] = update.message.text
    category = context.user_data["category"]
    
    if category in THOUGHT_CATEGORIES:
        save_to_excel(context.user_data)
        await update.message.reply_text("✅ Збережено!")
        context.user_data.clear()
        return ConversationHandler.END
    
    # Переходимо до пріоритету
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
        await query.edit_message_text(
            f"📌 {context.user_data.get('category', '')}\n\n✏️ Введіть ОПИС:",
            reply_markup=get_back_button("category")
        )
        return DESCRIPTION
    
    context.user_data["priority"] = query.data
    await query.edit_message_text(
        "👤 Відповідальний:",
        reply_markup=get_skip_and_back_buttons("responsible")
    )
    return RESPONSIBLE

async def get_responsible(update, context):
    if "category" not in context.user_data:
        await update.message.reply_text(
            "⚠️ Оберіть категорію:",
            reply_markup=get_category_keyboard()
        )
        return CATEGORY
    
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
        
        elif query.data == "skip_responsible":
            context.user_data["responsible"] = ""
            await query.edit_message_text(
                "📅 Дата виконання:",
                reply_markup=get_skip_and_back_buttons("due_date")
            )
            return DUE_DATE
    
    # Якщо текст
    context.user_data["responsible"] = update.message.text
    await update.message.reply_text(
        "📅 Дата виконання:",
        reply_markup=get_skip_and_back_buttons("due_date")
    )
    return DUE_DATE

async def get_due_date(update, context):
    if "category" not in context.user_data:
        await update.message.reply_text(
            "⚠️ Оберіть категорію:",
            reply_markup=get_category_keyboard()
        )
        return CATEGORY
    
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        
        if query.data == "back_due_date":
            await query.edit_message_text(
                "👤 Відповідальний:",
                reply_markup=get_skip_and_back_buttons("responsible")
            )
            return RESPONSIBLE
        
        elif query.data == "skip_due_date":
            context.user_data["due_date"] = ""
            save_to_excel(context.user_data)
            await query.edit_message_text("✅ Збережено!")
            context.user_data.clear()
            return ConversationHandler.END
    
    context.user_data["due_date"] = update.message.text
    save_to_excel(context.user_data)
    await update.message.reply_text("✅ Збережено!")
    context.user_data.clear()
    return ConversationHandler.END

async def get_name(update, context):
    if "category" not in context.user_data:
        await update.message.reply_text(
            "⚠️ Оберіть категорію:",
            reply_markup=get_category_keyboard()
        )
        return CATEGORY
    
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        if query.data == "back_category":
            await query.edit_message_text(
                "📋 Оберіть категорію:",
                reply_markup=get_category_keyboard()
            )
            return CATEGORY
        return NAME
    
    context.user_data["name"] = update.message.text
    await update.message.reply_text(
        "🔗 Лінк:",
        reply_markup=get_skip_and_back_buttons("link")
    )
    return LINK

async def get_link(update, context):
    if "category" not in context.user_data:
        await update.message.reply_text(
            "⚠️ Оберіть категорію:",
            reply_markup=get_category_keyboard()
        )
        return CATEGORY
    
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        
        if query.data == "back_link":
            await query.edit_message_text(
                f"📌 {context.user_data.get('category', '')}\n\n📝 Введіть НАЗВУ:",
                reply_markup=get_back_button("category")
            )
            return NAME
        
        elif query.data == "skip_link":
            context.user_data["link"] = ""
            save_to_excel(context.user_data)
            await query.edit_message_text("✅ Збережено!")
            context.user_data.clear()
            return ConversationHandler.END
    
    context.user_data["link"] = update.message.text
    save_to_excel(context.user_data)
    await update.message.reply_text("✅ Збережено!")
    context.user_data.clear()
    return ConversationHandler.END

async def cancel(update, context):
    context.user_data.clear()
    await update.message.reply_text("❌ Скасовано.")
    return ConversationHandler.END

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник помилок"""
    print(f"❌ Помилка: {context.error}")
    sys.stdout.flush()
    
    # Якщо це NetworkError — пробуємо перезапустити
    if isinstance(context.error, Exception):
        error_str = str(context.error)
        if "NetworkError" in error_str or "Conflict" in error_str:
            print("⚠️ Проблема з мережею. Бот продовжує роботу...")
            sys.stdout.flush()
            return
    
    # Якщо помилка відома — повідомляємо користувача
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "❌ Сталася помилка. Спробуйте ще раз через /start"
        )

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
        
        # Додаємо обробник помилок
        app.add_error_handler(error_handler)
        
        app.add_handler(CommandHandler("download", download_excel))
        print("✅ Команду /download додано")
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
                NAME: [
                    CallbackQueryHandler(get_name),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)
                ],
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
        print("📌 Команди:")
        print("  /start - почати новий запис")
        print("  /download - завантажити Excel-файл")
        print("=" * 60)
        sys.stdout.flush()
        
        app.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        print(f"❌ КРИТИЧНА ПОМИЛКА: {e}")
        traceback.print_exc()
        sys.stdout.flush()

if __name__ == "__main__":
    main()
    print("⚠️ Бот завершив роботу")
    sys.stdout.flush()
