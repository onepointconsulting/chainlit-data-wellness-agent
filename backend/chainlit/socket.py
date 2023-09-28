import asyncio
import json
from typing import Any, Dict

from chainlit.action import Action
from chainlit.auth import get_current_user, require_login
from chainlit.client.base import MessageDict
from chainlit.config import config
from chainlit.context import init_ws_context
from chainlit.logger import logger
from chainlit.message import ErrorMessage, Message
from chainlit.server import socket
from chainlit.session import WebsocketSession
from chainlit.telemetry import trace_event
from chainlit.user_session import user_sessions


def restore_existing_session(sid, session_id, emit_fn, ask_user_fn):
    """Restore a session from the sessionId provided by the client."""
    if session := WebsocketSession.get_by_id(session_id):
        session.restore(new_socket_id=sid)
        session.emit = emit_fn
        session.ask_user = ask_user_fn
        trace_event("session_restored")
        return True
    return False


def load_user_env(user_env):
    # Check user env
    if config.project.user_env:
        # Check if requested user environment variables are provided
        if user_env:
            user_env = json.loads(user_env)
            for key in config.project.user_env:
                if key not in user_env:
                    trace_event("missing_user_env")
                    raise ConnectionRefusedError(
                        "Missing user environment variable: " + key
                    )
        else:
            raise ConnectionRefusedError("Missing user environment variables")
    return user_env


@socket.on("connect")
async def connect(sid, environ, auth):
    if not config.code.on_chat_start and not config.code.on_message:
        raise ConnectionRefusedError("No websocket endpoint configured")

    user = None
    token = None
    try:
        # Check if the authentication is required
        if require_login():
            authorization_header = environ.get("HTTP_AUTHORIZATION")
            token = authorization_header.split(" ")[1] if authorization_header else None
            user = await get_current_user(token=token)
    except Exception as e:
        return False

    # Function to send a message to this particular session
    def emit_fn(event, data):
        if session := WebsocketSession.get(sid):
            if session.should_stop:
                session.should_stop = False
                raise InterruptedError("Task stopped by user")
        return socket.emit(event, data, to=sid)

    # Function to ask the user a question
    def ask_user_fn(data, timeout):
        if session := WebsocketSession.get(sid):
            if session.should_stop:
                session.should_stop = False
                raise InterruptedError("Task stopped by user")
        return socket.call("ask", data, timeout=timeout, to=sid)

    session_id = environ.get("HTTP_X_CHAINLIT_SESSION_ID")
    if restore_existing_session(sid, session_id, emit_fn, ask_user_fn):
        return True

    user_env_string = environ.get("HTTP_USER_ENV")
    user_env = load_user_env(user_env_string)

    WebsocketSession(
        id=session_id,
        socket_id=sid,
        emit=emit_fn,
        ask_user=ask_user_fn,
        user_env=user_env,
        user=user,
        token=token,
    )

    trace_event("connection_successful")
    return True


@socket.on("connection_successful")
async def connection_successful(sid):
    context = init_ws_context(sid)
    if context.session.restored:
        return

    if config.code.on_file_upload:
        await context.emitter.enable_file_upload(config.code.on_file_upload_config)

    if config.code.on_chat_start:
        """Call the on_chat_start function provided by the developer."""
        await config.code.on_chat_start()


@socket.on("clear_session")
async def clean_session(sid):
    if session := WebsocketSession.get(sid):
        if config.code.on_chat_end:
            init_ws_context(session)
            """Call the on_chat_end function provided by the developer."""
            await config.code.on_chat_end()
        # Clean up the user session
        if session.id in user_sessions:
            user_sessions.pop(session.id)
        # Clean up the session
        session.delete()


@socket.on("disconnect")
async def disconnect(sid):
    session = WebsocketSession.get(sid)
    if config.code.on_chat_end and session:
        init_ws_context(session)
        """Call the on_chat_end function provided by the developer."""
        await config.code.on_chat_end()

    async def disconnect_on_timeout(sid):
        await asyncio.sleep(config.project.session_timeout)
        if session := WebsocketSession.get(sid):
            # Clean up the user session
            if session.id in user_sessions:
                user_sessions.pop(session.id)
            # Clean up the session
            session.delete()

    asyncio.ensure_future(disconnect_on_timeout(sid))


@socket.on("stop")
async def stop(sid):
    if session := WebsocketSession.get(sid):
        trace_event("stop_task")

        init_ws_context(session)
        await Message(author="System", content="Task stopped by the user.").send()

        session.should_stop = True

        if config.code.on_stop:
            await config.code.on_stop()


async def process_message(session: WebsocketSession, message_dict: MessageDict):
    """Process a message from the user."""
    try:
        context = init_ws_context(session)

        await context.emitter.task_start()
        if config.code.on_message:
            await context.emitter.process_user_message(message_dict)
            message = Message.from_dict(message_dict)
            await config.code.on_message(message.content.strip(), message.id)
    except InterruptedError:
        pass
    except Exception as e:
        logger.exception(e)
        await ErrorMessage(
            author="Error", content=str(e) or e.__class__.__name__
        ).send()
    finally:
        await context.emitter.task_end()


@socket.on("ui_message")
async def message(sid, message):
    """Handle a message sent by the User."""
    session = WebsocketSession.require(sid)
    session.should_stop = False

    await process_message(session, message)


async def process_action(action: Action):
    callback = config.code.action_callbacks.get(action.name)
    if callback:
        await callback(action)
    else:
        logger.warning("No callback found for action %s", action.name)


@socket.on("action_call")
async def call_action(sid, action):
    """Handle an action call from the UI."""
    init_ws_context(sid)

    action = Action(**action)

    await process_action(action)


@socket.on("chat_settings_change")
async def change_settings(sid, settings: Dict[str, Any]):
    """Handle change settings submit from the UI."""
    context = init_ws_context(sid)

    for key, value in settings.items():
        context.session.chat_settings[key] = value

    if config.code.on_settings_update:
        await config.code.on_settings_update(settings)


@socket.on("file_upload")
async def file_upload(sid, files: Any):
    """Handle file upload from the UI."""
    init_ws_context(sid)

    if config.code.on_file_upload:
        await config.code.on_file_upload(files)
