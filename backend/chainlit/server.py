import glob
import json
import mimetypes
import urllib.parse
from typing import Optional, Union

from chainlit.oauth_providers import get_oauth_provider
from chainlit.secret import random_secret

mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("text/css", ".css")

import asyncio
import os
import webbrowser
from contextlib import asynccontextmanager
from pathlib import Path

from chainlit.auth import create_jwt, get_configuration, get_current_user
from chainlit.client.acl import is_conversation_author
from chainlit.client.cloud import AppUser, PersistedAppUser, chainlit_client
from chainlit.config import (
    APP_ROOT,
    BACKEND_ROOT,
    DEFAULT_HOST,
    PACKAGE_ROOT,
    config,
    load_module,
    reload_config,
)
from chainlit.logger import logger
from chainlit.markdown import get_markdown_str
from chainlit.playground.config import get_llm_providers
from chainlit.telemetry import trace_event
from chainlit.types import (
    CompletionRequest,
    DeleteConversationRequest,
    GetConversationsRequest,
    Theme,
    UpdateFeedbackRequest,
)
from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi_socketio import SocketManager
from starlette.middleware.cors import CORSMiddleware
from typing_extensions import Annotated
from watchfiles import awatch


@asynccontextmanager
async def lifespan(app: FastAPI):
    host = config.run.host
    port = config.run.port

    if host == DEFAULT_HOST:
        url = f"http://localhost:{port}"
    else:
        url = f"http://{host}:{port}"

    logger.info(f"Your app is available at {url}")

    if not config.run.headless:
        # Add a delay before opening the browser
        await asyncio.sleep(1)
        webbrowser.open(url)

    watch_task = None
    stop_event = asyncio.Event()

    if config.run.watch:

        async def watch_files_for_changes():
            extensions = [".py"]
            files = ["chainlit.md", "config.toml"]
            async for changes in awatch(config.root, stop_event=stop_event):
                for change_type, file_path in changes:
                    file_name = os.path.basename(file_path)
                    file_ext = os.path.splitext(file_name)[1]

                    if file_ext.lower() in extensions or file_name.lower() in files:
                        logger.info(
                            f"File {change_type.name}: {file_name}. Reloading app..."
                        )

                        try:
                            reload_config()
                        except Exception as e:
                            logger.error(f"Error reloading config: {e}")
                            break

                        # Reload the module if the module name is specified in the config
                        if config.run.module_name:
                            try:
                                load_module(config.run.module_name)
                            except Exception as e:
                                logger.error(f"Error reloading module: {e}")
                                break

                        await socket.emit("reload", {})

                        break

        watch_task = asyncio.create_task(watch_files_for_changes())

    try:
        yield
    finally:
        if watch_task:
            try:
                stop_event.set()
                watch_task.cancel()
                await watch_task
            except asyncio.exceptions.CancelledError:
                pass

        # Force exit the process to avoid potential AnyIO threads still running
        os._exit(0)


def get_build_dir():
    local_build_dir = os.path.join(PACKAGE_ROOT, "frontend", "dist")
    packaged_build_dir = os.path.join(BACKEND_ROOT, "frontend", "dist")
    if os.path.exists(local_build_dir):
        return local_build_dir
    elif os.path.exists(packaged_build_dir):
        return packaged_build_dir
    else:
        raise FileNotFoundError("Built UI dir not found")


build_dir = get_build_dir()

app = FastAPI(lifespan=lifespan)

app.mount("/public", StaticFiles(directory="public", check_dir=False), name="public")
app.mount(
    "/assets",
    StaticFiles(
        packages=[("chainlit", os.path.join(build_dir, "assets"))],
        follow_symlink=config.project.follow_symlink,
    ),
    name="assets",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Define max HTTP data size to 100 MB
max_message_size = 100 * 1024 * 1024

socket = SocketManager(
    app,
    cors_allowed_origins=[],
    async_mode="asgi",
    max_http_buffer_size=max_message_size,
)


# -------------------------------------------------------------------------------
#                               HTTP HANDLERS
# -------------------------------------------------------------------------------


def get_html_template():
    PLACEHOLDER = "<!-- TAG INJECTION PLACEHOLDER -->"
    JS_PLACEHOLDER = "<!-- JS INJECTION PLACEHOLDER -->"
    CSS_PLACEHOLDER = "<!-- CSS INJECTION PLACEHOLDER -->"
    CUSTOM_JS_PLACEHOLDER = "<!-- CUSTOM JS INJECTION PLACEHOLDER -->"

    default_url = "https://github.com/Chainlit/chainlit"
    url = config.ui.github or default_url

    tags = f"""<title>{config.ui.name}</title>
    <meta name="description" content="{config.ui.description}">
    <meta property="og:type" content="website">
    <meta property="og:title" content="{config.ui.name}">
    <meta property="og:description" content="{config.ui.description}">
    <meta property="og:image" content="https://chainlit-cloud.s3.eu-west-3.amazonaws.com/logo/chainlit_banner.png">
    <meta property="og:url" content="{url}">"""

    js = f"""<script>{f"window.theme = {json.dumps(config.ui.theme.to_dict())}; " if config.ui.theme else ""}</script>"""

    css = None
    if config.ui.custom_css:
        css = (
            f"""<link rel="stylesheet" type="text/css" href="{config.ui.custom_css}">"""
        )

    custom_js = None
    if config.ui.custom_js:
        custom_js = (
            f"""<script src="{config.ui.custom_js}"></script>"""
        )

    index_html_file_path = os.path.join(build_dir, "index.html")

    with open(index_html_file_path, "r", encoding="utf-8") as f:
        content = f.read()
        content = content.replace(PLACEHOLDER, tags)
        if js:
            content = content.replace(JS_PLACEHOLDER, js)
        if css:
            content = content.replace(CSS_PLACEHOLDER, css)
        if custom_js:
            content = content.replace(CUSTOM_JS_PLACEHOLDER, custom_js)
        return content


@app.get("/auth/config")
async def auth(request: Request):
    return get_configuration()


@app.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    if not config.code.password_auth_callback:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No auth_callback defined"
        )

    app_user = await config.code.password_auth_callback(
        form_data.username, form_data.password
    )

    if not app_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="credentialssignin",
        )
    access_token = create_jwt(app_user)
    if chainlit_client:
        await chainlit_client.create_app_user(app_user=app_user)
    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@app.post("/auth/header")
