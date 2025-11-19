from telegram.ext import Application, CommandHandler, MessageHandler
from telegram.ext import filters 
from telegram import Update
from telegram.ext import ContextTypes # برای type hinting
import os 
from http.server import HTTPServer # برای اجرای وب‌هوک در نسخه‌های جدید

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

# دستور /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # توجه: در ساختار Application توابع باید async باشند
    await update.message.reply_text("سلام! ربات بر روی سرور ابری روشن است و با وب‌هوک کار می‌کند. ✔️")

# هندل پیام‌های معمولی
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    await update.message.reply_text(f"شما گفتید: {text}")


# =========================================================
# تابع اصلی و اجرای وب‌هوک
# =========================================================
def main():
    if not TOKEN or not WEBHOOK_URL:
        print("خطا: متغیرهای محیطی TOKEN یا WEBHOOK_URL در Render تنظیم نشده‌اند.")
        return

    # ۱. استفاده از کلاس Application.builder() به جای Updater
    application = (
        Application.builder()
        .token(TOKEN)
        .build()
    )
    
    # ۲. ثبت هندلرها
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT, echo))

    # --- تنظیمات وب‌هوک ---
    full_url = WEBHOOK_URL + WEBHOOK_PATH
    
    # تنظیمات وب‌هوک (تنظیم پورت و مسیر)
    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=WEBHOOK_PATH,
        webhook_url=full_url # ارسال URL کامل
    )

    print(f"ربات با وب‌هوک روی URL زیر اجرا شد: {full_url}")
    # idle دیگر در این ساختار استفاده نمی‌شود

if __name__ == "__main__":
    main()
