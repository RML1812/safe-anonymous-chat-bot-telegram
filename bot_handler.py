import random
import string
from io import BytesIO

from captcha.image import ImageCaptcha
from telegram import ChatMember, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update, Message
from telegram.ext import ContextTypes, ConversationHandler

import db_connection
import responses
from toxic_handler import predict_toxicity
from UserStatus import UserStatus

# Define status for states
CAPTCHA = 0
USER_ACTION = 1


def update_keyboard(user_id: int) -> ReplyKeyboardMarkup:
    user_status = db_connection.get_user_status(user_id=user_id)  # Get user's status

    # Return ReplyKeyboardMarkup based on user's status
    if user_status == UserStatus.IDLE or user_status == UserStatus.PARTNER_LEFT:
        return ReplyKeyboardMarkup(
            [["/chat"]], resize_keyboard=True, is_persistent=True
        )
    
    elif user_status == UserStatus.IN_SEARCH:
        return ReplyKeyboardMarkup(
            [["/stop"]], resize_keyboard=True, is_persistent=True
        )
    
    elif user_status == UserStatus.COUPLED:
        return ReplyKeyboardRemove()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id

    # Check if the user exists in the database, returns to captcha state if not
    if db_connection.check_user(user_id):
        # Check if user's duration on bot is within min_duration (24h), returns to captcha state if not
        if db_connection.check_user_duration(user_id):
            return USER_ACTION

        else:
            await send_captcha(update, context)
            return CAPTCHA

    else:
        await send_captcha(update, context)
        return CAPTCHA


