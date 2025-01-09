import db_connection
import responses
import random
import string
from telegram import Update, ChatMember, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler
from UserStatus import UserStatus
from toxic_handler import predict_toxicity
from io import BytesIO
from captcha.image import ImageCaptcha


# Define status for states
CAPTCHA = 0
USER_ACTION = 1


def update_keyboard(user_id):
    user_status = db_connection.get_user_status(user_id=user_id)

    if user_status == UserStatus.IDLE or user_status == UserStatus.PARTNER_LEFT:
        return ReplyKeyboardMarkup([["/chat"]], resize_keyboard=True, is_persistent=True)
    elif user_status == UserStatus.IN_SEARCH:
        return ReplyKeyboardMarkup([["/stop"]], resize_keyboard=True, is_persistent=True)
    elif user_status == UserStatus.COUPLED:
        return ReplyKeyboardRemove()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Welcomes the user and sets their status to idle if not already in the database.
    Prompts for captcha verification for new users.
    """
    user_id = update.effective_user.id

    # Check if the user exists in the database
    if db_connection.check_user(user_id):
        await context.bot.send_message(reply_markup=update_keyboard(user_id), chat_id=update.effective_chat.id, text=responses.start)
        return USER_ACTION

    # Generate and send the captcha for new users
    captcha = ImageCaptcha()
    random_string = ''.join(random.choices(string.ascii_letters.lower() + string.digits, k=5))
    context.user_data['captcha'] = random_string  # Store the captcha in user data

    data: BytesIO = captcha.generate(random_string)
    await context.bot.send_photo(chat_id=update.effective_chat.id, photo=data, caption=responses.captcha_start)

    # Move to CAPTCHA verification state
    return CAPTCHA


async def verify_captcha(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Verifies the user's input against the captcha.
    """
    user_input = update.message.text
    correct_captcha = context.user_data.get('captcha')  # Retrieve stored captcha

    if user_input == correct_captcha:
        user_id = update.effective_user.id
        db_connection.insert_user(user_id)
        await context.bot.send_message(reply_markup=update_keyboard(user_id), chat_id=update.effective_chat.id, text=responses.captcha_true)

        # Proceed to the main functionality
        await context.bot.send_message(reply_markup=update_keyboard(user_id), chat_id=update.effective_chat.id, text=responses.start)
        return USER_ACTION
    else:
        await context.bot.send_message(reply_markup=update_keyboard(user_id), chat_id=update.effective_chat.id, text=responses.captcha_false)

        # Generate and send a new captcha
        captcha = ImageCaptcha()
        random_string = ''.join(random.choices(string.ascii_letters.lower() + string.digits, k=5))
        context.user_data['captcha'] = random_string

        data: BytesIO = captcha.generate(random_string)
        await context.bot.send_photo(chat_id=update.effective_chat.id, photo=data, caption=responses.captcha_start)

        # Stay in CAPTCHA state
        return CAPTCHA


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Define the action to do based on the message received and the actual status of the user
    :param update: update received from the user
    :param context: context of the bot
    :return: None
    """
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
    """
    Handles the /chat command, starting the search for a partner if the user is not already in search
    :param update: update received from the user
    :param context: context of the bot
    :return: None
    """
    # Handle the command /chat in different cases, based on the status of the user
    current_user_id = update.effective_user.id
    current_user_status = db_connection.get_user_status(user_id=current_user_id)

    # Check user eligibility
    if not db_connection.is_eligible_to_chat(current_user_id):
        await context.bot.send_message(reply_markup=update_keyboard(current_user_id), chat_id=current_user_id, text="⚠️ Your credit has reached 0. You are no longer allowed to use the chat feature.")
        return

    if current_user_status == UserStatus.PARTNER_LEFT:
        # First, check if the user has been left by his/her partner (he/she would have updated this user's status to
        # PARTNER_LEFT)
        db_connection.set_user_status(user_id=current_user_id, new_status=UserStatus.IDLE)

        return await start_search(update, context)
    elif current_user_status == UserStatus.IN_SEARCH:
        # Warn him/her that he/she is already in search
        return await handle_already_in_search(update, context)
    elif current_user_status == UserStatus.COUPLED:
        # Double check if the user is in chat
        other_user = db_connection.get_partner_id(current_user_id)
        if other_user is not None:
            # If the user has been paired, then he/she is already in a chat, so warn him/her
            await context.bot.send_message(reply_markup=update_keyboard(current_user_id), chat_id=current_user_id, text=responses.in_chat)
            return None
        else:
            return await start_search(update, context)
    elif current_user_status == UserStatus.IDLE:
        # The user is in IDLE status, so simply start the search
        return await start_search(update, context)


async def handle_not_in_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles the case when the user is not in chat
    :param update: update received from the user
    :param context: context of the bot
    :return: None
    """
    current_user_id = update.effective_user.id
    current_user_status = db_connection.get_user_status(user_id=current_user_id)

    if current_user_status in [UserStatus.IDLE, UserStatus.PARTNER_LEFT]:
        await context.bot.send_message(reply_markup=update_keyboard(current_user_id), chat_id=current_user_id, text=responses.not_in_chat)
        return
    elif current_user_status == UserStatus.IN_SEARCH:
        await context.bot.send_message(reply_markup=update_keyboard(current_user_id), chat_id=current_user_id, text=responses.in_searching)
        return