async def header_auth(request: Request):
    if not config.code.header_auth_callback:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No header_auth_callback defined",
        )

    app_user = await config.code.header_auth_callback(request.headers)

    if not app_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )

    access_token = create_jwt(app_user)
    if chainlit_client:
        await chainlit_client.create_app_user(app_user=app_user)
    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@app.get("/auth/oauth/{provider_id}")
async def oauth_login(provider_id: str, request: Request):
    if config.code.oauth_callback is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No oauth_callback defined",
        )

    provider = get_oauth_provider(provider_id)
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider {provider_id} not found",
        )

    random = random_secret(32)

    params = urllib.parse.urlencode(
        {
            "client_id": provider.client_id,
            "redirect_uri": f"{request.url}/callback",
            "state": random,
            **provider.authorize_params,
        }
    )
    response = RedirectResponse(
        url=f"{provider.authorize_url}?{params}",
    )
    response.set_cookie("oauth_state", random, httponly=True, max_age=3 * 60)
    return response


@app.get("/auth/oauth/{provider_id}/callback")
async def oauth_callback(
    provider_id: str,
    request: Request,
    error: Optional[str] = None,
    code: Optional[str] = None,
    state: Optional[str] = None,
):
    if config.code.oauth_callback is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No oauth_callback defined",
        )

    provider = get_oauth_provider(provider_id)
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider {provider_id} not found",
        )

    if error:
        params = urllib.parse.urlencode(
            {
                "error": error,
            }
        )
        response = RedirectResponse(
            # FIXME: redirect to the right frontend base url to improve the dev environment
            url=f"/login?{params}",
        )
        return response

    if not code or not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing code or state",
        )

    # Check the state from the oauth provider against the browser cookie
    oauth_state = request.cookies.get("oauth_state")
    if oauth_state != state:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )

    url = request.url.replace(query="").__str__()
    token = await provider.get_token(code, url)

    (raw_user_data, default_app_user) = await provider.get_user_info(token)

    app_user = await config.code.oauth_callback(
        provider_id, token, raw_user_data, default_app_user
    )

    if not app_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )

    access_token = create_jwt(app_user)
    if chainlit_client:
        await chainlit_client.create_app_user(app_user=app_user)

    params = urllib.parse.urlencode(
        {
            "access_token": access_token,
            "token_type": "bearer",
        }
    )
    response = RedirectResponse(
        # FIXME: redirect to the right frontend base url to improve the dev environment
        url=f"/login/callback?{params}",
    )
    response.delete_cookie("oauth_state")
    return response


@app.post("/completion")
async def completion(
    request: CompletionRequest,
    current_user: Annotated[
        Union[AppUser, PersistedAppUser], Depends(get_current_user)
    ],
):
    """Handle a completion request from the prompt playground."""

    providers = get_llm_providers()

    try:
        provider = [p for p in providers if p.id == request.prompt.provider][0]
    except IndexError:
        raise HTTPException(
            status_code=404,
            detail=f"LLM provider '{request.prompt.provider}' not found",
        )

    trace_event("pp_create_completion")
    response = await provider.create_completion(request)

    return response


@app.get("/project/llm-providers")
async def get_providers(
    current_user: Annotated[Union[AppUser, PersistedAppUser], Depends(get_current_user)]
):
    """List the providers."""
    trace_event("pp_get_llm_providers")
    providers = get_llm_providers()
    providers = [p.to_dict() for p in providers]
    return JSONResponse(content={"providers": providers})


@app.get("/project/settings")
async def project_settings(
    current_user: Annotated[Union[AppUser, PersistedAppUser], Depends(get_current_user)]
):
    """Return project settings. This is called by the UI before the establishing the websocket connection."""
    return JSONResponse(
        content={
            "ui": config.ui.to_dict(),
            "userEnv": config.project.user_env,
            "dataPersistence": config.data_persistence,
            "markdown": get_markdown_str(config.root),
        }
    )


