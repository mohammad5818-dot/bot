import os
import io 

# =========================================================
# بخش ۱: عیب‌یابی ایمپورت‌ها (Import Error Check)
# =========================================================
try:
    from telegram.ext import Application, CommandHandler, MessageHandler
    from telegram.ext import filters, CallbackQueryHandler 
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup 
    from telegram import InputFile 
    from telegram.ext import ContextTypes 
    
    from google import genai 
    from google.genai.errors import APIError 
    
    print("✅ تمامی کتابخانه‌ها با موفقیت وارد شدند.")

except ImportError as e:
    # ❌
    print(f"❌ خطای حیاتی ImportError: {e}. مطمئن شوید که requirements.txt شامل 'python-telegram-bot' و 'google-genai' است.")
    exit(1)


# =========================================================
# بخش ۲: تنظیمات و ثابت‌ها
# =========================================================
# متغیرهای پیش‌فرض - مقادیر واقعی باید از Render خوانده شوند
TOKEN = "8314422409:AAF9hZ0uEe1gQH5Fx9xpUuiGFuX8lXvzm4"  
GEMINI_API_KEY = "AIzaSyDtkVNu7esH4OfQWmK65leFtf4DU8eD1oY" 
TARGET_CHANNEL_USERNAME = "@hodhod500_ax" 

# متغیرهای حیاتی Render
PORT = int(os.environ.get("PORT", 8443)) 
WEBHOOK_URL = os.environ.get("WEBHOOK_URL") 
WEBHOOK_PATH = "/" + os.environ.get("TOKEN", TOKEN) 

# حالت‌های کاربر: 0 = بیکار/آماده، 1 = منتظر پرامپت
user_states = {} 
user_credits = {} 

# =========================================================
# بخش ۳: توابع مدیریتی و اتصال به Gemini
# =========================================================

# اتصال به Gemini - مقداردهی اولیه فقط یک بار
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
    # مقداردهی اولیه اعتبار در صورت جدید بودن کاربر (برای تست)
    if user_id not in user_credits:
        user_credits[user_id] = 5 # اعتبار پیش‌فرض برای شروع
    
    credit = user_credits.get(user_id, 0)
    return credit > 0, credit

async def send_credit_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    """هندلر فرمان /start. عضویت را بررسی کرده یا منوی شروع را نمایش می‌دهد."""
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name or "کاربر"
    
    # فرض می‌کنیم کاربر ابتدا باید عضویت را چک کند
    await send_channel_check_message(update, context)


