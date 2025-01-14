import logging
import os
from datetime import datetime


class LogHandler(logging.FileHandler):
    def __init__(self):
        # Create the logs directory if it doesn't exist
        os.makedirs("logs", exist_ok=True)

        # Define the log file name with the current date
        log_filename = datetime.now().strftime("logs/logs_%d-%m-%Y.txt")

        # Initialize the parent FileHandler with the log file name
        super().__init__(log_filename, mode="a", encoding="utf-8")

    def emit(self, record):
        """Override emit to write newest logs at the top."""
        try:
            # Format the log entry
            log_entry = self.format(record) + "\n"

            # Write the log entry to the top of the file
            if os.path.exists(self.baseFilename):
                with open(self.baseFilename, "r+", encoding="utf-8") as file:
                    content = file.read()
                    file.seek(0, 0)
                    file.write(log_entry.rstrip("\r\n") + "\n" + content)
            else:
                # If the file doesn't exist, create it and write the log entry
                with open(self.baseFilename, "w", encoding="utf-8") as file:
                    file.write(log_entry)
        except Exception:
            self.handleError(record)
