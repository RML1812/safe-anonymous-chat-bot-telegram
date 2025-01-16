import sqlite3
from datetime import datetime

from UserStatus import UserStatus


def connect_to_db() -> tuple[sqlite3.Connection, sqlite3.Cursor]:
    # Connect to the chatbot database
    conn = sqlite3.connect("users_database.db")
    c = conn.cursor()

    return conn, c


def create_db() -> None:
    conn, c = connect_to_db()  # Connect to the chatbot database

    # Create the users table if it does not exist
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            start_bot_time TIMESTAMP,
            start_chat_time TIMESTAMP,
            credit INT CHECK(credit >= 0 AND credit <= 100),
            status TEXT,
            partner_id TEXT
        )
        """
    )

    # Create the bot_status table if it does not exist
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS bot_status (
            online BOOLEAN,
            pid INTEGER
        )
        """
    )

    # Insert the default row into bot_status if the table is empty
    c.execute(
        """
        INSERT INTO bot_status (online, pid)
        SELECT 0, 0
        WHERE NOT EXISTS (SELECT 1 FROM bot_status)
        """
    )

    # Commit and close connection
    conn.commit()
    conn.close()


def check_user(user_id: int) -> bool:
    conn, c = connect_to_db()  # Connect to the chatbot database

    # Check if the user is already in the users table
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))

    if c.fetchone():
        # If the user is already in the users table, returns True
        conn.close()
        return True
    
    else:
        return False


def insert_user(user_id: int) -> None:
    conn, c = connect_to_db()  # Connect to the chatbot database

    # Insert the user into the users table
    c.execute(
        "INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)",
        (
            user_id,
            None,
            None,
            100,
            UserStatus.IDLE,
            None,
        ),
    )

    # Commit and close connection
    conn.commit()
    conn.close()


def set_bot_status(online: bool, pid: int) -> None:
    conn, c = connect_to_db()  # Connect to the chatbot database

    # Ensure there's only one row in the table
    c.execute("DELETE FROM bot_status")

    # Insert the single row
    c.execute("INSERT INTO bot_status (online, pid) VALUES (?, ?)", (online, pid))

    # Commit and close connection
    conn.commit()
    conn.close()


def get_bot_pid() -> int:
    conn, c = connect_to_db()  # Connect to the chatbot database

    # Get pid
    c.execute("SELECT pid FROM bot_status")
    pid = c.fetchone()[0]

    # Close connection
    conn.close()

    return pid


def is_online() -> bool:
    conn, c = connect_to_db()  # Connect to the chatbot database

    # Get online status
    c.execute("SELECT online FROM bot_status")
    is_online = c.fetchone()[0] 

    # Close connection
    conn.close()

    return is_online


def get_all_user_ids() -> list:
    conn, c = connect_to_db()  # Connect to the chatbot database

    # Get all user_ids
    c.execute("SELECT user_id FROM users")
    user_ids = [row[0] for row in c.fetchall()]

    # Close connection
    conn.close()

    return user_ids


def get_user_status(user_id: int) -> str:
    conn, c = connect_to_db()  # Connect to the chatbot database

    # Get the status of the user
    c.execute("SELECT status FROM users WHERE user_id=?", (user_id,))
    status = c.fetchone()[0]

    # Close connection
    conn.close()

    return status


def set_user_status(user_id: int, new_status: str) -> None:
    conn, c = connect_to_db()  # Connect to the chatbot database

    # Update the status of the user
    c.execute(
        "UPDATE users SET status=? WHERE user_id=?",
        (
            new_status,
            user_id,
        ),
    )

    # Commit and close connection
    conn.commit()
    conn.close()


def set_user_start_bot_time(user_id) -> None:
    conn, c = connect_to_db()  # Connect to the chatbot database

    # Update the user's start bot time
    c.execute(
        "UPDATE users SET start_bot_time=? WHERE user_id=?",
        (
            datetime.now(),
            user_id,
        ),
    )

    # Commit and close connection
    conn.commit()
    conn.close()


def set_credit(user_id: int, delta: int) -> None:
    conn, c = connect_to_db()  # Connect to the chatbot database

    # Get the current credit
    c.execute("SELECT credit FROM users WHERE user_id=?", (user_id,))
    current_credit = c.fetchone()[0]

    # Set credit value within bounds
    new_credit = max(0, min(100, current_credit + delta))

    # Update the credit in the database
    c.execute(
        "UPDATE users SET credit=? WHERE user_id=?",
        (
            new_credit,
            user_id,
        ),
    )

    # Commit and close connection
    conn.commit()
    conn.close()


def get_user_credit(user_id: int) -> int:
    conn, c = connect_to_db()  # Connect to the chatbot database

    # Get the user's credit
    c.execute("SELECT credit FROM users WHERE user_id=?", (user_id,))
    credit = c.fetchone()[0]

    # Close connection
    conn.close()

    return credit


