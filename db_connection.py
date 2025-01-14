import datetime
import sqlite3

from UserStatus import UserStatus


def connect_to_db():
    # Connect to the chatbot database
    conn = sqlite3.connect("users_database.db")
    c = conn.cursor()

    return conn, c


def create_db():
    # Connect to the chatbot database
    conn, c = connect_to_db()
    # Create the users table if it does not exist (user_id, start_bot_time, start_chat_time, credit, status, partner_id)
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS
            users (
                user_id TEXT PRIMARY KEY,
                start_bot_time TIMESTAMP,
                start_chat_time TIMESTAMP,
                credit INT CHECK(credit >= 0 AND credit <= 100),
                status TEXT,
                partner_id TEXT
            )
        """
    )
    conn.commit()
    conn.close()


def check_user(user_id):
    # Connect to the chatbot database
    conn, c = connect_to_db()
    # Check if the user is already in the users table
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    if c.fetchone():
        # If the user is already in the users table, returns True
        conn.close()
        return True
    else:
        return False


def insert_user(user_id):
    # Connect to the chatbot database
    conn, c = connect_to_db()

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
    )  # No partner_id initially
    conn.commit()
    conn.close()


def get_all_user_ids():
    # Connect to the chatbot database
    conn, c = connect_to_db()

    # Execute the query to fetch all user_ids
    c.execute("SELECT user_id FROM users")
    user_ids = [row[0] for row in c.fetchall()]

    # Close the connection
    c.close()
    conn.close()

    return user_ids


def get_user_status(user_id):
    # Connect to the chatbot database
    conn, c = connect_to_db()
    # Get the status of the user
    c.execute("SELECT status FROM users WHERE user_id=?", (user_id,))
    status = c.fetchone()[0]
    conn.close()

    return status


def set_user_status(user_id, new_status):
    # Connect to the chatbot database
    conn, c = connect_to_db()
    # Set the status of the user
    c.execute(
        "UPDATE users SET status=? WHERE user_id=?",
        (
            new_status,
            user_id,
        ),
    )
    conn.commit()
    conn.close()


def set_user_start_bot_time(user_id):
    # Connect to the chatbot database
    conn, c = connect_to_db()
    # Set the status of the user
    c.execute(
        "UPDATE users SET start_bot_time=? WHERE user_id=?",
        (
            datetime.datetime.now(),
            user_id,
        ),
    )
    conn.commit()
    conn.close()


def update_credit(user_id, delta, conn=any, c=any):
    """
    Updates the credit of the user by delta.
    If delta is positive, adds credit up to a max of 100.
    If delta is negative, subtracts credit down to a minimum of 0.
    """
    conn, c = connect_to_db()

    # Fetch the current credit
    c.execute("SELECT credit FROM users WHERE user_id=?", (user_id,))
    current_credit = c.fetchone()
    if not current_credit:
        conn.close()
        return

    current_credit = current_credit[0]
    # Update credit value within bounds
    new_credit = max(0, min(100, current_credit + delta))

    # Update the credit in the database
    c.execute(
        "UPDATE users SET credit=? WHERE user_id=?",
        (
            new_credit,
            user_id,
        ),
    )

    conn.commit()
    conn.close()

    # Return the updated credit for logging or further use
    return new_credit


def get_user_credit(user_id):
    """
    Retrieves the current credit value of a user by user_id.
    :param user_id: The ID of the user whose credit is being retrieved.
    :return: The user's credit as an integer, or None if the user does not exist.
    """
    conn, c = connect_to_db()

    # Fetch the user's credit
    c.execute("SELECT credit FROM users WHERE user_id=?", (user_id,))
    credit = c.fetchone()
    conn.close()

    # Check if the user exists
    if credit is not None:
        return credit[0]  # Return the credit value
    return None  # Return None if the user is not found


def is_eligible_to_chat(user_id):
    """
    Checks if the user is eligible to chat based on their credit.
    Returns True if credit > 0, otherwise False.
    """
    conn, c = connect_to_db()
    c.execute("SELECT credit FROM users WHERE user_id=?", (user_id,))
    credit = c.fetchone()
    conn.close()

    if credit and credit[0] > 0:
        return True

    return False


def get_partner_id(user_id):
    # Connect to the chatbot database
    conn, c = connect_to_db()
    # If the user is a guest, then search for the host
    c.execute("SELECT user_id FROM users WHERE partner_id=?", (user_id,))
    other_user_id = c.fetchone()
    if not other_user_id:
        # If no user is found, return None
        conn.close()
        return None

    # otherwise, return the other user's id
    other_user_id = other_user_id[0]
    conn.close()

    return other_user_id


def couple(current_user_id):
    # Connect to the chatbot database
    conn, c = connect_to_db()
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
    # Update both users' partner_id to reflect the coupling
    start_chat_time = datetime.datetime.now()
    c.execute(
        "UPDATE users SET partner_id=?, start_chat_time=?, status=? WHERE user_id=?",
        (other_user_id, start_chat_time, UserStatus.COUPLED, current_user_id),
    )
    c.execute(
        "UPDATE users SET partner_id=?, start_chat_time=?, status=? WHERE user_id=?",
        (current_user_id, start_chat_time, UserStatus.COUPLED, other_user_id),
    )

    conn.commit()
    conn.close()

    return other_user_id


def check_user_duration(user_id, min_duration=86400.0):
    # Connect to the chatbot database
    conn, c = connect_to_db()

    c.execute("SELECT start_bot_time FROM users WHERE user_id=?", (user_id,))
    start_bot_time = c.fetchone()
    if not start_bot_time[0]:
        conn.close()
        return True

    start_bot_time = datetime.datetime.fromisoformat(start_bot_time[0])
    duration = datetime.datetime.now() - start_bot_time

    return duration.total_seconds() >= min_duration


def check_chat_duration(user_id, min_duration=300.0):
    # Connect to the chatbot database
    conn, c = connect_to_db()
    # Retrieve the partner_id of the user
    partner_id = get_partner_id(user_id)
    if not partner_id:
        # If the user is not coupled, return None
        return False

    c.execute("SELECT start_chat_time FROM users WHERE user_id=?", (user_id,))
    start_chat_time = c.fetchone()
    if not start_chat_time:
        conn.close()
        return False

    start_chat_time = datetime.datetime.fromisoformat(start_chat_time[0])
    duration = datetime.datetime.now() - start_chat_time

    return duration.total_seconds() >= min_duration


def uncouple(user_id):
    # Connect to the chatbot database
    conn, c = connect_to_db()
    # Retrieve the partner_id of the user
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

    conn.commit()
    conn.close()

    return


def retrieve_users_number():
    # Connect to the chatbot database
    conn, c = connect_to_db()
    # Retrieve the number of users in the users table
    c.execute("SELECT COUNT(*) FROM users")
    total_users_number = c.fetchone()[0]
    # Retrieve the number of users who are currently coupled
    c.execute("SELECT COUNT(*) FROM users WHERE status='coupled'")
    paired_users_number = c.fetchone()[0]
    conn.close()

    return total_users_number, paired_users_number


def reset_users_status():
    # Connect to the chatbot database
    conn, c = connect_to_db()
    # Reset the status of all users to UserStatus.IDLE
    c.execute(
        "UPDATE users SET start_bot_time=?, start_chat_time=?, status=?",
        (
            None,
            None,
            UserStatus.IDLE,
        ),
    )
    conn.commit()
    conn.close()
