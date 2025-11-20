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
GEMINI_API_KEY = "AIzaSyDtkVNu7esH4OfQWmK65leFtf4DU8eD1oY" # ⭐ باید در متغیر محیطی Render تنظیم شود
TARGET_CHANNEL_USERNAME = "@hodhod500_ax" 

PORT = int(os.environ.get("PORT", 8443)) 
WEBHOOK_URL = os.environ.get("WEBHOOK_URL") 
WEBHOOK_PATH = "/" + TOKEN 

user_states = {} 
user_credits = {} 

# =========================================================
# توابع مدیریتی و کمکی
# =========================================================

# اتصال به Gemini
try:
    # ابتدا از متغیرهای محیطی می خواند، اگر نبود از هاردکد استفاده می کند
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
    referral_link = f"https://t.me/{context.bot.username}?start=ref_{user_id}"
    
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
    caption = f"توضیحات کاربر: {user_prompt}"

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
    user_id = update.message.from_user.id
    
    state = user_states.get(user_id, {'state': 0})
    if state['state'] != 0:
        await update.message.reply_text("لطفاً ابتدا مرحله عضویت در کانال را تکمیل کنید یا پرامپت خود را بفرستید.")
        return

    has_credit, current_credit = check_credit(user_id)
    if not has_credit:
        await send_credit_menu(update, context)
        return

    file_id = update.message.photo[-1].file_id 
    
    user_states[user_id] = {
        'state': 1, 
        'last_photo_id': file_id, 
        'media_type': 'photo' 
    }

    await update.message.reply_text(
        "عکس با موفقیت دریافت شد. حالا لطفاً تغییراتی که می‌خواهید روی این عکس اعمال شود (پرامپت) را در قالب یک پیام متنی برای من بنویسید."
    )


