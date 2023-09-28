import asyncio
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional, Union

if TYPE_CHECKING:
    from chainlit.message import Message
    from chainlit.types import AskResponse

from chainlit.client.cloud import AppUser, PersistedAppUser, chainlit_client


class BaseSession:
    """Base object."""

    def __init__(
        self,
        # Id of the session
        id: str,
        # Logged-in user informations
        user: Optional[Union["AppUser", "PersistedAppUser"]],
        # Logged-in user token
        token: Optional[str],
        user_env: Optional[Dict[str, str]],
        # Last message at the root of the chat
        root_message: Optional["Message"] = None,
        # User specific environment variables. Empty if no user environment variables are required.
    ):
        self.user = user
        self.token = token
        self.root_message = root_message
        self.user_env = user_env or {}

        self.id = id
        self.conversation_id: Optional[str] = None

        self.chat_settings: Dict[str, Any] = {}

        self.lock = asyncio.Lock()

    async def get_conversation_id(self) -> Optional[str]:
        if not chainlit_client:
            return None

        if isinstance(self, HTTPSession):
            tags = ["api"]
        else:
            tags = ["chat"]

        if not self.conversation_id:
            async with self.lock:
                app_user_id = (
                    self.user.id if isinstance(self.user, PersistedAppUser) else None
                )
                self.conversation_id = await chainlit_client.create_conversation(
                    app_user_id=app_user_id, tags=tags
                )

        return self.conversation_id


class HTTPSession(BaseSession):
    """Internal HTTP session object. Used to consume Chainlit through API (no websocket)."""

    def __init__(
        self,
        # Id of the session
        id: str,
        # Logged-in user informations
        user: Optional[Union["AppUser", "PersistedAppUser"]],
        # Logged-in user token
        token: Optional[str],
        user_env: Optional[Dict[str, str]],
        # Last message at the root of the chat
        root_message: Optional["Message"] = None,
        # User specific environment variables. Empty if no user environment variables are required.
    ):
        super().__init__(
            id=id, user=user, token=token, user_env=user_env, root_message=root_message
        )


class WebsocketSession(BaseSession):
    """Internal web socket session object.

    A socket id is an ephemeral id that can't be used as a session id
    (as it is for instance regenerated after each reconnection).

    The Session object store an internal mapping between socket id and
    a server generated session id, allowing to persists session
    between socket reconnection but also retrieving a session by
    socket id for convenience.
    """

    def __init__(
        self,
        # Id from the session cookie
        id: str,
        # Associated socket id
        socket_id: str,
        # Function to emit a message to the user
        emit: Callable[[str, Any], None],
        # Function to ask the user a question
        ask_user: Callable[[Any, Optional[int]], Union["AskResponse", None]],
        # User specific environment variables. Empty if no user environment variables are required.
        user_env: Dict[str, str],
        # Logged-in user informations
        user: Optional[Union["AppUser", "PersistedAppUser"]],
        # Logged-in user token
        token: Optional[str],
        # Last message at the root of the chat
        root_message: Optional["Message"] = None,
    ):
        super().__init__(
            id=id, user=user, token=token, user_env=user_env, root_message=root_message
        )

        self.socket_id = socket_id
        self.ask_user = ask_user
        self.emit = emit

        self.should_stop = False
        self.restored = False

        ws_sessions_id[self.id] = self
        ws_sessions_sid[socket_id] = self

    def restore(self, new_socket_id: str):
        """Associate a new socket id to the session."""
        ws_sessions_sid.pop(self.socket_id, None)
        ws_sessions_sid[new_socket_id] = self
        self.socket_id = new_socket_id
        self.restored = True

    def delete(self):
        """Delete the session."""
        ws_sessions_sid.pop(self.socket_id, None)
        ws_sessions_id.pop(self.id, None)

    @classmethod
    def get(cls, socket_id: str):
        """Get session by socket id."""
        return ws_sessions_sid.get(socket_id)

    @classmethod
    def get_by_id(cls, session_id: str):
        """Get session by session id."""
        return ws_sessions_id.get(session_id)

    @classmethod
    def require(cls, socket_id: str):
        """Throws an exception if the session is not found."""
        if session := cls.get(socket_id):
            return session
        raise ValueError("Session not found")


ws_sessions_sid: Dict[str, WebsocketSession] = {}
ws_sessions_id: Dict[str, WebsocketSession] = {}
