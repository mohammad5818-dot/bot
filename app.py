from telegram.ext import Updater, CommandHandler, MessageHandler
from telegram.ext import filters # ایمپورت صحیح برای فیلترها
import os 

# =========================================================
# بخش خواندن متغیرهای محیطی از Render
# =========================================================
TOKEN = os.environ.get("TOKEN")
# Render پورت را به عنوان یک متغیر محیطی تنظیم می‌کند؛ اگر تنظیم نشد، از 8443 استفاده می‌کنیم.
PORT = int(os.environ.get("PORT", 8443)) 
WEBHOOK_URL = os.environ.get("WEBHOOK_URL") 
# PATH امن برای وب‌هوک را از توکن می‌گیریم
WEBHOOK_PATH = "/" + TOKEN 


# =========================================================
# توابع هندلر (Handler Functions)
# =========================================================

# دستور /start
def start(update, context):
    # 'update' شامل اطلاعات مربوط به پیام دریافتی است
    update.message.reply_text("سلام! ربات بر روی سرور ابری روشن است و با وب‌هوک کار می‌کند. ✔️")

# هندل پیام‌های معمولی
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

    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    # ثبت دستور /start
    dp.add_handler(CommandHandler("start", start))

    # ثبت هندلر پیام‌های متنی (استفاده از filters.TEXT به جای Filters.text)
    dp.add_handler(MessageHandler(filters.TEXT, echo))

    # --- تنظیمات وب‌هوک برای محیط ابری ---
    
    # 1. آدرس کامل وب‌هوک را به تلگرام اطلاع می‌دهد
    full_url = WEBHOOK_URL + WEBHOOK_PATH
    updater.bot.set_webhook(url=full_url)
    
    # 2. ربات را به صورت سرور اجرا می‌کند تا روی پورت و مسیر مشخص گوش دهد
    updater.start_webhook(listen="0.0.0.0", # گوش دادن از هر آدرسی
                          port=PORT,
                          url_path=WEBHOOK_PATH) 

    print(f"ربات با وب‌هوک روی URL زیر اجرا شد: {full_url}")
    updater.idle() # در حالت انتظار برای پیام‌های وب‌هوک باقی می‌ماند

if __name__ == "__main__":
    main()
