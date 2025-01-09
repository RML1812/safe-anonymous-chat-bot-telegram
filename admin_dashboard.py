import asyncio
import logging
import os
import subprocess
import sys
import time  # Added for delay
from datetime import datetime

import psutil
import streamlit as st
from telegram import Bot, ReplyKeyboardMarkup, ReplyKeyboardRemove

import db_connection
import responses
from config import ADMIN_NAME, ADMIN_PW, BOT_TOKEN

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "is_online" not in st.session_state:
    st.session_state["is_online"] = False
if "pid" not in st.session_state:
    st.session_state["pid"] = 0
if "delay" not in st.session_state:
    st.session_state["delay"] = 3

# Ensure the logs directory exists
os.makedirs("logs", exist_ok=True)

# Generate log file name with current date
log_filename = datetime.now().strftime("logs/logs_%d-%m-%Y.txt")


# Configure logging
class ReverseLogHandler(logging.FileHandler):
    def emit(self, record):
        """Override emit to write newest logs at the top."""
        try:
            log_entry = self.format(record) + "\n"
            if os.path.exists(self.baseFilename):
                with open(self.baseFilename, "r+", encoding="utf-8") as file:
                    content = file.read()
                    file.seek(0, 0)
                    file.write(log_entry.rstrip("\r\n") + "\n" + content)
            else:
                with open(self.baseFilename, "w", encoding="utf-8") as file:
                    file.write(log_entry)
        except Exception:
            self.handleError(record)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        ReverseLogHandler(log_filename),
        logging.StreamHandler(),  # Optional: to also output logs to the console
    ],
)


def init_bot():
    return Bot(token=BOT_TOKEN)


def get_user_numbers():
    total_users, coupled_users = db_connection.retrieve_users_number()
    return total_users, coupled_users


def kills(pid):
    parent = psutil.Process(pid)
    for child in parent.children(recursive=True):
        child.kill()
    parent.kill()


async def set_online():
    st.session_state["is_online"] = True

    with st.spinner("Setting bot online, please wait..."):
        process = subprocess.Popen([sys.executable, "main.py"])
        st.session_state["pid"] = process.pid

        bot = init_bot()
        user_ids = db_connection.get_all_user_ids()
        for user_id in user_ids:
            await bot.send_message(
                reply_markup=ReplyKeyboardMarkup(
                    [["/start"]],
                    resize_keyboard=True,
                    one_time_keyboard=True,
                    is_persistent=True,
                ),
                chat_id=user_id,
                text=responses.turn_online,
            )

        logging.info("Bot turned online.")
        time.sleep(st.session_state["delay"])
        st.rerun()


async def set_offline():
    st.session_state["is_online"] = False

    with st.spinner("Setting bot offline, please wait..."):
        bot = init_bot()
        user_ids = db_connection.get_all_user_ids()

        if st.session_state["pid"] is not None:
            kills(st.session_state["pid"])
            for user_id in user_ids:
                await bot.send_message(
                    reply_markup=ReplyKeyboardRemove(),
                    chat_id=user_id,
                    text=responses.turn_offline,
                )

            logging.info("Bot turned offline.")
            time.sleep(st.session_state["delay"])
            st.rerun()


def reset_database():
    with st.spinner("Resetting database, please wait..."):
        if st.session_state["is_online"]:
            asyncio.run(set_offline())
        else:
            if os.path.exists("users_database.db"):
                os.remove("users_database.db")
                logging.info("Database reset.")
            else:
                logging.warning("Database file not found.")
        time.sleep(st.session_state["delay"])
        st.rerun()


def login():
    st.title("Admin Dashboard Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if username == ADMIN_NAME and password == ADMIN_PW:
            st.session_state["logged_in"] = True
            st.success("Logged in successfully")
            st.rerun()
        else:
            st.error("Invalid username or password")


def logout():
    if st.sidebar.button("Logout"):
        st.session_state["logged_in"] = False
        st.success("Logged out successfully")
        st.rerun()


def refresh():
    if st.sidebar.button("Refresh"):
        st.rerun()


def sidebar_status():
    # Show Online/Offline state in the sidebar
    is_online_status = "Online" if st.session_state["is_online"] else "Offline"
    status_color = "green" if st.session_state["is_online"] else "red"
    st.sidebar.markdown(
        f"### Current State: <span style='color:{status_color}'>{is_online_status}</span>",
        unsafe_allow_html=True,
    )


def dashboard():
    st.header("Dashboard")

    # Display user statistics
    total_users, coupled_users = get_user_numbers()
    st.metric("Total Users", total_users)
    st.metric("Coupled Users", coupled_users)

    # Online/Offline
    col1, col2, col3 = st.columns(3)

    with col1:
        if not st.session_state["is_online"]:
            if st.button("Go Online"):
                asyncio.run(set_online())
        else:
            st.button("Go Online", disabled=True)

    with col2:
        if st.session_state["is_online"]:
            if st.button("Go Offline"):
                asyncio.run(set_offline())
        else:
            st.button("Go Offline", disabled=True)

    with col3:
        if not st.session_state["is_online"]:
            if st.button("Reset Database"):
                reset_database()
        else:
            st.button("Reset Database", disabled=True)

    # Log section in the dashboard
    st.subheader("Today's Logs")
    log_content = read_latest_log()
    st.text_area("Current Day Log Output", log_content, height=300)


def logs():
    st.header("Logs")

    # List all available log files
    log_files = sorted([f for f in os.listdir("logs") if f.startswith("logs_")])
    selected_log = st.selectbox("Select a log file to view:", log_files)

    # Display content of selected log file
    if selected_log:
        with open(os.path.join("logs", selected_log), "r") as file:
            log_content = file.read()
        st.text_area("Log Output", log_content, height=400)


def read_latest_log():
    log_filename = datetime.now().strftime("logs/logs_%d-%m-%Y.txt")
    if os.path.exists(log_filename):
        with open(log_filename, "r") as file:
            return file.read()
    else:
        return "Log file not found."


def main():
    if st.session_state["logged_in"]:
        sidebar_status()
        st.sidebar.title("Navigation")
        selection = st.sidebar.radio("Go to", ["Dashboard", "Logs"])
        logout()
        refresh()
        if selection == "Dashboard":
            dashboard()
        elif selection == "Logs":
            logs()
    else:
        login()


if __name__ == "__main__":
    db_connection.create_db()
    main()