async def handle_already_in_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles the case when the user is already in search
    :param update: update received from the user
    :param context: context of the bot
    :return: None
    """
    await context.bot.send_message(reply_markup=update_keyboard(update.effective_user.id), chat_id=update.effective_chat.id, text=responses.in_searching)
    return


async def start_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Starts the search for a partner, setting the user status to in_search and adding him/her to the list of users
    :param update: update received from the user
    :param context: context of the bot
    :return: None
    """
    current_user_id = update.effective_chat.id

    # Set the user status to in_search
    db_connection.set_user_status(user_id=current_user_id, new_status=UserStatus.IN_SEARCH)
    await context.bot.send_message(reply_markup=update_keyboard(current_user_id), chat_id=current_user_id, text=responses.start_searching)

    # Search for a partner
    other_user_id = db_connection.couple(current_user_id=current_user_id)
    # If a partner is found, notify both the users
    if other_user_id is not None:
        await context.bot.send_message(reply_markup=update_keyboard(current_user_id), chat_id=current_user_id, text=responses.searching_found)
        await context.bot.send_message(reply_markup=update_keyboard(other_user_id), chat_id=other_user_id, text=responses.searching_found)

    return


async def handle_stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles the /exit command, exiting from the chat if the user is in chat
    :param update: update received from the user
    :param context: context of the bot
    :return: None
    """
    await stop_chat(update, context)
    return


async def handle_credit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles the /stats command, showing the bot statistics if the user is the admin
    :param update: update received from the user
    :param context: context of the bot
    :return: None
    """
    user_id = update.effective_user.id
    await context.bot.send_message(reply_markup=update_keyboard(user_id), chat_id=user_id, text=f"{responses.credit_score}{db_connection.get_user_credit(user_id)}")

    return


async def handle_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles the /stats command, showing the bot statistics if the user is the admin
    :param update: update received from the user
    :param context: context of the bot
    :return: None
    """
    user_id = update.effective_user.id
    await context.bot.send_message(reply_markup=update_keyboard(user_id), chat_id=user_id, text=responses.help)
    
    return


async def handle_rules(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles the /stats command, showing the bot statistics if the user is the admin
    :param update: update received from the user
    :param context: context of the bot
    :return: None
    """
    user_id = update.effective_user.id
    await context.bot.send_message(reply_markup=update_keyboard(user_id), chat_id=user_id, text=responses.rules)
    
    return


async def stop_chat(update: Update, context: ContextTypes.DEFAULT_TYPE, toxic=False) -> None:
    """
    Exits from the chat, sending a message to the other user and updating the status of both the users
    :param update: update received from the user
    :param context: context of the bot
    :return: a boolean value, True if the user was in chat (and so exited), False otherwise
    """
    current_user = update.effective_user.id

    if db_connection.get_user_status(user_id=current_user) == UserStatus.IN_SEARCH:
        db_connection.set_user_status(user_id=current_user, new_status=UserStatus.IDLE)
        await context.bot.send_message(reply_markup=update_keyboard(current_user), chat_id=current_user, text=responses.searching_stopped)
        return
    
    if db_connection.get_user_status(user_id=current_user) != UserStatus.COUPLED:
        await context.bot.send_message(reply_markup=update_keyboard(current_user), chat_id=current_user, text=responses.not_in_chat)
        return

    other_user = db_connection.get_partner_id(current_user)
    if other_user is None:
        return
    
    if toxic is False:
        db_connection.update_credit(other_user, 5)
        db_connection.update_credit(current_user, 5)

    # Perform the uncoupling
    db_connection.uncouple(user_id=current_user)

    await context.bot.send_message(reply_markup=update_keyboard(current_user), chat_id=current_user, text=responses.ending_chat)
    await context.bot.send_message(reply_markup=update_keyboard(other_user), chat_id=other_user, text=responses.stopped_chat)
    await context.bot.send_message(reply_markup=update_keyboard(other_user), chat_id=other_user, text=f"{responses.credit_score}{db_connection.get_user_credit(other_user)}")
    await update.message.reply_text(responses.stop_chat)
    await context.bot.send_message(reply_markup=update_keyboard(current_user), chat_id=current_user, text=f"{responses.credit_score}{db_connection.get_user_credit(current_user)}")

    return


