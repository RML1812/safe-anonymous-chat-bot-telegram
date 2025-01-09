import db_connection
from bot_handler import *
from config import BOT_TOKEN
from telegram.ext import filters, ApplicationBuilder, CommandHandler, MessageHandler, ChatMemberHandler


"""
List of commands
---> start - 🤖 memulai bot
---> chat - 💬 melakukan pencarian chat dengan orang lain
---> next - ⏭ melakukan skip terhadap chat yang berjalan dan mencari chat kembali dengan orang lain 
---> stop - 🔚 memberhentikan aktivitas /search ataupun chat yang sedang berjalan
---> credit - 🧪 melihat angka kesehatan perilaku pengguna berdasarkan hasil riwayat dari toxic detection
---> rules - 🚦 memperlihatkan peraturan yang ada saat menggunakan chat bot 
---> help - 🔍 menjelaskan cara penggunaan chat bot
"""


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
                MessageHandler((filters.TEXT | filters.ATTACHMENT) & ~ filters.COMMAND & ~filters.Regex("stop") & ~filters.Regex("chat")& ~filters.Regex("next") & ~filters.Regex("help") & ~filters.Regex("credit"), handle_message),
                CommandHandler("stop", handle_stop),
                CommandHandler("chat", handle_chat),
                CommandHandler("next", exit_then_chat),
                CommandHandler("help", handle_help),
                CommandHandler("rules", handle_rules),
                CommandHandler("credit", handle_credit)]
        },
        fallbacks=[MessageHandler(filters.TEXT, handle_not_in_chat)]
    )
    application.add_handler(conv_handler)
    application.run_polling()