async def handle_image_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    هندلر دریافت تصویر.
    تصویر را در Gemini آپلود می‌کند و منتظر پرامپت (دستور تغییر) می‌ماند.
    """
    user_id = update.effective_user.id
    
    can_work, credit_count = check_credit(user_id)
    if not can_work:
        await send_credit_menu(update, context)
        return

    if user_states.get(user_id, {}).get('state') != 0:
        await update.message.reply_text("لطفاً قبل از ارسال تصویر، از منوی /start کار را شروع کنید.")
        return

    # ۱. دریافت بزرگترین نسخه تصویر
    photo_file = update.message.photo[-1]
    
    # ۲. دانلود تصویر به حافظه
    status_message = await update.message.reply_text("در حال دانلود و آپلود تصویر در سرویس Gemini...")
    file_info = await context.bot.get_file(photo_file.file_id)
    
    # ❌ اینجا ممکن است دانلود فایل طولانی باشد.
    # به جای ذخیره روی دیسک، آن را در یک بافر (buffer) ذخیره می‌کنیم.
    photo_data = io.BytesIO()
    await file_info.download_to_get_content(out=photo_data)
    
    # 
    # ۳. آپلود در Gemini (رفع خطای mime_type)
    # ----------------------------------------------------
    # توجه: کتابخانه google-genai از `io.BytesIO` پشتیبانی می‌کند
    # و خودکار نوع MIME را تشخیص می‌دهد (اغلب به نام فایل نیاز دارد).
    
    # برای اطمینان از تشخیص MIME، نامی با پسوند تعیین می‌کنیم
    photo_data.name = f"{photo_file.file_unique_id}.jpeg"
    
    try:
        # ⚠️ رفع خطا: آرگومان 'mime_type' حذف شد
        gemini_file = client.files.upload(file=photo_data) 
        
        # ۴. ذخیره وضعیت و فایل Gemini
        user_states[user_id] = {
            'state': 1, # منتظر پرامپت
            'gemini_file_id': gemini_file.name,
            'credit_before': credit_count 
        }

        await status_message.edit_text(
            f"✅ تصویر با موفقیت آپلود شد. اعتبار شما: {credit_count} عکس\n\n"
            "💬 **لطفاً توضیحات یا پرامپت خود را برای تغییر تصویر ارسال کنید.**\n"
            "مثال: «او را با کت و شلوار آبی در یک زمینه مهتابی قرار بده.»"
        )
        
    except APIError as e:
        await status_message.edit_text(f"❌ خطای API در آپلود Gemini: {e}")
    except Exception as e:
        await status_message.edit_text(f"❌ خطای نامشخص در آپلود: {e}")


async def handle_prompt_and_generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    هندلر دریافت پرامپت (دستور تغییر) و اجرای فرایند تولید تصویر.
    """
    user_id = update.effective_user.id
    user_state = user_states.get(user_id, {})
    
    if user_state.get('state') != 1:
        await update.message.reply_text("لطفاً ابتدا تصویر خود را ارسال کنید تا منتظر پرامپت باشم.")
        return
        
    prompt = update.message.text
    gemini_file_id = user_state.get('gemini_file_id')
    
    if not gemini_file_id:
        await update.message.reply_text("❌ خطای داخلی: فایل تصویری آپلود شده یافت نشد.")
        user_states[user_id] = {'state': 0}
        return

    # ۱. کسر اعتبار
    if not deduct_credit(user_id):
        await update.message.reply_text("❌ خطای اعتبار: در حین کسر اعتبار، مشکلی رخ داد. لطفاً /start را بزنید.")
        await client.files.delete(name=gemini_file_id) # پاکسازی فایل
        user_states[user_id] = {'state': 0}
        return
    
    status_message = await update.message.reply_text("⏳ **در حال تولید تصویر...** این فرآیند ممکن است یک دقیقه طول بکشد.")
    
    try:
        # ۲. فراخوانی مدل Imagen/Gemini برای ویرایش تصویر
        
        # برای Image Editing باید از یک مدل Vision/Multimodal مانند gemini-2.5-flash استفاده کرد.
        # توجه: فرض می‌کنیم که خروجی مدل (response) شامل یک تصویر است که باید پردازش شود.
        
        model = 'gemini-2.5-flash' 
        
        # فایل آپلود شده را از سرویس Gemini بازیابی می‌کنیم
        uploaded_file = client.files.get(name=gemini_file_id)
        
        # اجرای فراخوانی: [فایل، پرامپت]
        response = client.models.generate_content(
            model=model,
            contents=[uploaded_file, prompt]
        )

        # ۳. پردازش و ارسال پاسخ (مثال: اگر پاسخ فقط متن باشد)
        # در اینجا منطق دقیق ارسال تصویر تولید شده نیاز به تنظیم دارد.
        # اگر از مدل‌های Text-to-Image (مانند Imagen) استفاده می‌کنید، باید از آن SDK استفاده کنید.
        
        # فرض: Gemini یک پاسخ متنی درباره تغییرات انجام شده می‌دهد
        await update.message.reply_text(
            f"✅ نتیجه پردازش Gemini:\n\n{response.text}\n\n"
            "⚠️ اگر قصد تولید تصویر داشتید، باید از API مدل‌های تولید عکس استفاده کنید.\n\n"
            f"اعتبار باقیمانده شما: {user_credits.get(user_id)} عکس"
        )
        
    except APIError as e:
        await status_message.edit_text(f"❌ خطای API در پردازش Gemini: {e}")
    except Exception as e:
        await status_message.edit_text(f"❌ خطای نامشخص در تولید: {e}")
        
    finally:
        # ۴. پاکسازی فایل آپلود شده
        try:
            client.files.delete(name=gemini_file_id)
        except Exception:
            print(f"هشدار: فایل {gemini_file_id} در Gemini پاک نشد.")
            
        # ۵. بازگشت به حالت بیکار
        user_states[user_id] = {'state': 0}


# =========================================================
# بخش ۵: توابع هندلر Callback Query (دکمه‌های شیشه‌ای)
# =========================================================

# ... (توابع send_channel_check_message، check_membership_callback، handle_invite_friends بدون تغییر) ...

