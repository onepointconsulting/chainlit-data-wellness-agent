import asyncio
import uuid
from contextvars import ContextVar
from typing import TYPE_CHECKING, Dict, Optional, Union

from chainlit.session import HTTPSession, WebsocketSession
from lazify import LazyProxy

if TYPE_CHECKING:
    from chainlit.client.cloud import AppUser, PersistedAppUser
    from chainlit.emitter import BaseChainlitEmitter
    from chainlit.message import Message


class ChainlitContextException(Exception):
    def __init__(self, msg="Chainlit context not found", *args, **kwargs):
        super().__init__(msg, *args, **kwargs)


class ChainlitContext:
    loop: asyncio.AbstractEventLoop
    emitter: "BaseChainlitEmitter"
    session: Union["HTTPSession", "WebsocketSession"]

    def __init__(self, session: Union["HTTPSession", "WebsocketSession"]):
        from chainlit.emitter import BaseChainlitEmitter, ChainlitEmitter

        self.loop = asyncio.get_running_loop()
        self.session = session
        if isinstance(self.session, HTTPSession):
            self.emitter = BaseChainlitEmitter(self.session)
        elif isinstance(self.session, WebsocketSession):
            self.emitter = ChainlitEmitter(self.session)


context_var: ContextVar[ChainlitContext] = ContextVar("chainlit")


def init_ws_context(session_or_sid: Union[WebsocketSession, str]) -> ChainlitContext:
    if not isinstance(session_or_sid, WebsocketSession):
        session = WebsocketSession.require(session_or_sid)
    else:
        session = session_or_sid
    context = ChainlitContext(session)
    context_var.set(context)
    return context


def init_http_context(
    user: Optional[Union["AppUser", "PersistedAppUser"]] = None,
    auth_token: Optional[str] = None,
    user_env: Optional[Dict[str, str]] = None,
) -> ChainlitContext:
    session = HTTPSession(
        id=str(uuid.uuid4()),
        token=auth_token,
        user=user,
        user_env=user_env,
    )
    context = ChainlitContext(session)
    context_var.set(context)
    return context


def get_context() -> ChainlitContext:
    try:
        return context_var.get()
    except LookupError:
        raise ChainlitContextException()


context: ChainlitContext = LazyProxy(get_context, enable_cache=False)
