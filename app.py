from telegram.ext import Application, CommandHandler, MessageHandler
from telegram.ext import filters 
from telegram import Update
from telegram.ext import ContextTypes # برای type hinting و Context
import os 

# =========================================================
# هشدار مهم: استفاده از دیتابیس (DB) الزامی است!
# این دیکشنری فقط برای تست است و با ری‌استارت شدن سرور، اطلاعات آن پاک می‌شود.
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

# دستور /start (شامل اعتباردهی اولیه و پیام خوش‌آمدگویی جدید)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    
    user = update.message.from_user
    user_id = user.id
    # برای پیام خوش‌آمدگویی از نام کوچک کاربر استفاده می‌کنیم
    first_name = user.first_name 

    # ۱. بررسی و تخصیص اعتبار اولیه
    if user_id not in user_credits:
        user_credits[user_id] = 3  # هدیه اولیه ۳ عکس
        print(f"کاربر جدید: {user_id} - اعتبار اولیه داده شد.")

    credit = user_credits[user_id]
    
    # ۲. ساختار پیام درخواستی شما
    welcome_message = (
        f"سلام {first_name} جان! \n"
        f"به ربات هُدهُد خوش اومدی! 🚀\n\n"
        f"💳 اعتبار شما: {credit} عکس با کیفیت\n"
        f"💡 دوستت رو معرفی کن و بابت هر معرفی ۳ عکس رایگان بگیر! 🎁\n\n"
        f"آماده‌ای عکست رو بسازی؟"
    )

    await update.message.reply_text(welcome_message)

# هندل پیام‌های معمولی (بدون تغییر)
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # برای این مثال، هر پیامی غیر از /start را تکرار می‌کند
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
        print("خطا: متغیرهای محیطی TOKEN یا WEBHOOK_URL در Render تنظیم نشده‌اند.")
        return

    # استفاده از Application.builder()
    application = (
        Application.builder()
        .token(TOKEN)
        .build()
    )
    
    # ثبت هندلرها
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), echo)) # پیام‌های متنی غیر از دستورات

    # --- تنظیمات وب‌هوک ---
    full_url = WEBHOOK_URL + WEBHOOK_PATH
    
    # اجرای وب‌هوک
    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=WEBHOOK_PATH,
        webhook_url=full_url
    )

    print(f"ربات با وب‌هوک روی URL زیر اجرا شد: {full_url}")

if __name__ == "__main__":
    main()
