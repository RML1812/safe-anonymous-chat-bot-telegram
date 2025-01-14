import asyncio
import logging
import os
import subprocess
import sys
import time
from datetime import datetime

import psutil
import streamlit as st
from telegram import Bot, ReplyKeyboardRemove

import db_connection
import responses
from config import ADMIN_NAME, ADMIN_PW, BOT_TOKEN
from LogHandler import LogHandler

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "delay" not in st.session_state:
    st.session_state["delay"] = 15


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        LogHandler(),
        logging.StreamHandler(),
    ],
)


def get_user_numbers():
    total_users, coupled_users = db_connection.retrieve_users_number()
    return total_users, coupled_users


async def set_online():
    with st.spinner("Setting bot online, please wait..."):
        process = subprocess.Popen([sys.executable, "main.py"], shell=True)
        db_connection.set_bot_status(True, process.pid)
        logging.info("Bot turned online.")
        time.sleep(st.session_state["delay"])
        st.rerun()


async def set_offline():
    with st.spinner("Setting bot offline, please wait..."):
        pid = db_connection.get_bot_pid()
        process = psutil.Process(pid)
        process.terminate()
        logging.info("Bot turned offline.")
        time.sleep(st.session_state["delay"])

        db_connection.set_bot_status(False, 0)
        user_ids = db_connection.get_all_user_ids()
        bot = Bot(token=BOT_TOKEN)
        for user_id in user_ids:
            await bot.send_message(
                reply_markup=ReplyKeyboardRemove(),
                chat_id=user_id,
                text=responses.turn_offline,
            )

        st.rerun()


def reset_database():
    with st.spinner("Resetting database, please wait..."):
        if db_connection.is_online():
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
    is_online_status = "Online" if db_connection.is_online() else "Offline"
    status_color = "green" if db_connection.is_online() else "red"
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
        if not db_connection.is_online():
            if st.button("Go Online"):
                asyncio.run(set_online())
        else:
            st.button("Go Online", disabled=True)

    with col2:
        if db_connection.is_online():
            if st.button("Go Offline"):
                asyncio.run(set_offline())
        else:
            st.button("Go Offline", disabled=True)

    with col3:
        if db_connection.is_online():
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
