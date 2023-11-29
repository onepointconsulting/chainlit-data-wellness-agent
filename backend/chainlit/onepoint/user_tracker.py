from typing import Optional, Generator
from pathlib import Path

from chainlit.logger import logger
from chainlit.onepoint.tracker_db import (
    write_single_record,
    create_table,
    TrackingRecord,
    TrackerOperations,
)


def track_message(
    operation: str, user_id: Optional[str], session_id: str, message: str
):
    logger.info(f"{operation} - {user_id} - {session_id} :: {message}")
    write_single_record(
        TrackingRecord(
            operation=operation, user_id=user_id, session_id=session_id, message=message
        )
    )


def track_message_dict(
    operation: str, user_id: Optional[str], session_id: str, message: dict
):
    logger.info(f"{operation} - {user_id} - {session_id} :: {message}")
    content = str(message)
    if "msg" in message:
        content = message["msg"].get("content", f"Empty message: {content}")
    write_single_record(
        TrackingRecord(
            operation=operation, user_id=user_id, session_id=session_id, message=content
        )
    )


create_table()

if __name__ == "__main__":

    from chainlit.onepoint.tracker_db import list_activity_log
    # track_message(TrackerOperations.CONNECTION_START, "1", "1231231231", "Test")
    logger.info("Printing content")
    for row in list_activity_log():
        logger.info(row)
