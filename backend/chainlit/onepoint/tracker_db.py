from pathlib import Path
from typing import Optional, Generator
from pydantic.dataclasses import dataclass

import os
import sqlite3

from chainlit.logger import logger

ONEPOINT_SQL_LITE_DB = os.getenv("ONEPOINT_SQL_LITE_DB", "/tmp/ONEPOINT_SQL_LITE_DB.db")
TABLE_NAME = "onepoint_activity_log"


class TrackerOperations:
    CONNECTION_START = "connection_start"
    ASK = "ask"
    NEW_MESSAGE = "new_message"
    USER_MESSAGE = "user_message"


@dataclass()
class TrackingRecord:
    user_id: Optional[str]
    session_id: str
    message: str
    operation: str = TrackerOperations.USER_MESSAGE


def execute_query(query: str):
    with sqlite3.connect(ONEPOINT_SQL_LITE_DB) as conn:
        cur = conn.cursor()
        cur.execute(query)
        conn.commit()
        cur.close()


def create_table():
    logger.info("Creating trackingg table ...")
    db_path = Path(ONEPOINT_SQL_LITE_DB)
    if not db_path.exists():
        logger.info(f"{db_path} does not exist.")
        execute_query(
            f"""CREATE TABLE IF NOT EXISTS {TABLE_NAME}
        (id INTEGER PRIMARY KEY, operation TEXT, user_id TEXT, session_id TEXT, message TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)"""
        )
    else:
        logger.info(f"{db_path} already exists.")


def list_activity_log() -> Generator:
    with sqlite3.connect(ONEPOINT_SQL_LITE_DB) as conn:
        cur = conn.cursor()
        data = cur.execute(f"SELECT * from {TABLE_NAME} order by id")
        for row in data:
            yield row


def write_single_record(tracking_record: TrackingRecord):
    with sqlite3.connect(ONEPOINT_SQL_LITE_DB) as conn:
        cur = conn.cursor()
        cur.executemany(
            """INSERT INTO onepoint_activity_log(operation, user_id, session_id, message)
VALUES (?, ?, ?, ?)
""",
            [
                (
                    tracking_record.operation,
                    tracking_record.user_id,
                    tracking_record.session_id,
                    tracking_record.message,
                )
            ],
        )
        cur.close()