async def exit_then_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles the /newchat command, exiting from the chat and starting a new search if the user is in chat
    :param update: update received from the user
    :param context: context of the bot
    :return: None
    """
    current_user = update.effective_user.id
    if db_connection.get_user_status(user_id=current_user) == UserStatus.IN_SEARCH:
        return await handle_already_in_search(update, context)
    # If exit_chat returns True, then the user was in chat and successfully exited
    await stop_chat(update, context)
    # Either the user was in chat or not, start the search
    return await start_search(update, context)


async def in_chat(update: Update, context: ContextTypes.DEFAULT_TYPE, other_user_id) -> None:
    """
    Handles the case when the user is in chat, processes and checks for toxicity in the message.
    If the message is toxic, the bot ends the chat for both users.
    :param update: update received from the user
    :param other_user_id: id of the other user in chat
    :return: None
    """
    # Retrieve the message
    message = update.message

    # Check for toxicity
    if await predict_toxicity(context, message):
        # Notify the sender about toxic content
        await context.bot.send_message(reply_markup=update_keyboard(update.effective_user.id), chat_id=update.effective_user.id, text=responses.toxic_stop_chat)
        
        # Notify the other user that the chat has ended
        await context.bot.send_message(reply_markup=update_keyboard(other_user_id), chat_id=other_user_id, text=responses.toxic_stopped_chat)

        # Decrease credit by 25 for the toxic user
        db_connection.update_credit(update.effective_user.id, -25)
        # Increase credit by 5 points for other user
        db_connection.update_credit(other_user_id, 5)

        # Exit chat
        await stop_chat(update, context, True)

        return

    # If not toxic, proceed to handle replies or forward messages
    # Check if the message is a reply to another message
    if update.message.reply_to_message is not None:
        # If the message is a reply to another message, check if the message is a reply to a message sent by the user
        # himself or by the other user
        if update.message.reply_to_message.from_user.id == update.effective_user.id:
            # The message is a reply to a message sent by the user himself, so send the message to the replyed+1
            # message (the one copyed by the bot has id+1)
            await update.effective_chat.copy_message(chat_id=other_user_id, message_id=update.message.message_id, protect_content=True, reply_to_message_id=update.message.reply_to_message.message_id + 1)

        # Else, the replied message could be sent either by the other user, another previous user or the bot
        # Since the bot sends non-protected-content messages, use this as discriminator
        elif update.message.reply_to_message.has_protected_content is None:
            # Message is sent by the bot, forward message without replying
            await update.effective_chat.copy_message(chat_id=other_user_id, message_id=update.message.message_id, protect_content=True)

        else:
            # The message is a reply to a message sent by another user, forward the message replyed to the replyed -1
            # message. Other user will see the message as a reply to the message he/she sent, only if he was the sender
            await update.effective_chat.copy_message(chat_id=other_user_id, message_id=update.message.message_id, protect_content=True, reply_to_message_id=update.message.reply_to_message.message_id - 1)
    else:
        # The message is not a reply to another message, so send the message without replying
        await update.effective_chat.copy_message(chat_id=other_user_id, message_id=update.message.message_id, protect_content=True)

    return


def is_bot_blocked_by_user(update: Update) -> bool:
    new_member_status = update.my_chat_member.new_chat_member.status
    old_member_status = update.my_chat_member.old_chat_member.status
    if new_member_status == ChatMember.BANNED and old_member_status == ChatMember.MEMBER:
        return True
    else:
        return False


async def blocked_bot_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_bot_blocked_by_user(update):
        # Check if user was in chat
        user_id = update.effective_user.id
        user_status = db_connection.get_user_status(user_id=user_id)
        if user_status == UserStatus.COUPLED:
            other_user = db_connection.get_partner_id(user_id)
            db_connection.uncouple(user_id=user_id)
            await context.bot.send_message(reply_markup=update_keyboard(user_id), chat_id=other_user, text=responses.stopped_chat)
        return ConversationHandler.END
    else:
        # Telegram API does not provide a way to check if the bot was unblocked by the user
        return USER_ACTION