async def send_captcha(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Generate and send the captcha user
    captcha = ImageCaptcha()
    random_string = "".join(
        random.choices(string.ascii_letters.lower() + string.digits, k=5)
    )
    context.user_data["captcha"] = random_string  # Store the captcha in user data
    data: BytesIO = captcha.generate(random_string)

    await context.bot.send_photo(
        reply_markup=ReplyKeyboardRemove(),
        chat_id=update.effective_chat.id,
        photo=data,
        caption=responses.captcha_start,
    )


async def verify_captcha(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_input = update.message.text  # Retrieve message (user's captcha input)
    correct_captcha = context.user_data.get("captcha")  # Retrieve stored captcha

    # Check if user's captcha input is correct, notify user that captcha is incorrect if not
    if user_input == correct_captcha:
        user_id = update.effective_user.id  # Retrieve user id
        # Check if user is already exist in database, insert user to database if not
        if not db_connection.check_user(user_id):
            db_connection.insert_user(user_id)

        db_connection.set_user_start_bot_time(user_id)  # Set user start bot timestamp

        await context.bot.send_message(
            chat_id=update.effective_chat.id, text=responses.captcha_true
        )

        await context.bot.send_message(
            reply_markup=update_keyboard(user_id),
            chat_id=update.effective_chat.id,
            text=responses.start,
        )

    else:
        # Send message to notify that captha is incorrect to user
        await context.bot.send_message(
            chat_id=update.effective_chat.id, text=responses.captcha_false
        )

    # Returns to start function for rechecking
    return await start(update, context)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    # Check if the user is in chat
    if db_connection.get_user_status(user_id=user_id) == UserStatus.COUPLED:
        # User is in chat, retrieve the other user
        other_user_id = db_connection.get_partner_id(user_id)

        if other_user_id is None:
            return await handle_not_in_chat(update, context)
        
        else:
            return await in_chat(update, context, other_user_id)
        
    else:
        return await handle_not_in_chat(update, context)


async def handle_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Handle the command /chat in different cases, based on the status of the user
    current_user_id = update.effective_user.id
    current_user_status = db_connection.get_user_status(user_id=current_user_id)

    # Check user eligibility
    if not db_connection.is_eligible_to_chat(current_user_id):
        await context.bot.send_message(
            reply_markup=update_keyboard(current_user_id),
            chat_id=current_user_id,
            text=responses.not_eligible,
        )

        return

    if current_user_status == UserStatus.PARTNER_LEFT:
        # First, check if the user has been left by partner
        db_connection.set_user_status(
            user_id=current_user_id, new_status=UserStatus.IDLE
        )

        return await start_search(update, context)
    
    elif current_user_status == UserStatus.IN_SEARCH:
        # Warn user is already in search
        return await handle_already_in_search(update, context)
    
    elif current_user_status == UserStatus.COUPLED:
        # Double check if the user is in chat
        other_user = db_connection.get_partner_id(current_user_id)

        if other_user is not None:
            # If the user has been paired, then he/she is already in a chat, so warn him/her
            await context.bot.send_message(
                reply_markup=update_keyboard(current_user_id),
                chat_id=current_user_id,
                text=responses.in_chat,
            )

            return None
        
        else:
            return await start_search(update, context)
        
    elif current_user_status == UserStatus.IDLE:
        # The user is in IDLE status, so simply start the search
        return await start_search(update, context)


async def handle_not_in_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Handle user that is not in chat but sent non-command message regardless
    current_user_id = update.effective_user.id
    current_user_status = db_connection.get_user_status(user_id=current_user_id)

    if current_user_status in [UserStatus.IDLE, UserStatus.PARTNER_LEFT]:
        await context.bot.send_message(
            reply_markup=update_keyboard(current_user_id),
            chat_id=current_user_id,
            text=responses.not_in_chat,
        )

        return
    
    elif current_user_status == UserStatus.IN_SEARCH:
        handle_already_in_search(update, context)

        return


async def handle_already_in_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Handle user that is searching but sent message regardless
    await context.bot.send_message(
        reply_markup=update_keyboard(update.effective_user.id),
        chat_id=update.effective_chat.id,
        text=responses.in_searching,
    )


async def start_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Recheck session with start function, returns to captcha state if true
    if await start(update, context) is CAPTCHA:
        return CAPTCHA

    current_user_id = update.effective_chat.id

    # Set the user status to in_search
    db_connection.set_user_status(
        user_id=current_user_id, new_status=UserStatus.IN_SEARCH
    )
    await context.bot.send_message(
        reply_markup=update_keyboard(current_user_id),
        chat_id=current_user_id,
        text=responses.start_searching,
    )

    # Search for a partner
    other_user_id = db_connection.couple(current_user_id=current_user_id)
    # If a partner is found, notify both the users
    if other_user_id is not None:
        await context.bot.send_message(
            reply_markup=update_keyboard(current_user_id),
            chat_id=current_user_id,
            text=responses.searching_found,
        )
        await context.bot.send_message(
            reply_markup=update_keyboard(other_user_id),
            chat_id=other_user_id,
            text=responses.searching_found,
        )


async def handle_credit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Handle the /credit command, send message of user's credit value
    user_id = update.effective_user.id
    await context.bot.send_message(
        reply_markup=update_keyboard(user_id),
        chat_id=user_id,
        text=f"{responses.credit_score}{db_connection.get_user_credit(user_id)}",
    )


async def handle_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Handles the /help command, send message of bot command's list
    user_id = update.effective_user.id
    await context.bot.send_message(
        reply_markup=update_keyboard(user_id), chat_id=user_id, text=responses.help
    )

    return


async def handle_rules(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Handles the /rules command, send message of bot's rules
    user_id = update.effective_user.id
    await context.bot.send_message(
        reply_markup=update_keyboard(user_id), chat_id=user_id, text=responses.rules
    )


async def handle_stop(update: Update, context: ContextTypes.DEFAULT_TYPE, toxic=False) -> None:
    # Handles the /stop command, able to stop ongoing search or chat
    current_user = update.effective_user.id

    if db_connection.get_user_status(user_id=current_user) == UserStatus.IN_SEARCH:
        db_connection.set_user_status(user_id=current_user, new_status=UserStatus.IDLE)
        await context.bot.send_message(
            reply_markup=update_keyboard(current_user),
            chat_id=current_user,
            text=responses.searching_stopped,
        )

        return

    if db_connection.get_user_status(user_id=current_user) != UserStatus.COUPLED:
        await context.bot.send_message(
            reply_markup=update_keyboard(current_user),
            chat_id=current_user,
            text=responses.not_in_chat,
        )

        return

    other_user = db_connection.get_partner_id(current_user)
    if other_user is None:
        return

    # If parameters toxic is True, reduce user credit by 25
    # User's credit increase by 5 if toxic is false and chat duration is over 5min
    if toxic is True:
        db_connection.set_credit(current_user, -25)

        if db_connection.check_chat_duration(other_user):
            db_connection.set_credit(other_user, 5)

    else:
        if db_connection.check_chat_duration(current_user):
            db_connection.set_credit(current_user, 5)
            db_connection.set_credit(other_user, 5)

    # Perform the uncoupling
    db_connection.uncouple(user_id=current_user)

    await context.bot.send_message(
        reply_markup=update_keyboard(current_user),
        chat_id=current_user,
        text=responses.ending_chat,
    )
    await context.bot.send_message(
        reply_markup=update_keyboard(other_user),
        chat_id=other_user,
        text=responses.stopped_chat,
    )
    await context.bot.send_message(
        reply_markup=update_keyboard(other_user),
        chat_id=other_user,
        text=f"{responses.credit_score}{db_connection.get_user_credit(other_user)}",
    )
    await update.message.reply_text(responses.stop_chat)
    await context.bot.send_message(
        reply_markup=update_keyboard(current_user),
        chat_id=current_user,
        text=f"{responses.credit_score}{db_connection.get_user_credit(current_user)}",
    )


async def handle_next(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Handles the /next command, exiting from the chat and starting a new search if the user is in chat
    current_user = update.effective_user.id

    if db_connection.get_user_status(user_id=current_user) == UserStatus.IN_SEARCH:
        return await handle_already_in_search(update, context)
    
    # If exit_chat returns True, then the user was in chat and successfully exited
    await handle_stop(update, context)

    # Either the user was in chat or not, start the search
    return await start_search(update, context)


async def is_message_incompatible(update: Update, context: ContextTypes.DEFAULT_TYPE, message: Message) -> bool:
    # Check if message is incompatible in this bot specs (inc. document, audio, video)
    if message.audio or message.video or message.video_note or message.voice or (message.document and not message.animation):
        await context.bot.send_message(
            reply_markup=update_keyboard(update.effective_user.id),
            chat_id=update.effective_user.id,
            text=responses.incompatible_message,
        )
        return True
    
    return False


async def in_chat(update: Update, context: ContextTypes.DEFAULT_TYPE, other_user_id) -> None:
    # Handles the case when the user is in chat, processes and checks for toxicity in the message.
    message = update.message

    # Check for message compatibility
    if await is_message_incompatible(update, context, message):
        return

    # Check for toxicity
    if await predict_toxicity(context, message):
        # Notify the sender about toxic content
        await context.bot.send_message(
            reply_markup=update_keyboard(update.effective_user.id),
            chat_id=update.effective_user.id,
            text=responses.toxic_stop_chat,
        )

        # Notify the other user that the chat has ended
        await context.bot.send_message(
            reply_markup=update_keyboard(other_user_id),
            chat_id=other_user_id,
            text=responses.toxic_stopped_chat,
        )

        # Exit chat
        await handle_stop(update, context, True)

        return

    # If not toxic, proceed to handle replies or forward messages
    # Check if the message is a reply to another message
    if update.message.reply_to_message is not None:
        # If the message is a reply to another message, check if the message is a reply to a message sent by the user
        # himself or by the other user
        if update.message.reply_to_message.from_user.id == update.effective_user.id:
            # The message is a reply to a message sent by the user himself, so send the message to the replyed+1
            # message (the one copyed by the bot has id+1)
            await update.effective_chat.copy_message(
                chat_id=other_user_id,
                message_id=update.message.message_id,
                protect_content=True,
                reply_to_message_id=update.message.reply_to_message.message_id + 1,
            )

        # Else, the replied message could be sent either by the other user, another previous user or the bot
        # Since the bot sends non-protected-content messages, use this as discriminator
        elif update.message.reply_to_message.has_protected_content is None:
            # Message is sent by the bot, forward message without replying
            await update.effective_chat.copy_message(
                chat_id=other_user_id,
                message_id=update.message.message_id,
                protect_content=True,
            )

        else:
            # The message is a reply to a message sent by another user, forward the message replyed to the replyed -1
            # message. Other user will see the message as a reply to the message he/she sent, only if he was the sender
            await update.effective_chat.copy_message(
                chat_id=other_user_id,
                message_id=update.message.message_id,
                protect_content=True,
                reply_to_message_id=update.message.reply_to_message.message_id - 1,
            )
    else:
        # The message is not a reply to another message, so send the message without replying
        await update.effective_chat.copy_message(
            chat_id=other_user_id,
            message_id=update.message.message_id,
            protect_content=True,
        )


def is_bot_blocked_by_user(update: Update) -> bool:
    # Check if bot is blocked by user
    new_member_status = update.my_chat_member.new_chat_member.status
    old_member_status = update.my_chat_member.old_chat_member.status
    if (
        new_member_status == ChatMember.BANNED
        and old_member_status == ChatMember.MEMBER
    ):
        return True
    
    else:
        return False


async def blocked_bot_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Handle if bot is blocked by user
    if is_bot_blocked_by_user(update):
        # Check if user was in chat
        user_id = update.effective_user.id
        user_status = db_connection.get_user_status(user_id=user_id)

        if user_status == UserStatus.COUPLED:
            other_user = db_connection.get_partner_id(user_id)
            db_connection.uncouple(user_id=user_id)
            await context.bot.send_message(
                reply_markup=update_keyboard(user_id),
                chat_id=other_user,
                text=responses.stopped_chat,
            )

        return ConversationHandler.END
    
    else:
        # Telegram API does not provide a way to check if the bot was unblocked by the user
        return USER_ACTION
