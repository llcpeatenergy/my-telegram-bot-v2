import sys
import os
import subprocess
import openpyxl
from datetime import datetime, timedelta, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler, ContextTypes
import speech_recognition as sr
from pydub import AudioSegment
import asyncio
import traceback

# ========================================
# ПЕРЕВІРКА FFMPEG
# ========================================
def find_ffmpeg():
    """Знаходить ffmpeg у системі"""
    possible_paths = [
        "/usr/bin/ffmpeg",
        "/usr/local/bin/ffmpeg",
        "/app/ffmpeg",
        "ffmpeg"
    ]
    for path in possible_paths:
        try:
            result = subprocess.run([path, "-version"], capture_output=True, timeout=3)
            if result.returncode == 0:
                print(f"✅ ffmpeg знайдено: {path}")
                return path
        except:
            continue
    print("❌ ffmpeg не знайдено")
    return None

FFMPEG_PATH = find_ffmpeg()
if FFMPEG_PATH:
    os.environ["PATH"] = os.path.dirname(FFMPEG_PATH) + os.pathsep + os.environ["PATH"]

# ========================================
# ЛОГУВАННЯ
# ========================================
print("=" * 60)
print("🤖 БОТ ЗАПУСКАЄТЬСЯ")
print(f"Python: {sys.version}")
print("=" * 60)
sys.stdout.flush()

# ========================================
# НАЛАШТУВАННЯ
# ========================================
TOKEN = os.environ.get("TOKEN")
if not TOKEN:
    print("❌ ТОКЕН НЕ ЗНАЙДЕНО!")
    sys.exit(1)

EXCEL_FILE = "notebook.xlsx"
CHECK_INTERVAL = 60
UKRAINE_TZ = timezone(timedelta(hours=3))

CATEGORIES = ["ТЕК", "Ідеї", "Особисті", "Книги", "Фільми", "Що відвідати", "Цікаві думки"]
TASK_CATEGORIES = ["ТЕК", "Ідеї", "Особисті"]
MEDIA_CATEGORIES = ["Книги", "Фільми", "Що відвідати"]
THOUGHT_CATEGORIES = ["Цікаві думки"]
CATEGORY, DESCRIPTION, PRIORITY, RESPONSIBLE, DUE_DATE, NAME, LINK = range(7)
REMINDER_TIME = 7
REMINDER_ACTION = 8

# ========================================
# КНОПКИ
# ========================================
def get_back_button(step):
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data=f"back_{step}")]])

def get_skip_and_back_buttons(step):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⏭️ Пропустити", callback_data=f"skip_{step}")],
        [InlineKeyboardButton("⬅️ Назад", callback_data=f"back_{step}")]
    ])

def get_category_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton(cat, callback_data=cat)] for cat in CATEGORIES])

def get_reminder_action_keyboard(row_index):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⏰ Перенагадати", callback_data=f"re_remind_{row_index}")],
        [InlineKeyboardButton("✅ Виконано", callback_data=f"done_remind_{row_index}")]
    ])

# ========================================
# EXCEL
# ========================================
def get_headers():
    return ["Категорія", "Дата", "Опис", "Пріоритет", "Хто відповідальний", 
            "Дата виконання", "Назва", "Лінк", "Нагадати о"]

def save_to_excel(data):
    try:
        try:
            wb = openpyxl.load_workbook(EXCEL_FILE)
            sheet = wb.active
        except FileNotFoundError:
            wb = openpyxl.Workbook()
            sheet = wb.active
            sheet.append(get_headers())
        
        now = datetime.now(UKRAINE_TZ)
        row = [
            data.get("category", ""),
            now.strftime("%Y-%m-%d %H:%M:%S"),
            data.get("description", ""),
            data.get("priority", ""),
            data.get("responsible", ""),
            data.get("due_date", ""),
            data.get("name", ""),
            data.get("link", ""),
            data.get("reminder_time", "")
        ]
        sheet.append(row)
        wb.save(EXCEL_FILE)
        print("✅ Excel збережено")
        return True
    except Exception as e:
        print(f"❌ Помилка Excel: {e}")
        return False

