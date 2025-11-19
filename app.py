موسوی, [20/11/25 01:19 ق.ظ]
from telegram.ext import Application, CommandHandler, MessageHandler
from telegram.ext import filters 
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup # ۱. اضافه شدن Update
from telegram.ext import ContextTypes # ۲. اضافه شدن ContextTypes
import os 

# =========================================================
# STATE MANAGER: برای ردیابی وضعیت کاربر 
# =========================================================
user_states = {} 
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

# تابع چک کردن اعتبار
def check_credit(user_id):
    credit = user_credits.get(user_id, 0)
    return credit > 0, credit

# دستور /start 
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = user.id
    first_name = user.first_name 

    if user_id not in user_credits:
        user_credits[user_id] = 3
    credit = user_credits[user_id]
    
    user_states[user_id] = {'state': 0} # ریست کردن وضعیت

    welcome_message = (
        f"سلام {first_name} جان! \n"
        f"به ربات هُدهُد خوش اومدی! 🚀\n\n"
        f"💳 اعتبار شما: {credit} عکس با کیفیت\n"
        f"💡 دوستت رو معرفی کن و بابت هر معرفی ۳ عکس رایگان بگیر! 🎁\n\n"
        f"برای شروع، عکس مورد نظر خود را بفرستید."
    )
    await update.message.reply_text(welcome_message)

# ۱. هندل کردن عکس‌های دریافتی
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    
    has_credit, current_credit = check_credit(user_id)
    if not has_credit:
        await update.message.reply_text("متأسفانه اعتبار شما به پایان رسیده است. لطفاً دوستان خود را معرفی کنید.")
        return

    file_id = update.message.photo[-1].file_id 
    
    user_states[user_id] = {
        'state': 1, # تغییر وضعیت به "منتظر پرامپت"
        'last_photo_id': file_id 
    }

    await update.message.reply_text(
        "عکس با موفقیت دریافت شد. حالا لطفاً تغییراتی که می‌خواهید روی این عکس اعمال شود (پرامپت) را در قالب یک پیام متنی برای من بنویسید."
    )

# ۲. هندل کردن متن پرامپت (وقتی کاربر منتظر پرامپت است)
async def handle_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_prompt = update.message.text
    
    state = user_states.get(user_id, {'state': 0})
    
    if state['state'] != 1:
        await update.message.reply_text("لطفاً ابتدا عکس خود را بفرستید تا بتوانم پرامپت را از شما بپرسم. /start")
        return

    last_photo_id = state['last_photo_id']
    
    # 🚨 اینجا باید منطق ارسال به AI و کسر اعتبار اتفاق بیفتد
    
    await update.message.reply_text(
        f"پرامپت شما: '{user_prompt}' دریافت شد.\n"
        f"عکس شما (ID: {last_photo_id}) در حال پردازش توسط هوش مصنوعی است. لطفا منتظر بمانید..."
    )

    # ج) ریست کردن وضعیت کاربر
    user_credits[user_id] -= 1 # کسر اعتبار
    has_credit, current_credit = check_credit(user_id)
    user_states[user_id] = {'state': 0}
    
    await update.message.reply_text(f"عملیات با موفقیت در صف قرار گرفت.\nاعتبار باقی‌مانده شما: {current_credit} عکس.")

# هندل پیام‌های متنی (که در هیچ وضعیت خاصی نیستند)
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    
    if user_states.get(user_id, {'state': 0})['state'] == 1:
        return 
        
    await update.message.reply_text("لطفا عکس خود را بفرستید یا از دستور /start استفاده کنید.")

موسوی, [20/11/25 01:19 ق.ظ]
# =========================================================
# تابع اصلی و اجرای وب‌هوک
# =========================================================
def main():
    if not TOKEN or not WEBHOOK_URL:
        print("خطا: متغیرهای محیطی TOKEN یا WEBHOOK_URL در Render تنظیم نشده‌اند.")
        return

    application = (
        Application.builder()
        .token(TOKEN)
        .build()
    )
    
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_prompt)) 
    application.add_handler(CommandHandler("start", start))
    
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
