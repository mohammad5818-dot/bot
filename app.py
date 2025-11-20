from telegram.ext import Application, CommandHandler, MessageHandler
from telegram.ext import filters, CallbackQueryHandler 
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup 
from telegram import InputFile 
from telegram.ext import ContextTypes 
import os 
import io 
from google import genai 
from google.genai.errors import APIError 

# =========================================================
# تنظیمات و ثابت‌ها
# =========================================================
# این مقادیر بهتر است از طریق متغیرهای محیطی Render تنظیم شوند.
TOKEN = "8314422409:AAF9hZ0uEe1gQH5Fx9xVpUuiGFuX8lXvzm4"  
GEMINI_API_KEY = "AIzaSyDtkVNu7esH4OfQWmK65leFtf4DU8eD1oY" 
TARGET_CHANNEL_USERNAME = "@hodhod500_ax" 

# متغیرهای محیطی حیاتی برای Render
PORT = int(os.environ.get("PORT", 8443)) 
WEBHOOK_URL = os.environ.get("WEBHOOK_URL") 
WEBHOOK_PATH = "/" + os.environ.get("TOKEN", TOKEN) 

user_states = {} 
user_credits = {} 

# =========================================================
# توابع مدیریتی و کمکی
# =========================================================

# اتصال به Gemini - مقداردهی اولیه فقط یک بار در این قسمت انجام می‌شود
try:
    final_gemini_key = os.environ.get("GEMINI_API_KEY", GEMINI_API_KEY)
    
    if final_gemini_key and final_gemini_key != "YOUR_GEMINI_API_KEY_HERE":
        client = genai.Client(api_key=final_gemini_key)
    else:
        print("هشدار: GEMINI_API_KEY تنظیم نشده است. فراخوانی‌های AI کار نخواهد کرد.")
        client = None
except Exception as e:
    print(f"خطا در ایجاد کلاینت Gemini: {e}")
    client = None

def check_credit(user_id):
    """بررسی اعتبار کاربر"""
    credit = user_credits.get(user_id, 0)
    return credit > 0, credit

async def send_credit_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش منوی اصلی مدیریت اعتبار"""
    user_id = update.effective_user.id
    
    credit_keyboard = [
        [InlineKeyboardButton("🤝 دعوت دوستان", callback_data='credit_invite_friends')],
        [InlineKeyboardButton("💰 خرید اعتبار", callback_data='credit_purchase_plans')]
    ]
    credit_markup = InlineKeyboardMarkup(credit_keyboard)
    
    await context.bot.send_message(
        chat_id=user_id,
        text="متأسفانه اعتبار شما به پایان رسیده است. برای دریافت اعتبار به یکی از دو روش زیر اقدام کنید:",
        reply_markup=credit_markup
    )

# =========================================================
# توابع هندلر Callback Query (دکمه‌های شیشه‌ای)
# =========================================================

async def send_channel_check_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer() 
    user_id = query.from_user.id
    
    keyboard = [
        [InlineKeyboardButton("کانال آموزش کار با ربات", url="https://t.me/hodhod500_amoozesh")],
        [InlineKeyboardButton("کانال نمونه عکس‌های تولیدی", url="https://t.me/hodhod500_ax")],
        [InlineKeyboardButton("✅ عضو شدم و ادامه می‌دهم", callback_data='check_membership')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = "برای شروع کار، لطفا در دو کانال زیر عضو شوید و سپس دکمه «عضو شدم و ادامه می‌دهم» را بزنید:"
    
    await context.bot.send_message(
        chat_id=user_id,
        text=message,
        reply_markup=reply_markup
    )
    user_states[user_id] = {'state': 'waiting_for_channel_check'}


async def check_membership_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("در حال بررسی... (فرض بر موفقیت است)")
    user_id = query.from_user.id

    user_states[user_id] = {'state': 0}
    
    start_work_message = (
        "عضویت شما بررسی و تأیید شد. شما می‌توانید اکنون کار خود را شروع کنید! 🎉\n\n"
        "لطفاً **عکس مورد نظر خود** که می‌خواهید تغییرات روی آن اعمال شود را ارسال کنید."
    )
    
    try:
        await query.edit_message_text(text=start_work_message, reply_markup=None)
    except Exception:
        await context.bot.send_message(chat_id=user_id, text=start_work_message)


async def handle_invite_friends(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    bot_username = "YourBotUsername" 
    referral_link = f"https://t.me/{context.bot.username if context.bot.username else bot_username}?start=ref_{user_id}"
    
    message = (
        "🔗 از طریق لینک زیر دوستانتان را به ربات دعوت کنید و بابت هر دعوت موفق، **۳ اعتبار رایگان** دریافت کنید:\n\n"
        f"`{referral_link}`"
    )
    
    await query.edit_message_text(
        text=message,
        reply_markup=None,
        parse_mode='Markdown'
    )

async def handle_purchase_plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    purchase_keyboard = [
        [InlineKeyboardButton("🥉 اعتبار برنزی (۱۰ عکس / ۵۰,۰۰۰ تومان)", callback_data='buy_plan_bronze')],
        [InlineKeyboardButton("🥈 اعتبار نقره‌ای (۲۰ عکس / ۹۰,۰۰۰ تومان)", callback_data='buy_plan_silver')],
        [InlineKeyboardButton("🥇 اعتبار طلایی (۴۰ عکس / ۱۸۰,۰۰۰ تومان)", callback_data='buy_plan_gold')]
    ]
    purchase_markup = InlineKeyboardMarkup(purchase_keyboard)
    
    message = "سه اعتبار مختلف برای خرید وجود دارد. لطفاً پلن مورد نظر خود را انتخاب کنید:"

    await query.edit_message_text(text=message, reply_markup=purchase_markup)


async def handle_plan_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    plan_key = query.data.split('_')[-1] 
    payment_link = "https://example.com/payment/" + plan_key 
    
    message = f"""