def get_reminders():
    reminders = []
    try:
        wb = openpyxl.load_workbook(EXCEL_FILE)
        sheet = wb.active
        headers = [cell.value for cell in sheet[1]]
        reminder_col = None
        for i, h in enumerate(headers):
            if h == "Нагадати о":
                reminder_col = i + 1
                break
        if not reminder_col:
            return reminders
        
        now = datetime.now(UKRAINE_TZ)
        for idx, row in enumerate(sheet.iter_rows(min_row=2, values_only=False)):
            val = row[reminder_col - 1].value
            if val and isinstance(val, str):
                try:
                    t = datetime.strptime(val, "%Y-%m-%d %H:%M").replace(tzinfo=UKRAINE_TZ)
                    if t <= now:
                        reminders.append({
                            "row_index": idx,
                            "row": row,
                            "category": row[0].value or "",
                            "description": row[2].value or "",
                            "priority": row[3].value or "",
                            "responsible": row[4].value or "",
                            "reminder_time": val
                        })
                except:
                    pass
    except:
        pass
    return reminders

def clear_reminder(row_index):
    try:
        wb = openpyxl.load_workbook(EXCEL_FILE)
        sheet = wb.active
        headers = [cell.value for cell in sheet[1]]
        reminder_col = None
        for i, h in enumerate(headers):
            if h == "Нагадати о":
                reminder_col = i + 1
                break
        if reminder_col:
            sheet[row_index + 2][reminder_col - 1].value = None
            wb.save(EXCEL_FILE)
            return True
    except:
        pass
    return False

def update_reminder_time(row_index, new_time):
    try:
        wb = openpyxl.load_workbook(EXCEL_FILE)
        sheet = wb.active
        headers = [cell.value for cell in sheet[1]]
        reminder_col = None
        for i, h in enumerate(headers):
            if h == "Нагадати о":
                reminder_col = i + 1
                break
        if reminder_col:
            sheet[row_index + 2][reminder_col - 1].value = new_time
            wb.save(EXCEL_FILE)
            return True
    except:
        pass
    return False

# ========================================
# НАГАДУВАННЯ (ФОН)
# ========================================
async def reminder_loop(app):
    while True:
        try:
            for r in get_reminders():
                chat_id = app.bot_data.get("chat_id")
                if chat_id:
                    await app.bot.send_message(
                        chat_id=chat_id,
                        text=f"⏰ **Нагадування!**\n\n📌 {r['category']}\n📝 {r['description']}\n⚡ {r['priority']}\n👤 {r.get('responsible', '—')}\n⏳ {r['reminder_time']}",
                        reply_markup=get_reminder_action_keyboard(r['row_index']),
                        parse_mode="Markdown"
                    )
                    clear_reminder(r['row_index'])
        except:
            pass
        await asyncio.sleep(CHECK_INTERVAL)

# ========================================
# КОМАНДИ
# ========================================
async def start(update, context):
    context.bot_data["chat_id"] = update.effective_chat.id
    await update.message.reply_text("📋 Оберіть категорію:", reply_markup=get_category_keyboard())
    return CATEGORY

async def handle_text(update, context):
    if "category" not in context.user_data:
        await update.message.reply_text("⚠️ Оберіть категорію:", reply_markup=get_category_keyboard())
        return CATEGORY
    return await start(update, context)

async def download_excel(update, context):
    try:
        if os.path.exists(EXCEL_FILE):
            await update.message.reply_document(
                document=open(EXCEL_FILE, 'rb'),
                filename="notebook.xlsx",
                caption="📊 Ваш файл з нотатками"
            )
        else:
            await update.message.reply_text("❌ Файл ще не створено")
    except Exception as e:
        await update.message.reply_text(f"❌ Помилка: {e}")

async def category_selected(update, context):
    query = update.callback_query
    await query.answer()
    cat = query.data
    context.user_data["category"] = cat
    
    if cat in TASK_CATEGORIES:
        await query.edit_message_text(f"📌 {cat}\n\n✏️ Введіть ОПИС:", reply_markup=get_back_button("category"))
        return DESCRIPTION
    elif cat in MEDIA_CATEGORIES:
        await query.edit_message_text(f"📌 {cat}\n\n📝 Введіть НАЗВУ:", reply_markup=get_back_button("category"))
        return NAME
    elif cat in THOUGHT_CATEGORIES:
        await query.edit_message_text(f"📌 {cat}\n\n🧠 Напишіть думку:", reply_markup=get_back_button("category"))
        return DESCRIPTION
    return ConversationHandler.END