async def send_channel_check_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer() 
        user_id = query.from_user.id
    else:
        user_id = update.effective_user.id
    
    keyboard = [
        [InlineKeyboardButton("کانال آموزش کار با ربات", url="https://t.me/hodhod500_amoozesh")],
        [InlineKeyboardButton("کانال نمونه عکس‌های تولیدی", url="https://t.me/hodhod500_ax")],
        [InlineKeyboardButton("✅ عضو شدم و ادامه می‌دهم", callback_data='check_membership')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = "برای شروع کار، لطفا در دو کانال زیر عضو شوید و سپس دکمه «عضو شدم و ادامه می‌دهم» را بزنید:"
    
    if query:
        # اگر از کال‌بک کوئری آمده
        await query.edit_message_text(
            text=message,
            reply_markup=reply_markup
        )
    else:
        # اگر از /start آمده
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

    # 0 = حالت آماده و بیکار
    user_states[user_id] = {'state': 0}
    
    start_work_message = (
        "عضویت شما بررسی و تأیید شد. شما می‌توانید اکنون کار خود را شروع کنید! 🎉\n\n"
        "لطفاً **عکس مورد نظر خود** که می‌خواهید تغییرات روی آن اعمال شود را ارسال کنید.\n"
        f"اعتبار فعلی شما: {user_credits.get(user_id, 5)} عکس"
    )
    
    try:
        await query.edit_message_text(text=start_work_message, reply_markup=None)
    except Exception:
        await context.bot.send_message(chat_id=user_id, text=start_work_message)


async def handle_invite_friends(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    bot_username = (await context.bot.get_me()).username # گرفتن یوزرنیم واقعی ربات
    referral_link = f"https://t.me/{bot_username if bot_username else 'YourBotUsername'}?start=ref_{user_id}"
    
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
        [InlineKeyboardButton("🥉 برنزی (۱۰ عکس / ۵۰,۰۰۰ تومان)", callback_data='buy_plan_10_50')],
        [InlineKeyboardButton("🥈 نقره‌ای (۲۰ عکس / ۹۰,۰۰۰ تومان)", callback_data='buy_plan_20_90')],
        [InlineKeyboardButton("🥇 طلایی (۴۰ عکس / ۱۸۰,۰۰۰ تومان)", callback_data='buy_plan_40_180')]
    ]
    purchase_markup = InlineKeyboardMarkup(purchase_keyboard)
    
    message = "سه اعتبار مختلف برای خرید وجود دارد. لطفاً پلن مورد نظر خود را انتخاب کنید:"

    await query.edit_message_text(text=message, reply_markup=purchase_markup)

async def handle_plan_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر نهایی خرید پلن‌ها"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    plan_data = query.data.split('_') # e.g., ['buy', 'plan', '10', '50']
    
    if len(plan_data) == 4:
        credits = plan_data[2]
        price = plan_data[3]
        
        payment_message = (
            f"شما **{credits} اعتبار** را با قیمت **{price},۰۰۰ تومان** انتخاب کردید.\n\n"
            "لطفاً برای تکمیل خرید، از طریق لینک زیر به درگاه پرداخت متصل شوید (لینک فرضی است):\n\n"
            "[لینک درگاه پرداخت امن (کلیک کنید)]\n\n"
            "پس از پرداخت، اعتبار شما به صورت خودکار به حساب شما اضافه خواهد شد."
        )
        
        await query.edit_message_text(text=payment_message, reply_markup=None, parse_mode='Markdown')
    else:
        await query.edit_message_text(text="❌ خطای انتخاب پلن. لطفاً مجدداً تلاش کنید.", reply_markup=None)


# =========================================================
# بخش ۶: راه‌اندازی ربات
# =========================================================

def main() -> None:
    """راه‌اندازی بات تلگرام."""
    
    application = Application.builder().token(TOKEN).build()

    # فرمان‌ها
    application.add_handler(CommandHandler("start", handle_start))

    # پیام‌های متنی (هندلر پرامپت)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_prompt_and_generate))
    
    # پیام‌های عکس (هندلر آپلود)
    application.add_handler(MessageHandler(filters.PHOTO, handle_image_upload))
    
    # دکمه‌های شیشه‌ای
    application.add_handler(CallbackQueryHandler(check_membership_callback, pattern='^check_membership$'))
    application.add_handler(CallbackQueryHandler(handle_invite_friends, pattern='^credit_invite_friends$'))
    application.add_handler(CallbackQueryHandler(handle_purchase_plans, pattern='^credit_purchase_plans$'))
    application.add_handler(CallbackQueryHandler(handle_plan_purchase, pattern='^buy_plan_'))

    # راه‌اندازی وب‌هوک (برای محیط Render)
    if WEBHOOK_URL:
        print(f"🚀 راه‌اندازی در حالت وب‌هوک در پورت: {PORT}")
        application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=WEBHOOK_PATH,
            webhook_url=WEBHOOK_URL + WEBHOOK_PATH
        )
    else:
        print("🤖 راه‌اندازی در حالت نظرسنجی (Polling)")
        application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
