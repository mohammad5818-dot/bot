# هندل پیام‌های متنی (که در هیچ وضعیت خاصی نیستند)
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # این هندلر فقط پیام‌های متنی را که پرامپت نیستند مدیریت می‌کند
    user_id = update.message.from_user.id
    
    if user_states.get(user_id, {'state': 0})['state'] == 1:
        # اگر کاربر در وضعیت منتظر پرامپت بود، باید توسط handle_prompt مدیریت شود.
        # این برای جلوگیری از تداخل است.
        return 

    await update.message.reply_text("لطفا عکس خود را بفرستید یا از دستور /start استفاده کنید.")


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
    
    # ۱. هندلر عکس: زمانی که کاربر عکس می‌فرستد
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    # ۲. هندلر متن: باید قبل از هندلر echo ثبت شود تا پرامپت‌ها را بگیرد
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_prompt)) 
    
    # ۳. هندلر دستورات
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
