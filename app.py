import os 
import io 
import logging

# تنظیمات لاگ (بهتر است برای محیط‌های Production استفاده شود)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# =========================================================
# بخش ۱: عیب‌یابی ایمپورت‌ها
# =========================================================
try:
    from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
    from telegram.ext import ContextTypes 
    
    from google import genai 
    from google.genai.errors import APIError 
    
    logger.info("✅ تمامی کتابخانه‌ها با موفقیت وارد شدند.")

except ImportError as e:
    logger.error(f"❌ خطای حیاتی ImportError: {e}. مطمئن شوید که requirements.txt شامل 'python-telegram-bot' و 'google-genai' است.")
    exit(1)


# =========================================================
# بخش ۲: تنظیمات و ثابت‌ها (حتماً این مقادیر را در Render تنظیم کنید)
# =========================================================
# ⚠️ توکن و کلیدهای API واقعی خود را اینجا یا در متغیرهای محیطی قرار دهید.
# این مقادیر صرفاً به عنوان مقدار پیش‌فرض استفاده می‌شوند.
FALLBACK_TOKEN = "8314422409:AAHVi3ecnPCXRdkj7JjRnxPDHeffOaPBt3A" # توکن واقعی را قرار دهید
FALLBACK_GEMINI_KEY = "AIzaSyDtkVNu7esH4OfQWmK65leFtf4DU8eD1oY" # کلید واقعی را قرار دهید

TOKEN = os.environ.get("TOKEN", FALLBACK_TOKEN)  
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", FALLBACK_GEMINI_KEY) 
TARGET_CHANNEL_USERNAME = "@hodhod500_ax" 

# متغیرهای حیاتی Render
PORT = int(os.environ.get("PORT", 8443)) 
WEBHOOK_URL = os.environ.get("WEBHOOK_URL") 
WEBHOOK_PATH = "/" + TOKEN # استفاده از توکن به عنوان مسیر وب‌هوک

# حالت‌های کاربر: 0 = بیکار/آماده، 1 = منتظر پرامپت
user_states = {} 
user_credits = {} 

# =========================================================
# بخش ۳: توابع مدیریتی و اتصال به Gemini
# =========================================================

# اتصال به Gemini - مقداردهی اولیه فقط یک بار
if GEMINI_API_KEY and GEMINI_API_KEY != FALLBACK_GEMINI_KEY:
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        logger.info("✅ اتصال به Gemini با موفقیت برقرار شد.")
    except Exception as e:
        logger.error(f"❌ خطا در ایجاد کلاینت Gemini: {e}")
        client = None
else:
    logger.warning("⚠️ GEMINI_API_KEY تنظیم نشده است. فراخوانی‌های AI کار نخواهد کرد.")
    client = None

def check_credit(user_id):
    """بررسی و مقداردهی اولیه اعتبار کاربر."""
    if user_id not in user_credits:
        # اعتبار پیش‌فرض برای شروع کار
        user_credits[user_id] = 5 
    
    credit = user_credits.get(user_id, 0)
    return credit > 0, credit

async def send_credit_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ارسال منوی اعتبار برای کاربران با اعتبار صفر."""
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
    
def deduct_credit(user_id):
    """کسر یک واحد اعتبار از کاربر"""
    if user_id in user_credits and user_credits[user_id] > 0:
        user_credits[user_id] -= 1
        return True
    return False


# =========================================================
# بخش ۴: توابع هندلر فرمان‌ها و پیام‌ها
# =========================================================

async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر فرمان /start. عضویت را بررسی کرده و منوی شروع را نمایش می‌دهد."""
    await send_channel_check_message(update, context)