async def get_description(update, context):
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        if query.data == "back_category":
            await query.edit_message_text("📋 Оберіть категорію:", reply_markup=get_category_keyboard())
            return CATEGORY
        return DESCRIPTION
    
    context.user_data["description"] = update.message.text
    cat = context.user_data["category"]
    
    if cat in THOUGHT_CATEGORIES:
        save_to_excel(context.user_data)
        await update.message.reply_text("✅ Збережено!")
        context.user_data.clear()
        return ConversationHandler.END
    
    keyboard = [
        [InlineKeyboardButton("🔴 Високий", callback_data="Високий")],
        [InlineKeyboardButton("🟡 Середній", callback_data="Середній")],
        [InlineKeyboardButton("🟢 Низький", callback_data="Низький")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_priority")]
    ]
    await update.message.reply_text("⚡ Пріоритет:", reply_markup=InlineKeyboardMarkup(keyboard))
    return PRIORITY

async def get_priority(update, context):
    query = update.callback_query
    await query.answer()
    
    if query.data == "back_priority":
        await query.edit_message_text(f"📌 {context.user_data.get('category', '')}\n\n✏️ Введіть ОПИС:", reply_markup=get_back_button("category"))
        return DESCRIPTION
    
    context.user_data["priority"] = query.data
    await query.edit_message_text("👤 Відповідальний:", reply_markup=get_skip_and_back_buttons("responsible"))
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
            await query.edit_message_text("⚡ Пріоритет:", reply_markup=InlineKeyboardMarkup(keyboard))
            return PRIORITY
        elif query.data == "skip_responsible":
            context.user_data["responsible"] = ""
            await query.edit_message_text("📅 Дата виконання:", reply_markup=get_skip_and_back_buttons("due_date"))
            return DUE_DATE
    else:
        context.user_data["responsible"] = update.message.text
        await update.message.reply_text("📅 Дата виконання:", reply_markup=get_skip_and_back_buttons("due_date"))
        return DUE_DATE

async def get_due_date(update, context):
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        if query.data == "back_due_date":
            await query.edit_message_text("👤 Відповідальний:", reply_markup=get_skip_and_back_buttons("responsible"))
            return RESPONSIBLE
        elif query.data == "skip_due_date":
            context.user_data["due_date"] = ""
            if context.user_data.get("category") in TASK_CATEGORIES:
                await query.edit_message_text("⏰ Введіть час нагадування (ДД.ММ.РРРР ГГ:ХХ) або 'Пропустити':", reply_markup=get_skip_and_back_buttons("reminder"))
                return REMINDER_TIME
            else:
                save_to_excel(context.user_data)
                await query.edit_message_text("✅ Збережено!")
                context.user_data.clear()
                return ConversationHandler.END
    else:
        context.user_data["due_date"] = update.message.text
        if context.user_data.get("category") in TASK_CATEGORIES:
            await update.message.reply_text("⏰ Введіть час нагадування (ДД.ММ.РРРР ГГ:ХХ) або 'Пропустити':", reply_markup=get_skip_and_back_buttons("reminder"))
            return REMINDER_TIME
        else:
            save_to_excel(context.user_data)
            await update.message.reply_text("✅ Збережено!")
            context.user_data.clear()
            return ConversationHandler.END

async def get_reminder_time(update, context):
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        if query.data == "back_reminder":
            await query.edit_message_text("📅 Дата виконання:", reply_markup=get_skip_and_back_buttons("due_date"))
            return DUE_DATE
        elif query.data == "skip_reminder":
            context.user_data["reminder_time"] = ""
            save_to_excel(context.user_data)
            await query.edit_message_text("✅ Збережено!")
            context.user_data.clear()
            return ConversationHandler.END
    else:
        try:
            t = datetime.strptime(update.message.text, "%d.%m.%Y %H:%M")
            context.user_data["reminder_time"] = t.strftime("%Y-%m-%d %H:%M")
            save_to_excel(context.user_data)
            await update.message.reply_text(f"✅ Нагадування на {update.message.text}")
            context.user_data.clear()
            return ConversationHandler.END
        except:
            await update.message.reply_text("❌ Неправильний формат. Введіть ДД.ММ.РРРР ГГ:ХХ")
            return REMINDER_TIME

async def get_name(update, context):
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        if query.data == "back_category":
            await query.edit_message_text("📋 Оберіть категорію:", reply_markup=get_category_keyboard())
            return CATEGORY
        return NAME
    
    context.user_data["name"] = update.message.text
    await update.message.reply_text("🔗 Лінк:", reply_markup=get_skip_and_back_buttons("link"))
    return LINK

async def get_link(update, context):
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        if query.data == "back_link":
            await query.edit_message_text(f"📌 {context.user_data.get('category', '')}\n\n📝 Введіть НАЗВУ:", reply_markup=get_back_button("category"))
            return NAME
        elif query.data == "skip_link":
            context.user_data["link"] = ""
            save_to_excel(context.user_data)
            await query.edit_message_text("✅ Збережено!")
            context.user_data.clear()
            return ConversationHandler.END
    else:
        context.user_data["link"] = update.message.text
        save_to_excel(context.user_data)
        await update.message.reply_text("✅ Збережено!")
        context.user_data.clear()
        return ConversationHandler.END

async def handle_reminder_action(update, context):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data.startswith("done_remind_"):
        row_index = int(data.split("_")[2])
        if clear_reminder(row_index):
            await query.edit_message_text("✅ Нагадування виконано!")
        else:
            await query.edit_message_text("❌ Помилка")
        return ConversationHandler.END
    
    elif data.startswith("re_remind_"):
        row_index = int(data.split("_")[2])
        context.user_data["remind_row_index"] = row_index
        await query.edit_message_text("⏰ Введіть новий час (ДД.ММ.РРРР ГГ:ХХ):")
        return REMINDER_ACTION

async def handle_new_reminder_time(update, context):
    row_index = context.user_data.get("remind_row_index")
    if row_index is None:
        await update.message.reply_text("❌ Помилка")
        return ConversationHandler.END
    
    try:
        t = datetime.strptime(update.message.text, "%d.%m.%Y %H:%M")
        if update_reminder_time(row_index, t.strftime("%Y-%m-%d %H:%M")):
            await update.message.reply_text(f"✅ Нагадування перенесено на {update.message.text}")
        else:
            await update.message.reply_text("❌ Помилка")
        context.user_data.pop("remind_row_index", None)
        return ConversationHandler.END
    except:
        await update.message.reply_text("❌ Неправильний формат. Введіть ДД.ММ.РРРР ГГ:ХХ")
        return REMINDER_ACTION

async def cancel(update, context):
    context.user_data.clear()
    await update.message.reply_text("❌ Скасовано")
    return ConversationHandler.END

async def error_handler(update, context):
    print(f"❌ Помилка: {context.error}")

# ========================================
# ГОЛОСОВІ (З FFMPEG)
# ========================================
async def transcribe_voice(update, context):
    if not FFMPEG_PATH:
        await update.message.reply_text("❌ ffmpeg не знайдено. Голосові не працюють.")
        return None
    
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
                if text:
                    break
            except:
                continue
        
        os.remove(ogg_path)
        os.remove(wav_path)
        
        if text:
            return text
        await update.message.reply_text("❌ Не вдалося розпізнати")
        return None
    except Exception as e:
        print(f"❌ Помилка: {e}")
        await update.message.reply_text("❌ Помилка обробки")
        return None

async def voice_handler(update, context):
    if "category" not in context.user_data:
        await update.message.reply_text("⚠️ Оберіть категорію")
        return
    
    text = await transcribe_voice(update, context)
    if not text:
        return
    
    context.user_data["description"] = text
    cat = context.user_data["category"]
    
    if cat in THOUGHT_CATEGORIES:
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
# ЗАПУСК
# ========================================
def main():
    try:
        app = Application.builder().token(TOKEN).build()
        app.add_error_handler(error_handler)
        
        app.add_handler(CommandHandler("download", download_excel))
        app.add_handler(MessageHandler(filters.VOICE, voice_handler))
        app.add_handler(CallbackQueryHandler(handle_reminder_action, pattern="^(done_remind_|re_remind_)"))
        
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
                REMINDER_TIME: [
                    CallbackQueryHandler(get_reminder_time),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, get_reminder_time)
                ],
                REMINDER_ACTION: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_new_reminder_time)
                ],
                NAME: [
                    CallbackQueryHandler(get_name),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)
                ],
                LINK: [
                    CallbackQueryHandler(get_link),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, get_link)
                ]
            },
            fallbacks=[CommandHandler("cancel", cancel)]
        )
        app.add_handler(conv_handler)
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.create_task(reminder_loop(app))
        
        print("=" * 60)
        print("🤖 БОТ УСПІШНО ЗАПУЩЕНО!")
        print("📌 /start - новий запис")
        print("📌 /download - завантажити Excel")
        print("=" * 60)
        
        app.run_polling()
    except Exception as e:
        print(f"❌ КРИТИЧНА ПОМИЛКА: {e}")

if __name__ == "__main__":
    main()
