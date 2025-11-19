from telegram.ext import Application, CommandHandler, MessageHandler
from telegram.ext import filters, CallbackQueryHandler 
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup 
from telegram.ext import ContextTypes 
import os 
import json 

# =========================================================
# STATE MANAGER: برای ردیابی وضعیت کاربر 
# =========================================================
user_states = {} 
user_credits = {} 

# =========================================================
# بخش خواندن متغیرهای محیطی و ثابت‌ها
# =========================================================
TOKEN = "1234567890" 
AI_API_KEY = "123456" 
TARGET_CHANNEL_USERNAME = "@hodhod500_ax" 

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

# تابع نمایش منوی اصلی مدیریت اعتبار
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

# تابع مدیریت دعوت دوستان
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

# تابع نمایش پلن‌های خرید اعتبار
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

    await query.edit_message_text(
        text=message,
        reply_markup=purchase_markup
    )


# تابع مدیریت کلیک روی پلن‌های خرید (ارسال لینک پرداخت فرضی)
async def handle_plan_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    plan_key = query.data.split('_')[-1] 
    
    payment_link = "https://example.com/payment/" + plan_key 
    
    message = (
        f"✅ پلن **{plan_key.upper()}** انتخاب شد.\n\n"
        f"لطفاً جهت تکمیل خرید و شارژ فوری اعتبار، روی دکمه پرداخت زیر کلیک کنید:\n"
        f"پس از پرداخت، اعتبار شما به‌طور خودکار شارژ خواهد شد."
    )
    
    payment_keyboard = [
        [InlineKeyboardButton("💳 شروع پرداخت", url=payment_link)]
    ]
    payment_markup = InlineKeyboardMarkup(payment_keyboard)

    await query.edit_message_text(
        text=message,
        reply_markup=payment_markup
    )


