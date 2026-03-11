# Safe Anonymous Chat Bot (Telegram)

A **Telegram bot built with Python** that enables **anonymous chatting between users** while incorporating **toxic content detection** to prevent malicious or harmful messages.

The bot automatically scans **text, images, and stickers** to detect potentially toxic or abusive content before it is delivered to another user. This helps maintain a safer anonymous communication environment.

---

## Features

- **Anonymous Chat System**
  - Users can communicate with others without revealing their identity.

- **Toxic Content Detection**
  - Automatically detects and filters harmful or abusive messages (utilizing IndoBERT for text messages).

- **Multi-Media Moderation**
  - Supports moderation for:
    - Text messages (in Indonesian language)
    - Images
    - Stickers

- **Admin Dashboard**
  - Built using **Streamlit** for monitoring and management.

---

## Installation

Clone the repository and install the required dependencies.

```bash
pip install -r requirements.txt
````

---

## Configuration

Create a file named **`config.py`** in the root directory and add your Telegram bot token.

```python
BOT_TOKEN = "your_telegram_bot_token_here"
```

You can obtain the token by creating a bot via **@BotFather** on Telegram.

---

## Running the Bot

Start the admin dashboard (which launches the bot system):

```bash
streamlit run admin_dashboard.py
```

---

## How It Works

1. Users connect to the Telegram bot.
2. The bot pairs users anonymously.
3. Messages sent between users are **scanned for toxic content**.
4. If the message passes moderation, it is forwarded to the recipient.
5. If the content is flagged as malicious, it is **blocked or handled according to moderation rules**.

---