@app.put("/message/feedback")
async def update_feedback(
    request: Request,
    update: UpdateFeedbackRequest,
    current_user: Annotated[
        Union[AppUser, PersistedAppUser], Depends(get_current_user)
    ],
):
    """Update the human feedback for a particular message."""

    # todo check that message belong to a user's conversation

    if not chainlit_client:
        raise HTTPException(status_code=400, detail="Data persistence is not enabled")

    await chainlit_client.set_human_feedback(
        message_id=update.messageId,
        feedback=update.feedback,
        feedbackComment=update.feedbackComment,
    )
    return JSONResponse(content={"success": True})


@app.post("/project/conversations")
async def get_user_conversations(
    request: Request,
    payload: GetConversationsRequest,
    current_user: Annotated[
        Union[AppUser, PersistedAppUser], Depends(get_current_user)
    ],
):
    """Get the conversations page by page."""
    # Only show the current user conversations

    if not chainlit_client:
        raise HTTPException(status_code=400, detail="Data persistence is not enabled")

    payload.filter.username = current_user.username
    res = await chainlit_client.get_conversations(payload.pagination, payload.filter)
    return JSONResponse(content=res.to_dict())


@app.get("/project/conversation/{conversation_id}")
async def get_conversation(
    request: Request,
    conversation_id: str,
    current_user: Annotated[
        Union[AppUser, PersistedAppUser], Depends(get_current_user)
    ],
):
    """Get a specific conversation."""

    if not chainlit_client:
        raise HTTPException(status_code=400, detail="Data persistence is not enabled")

    await is_conversation_author(current_user.username, conversation_id)

    res = await chainlit_client.get_conversation(conversation_id)
    return JSONResponse(content=res)


@app.get("/project/conversation/{conversation_id}/element/{element_id}")
async def get_conversation_element(
    request: Request,
    conversation_id: str,
    element_id: str,
    current_user: Annotated[
        Union[AppUser, PersistedAppUser], Depends(get_current_user)
    ],
):
    """Get a specific conversation element."""

    if not chainlit_client:
        raise HTTPException(status_code=400, detail="Data persistence is not enabled")

    await is_conversation_author(current_user.username, conversation_id)

    res = await chainlit_client.get_element(conversation_id, element_id)
    return JSONResponse(content=res)


@app.delete("/project/conversation")
async def delete_conversation(
    request: Request,
    payload: DeleteConversationRequest,
    current_user: Annotated[
        Union[AppUser, PersistedAppUser], Depends(get_current_user)
    ],
):
    """Delete a conversation."""

    if not chainlit_client:
        raise HTTPException(status_code=400, detail="Data persistence is not enabled")

    conversation_id = payload.conversationId

    await is_conversation_author(current_user.username, conversation_id)

    await chainlit_client.delete_conversation(conversation_id)
    return JSONResponse(content={"success": True})


@app.get("/files/{filename:path}")
async def serve_file(
    filename: str,
    current_user: Annotated[
        Union[AppUser, PersistedAppUser], Depends(get_current_user)
    ],
):
    base_path = Path(config.project.local_fs_path).resolve()
    file_path = (base_path / filename).resolve()

    # Check if the base path is a parent of the file path
    if base_path not in file_path.parents:
        raise HTTPException(status_code=400, detail="Invalid filename")

    if file_path.is_file():
        return FileResponse(file_path)
    else:
        raise HTTPException(status_code=404, detail="File not found")


@app.get("/favicon")
async def get_favicon():
    custom_favicon_path = os.path.join(APP_ROOT, "public", "favicon.*")
    files = glob.glob(custom_favicon_path)

    if files:
        favicon_path = files[0]
    else:
        favicon_path = os.path.join(build_dir, "favicon.svg")

    media_type, _ = mimetypes.guess_type(favicon_path)

    return FileResponse(favicon_path, media_type=media_type)


@app.get("/logo")
async def get_logo(theme: Optional[Theme] = Query(Theme.light)):
    theme_value = theme.value if theme else Theme.light.value
    logo_path = None

    public_path = os.path.join(APP_ROOT, "public", f"logo_{theme_value}.*")
    assets_path = os.path.join(build_dir, "assets", f"logo_{theme_value}*.*")
    print("public_path", public_path)
    print("assets_path", assets_path)
    for path in [
        public_path,
        assets_path,
    ]:
        files = glob.glob(path)

        if files:
            logo_path = files[0]
            break

    if not logo_path:
        raise HTTPException(
            status_code=404, detail=f"Missing default logo: {logo_path}"
        )
    media_type, _ = mimetypes.guess_type(logo_path)

    return FileResponse(logo_path, media_type=media_type)


def register_wildcard_route_handler():
    @app.get("/{path:path}")
    async def serve(request: Request, path: str):
        html_template = get_html_template()
        """Serve the UI files."""
        response = HTMLResponse(content=html_template, status_code=200)

        print("build_dir", build_dir)

        return response


import chainlit.socket  # noqa