# دستور /start 
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = user.id
    first_name = user.first_name 

    if user_id not in user_credits:
        user_credits[user_id] = 3
    credit = user_credits[user_id]
    
    user_states[user_id] = {'state': 'waiting_for_start_confirm'} 
    
    keyboard = [
        [InlineKeyboardButton("شروع کار / بله", callback_data='start_confirmation')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    welcome_message = (
        f"سلام {first_name} جان! \n"
        f"به ربات هُدهُد خوش اومدی! 🚀\n\n"
        f"💳 اعتبار شما: {credit} عکس با کیفیت\n" # به‌روزرسانی متن
        f"💡 دوستت رو معرفی کن و بابت هر معرفی ۳ عکس رایگان بگیر! 🎁\n\n"
        f"برای شروع و دسترسی به امکانات ربات، روی دکمه «شروع کار / بله» کلیک کنید."
    )
    await update.message.reply_text(welcome_message, reply_markup=reply_markup)


# تابع: ارسال پیام عضویت در کانال‌ها هنگام کلیک روی دکمه "بله"
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


# تابع: هندل کردن کلیک روی دکمه "عضو شدم و ادامه می‌دهم"
async def check_membership_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("در حال بررسی... (فرض بر موفقیت است)")
    user_id = query.from_user.id

    user_states[user_id] = {'state': 0}
    
    start_work_message = (
        "عضویت شما بررسی و تأیید شد. شما می‌توانید اکنون کار خود را شروع کنید! 🎉\n\n"
        "لطفاً **عکس مورد نظر خود** که می‌خواهید تغییرات روی آن اعمال شود را ارسال کنید." # به‌روزرسانی متن
    )
    
    try:
        await query.edit_message_text(
            text=start_work_message,
            reply_markup=None 
        )
    except Exception:
        await context.bot.send_message(
            chat_id=user_id,
            text=start_work_message
        )


# ۱. هندل کردن عکس‌های دریافتی (handle_photo)
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

# ⭐ تابع handle_video حذف شد.


# ۲. هندل کردن متن پرامپت (handle_prompt) - (به‌روزرسانی‌شده)
async def handle_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_prompt = update.message.text
    
    state = user_states.get(user_id, {'state': 0})
    current_state = state.get('state', 0)

    # اگر کاربر در وضعیت انتظار پرامپت باشد
    if current_state == 1:
        
        # ⭐ فقط برای عکس (photo)
        media_id = state.get('last_photo_id')
        media_type = 'photo'
        media_type_fa = "عکس"
        
        
        await update.message.reply_text(
            f"پرامپت شما: '{user_prompt}' دریافت شد.\n"
            f"{media_type_fa} شما (ID: {media_id}) در حال پردازش توسط هوش مصنوعی است. لطفا منتظر بمانید..."
        )

        # 📌📌📌 محل استفاده از API Key هوش مصنوعی (AI) 📌📌📌
        
        # --- فرض می‌کنیم که در اینجا پردازش AI انجام شده و نتیجه آماده ارسال است ---
        ai_output_media_id = media_id 
        
        # 📌📌📌 پایان محل استفاده از API Key هوش مصنوعی 📌📌📌
        
        
        # کسر اعتبار
        user_credits[user_id] -= 1 
        has_credit, current_credit = check_credit(user_id) 
        
        # ذخیره اطلاعات در user_data برای استفاده در Callback Query 
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
        
        # ارسال خروجی (شبیه‌سازی تحویل با استفاده از مدیا آیدی اصلی)
        caption = (
            f"✅ پردازش موفقیت‌آمیز بود! (خروجی هوش مصنوعی)\n\n"
            f"اعتبار باقی‌مانده شما: {current_credit} عکس."
        )
        
        try:
            # ارسال مدیا (خروجی AI) با دکمه شیشه‌ای
            await update.message.reply_photo(photo=ai_output_media_id, caption=caption, reply_markup=share_markup)
        except Exception:
            await update.message.reply_text(caption, reply_markup=share_markup)


        # ریست وضعیت
        user_states[user_id] = {'state': 0}
        
        return

    # اگر کاربر در وضعیت انتظار تأیید شروع کار یا کانال باشد
    if current_state in ['waiting_for_start_confirm', 'waiting_for_channel_check']:
        await update.message.reply_text("لطفا برای ادامه، روی دکمه‌های شیشه‌ای که زیر پیام‌های قبلی ارسال شد، کلیک کنید.")
        return

    # حالت پیش‌فرض (Idle)
    await update.message.reply_text("لطفا عکس خود را بفرستید یا از دستور /start استفاده کنید.")


# تابع هندل کردن کلیک روی دکمه ارسال به کانال (به‌روزرسانی‌شده)
async def share_to_channel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("در حال ارسال به کانال...") 

    # 1. بازیابی کلید و اطلاعات
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
    
    # 2. آماده‌سازی کپشن
    caption = f"توضیحات کاربر: {user_prompt}"

    # 3. ارسال مدیا به کانال مقصد
    try:
        # ⭐ فقط برای عکس (photo)
        await context.bot.send_photo(
            chat_id=TARGET_CHANNEL_USERNAME,
            photo=media_id,
            caption=caption
        )
        
        # 4. به‌روزرسانی پیام کاربر
        await query.edit_message_reply_markup(
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ به کانال نمونه‌ها ارسال شد", callback_data='dummy_sent')]
            ])
        )
        
    except Exception as e:
        error_message = f"❌ خطایی در ارسال به کانال رخ داد."
        await context.bot.send_message(query.from_user.id, error_message)


# =========================================================
# تابع اصلی و اجرای وب‌هوک 
# =========================================================
def main():
    if not WEBHOOK_URL:
        print("خطا: متغیر محیطی WEBHOOK_URL در Render تنظیم نشده است.")
        return

    application = (
        Application.builder()
        .token(TOKEN) 
        .build()
    )
    
    # هندلرهای دستورات و دکمه‌های شیشه‌ای
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(send_channel_check_message, pattern='^start_confirmation$'))
    application.add_handler(CallbackQueryHandler(check_membership_callback, pattern='^check_membership$'))
    application.add_handler(CallbackQueryHandler(share_to_channel_callback, pattern='^share_to_channel\|'))

    # هندلرهای مدیریت اعتبار
    application.add_handler(CallbackQueryHandler(handle_invite_friends, pattern='^credit_invite_friends$'))
    application.add_handler(CallbackQueryHandler(handle_purchase_plans, pattern='^credit_purchase_plans$'))
    application.add_handler(CallbackQueryHandler(handle_plan_selection, pattern='^buy_plan_(bronze|silver|gold)$'))

    # هندلرهای مدیا و متن
    # ⭐ حذف هندلر filters.VIDEO
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
    pass # جایگزین main()
