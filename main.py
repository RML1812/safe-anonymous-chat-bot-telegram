import db_connection
from bot_handler import *
from config import BOT_TOKEN
from telegram.ext import (filters, ApplicationBuilder, CommandHandler, MessageHandler, ChatMemberHandler)

if __name__ == '__main__':
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    # Create the database, if not already present
    db_connection.create_db()

    # Reset the status of all the previous existent users to IDLE, if the bot is restarted
    db_connection.reset_users_status()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CAPTCHA: [MessageHandler(filters.TEXT & ~filters.COMMAND, verify_captcha)],
            USER_ACTION: [
                ChatMemberHandler(blocked_bot_handler),
                MessageHandler((filters.TEXT | filters.ATTACHMENT) & ~ filters.COMMAND & ~filters.Regex("stop") & ~filters.Regex("chat")& ~filters.Regex("next") & ~filters.Regex("stats") & ~filters.Regex("help") & ~filters.Regex("credit") & ~filters.Regex("stats"), handle_message),
                CommandHandler("stop", handle_stop),
                CommandHandler("chat", handle_chat),
                CommandHandler("next", exit_then_chat),
                CommandHandler("help", handle_help),
                CommandHandler("rules", handle_rules),
                CommandHandler("credit", handle_credit),
                CommandHandler("stats", handle_stats)]
        },
        fallbacks=[MessageHandler(filters.TEXT, handle_not_in_chat)]
    )
    application.add_handler(conv_handler)
    application.run_polling()