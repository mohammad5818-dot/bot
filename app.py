from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler
from telegram.ext import filters 
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup 
from telegram.ext import ContextTypes 
import os 

# =========================================================
# هشدار مهم: استفاده از دیتابیس (DB) الزامی است!
# =========================================================
user_credits = {} 

# =========================================================
# بخش خواندن متغیرهای محیطی از Render
# =========================================================
TOKEN = os.environ.get("TOKEN")
PORT = int(os.environ.get("PORT", 8443)) 
WEBHOOK_URL = os.environ.get("WEBHOOK_URL") 
WEBHOOK_PATH = "/" + TOKEN 


# =========================================================
# توابع هندلر (Handler Functions)
# =========================================================

# ۱. تابع شروع (نمایش منوی شیشه‌ای "بله/خیر")
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = user.id
    first_name = user.first_name 

    # ۱. بررسی و تخصیص اعتبار اولیه (منطق اعتباردهی در حافظه)
    if user_id not in user_credits:
        user_credits[user_id] = 3
    credit = user_credits[user_id]
    
    # ۲. ساختار پیام خوش‌آمدگویی
    welcome_message = (
        f"سلام {first_name} جان! \n"
        f"به ربات هُدهُد خوش اومدی! 🚀\n\n"
        f"💳 اعتبار شما: {credit} عکس با کیفیت\n"
        f"💡 دوستت رو معرفی کن و بابت هر معرفی ۳ عکس رایگان بگیر! 🎁\n\n"
        f"آماده‌ای عکست رو بسازی؟"
    )

    # ۳. ساخت منوی شیشه‌ای بله/خیر
    keyboard = [
        [
            InlineKeyboardButton("بله", callback_data='start_yes'),
            InlineKeyboardButton("خیر", callback_data='start_no')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # ارسال پیام با منوی شیشه‌ای
    await update.message.reply_text(welcome_message, reply_markup=reply_markup)


# ۲. تابع پاسخ به دکمه‌های شیشه‌ای (callback_query)
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    await query.answer() # دایره‌ی چرخان را حذف می‌کند

    if query.data == 'start_yes':
        
        # تعریف دکمه‌های کانال‌های اجباری با لینک مستقیم
        channel_keyboard = [
            [
                InlineKeyboardButton("کانال آموزش ربات هُدهُد", url="https://t.me/hodhod500_amoozesh"),
            ],
            [
                InlineKeyboardButton("کانال نمونه عکس‌های تولیدی", url="https://t.me/hodhod500_ax"),
            ]
        ]
        channel_markup = InlineKeyboardMarkup(channel_keyboard)

        channel_message = ("لطفاً برای شروع کار در دو کانال زیر عضو شوید:")

        # ویرایش پیام قبلی با دکمه‌های کانال
        await query.edit_message_text(text=channel_message, reply_markup=channel_markup)

    elif query.data == 'start_no':
        await query.edit_message_text(text="بسیار خب! هر وقت آماده شدی، مجدداً دستور /start را ارسال کن.")

# هندل پیام‌های معمولی (بدون تغییر)
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.message.from_user.id
    
    current_credit = user_credits.get(user_id, 0)
    
    if current_credit > 0:
        await update.message.reply_text(f"شما گفتید: {text}\n(اعتبار فعلی: {current_credit} عکس)")
    else:
        await update.message.reply_text("متأسفانه اعتبار شما به پایان رسیده است. لطفاً دوستان خود را معرفی کنید.")


# =========================================================
# تابع اصلی و اجرای وب‌هوک
# =========================================================
def main():
    if not TOKEN or not WEBHOOK_URL:
        # اگر متغیرها تنظیم نشده باشند، برنامه از اینجا خارج می‌شود.
        print("خطا: متغیرهای محیطی TOKEN یا WEBHOOK_URL در Render تنظیم نشده‌اند.")
        return
