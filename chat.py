import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    CallbackQueryHandler,
    filters
)
import sqlite3
from datetime import datetime

# تنظیمات اولیه
TOKEN = '7418831982:AAEFl_D-mb1voeAty1T00x0Tdwb6wMBfLgk'  # توکن ربات خود را اینجا قرار دهید
ADMIN_ID = 508332264  # آیدی عددی ادمین را اینجا قرار دهید

# فعال کردن لاگینگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ایجاد و تنظیم دیتابیس
def init_db():
    conn = sqlite3.connect('anonymous_chat.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        last_name TEXT,
        full_name TEXT,
        last_seen TEXT
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS messages (
        message_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        message_text TEXT,
        timestamp TEXT,
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    )
    ''')
    
    conn.commit()
    conn.close()

init_db()

def update_user_info(user):
    conn = sqlite3.connect('anonymous_chat.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    INSERT OR REPLACE INTO users 
    (user_id, username, first_name, last_name, full_name, last_seen)
    VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        user.id,
        user.username,
        user.first_name,
        user.last_name,
        user.full_name,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    
    conn.commit()
    conn.close()

def save_message(user_id, message_text):
    conn = sqlite3.connect('anonymous_chat.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    INSERT INTO messages 
    (user_id, message_text, timestamp)
    VALUES (?, ?, ?)
    ''', (
        user_id,
        message_text,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    
    conn.commit()
    conn.close()

def get_user_messages(user_id):
    conn = sqlite3.connect('anonymous_chat.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT message_text, timestamp FROM messages 
    WHERE user_id = ?
    ORDER BY timestamp DESC
    ''', (user_id,))
    
    messages = cursor.fetchall()
    conn.close()
    return messages

def get_all_users():
    conn = sqlite3.connect('anonymous_chat.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT u.user_id, u.full_name, u.username, COUNT(m.message_id) as message_count
    FROM users u
    LEFT JOIN messages m ON u.user_id = m.user_id
    GROUP BY u.user_id
    ORDER BY message_count DESC
    ''')
    
    users = cursor.fetchall()
    conn.close()
    return users

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ارسال پیام خوشآمدگویی جدید"""
    user = update.effective_user
    update_user_info(user)
    await update.message.reply_text(
        f"سلام {user.first_name} عزیز! 👋\n"
        "به ربات چت ناشناس خوش اومدی 🎭\n\n"
        "اینجا می‌تونی بدون اینکه طرف مقابل بفهمه کی هستی، راحت پیامتو ارسال کنی؛ "
        "اطلاعاتت کاملاً پنهان می‌مونه! ✉️\n\n"
        "حالا پیامتو بنویس تا بفرستم!"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """پردازش پیام‌های کاربران عادی"""
    user = update.effective_user
    message = update.message
    
    # ذخیره اطلاعات کاربر و پیام
    update_user_info(user)
    save_message(user.id, message.text)
    
    # ارسال پیام به ادمین با اطلاعات کامل کاربر
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"پیام ناشناس از:\n"
             f"👤 نام: {user.full_name}\n"
             f"🆔 آیدی: {user.id}\n"
             f"📌 یوزرنیم: @{user.username if user.username else 'ندارد'}\n\n"
             f"📩 پیام:\n{message.text}",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("پاسخ", callback_data=f"reply_{user.id}"),
                InlineKeyboardButton("تاریخچه", callback_data=f"history_{user.id}")
            ]
        ])
    )
    
    # ارسال تأییدیه به کاربر
    await update.message.reply_text(" پیام شما به صورت ناشناس ارسال شد منتظر پاسخ باش ✅")

async def handle_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """پردازش پیام‌های ادمین"""
    user = update.effective_user
    message = update.message
    
    # اگر در حال پاسخ دادن به کاربری است
    if 'replying_to' in context.user_data:
        target_user_id = context.user_data['replying_to']
        reply_text = message.text
        
        try:
            # ارسال پاسخ به کاربر
            await context.bot.send_message(
                chat_id=target_user_id,
                text=f"📩 پاسخ از مدیر:\n\n{reply_text}"
            )
            await update.message.reply_text("✅ پاسخ شما با موفقیت ارسال شد.")
            
            # حذف حالت پاسخ
            del context.user_data['replying_to']
        except Exception as e:
            await update.message.reply_text(f"❌ خطا در ارسال پاسخ: {e}")
        return
    
    # پردازش دستورات ادمین
    if message.text.startswith('/reply'):
        try:
            target_user_id = int(message.text.split()[1])
            reply_text = ' '.join(message.text.split()[2:])
            await context.bot.send_message(chat_id=target_user_id, text=f"پاسخ مدیر: {reply_text}")
            await update.message.reply_text("پاسخ شما ارسال شد.")
        except (IndexError, ValueError):
            await update.message.reply_text("استفاده: /reply <user_id> <message>")
    
    elif message.text.startswith('/history'):
        try:
            target_user_id = int(message.text.split()[1])
            messages = get_user_messages(target_user_id)
            
            if not messages:
                await update.message.reply_text("این کاربر تاکنون پیامی ارسال نکرده است.")
                return
            
            user_info = get_all_users()
            target_user = next((u for u in user_info if u[0] == target_user_id), None)
            
            if target_user:
                response = f"📝 تاریخچه پیام‌های کاربر:\n\n"
                response += f"👤 نام: {target_user[1]}\n"
                response += f"🆔 آیدی: {target_user[0]}\n"
                response += f"📌 یوزرنیم: @{target_user[2] if target_user[2] else 'ندارد'}\n"
                response += f"📩 تعداد پیام‌ها: {target_user[3]}\n\n"
                
                for msg in messages[:20]:
                    response += f"🗓 {msg[1]}\n📩 {msg[0]}\n\n"
                
                await update.message.reply_text(response)
            else:
                await update.message.reply_text("کاربر یافت نشد.")
        except (IndexError, ValueError):
            await update.message.reply_text("استفاده: /history <user_id>")
    
    elif message.text == '/users':
        users = get_all_users()
        
        if not users:
            await update.message.reply_text("هنوز کاربری پیامی ارسال نکرده است.")
            return
        
        response = "📊 لیست کاربران و تعداد پیام‌هایشان:\n\n"
        for user in users[:50]:
            response += f"👤 {user[1]} (🆔{user[0]}) - 📩 {user[3]} پیام\n"
            response += f"📌 @{user[2] if user[2] else 'ندارد'}\n\n"
        
        await update.message.reply_text(response)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """پردازش کلیک روی دکمه‌های اینلاین"""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith('reply_'):
        user_id = query.data.split('_')[1]
        await query.edit_message_text(
            text=query.message.text + "\n\n✅ مدیر در حال پاسخ به این پیام است...",
            reply_markup=None
        )
        context.user_data['replying_to'] = user_id
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"لطفا پاسخ خود را برای کاربر با آیدی {user_id} ارسال کنید:"
        )
    
    elif query.data.startswith('history_'):
        user_id = int(query.data.split('_')[1])
        messages = get_user_messages(user_id)
        
        if not messages:
            await query.edit_message_text(
                text=query.message.text + "\n\n⚠️ این کاربر تاکنون پیامی ارسال نکرده است.",
                reply_markup=None
            )
            return
        
        user_info = get_all_users()
        target_user = next((u for u in user_info if u[0] == user_id), None)
        
        if target_user:
            response = f"📝 تاریخچه پیام‌های کاربر:\n\n"
            response += f"👤 نام: {target_user[1]}\n"
            response += f"🆔 آیدی: {target_user[0]}\n"
            response += f"📌 یوزرنیم: @{target_user[2] if target_user[2] else 'ندارد'}\n"
            response += f"📩 تعداد پیام‌ها: {target_user[3]}\n\n"
            
            for msg in messages[:5]:
                response += f"🗓 {msg[1]}\n📩 {msg[0]}\n\n"
            
            await query.edit_message_text(
                text=response,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("نمایش همه پیام‌ها", callback_data=f"fullhistory_{user_id}")]
                ])
            )
    
    elif query.data.startswith('fullhistory_'):
        user_id = int(query.data.split('_')[1])
        messages = get_user_messages(user_id)
        user_info = get_all_users()
        target_user = next((u for u in user_info if u[0] == user_id), None)
        
        if target_user:
            response = f"📝 تمام پیام‌های کاربر:\n\n"
            response += f"👤 نام: {target_user[1]}\n"
            response += f"🆔 آیدی: {target_user[0]}\n"
            response += f"📌 یوزرنیم: @{target_user[2] if target_user[2] else 'ندارد'}\n"
            response += f"📩 تعداد پیام‌ها: {target_user[3]}\n\n"
            
            for msg in messages[:20]:
                response += f"🗓 {msg[1]}\n📩 {msg[0]}\n\n"
            
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=response
            )
            
            await query.edit_message_text(
                text="تمام پیام‌های کاربر در چت خصوصی ارسال شد.",
                reply_markup=None
            )

def main() -> None:
    """اجرای ربات"""
    application = Application.builder().token(TOKEN).build()

    # دستورات
    application.add_handler(CommandHandler("start", start))
    
    # پردازش پیام‌های متنی ادمین
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.User(ADMIN_ID),
        handle_admin_message
    ))
    
    # پردازش پیام‌های متنی کاربران عادی
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & ~filters.User(ADMIN_ID),
        handle_message
    ))
    
    # پردازش دکمه‌های اینلاین
    application.add_handler(CallbackQueryHandler(button_handler))

    # شروع ربات
    application.run_polling()

if __name__ == '__main__':
    main()