async def handle_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندل کردن متن پرامپت و پردازش AI (با Gemini Flash 2.5)"""
    user_id = update.message.from_user.id
    user_prompt = update.message.text
    
    state = user_states.get(user_id, {'state': 0})
    current_state = state.get('state', 0)

    if current_state == 1:
        
        media_id = state.get('last_photo_id')
        media_type = 'photo'
        media_type_fa = "عکس"
        
        await update.message.reply_text(
            f"پرامپت شما: '{user_prompt}' دریافت شد.\n"
            f"{media_type_fa} شما در حال پردازش توسط هوش مصنوعی است. لطفا منتظر بمانید..."
        )

        ai_output_media_id = None 
        uploaded_message = None 

        # 📌📌📌 اتصال واقعی به Gemini Flash 2.5 📌📌📌
        
        if client:
            try:
                # 1. دانلود عکس اصلی از تلگرام
                
                # ⭐ استفاده از متد download_as_bytearray به عنوان روش جایگزین
                telegram_file_object = await context.bot.get_file(media_id)
                
                # بررسی اطمینان از وجود متد
                if not hasattr(telegram_file_object, 'download_as_bytearray'):
                    # اگر این متد هم نباشد، نسخه کتابخانه بسیار قدیمی است
                    raise Exception("کتابخانه python-telegram-bot قدیمی است. متد download_as_bytearray یافت نشد.")

                # دانلود فایل به صورت bytearray و تبدیل آن به bytes
                downloaded_file_bytearray = await telegram_file_object.download_as_bytearray() 
                downloaded_file_bytes = bytes(downloaded_file_bytearray)
                
                # 2. آماده‌سازی محتوا برای Gemini
                image = client.files.upload(
                    file=downloaded_file_bytes,
                    mime_type='image/jpeg' 
                )

                # 3. فراخوانی مدل Gemini Flash 2.5
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=[
                        image,
                        f"این عکس را بر اساس دستور زیر ویرایش کن. فقط عکس ویرایش شده را خروجی بده. دستور: {user_prompt}"
                    ]
                )
                
                # 4. دریافت بایت‌های خروجی
                if response.candidates and response.candidates[0].content.parts[0].inline_data:
                    output_data = response.candidates[0].content.parts[0].inline_data.data
                    
                    # 5. ارسال خروجی به تلگرام و دریافت File ID جدید
                    uploaded_message = await context.bot.send_photo(
                        chat_id=update.effective_chat.id,
                        photo=InputFile(io.BytesIO(output_data)), 
                        caption="در حال نهایی‌سازی..." 
                    )
                    ai_output_media_id = uploaded_message.photo[-1].file_id
                    
                else:
                    await update.message.reply_text("❌ هوش مصنوعی نتوانست عکس جدیدی تولید کند. (خروجی بدون عکس بود.)")
                    client.files.delete(name=image.name) 
                    return 
                
                # حذف فایل موقت آپلود شده در Gemini
                client.files.delete(name=image.name) 
                
            except APIError as e:
                await update.message.reply_text(f"❌ خطای API هوش مصنوعی (Gemini): {e.message}")
                return
            except Exception as e:
                # خطای کلی را گزارش می کنیم
                await update.message.reply_text(f"❌ خطای نامشخص در پردازش تصویر: {e}")
                return
        
        else:
            await update.message.reply_text("❌ ربات به API هوش مصنوعی متصل نیست. لطفاً GEMINI_API_KEY را تنظیم کنید.")
            return
            
        # 📌📌📌 پایان اتصال واقعی به Gemini Flash 2.5 📌📌📌
        
        
        # کسر اعتبار
        user_credits[user_id] -= 1 
        has_credit, current_credit = check_credit(user_id) 
        
        # ذخیره اطلاعات برای اشتراک‌گذاری در کانال
        callback_key = f"share_{user_id}_{update.update_id}" 
        context.user_data[callback_key] = {
            'media_id': ai_output_media_id, 
            'prompt': user_prompt, 
            'media_type': media_type
        }

        # تعریف دکمه شیشه‌ای برای ارسال به کانال
        share_keyboard = [
            [InlineKeyboardButton("🖼 ارسال به کانال نمونه‌ها", callback_data=f'share_to_channel|{callback_key}')]
        ]
        share_markup = InlineKeyboardMarkup(share_keyboard)
        
        # ارسال خروجی نهایی (به‌روزرسانی کپشن پیام موقتی که قبلا فرستاده شد)
        caption = (
            f"✅ پردازش موفقیت‌آمیز بود! (خروجی هوش مصنوعی)\n\n"
            f"اعتبار باقی‌مانده شما: {current_credit} عکس."
        )
        
        if uploaded_message:
            await context.bot.edit_message_caption(
                chat_id=uploaded_message.chat.id,
                message_id=uploaded_message.message_id,
                caption=caption,
                reply_markup=share_markup
            )
        
        # ریست وضعیت
        user_states[user_id] = {'state': 0}
        
        return

    if current_state in ['waiting_for_start_confirm', 'waiting_for_channel_check']:
        await update.message.reply_text("لطفا برای ادامه، روی دکمه‌های شیشه‌ای که زیر پیام‌های قبلی ارسال شد، کلیک کنید.")
        return

    await update.message.reply_text("لطفا عکس خود را بفرستید یا از دستور /start استفاده کنید.")


# =========================================================
# تابع اصلی و اجرای وب‌هوک
# =========================================================
def main():
    
    # برای محیط Render، ابتدا از متغیرهای محیطی می خوانیم.
    final_token = os.environ.get("TOKEN", TOKEN)

    if not WEBHOOK_URL:
        print("خطا: متغیر محیطی WEBHOOK_URL در Render تنظیم نشده است.")
        return

    application = (
        Application.builder()
        .token(final_token) 
        .build()
    )
    
    # هندلرهای دستورات
    application.add_handler(CommandHandler("start", start))
    
    # هندلرهای Callback Query (دکمه‌های شیشه‌ای)
    application.add_handler(CallbackQueryHandler(send_channel_check_message, pattern='^start_confirmation$'))
    application.add_handler(CallbackQueryHandler(check_membership_callback, pattern='^check_membership$'))
    
    application.add_handler(CallbackQueryHandler(share_to_channel_callback, pattern=r'^share_to_channel\|'))

    # هندلرهای مدیریت اعتبار
    application.add_handler(CallbackQueryHandler(handle_invite_friends, pattern='^credit_invite_friends$'))
    application.add_handler(CallbackQueryHandler(handle_purchase_plans, pattern='^credit_purchase_plans$'))
    application.add_handler(CallbackQueryHandler(handle_plan_selection, pattern=r'^buy_plan_(bronze|silver|gold)$'))

    # هندلرهای مدیا و متن
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo)) 
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_prompt)) 
    
    # --- تنظیمات وب‌هوک ---
    full_url = WEBHOOK_URL + WEBHOOK_PATH
    
    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=WEBHOOK_PATH,
        webhook_url=full_url
    )

    print(f"ربات با وب‌هوک روی URL زیر اجرا شد: {full_url}")

if __name__ == "__main__":
    main()