✅ پلن **{plan_key.upper()}** انتخاب شد.

لطفاً جهت تکمیل خرید و شارژ فوری اعتبار، روی دکمه پرداخت زیر کلیک کنید:
پس از پرداخت، اعتبار شما به‌طور خودکار شارژ خواهد شد.
"""
    
    payment_keyboard = [
        [InlineKeyboardButton("💳 شروع پرداخت", url=payment_link)]
    ]
    payment_markup = InlineKeyboardMarkup(payment_keyboard)

    await query.edit_message_text(
        text=message,
        reply_markup=payment_markup
    )


async def share_to_channel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندل کردن کلیک روی دکمه ارسال به کانال نمونه‌ها"""
    query = update.callback_query
    await query.answer("در حال ارسال به کانال...") 

    try:
        data_key = query.data.split('|')[1]
        data = context.user_data.pop(data_key, None) 
    except IndexError:
        await context.bot.send_message(query.from_user.id, "خطا در بازیابی اطلاعات تصویر.")
        return

    if not data:
        await context.bot.send_message(query.from_user.id, "اطلاعات تصویر یافت نشد. شاید قبلاً ارسال شده باشد.")
        return
        
    media_id = data['media_id']
    user_prompt = data['prompt']
    caption = f"توضیحات کاربر: {user_prompt[:500]}..." 

    try:
        await context.bot.send_photo(
            chat_id=TARGET_CHANNEL_USERNAME,
            photo=media_id,
            caption=caption
        ) 
        
        await query.edit_message_reply_markup(
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ به کانال نمونه‌ها ارسال شد", callback_data='dummy_sent')]
            ])
        ) 
        
    except Exception as e:
        error_message = f"❌ خطایی در ارسال به کانال رخ داد."
        await context.bot.send_message(query.from_user.id, error_message)

# ---------------------------------------------------------
## توابع هندلر پیام (دستورات و مدیا)
# ---------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور /start"""
    user = update.message.from_user
    user_id = user.id
    first_name = user.first_name 

    if user_id not in user_credits:
        user_credits[user_id] = 3
    credit = user_credits[user_id]
    
    user_states[user_id] = {'state': 'waiting_for_start_confirm'} 
    
    keyboard = [[InlineKeyboardButton("شروع کار / بله", callback_data='start_confirmation')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    welcome_message = (
        f"سلام {first_name} جان! \n"
        f"به ربات هُدهُد خوش اومدی! 🚀\n\n"
        f"💳 اعتبار شما: {credit} عکس با کیفیت\n"
        f"💡 دوستت رو معرفی کن و بابت هر معرفی ۳ عکس رایگان بگیر! 🎁\n\n"
        f"برای شروع و دسترسی به امکانات ربات، روی دکمه «شروع کار / بله» کلیک کنید."
    )
    await update.message.reply_text(welcome_message, reply_markup=reply_markup)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندل کردن عکس‌های دریافتی"""
    user_id = update.message.from_user
