from telegram.ext import Updater, CommandHandler, MessageHandler
from telegram.ext import filters # ۱. ایمپورت صحیح فیلترها
import os 

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
        # این پیام فقط زمانی ظاهر می‌شود که متغیرها تنظیم نشده باشند
        print("خطا: متغیرهای محیطی TOKEN یا WEBHOOK_URL در Render تنظیم نشده‌اند.")
        return

    # ۲. حذف use_context=True و update_queue (زیرا نسخه جدید را اجباری می‌کنیم)
    updater = Updater(TOKEN) 
    dp = updater.dispatcher

    # ثبت دستور /start
    dp.add_handler(CommandHandler("start", start))

    # ثبت هندلر پیام‌های متنی (استفاده از filters.TEXT)
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

if __name__ == "__main__":
    main()