async def handle_image_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر دریافت تصویر، آپلود در Gemini و انتظار برای پرامپت."""
    user_id = update.effective_user.id
    
    if client is None:
        await update.message.reply_text("❌ سرویس Gemini به دلیل مشکل در کلید API غیرفعال است.")
        return

    can_work, credit_count = check_credit(user_id)
    if not can_work:
        await send_credit_menu(update, context)
        return

    # وضعیت 0 = آماده دریافت عکس است
    if user_states.get(user_id, {}).get('state') != 0:
        await update.message.reply_text("لطفاً منتظر بمانید یا کار قبلی را تکمیل کنید. یا اگر منتظر پرامپت هستید، توضیحات خود را بنویسید.")
        return

    # ۱. دریافت بزرگترین نسخه تصویر
    photo_file = update.message.photo[-1]
    
    status_message = await update.message.reply_text("⏳ در حال دانلود و آپلود تصویر در سرویس Gemini...")
    
    try:
        # ۲. دانلود تصویر به حافظه و آپلود
        file_info = await context.bot.get_file(photo_file.file_id)
        photo_data = io.BytesIO()
        
        # ✅ رفع خطای AttributeError: 'File' object has no attribute 'download_to_get_content'
        await file_info.download_to_handle(photo_data)
        
        # برای کمک به تشخیص MIME type توسط SDK
        photo_data.name = f"{photo_file.file_unique_id}.jpeg"
        
        # ⚠️ رفع خطای: Files.upload() got an unexpected keyword argument 'mime_type'
        gemini_file = client.files.upload(file=photo_data) 
        
        # ۳. ذخیره وضعیت و فایل Gemini
        user_states[user_id] = {
            'state': 1, # منتظر پرامپت
            'gemini_file_id': gemini_file.name,
            'credit_before': credit_count 
        }

        await status_message.edit_text(
            f"✅ تصویر با موفقیت آپلود شد. اعتبار شما: **{credit_count}** عکس\n\n"
            "💬 **لطفاً توضیحات یا پرامپت خود را برای تغییر تصویر ارسال کنید.**"
        )
        
    except APIError as e:
        logger.error(f"خطای API در آپلود Gemini: {e}")
        await status_message.edit_text(f"❌ خطای API: آپلود تصویر ناموفق بود. {e}")
    except Exception as e:
        logger.error(f"خطای نامشخص در آپلود: {e}")
        await status_message.edit_text(f"❌ خطای نامشخص در آپلود: {e}")


async def handle_prompt_and_generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر دریافت پرامپت و اجرای فرایند تولید تصویر توسط Gemini."""
    user_id = update.effective_user.id
    user_state = user_states.get(user_id, {})
    
    if user_state.get('state') != 1:
        await update.message.reply_text("لطفاً ابتدا عکس خود را ارسال کنید تا منتظر پرامپت بمانم.")
        return
        
    prompt = update.message.text
    gemini_file_id = user_state.get('gemini_file_id')
    
    if not gemini_file_id:
        await update.message.reply_text("❌ خطای داخلی: فایل تصویری آپلود شده یافت نشد. لطفاً دوباره تلاش کنید.")
        user_states[user_id] = {'state': 0}
        return

    # ۱. کسر اعتبار
    if not deduct_credit(user_id):
        await update.message.reply_text("❌ خطای اعتبار: اعتبار شما کافی نیست.")
        await client.files.delete(name=gemini_file_id) # پاکسازی فایل
        user_states[user_id] = {'state': 0}
        return
    
    status_message = await update.message.reply_text("⏳ **در حال تولید تصویر...** این فرآیند ممکن است کمی طول بکشد.")
    
    try:
        # ۲. فراخوانی مدل Vision/Multimodal
        model = 'gemini-2.5-flash' 
        uploaded_file = client.files.get(name=gemini_file_id)
        
        # ساخت یک پرامپت سیستم برای بهتر شدن عملکرد ویرایش
        system_instruction = "You are an expert image editor. Based on the user's prompt, edit the provided image to fulfill the request. Describe the changes you made concisely."

        response = client.models.generate_content(
            model=model,
            contents=[uploaded_file, prompt],
            config=genai.types.GenerateContentConfig(
                system_instruction=system_instruction
            )
        )

        # ۳. ارسال پاسخ (اینجا باید منطق تولید تصویر/ویرایش واقعی را بر اساس مدل خود پیاده کنید)
        
        # اگر خروجی فقط متن است:
        current_credit = user_credits.get(user_id)
        await update.message.reply_text(
            f"✅ **نتیجه (توصیه Gemini):**\n{response.text}\n\n"
            f"اعتبار باقیمانده شما: **{current_credit}** عکس."
        )
        
    except APIError as e:
        logger.error(f"خطای API در پردازش Gemini: {e}")
        await status_message.edit_text(f"❌ خطای API در پردازش: {e}")
    except Exception as e:
        logger.error(f"خطای نامشخص در تولید: {e}")
        await status_message.edit_text(f"❌ خطای نامشخص در تولید: {e}")
        
    finally:
        # ۴. پاکسازی فایل آپلود شده
        try:
            client.files.delete(name=gemini_file_id)
            logger.info(f"فایل {gemini_file_id} در Gemini پاک شد.")
        except Exception:
            logger.warning(f"هشدار: فایل {gemini_file_id} در Gemini پاک نشد.")
            
        # ۵. بازگشت به حالت بیکار
        user_states[user_id] = {'state': 0}


# =========================================================
# بخش ۵: توابع هندلر Callback Query (دکمه‌های شیشه‌ای)
# =========================================================

async def send_channel_check_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ارسال پیام جهت بررسی عضویت در کانال."""
    query = update.callback_query
    if query:
        await query.answer() 
        user_id = query.from_user.id
        source_message = query.message
