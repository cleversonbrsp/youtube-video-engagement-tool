"""
YouTube API v3 client with OAuth 2.0 authentication.
Handles videos.rate (like) and commentThreads.insert (comment).
"""

import re
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]
TOKEN_PATH = Path(__file__).parent / "token.json"
CREDENTIALS_PATH = Path(__file__).parent / "client_secret.json"
API_SERVICE_NAME = "youtube"
API_VERSION = "v3"
OAUTH_PORT = 8080  # Deve coincidir com o URI de redirect do cliente Web


def extract_video_id(url: str) -> str | None:
    """Extract video ID from common YouTube URL formats."""
    patterns = [
        r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/|youtube\.com/v/)([a-zA-Z0-9_-]{11})",
        r"^([a-zA-Z0-9_-]{11})$",
    ]
    for pattern in patterns:
        match = re.search(pattern, url.strip())
        if match:
            return match.group(1)
    return None


def get_authenticated_service() -> tuple:
    """
    Build YouTube API service using OAuth 2.0.
    Returns (youtube_service, channel_id, channel_title) or raises on failure.
    """
    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_PATH.exists():
                raise FileNotFoundError(
                    f"Arquivo de credenciais não encontrado: {CREDENTIALS_PATH}\n"
                    "Baixe o client_secret.json do Google Cloud Console e salve como client_secret.json"
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_PATH), SCOPES
            )
            creds = flow.run_local_server(port=OAUTH_PORT)
        with open(TOKEN_PATH, "w") as token:
            token.write(creds.to_json())

    youtube = build(API_SERVICE_NAME, API_VERSION, credentials=creds)
    channel_id, channel_title = _get_channel_info(youtube)
    return youtube, channel_id, channel_title


def _get_channel_info(youtube) -> tuple[str, str]:
    """Get the authenticated user's YouTube channel ID and title."""
    response = youtube.channels().list(part="id,snippet", mine=True).execute()
    items = response.get("items", [])
    if not items:
        raise RuntimeError(
            "Conta não possui canal YouTube associado. "
            "Verifique se a conta está vinculada ao YouTube."
        )
    item = items[0]
    return item["id"], item["snippet"]["title"]


def rate_video(youtube, video_id: str, rating: str = "like") -> None:
    """
    Rate a video (like/dislike/none).
    Raises HttpError on API failure.
    """
    youtube.videos().rate(id=video_id, rating=rating).execute()


def _get_video_channel_id(youtube, video_id: str) -> str | None:
    """Get the channel ID of the video uploader. Returns None if unavailable."""
    try:
        response = (
            youtube.videos()
            .list(id=video_id, part="snippet")
            .execute()
        )
        items = response.get("items", [])
        if not items:
            return None
        return items[0]["snippet"].get("channelId")
    except HttpError:
        return None


def insert_comment(youtube, video_id: str, text: str, fallback_channel_id: str = "", verbose: bool = False) -> dict:
    """
    Insert a top-level comment on a video.
    Uses video uploader's channelId (required by API). Falls back to commenter's channel if fetch fails.
    Returns the commentThread resource.
    Raises HttpError on API failure.
    """
    video_channel = _get_video_channel_id(youtube, video_id)
    channel_id = video_channel or fallback_channel_id
    if verbose and not video_channel and fallback_channel_id:
        print(f"    [INFO] Usando canal fallback (não foi possível obter canal do vídeo)")
    if verbose:
        print(f"    [INFO] channelId para comentário: {channel_id[:20]}...")
    if not channel_id:
        raise ValueError(
            f"Não foi possível obter o canal do vídeo {video_id}. "
            "O vídeo pode ser privado ou ter sido removido."
        )
    body = {
        "snippet": {
            "channelId": channel_id,
            "videoId": video_id,
            "topLevelComment": {
                "snippet": {
                    "textOriginal": text,
                }
            },
        }
    }
    response = (
        youtube.commentThreads()
        .insert(part="snippet", body=body)
        .execute()
    )
    return response
