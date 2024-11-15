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
            USER_ACTION: [
                ChatMemberHandler(blocked_bot_handler),
                MessageHandler((filters.TEXT | filters.ATTACHMENT) & ~ filters.COMMAND & ~filters.Regex("exit") & ~filters.Regex("chat")& ~filters.Regex("newchat") & ~filters.Regex("stats"), handle_message),
                CommandHandler("exit", handle_exit_chat),
                CommandHandler("chat", handle_chat),
                CommandHandler("newchat", exit_then_chat),
                CommandHandler("stats", handle_stats)]
        },
        fallbacks=[MessageHandler(filters.TEXT, handle_not_in_chat)]
    )
    application.add_handler(conv_handler)
    application.run_polling()