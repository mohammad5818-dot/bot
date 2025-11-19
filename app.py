from telegram.ext import Updater, CommandHandler, MessageHandler
from telegram.ext import filters 
import os 
from queue import Queue # ۱. ایمپورت کلاس Queue

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
def start(update, context):
    update.message.reply_text("سلام! ربات بر روی سرور ابری روشن است و با وب‌هوک کار می‌کند. ✔️")

def echo(update, context):
    text = update.message.text
    update.message.reply_text(f"شما گفتید: {text}")

# =========================================================
# تابع اصلی و اجرای وب‌هوک
# =========================================================
def main():
    if not TOKEN or not WEBHOOK_URL:
        print("خطا: متغیرهای محیطی TOKEN یا WEBHOOK_URL در Render تنظیم نشده‌اند.")
        return

    # ۲. اضافه کردن آرگومان update_queue=Queue() برای رفع خطای قدیمی
    updater = Updater(TOKEN, update_queue=Queue()) 
    
    dp = updater.dispatcher

    # ثبت دستور /start
    dp.add_handler(CommandHandler("start", start))

    # ثبت هندلر پیام‌های متنی
    dp.add_handler(MessageHandler(filters.TEXT, echo))

    # --- تنظیمات وب‌هوک ---
    full_url = WEBHOOK_URL + WEBHOOK_PATH
    
    # 1. آدرس کامل وب‌هوک را به تلگرام اطلاع می‌دهد
    updater.bot.set_webhook(url=full_url)
    
    # 2. اجرای وب‌هوک
    updater.start_webhook(listen="0.0.0.0", 
                          port=PORT,
                          url_path=WEBHOOK_PATH) 

    print(f"ربات با وب‌هوک روی URL زیر اجرا شد: {full_url}")
    updater.idle() 

if name == "__main__":
    main()
