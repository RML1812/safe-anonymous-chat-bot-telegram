import logging

from telegram.ext import (
    Application,
    ApplicationBuilder,
    ChatMemberHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

import db_connection
from bot_handler import *
from config import BOT_TOKEN
from LogHandler import LogHandler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        LogHandler(),
        logging.StreamHandler(),
    ],
)


async def turn_online(application: Application):
    user_ids = db_connection.get_all_user_ids()
    for user_id in user_ids:
        await application.bot.send_message(
            reply_markup=ReplyKeyboardMarkup(
                [["/start"]],
                resize_keyboard=True,
                one_time_keyboard=True,
                is_persistent=True,
            ),
            chat_id=user_id,
            text=responses.turn_online,
        )


async def turn_offline(application: Application):
    user_ids = db_connection.get_all_user_ids()
    for user_id in user_ids:
        await application.bot.send_message(
            reply_markup=ReplyKeyboardRemove(),
            chat_id=user_id,
            text=responses.turn_offline,
        )


if __name__ == "__main__":
    application = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .post_init(turn_online)
        .post_stop(turn_offline)
        .build()
    )
    # Create the database, if not already present
    db_connection.create_db()

    # Reset the status of all the previous existent users to IDLE, if the bot is restarted
    db_connection.reset_users_status()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CAPTCHA: [
                ChatMemberHandler(blocked_bot_handler),
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    verify_captcha,
                ),
            ],
            USER_ACTION: [
                ChatMemberHandler(blocked_bot_handler),
                MessageHandler(
                    (filters.TEXT | filters.ATTACHMENT) & ~filters.COMMAND,
                    handle_message,
                ),
                CommandHandler("stop", handle_stop),
                CommandHandler("chat", handle_chat),
                CommandHandler("next", exit_then_chat),
                CommandHandler("help", handle_help),
                CommandHandler("rules", handle_rules),
                CommandHandler("credit", handle_credit),
            ],
        },
        fallbacks=[MessageHandler(filters.TEXT, handle_not_in_chat)],
    )
    application.add_handler(conv_handler)
    application.run_polling()