def is_eligible_to_chat(user_id: int) -> bool:
    credit = get_user_credit(user_id)  # Get the user's credit

    # Returns True if credit is > 0 (eligible)
    if credit > 0:
        return True

    return False


def get_partner_id(user_id: int) -> int:
    conn, c = connect_to_db()  # Connect to the chatbot database

    # If the user is a guest, then search for the host
    c.execute("SELECT user_id FROM users WHERE partner_id=?", (user_id,))
    other_user_id = c.fetchone()

    if not other_user_id:
        # If no user is found, return None
        conn.close()
        return None

    # Otherwise, returns the other user's id
    other_user_id = other_user_id[0]

    # Close connection
    conn.close()

    return other_user_id


def couple(current_user_id: int) -> int:
    conn, c = connect_to_db() # Connect to the chatbot database

    # If the user is not the current one and is in search, then couple them
    c.execute(
        "SELECT user_id FROM users WHERE status=? AND user_id!=?",
        (
            UserStatus.IN_SEARCH,
            current_user_id,
        ),
    )

    # Verify if another user in search is found
    other_user_id = c.fetchone()
    if not other_user_id:
        # If no user is found, return None
        return None
    
    # If another user in search is found, couple the users
    other_user_id = other_user_id[0]

    # Update both users' partner_id and start chat time to reflect the coupling
    start_chat_time = datetime.now()
    c.execute(
        "UPDATE users SET partner_id=?, start_chat_time=?, status=? WHERE user_id=?",
        (other_user_id, start_chat_time, UserStatus.COUPLED, current_user_id),
    )
    c.execute(
        "UPDATE users SET partner_id=?, start_chat_time=?, status=? WHERE user_id=?",
        (current_user_id, start_chat_time, UserStatus.COUPLED, other_user_id),
    )

    # Commit and close connection
    conn.commit()
    conn.close()

    return other_user_id


def check_user_duration(user_id: int, max_duration: float=86400.0) -> bool:
    conn, c = connect_to_db()  # Connect to the chatbot database

    # Get user's start bot time and check if its exist, if not returns false
    c.execute("SELECT start_bot_time FROM users WHERE user_id=?", (user_id,))
    start_bot_time = c.fetchone()
    if not start_bot_time[0]:
        conn.close()
        return False

    # Calculate duration in seconds
    start_bot_time = datetime.fromisoformat(start_bot_time[0])
    duration = datetime.now() - start_bot_time

    # Close connection
    conn.close()

    return duration.total_seconds() < max_duration


def check_chat_duration(user_id: int, min_duration: float=300.0) -> bool:
    conn, c = connect_to_db()  # Connect to the chatbot database

    # Get user's start chat time
    c.execute("SELECT start_chat_time FROM users WHERE user_id=?", (user_id,))
    start_chat_time = c.fetchone()[0]

    # Calculate duration in seconds
    start_chat_time = datetime.fromisoformat(start_chat_time)
    duration = datetime.now() - start_chat_time

    # Close connection
    conn.close()

    return duration.total_seconds() >= min_duration


def uncouple(user_id: int) -> None:
    conn, c = connect_to_db()  # Connect to the chatbot database

    # Get partner_id of the user
    partner_id = get_partner_id(user_id)
    if not partner_id:
        # If the user is not coupled, return None
        return None

    # Update both users to reflect the uncoupling
    c.execute(
        "UPDATE users SET partner_id=?, start_chat_time=?, status=? WHERE user_id=?",
        (
            None,
            None,
            UserStatus.IDLE,
            user_id,
        ),
    )
    c.execute(
        "UPDATE users SET partner_id=?, start_chat_time=?, status=? WHERE user_id=?",
        (
            None,
            None,
            UserStatus.IDLE,
            partner_id,
        ),
    )

    # Commit and close connection
    conn.commit()
    conn.close()


def retrieve_users_number() -> tuple[int, int]:
    conn, c = connect_to_db()  # Connect to the chatbot database

    # Retrieve the number of users in the users table
    c.execute("SELECT COUNT(*) FROM users")
    total_users_number = c.fetchone()[0]

    # Retrieve the number of users who are currently coupled
    c.execute("SELECT COUNT(*) FROM users WHERE status='coupled'")
    paired_users_number = c.fetchone()[0]

    # Close connection
    conn.close()

    return total_users_number, paired_users_number


def reset_users_status() -> None:
    conn, c = connect_to_db()  # Connect to the chatbot database

    # Reset the status of all users to UserStatus.IDLE
    c.execute(
        "UPDATE users SET start_bot_time=?, start_chat_time=?, status=?",
        (
            None,
            None,
            UserStatus.IDLE,
        ),
    )

    # Commit and close connection
    conn.commit()
    conn.close()
