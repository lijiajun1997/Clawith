"""WeChat iLink Bot long-poll manager with media (file/image/video) support."""

from __future__ import annotations

import asyncio
import base64
import collections
import json
import hashlib
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx
from loguru import logger
from sqlalchemy import select

from app.database import async_session
from app.models.agent import Agent as AgentModel
from app.models.agent import DEFAULT_CONTEXT_WINDOW_SIZE
from app.models.audit import ChatMessage
from app.models.channel_config import ChannelConfig
from app.services.channel_session import find_or_create_channel_session
from app.services.channel_user_service import channel_user_service
from app.services.channel_commands import (
    detect_and_handle_command,
    register_running_task,
    unregister_running_task,
)
from app.services.wechat_crypto import (
    decrypt_aes_ecb,
    decode_aes_key,
    encode_aes_key_base64,
    encode_aes_key_hex,
    encrypt_aes_ecb,
    generate_aes_key,
)

WECHAT_ILINK_BASE_URL = "https://ilinkai.weixin.qq.com"
WECHAT_CHANNEL_VERSION = "1.0.0"
WECHAT_TEXT_LIMIT = 2000
CDN_BASE_URL = "https://novac2c.cdn.weixin.qq.com/c2c"

# iLink required headers (per SDK)
ILINK_APP_ID = "bot"

def _build_client_version() -> str:
    """Encode WECHAT_CHANNEL_VERSION as uint32 MMNNPP."""
    parts = WECHAT_CHANNEL_VERSION.split(".")
    try:
        major = int(parts[0]) & 0xFF if len(parts) > 0 else 0
        minor = int(parts[1]) & 0xFF if len(parts) > 1 else 0
        patch = int(parts[2]) & 0xFF if len(parts) > 2 else 0
    except (ValueError, IndexError):
        major = minor = patch = 0
    return str((major << 16) | (minor << 8) | patch)

ILINK_APP_CLIENT_VERSION = _build_client_version()

# Cache context_token per (agent_id, user_id) for proactive sends
# Dual-layer: in-memory dict (fast) + Redis (persistent across restarts)
_context_token_cache: dict[tuple[str, str], dict[str, str]] = {}
_WECHAT_CTX_TOKEN_TTL = 86400 * 7  # 7 days in Redis
_WECHAT_CTX_TOKEN_KEY = "wechat:ctx_token:{agent_id}:{user_id}"

# MessageItemType
ITEM_TEXT = 1
ITEM_IMAGE = 2
ITEM_VOICE = 3
ITEM_FILE = 4
ITEM_VIDEO = 5

# MediaType for upload
MEDIA_IMAGE = 1
MEDIA_VIDEO = 2
MEDIA_FILE = 3


class WeChatSessionExpiredError(RuntimeError):
    pass


def random_wechat_uin() -> str:
    value = int.from_bytes(os.urandom(4), "big", signed=False)
    return base64.b64encode(str(value).encode("utf-8")).decode("utf-8")


def build_wechat_headers(token: str, route_tag: str | None = None, *, skip_auth: bool = False) -> dict[str, str]:
    """Build iLink API request headers, matching SDK's auth_headers + _common_headers."""
    headers = {
        "iLink-App-Id": ILINK_APP_ID,
        "iLink-App-ClientVersion": ILINK_APP_CLIENT_VERSION,
    }
    if not skip_auth:
        headers.update({
            "Content-Type": "application/json",
            "AuthorizationType": "ilink_bot_token",
            "Authorization": f"Bearer {token}",
            "X-WECHAT-UIN": random_wechat_uin(),
        })
    if route_tag:
        headers["SKRouteTag"] = route_tag
    return headers


def split_wechat_text(text: str, limit: int = WECHAT_TEXT_LIMIT) -> list[str]:
    remaining = text or ""
    chunks: list[str] = []
    while remaining:
        if len(remaining) <= limit:
            chunks.append(remaining)
            break
        segment = remaining[:limit]
        cut = max(segment.rfind("\n\n"), segment.rfind("\n"), segment.rfind(" "))
        if cut <= 0:
            cut = limit
        chunks.append(remaining[:cut].rstrip())
        remaining = remaining[cut:].lstrip()
    return chunks or [""]


# ─── CDN Download ─────────────────────────────────────────────────


def get_cached_context_token(agent_id: str, user_id: str) -> str | None:
    """Return cached context_token for proactive sends (memory layer only).

    For full lookup with Redis fallback, use `load_context_token()`.
    """
    entry = _context_token_cache.get((str(agent_id), user_id))
    if entry:
        return entry.get("token")
    return None


async def save_context_token(agent_id: str | uuid.UUID, user_id: str, token: str) -> None:
    """Persist context_token to both memory cache and Redis."""
    aid = str(agent_id)
    now_iso = datetime.now(timezone.utc).isoformat()
    entry = {"token": token, "saved_at": now_iso}
    _context_token_cache[(aid, user_id)] = entry

    try:
        from app.core.events import get_redis
        r = await get_redis()
        key = _WECHAT_CTX_TOKEN_KEY.format(agent_id=aid, user_id=user_id)
        await r.hset(key, mapping={"token": token, "saved_at": now_iso})
        await r.expire(key, _WECHAT_CTX_TOKEN_TTL)
    except Exception as exc:
        logger.debug(f"[WeChat] Failed to persist context_token to Redis: {exc}")


async def load_context_token(agent_id: str | uuid.UUID, user_id: str) -> str | None:
    """Load context_token with memory → Redis fallback. Returns token or None."""
    aid = str(agent_id)

    # Memory first
    entry = _context_token_cache.get((aid, user_id))
    if entry:
        return entry.get("token")

    # Redis fallback
    try:
        from app.core.events import get_redis
        r = await get_redis()
        key = _WECHAT_CTX_TOKEN_KEY.format(agent_id=aid, user_id=user_id)
        data = await r.hgetall(key)
        if data and data.get("token"):
            token = data["token"]
            _context_token_cache[(aid, user_id)] = {
                "token": token,
                "saved_at": data.get("saved_at", ""),
            }
            return token
    except Exception as exc:
        logger.debug(f"[WeChat] Failed to load context_token from Redis: {exc}")

    return None


async def cdn_download(encrypt_query_param: str, aes_key_encoded: str | None = None) -> bytes:
    """Download and decrypt a file from WeChat CDN."""
    url = f"{CDN_BASE_URL}/download?encrypted_query_param={quote(encrypt_query_param)}"
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.get(url)
        if resp.status_code >= 400:
            raise RuntimeError(f"CDN download failed: HTTP {resp.status_code}")
        ciphertext = resp.content

    if not aes_key_encoded:
        raise RuntimeError("No AES key for CDN decryption")

    aes_key = decode_aes_key(aes_key_encoded)
    return decrypt_aes_ecb(ciphertext, aes_key)


# ─── CDN Upload ───────────────────────────────────────────────────


async def cdn_upload(
    *,
    token: str,
    base_url: str,
    data: bytes,
    to_user_id: str,
    media_type: int,
    route_tag: str | None = None,
) -> dict[str, Any]:
    """Encrypt, upload to CDN, return CDN media dict for message sending."""
    aes_key = generate_aes_key()
    ciphertext = encrypt_aes_ecb(data, aes_key)
    filekey = os.urandom(16).hex()
    raw_md5 = hashlib.md5(data).hexdigest()

    # Step 1: get upload URL
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{base_url.rstrip('/')}/ilink/bot/getuploadurl",
            headers=build_wechat_headers(token, route_tag=route_tag),
            json={
                "filekey": filekey,
                "media_type": media_type,
                "to_user_id": to_user_id,
                "rawsize": len(data),
                "rawfilemd5": raw_md5,
                "filesize": len(ciphertext),
                "no_need_thumb": True,
                "aeskey": encode_aes_key_hex(aes_key),
                "base_info": {"channel_version": WECHAT_CHANNEL_VERSION},
            },
        )
        if resp.status_code >= 400:
            raise RuntimeError(f"getuploadurl failed: {resp.text[:300]}")
        upload_info = resp.json()

    upload_param = upload_info.get("upload_param")
    if not upload_param:
        raise RuntimeError("getuploadurl did not return upload_param")

    # Step 2: upload encrypted data to CDN
    cdn_url = (
        f"{CDN_BASE_URL}/upload"
        f"?encrypted_query_param={quote(upload_param)}"
        f"&filekey={quote(filekey)}"
    )
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            cdn_url,
            content=ciphertext,
            headers={"Content-Type": "application/octet-stream"},
        )
        if resp.status_code >= 400:
            raise RuntimeError(f"CDN upload failed: HTTP {resp.status_code}")
        encrypt_query_param = resp.headers.get("x-encrypted-param")
        if not encrypt_query_param:
            raise RuntimeError("CDN upload succeeded but x-encrypted-param header missing")

    return {
        "encrypt_query_param": encrypt_query_param,
        "aes_key": encode_aes_key_base64(aes_key),
        "encrypt_type": 1,
        "_encrypted_file_size": len(ciphertext),
    }


# ─── Send Functions ───────────────────────────────────────────────


async def send_wechat_text_message(
    *,
    token: str,
    base_url: str,
    to_user_id: str,
    context_token: str,
    text: str,
    route_tag: str | None = None,
) -> None:
    async with httpx.AsyncClient(timeout=20) as client:
        for chunk in split_wechat_text(text):
            resp = await client.post(
                f"{base_url.rstrip('/')}/ilink/bot/sendmessage",
                headers=build_wechat_headers(token, route_tag=route_tag),
                json={
                    "msg": {
                        "from_user_id": "",
                        "to_user_id": to_user_id,
                        "client_id": f"clawith-wechat:{int(time.time() * 1000)}-{uuid.uuid4().hex[:8]}",
                        "message_type": 2,
                        "message_state": 2,
                        "context_token": context_token,
                        "item_list": [{"type": ITEM_TEXT, "text_item": {"text": chunk}}],
                    },
                    "base_info": {"channel_version": WECHAT_CHANNEL_VERSION},
                },
            )
            if resp.status_code >= 400:
                raise RuntimeError(f"WeChat sendmessage failed: {resp.text[:300]}")


async def send_wechat_file_message(
    *,
    token: str,
    base_url: str,
    to_user_id: str,
    context_token: str,
    file_data: bytes,
    file_name: str,
    route_tag: str | None = None,
) -> None:
    """Upload a file to CDN and send it as a WeChat file message."""
    media = await cdn_upload(
        token=token, base_url=base_url, data=file_data,
        to_user_id=to_user_id, media_type=MEDIA_FILE, route_tag=route_tag,
    )
    msg = {
        "from_user_id": "",
        "to_user_id": to_user_id,
        "client_id": f"clawith-wechat:{int(time.time() * 1000)}-{uuid.uuid4().hex[:8]}",
        "message_type": 2,
        "message_state": 2,
        "context_token": context_token,
        "item_list": [{
            "type": ITEM_FILE,
            "file_item": {
                "media": media,
                "file_name": file_name,
                "len": str(len(file_data)),
            },
        }],
    }
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            f"{base_url.rstrip('/')}/ilink/bot/sendmessage",
            headers=build_wechat_headers(token, route_tag=route_tag),
            json={"msg": msg, "base_info": {"channel_version": WECHAT_CHANNEL_VERSION}},
        )
        if resp.status_code >= 400:
            raise RuntimeError(f"WeChat file sendmessage failed: {resp.text[:300]}")


async def send_wechat_image_message(
    *,
    token: str,
    base_url: str,
    to_user_id: str,
    context_token: str,
    image_data: bytes,
    route_tag: str | None = None,
) -> None:
    """Upload an image to CDN and send it as a WeChat image message."""
    media = await cdn_upload(
        token=token, base_url=base_url, data=image_data,
        to_user_id=to_user_id, media_type=MEDIA_IMAGE, route_tag=route_tag,
    )
    msg = {
        "from_user_id": "",
        "to_user_id": to_user_id,
        "client_id": f"clawith-wechat:{int(time.time() * 1000)}-{uuid.uuid4().hex[:8]}",
        "message_type": 2,
        "message_state": 2,
        "context_token": context_token,
        "item_list": [{
            "type": ITEM_IMAGE,
            "image_item": {
                "media": media,
                "mid_size": media.get("_encrypted_file_size", 0),
            },
        }],
    }
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            f"{base_url.rstrip('/')}/ilink/bot/sendmessage",
            headers=build_wechat_headers(token, route_tag=route_tag),
            json={"msg": msg, "base_info": {"channel_version": WECHAT_CHANNEL_VERSION}},
        )
        if resp.status_code >= 400:
            raise RuntimeError(f"WeChat image sendmessage failed: {resp.text[:300]}")


async def get_wechat_config(
    *,
    token: str,
    base_url: str,
    ilink_user_id: str,
    context_token: str,
    route_tag: str | None = None,
) -> dict[str, Any] | None:
    """Call /ilink/bot/getconfig to retrieve config including typing_ticket.

    Per SDK: POST with {ilink_user_id, context_token, base_info}.
    """
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{base_url.rstrip('/')}/ilink/bot/getconfig",
                headers=build_wechat_headers(token, route_tag=route_tag),
                json={
                    "ilink_user_id": ilink_user_id,
                    "context_token": context_token,
                    "base_info": {"channel_version": WECHAT_CHANNEL_VERSION},
                },
            )
            if resp.status_code >= 400:
                logger.debug(f"[WeChat] getconfig failed: HTTP {resp.status_code}")
                return None
            data = resp.json()
            ret = data.get("ret", 0)
            errcode = data.get("errcode", 0)
            if (isinstance(ret, int) and ret != 0) or (isinstance(errcode, int) and errcode != 0):
                logger.debug(f"[WeChat] getconfig error: ret={ret}, errcode={errcode}")
                return None
            return data
    except Exception as exc:
        logger.debug(f"[WeChat] getconfig failed (non-critical): {exc}")
        return None


async def send_wechat_typing(
    *,
    token: str,
    base_url: str,
    ilink_user_id: str,
    context_token: str,
    route_tag: str | None = None,
) -> bool:
    """Show 'typing...' indicator via /ilink/bot/sendtyping (status=1).

    Calls getconfig first to obtain the typing_ticket.
    Returns True on success, False on failure (best-effort).
    """
    try:
        config = await get_wechat_config(
            token=token, base_url=base_url,
            ilink_user_id=ilink_user_id, context_token=context_token,
            route_tag=route_tag,
        )
        if not config:
            return False
        typing_ticket = config.get("typing_ticket")
        if not typing_ticket:
            return False

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{base_url.rstrip('/')}/ilink/bot/sendtyping",
                headers=build_wechat_headers(token, route_tag=route_tag),
                json={
                    "ilink_user_id": ilink_user_id,
                    "typing_ticket": typing_ticket,
                    "status": 1,
                    "base_info": {"channel_version": WECHAT_CHANNEL_VERSION},
                },
            )
            return resp.status_code < 400
    except Exception as exc:
        logger.debug(f"[WeChat] send_typing failed (non-critical): {exc}")
        return False


async def _stop_typing_bg(token: str, base_url: str, ilink_user_id: str, context_token: str, route_tag: str | None) -> None:
    """Fire-and-forget wrapper: stop typing without blocking the reply."""
    try:
        await stop_wechat_typing(
            token=token, base_url=base_url,
            ilink_user_id=ilink_user_id, context_token=context_token,
            route_tag=route_tag,
        )
    except Exception:
        pass


async def stop_wechat_typing(
    *,
    token: str,
    base_url: str,
    ilink_user_id: str,
    context_token: str,
    route_tag: str | None = None,
) -> bool:
    """Cancel 'typing...' indicator via /ilink/bot/sendtyping (status=2)."""
    try:
        config = await get_wechat_config(
            token=token, base_url=base_url,
            ilink_user_id=ilink_user_id, context_token=context_token,
            route_tag=route_tag,
        )
        if not config:
            return False
        typing_ticket = config.get("typing_ticket")
        if not typing_ticket:
            return False

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{base_url.rstrip('/')}/ilink/bot/sendtyping",
                headers=build_wechat_headers(token, route_tag=route_tag),
                json={
                    "ilink_user_id": ilink_user_id,
                    "typing_ticket": typing_ticket,
                    "status": 2,
                    "base_info": {"channel_version": WECHAT_CHANNEL_VERSION},
                },
            )
            return resp.status_code < 400
    except Exception as exc:
        logger.debug(f"[WeChat] stop_typing failed (non-critical): {exc}")
        return False


# ─── Message Parsing ──────────────────────────────────────────────


def _extract_text(item_list: list[dict[str, Any]] | None) -> str:
    parts: list[str] = []
    for item in item_list or []:
        t = item.get("type")
        if t == ITEM_TEXT:
            ti = item.get("text_item") or {}
            text = (ti.get("text") or ti.get("content") or "").strip()
            if text:
                parts.append(text)
    return "\n".join(parts).strip()


def _describe_item_list(item_list: list[dict[str, Any]] | None) -> str:
    """Return a compact description of item_list for debugging purposes."""
    if not item_list:
        return "empty"
    descs = []
    for item in item_list:
        t = item.get("type")
        keys = sorted(item.keys())
        if t == ITEM_TEXT:
            ti = item.get("text_item") or {}
            txt = (ti.get("text") or ti.get("content") or "")[:50]
            descs.append(f"text(type={t}, keys={keys}, text={txt!r})")
        else:
            descs.append(f"type={t}, keys={keys}")
    return "; ".join(descs)


def _extract_media_info(item_list: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Extract all media items from a message's item_list."""
    media_items: list[dict[str, Any]] = []
    for item in item_list or []:
        t = item.get("type")
        if t == ITEM_IMAGE and item.get("image_item"):
            ii = item["image_item"]
            m = ii.get("media") or {}
            media_items.append({
                "type": "image",
                "encrypt_query_param": m.get("encrypt_query_param", ""),
                "aes_key": ii.get("aeskey") or m.get("aes_key", ""),
                "url": ii.get("url"),
            })
        elif t == ITEM_FILE and item.get("file_item"):
            fi = item["file_item"]
            m = fi.get("media") or {}
            media_items.append({
                "type": "file",
                "encrypt_query_param": m.get("encrypt_query_param", ""),
                "aes_key": m.get("aes_key", ""),
                "file_name": fi.get("file_name", "file.bin"),
                "file_size": fi.get("len"),
            })
        elif t == ITEM_VIDEO and item.get("video_item"):
            vi = item["video_item"]
            m = vi.get("media") or {}
            media_items.append({
                "type": "video",
                "encrypt_query_param": m.get("encrypt_query_param", ""),
                "aes_key": m.get("aes_key", ""),
            })
        elif t == ITEM_VOICE and item.get("voice_item"):
            vi = item["voice_item"]
            m = vi.get("media") or {}
            media_items.append({
                "type": "voice",
                "encrypt_query_param": m.get("encrypt_query_param", ""),
                "aes_key": m.get("aes_key", ""),
                "text": vi.get("text"),
            })
    return media_items


def _agent_base_dir(agent_id: uuid.UUID) -> Path:
    from app.config import get_settings
    settings = get_settings()
    return Path(settings.AGENT_DATA_DIR) / str(agent_id)


async def _download_and_save_media(
    agent_id: uuid.UUID,
    media: dict[str, Any],
) -> str | None:
    """Download a media item from CDN and save to agent workspace. Returns saved path or None."""
    eqp = media.get("encrypt_query_param", "")
    aes_key = media.get("aes_key", "")
    if not eqp:
        return None

    try:
        data = await cdn_download(eqp, aes_key)
    except Exception as exc:
        logger.error(f"[WeChat] CDN download failed: {exc}")
        return None

    base_dir = _agent_base_dir(agent_id)
    media_type = media.get("type", "file")
    file_name = media.get("file_name")

    if not file_name:
        ext_map = {"image": ".png", "video": ".mp4", "voice": ".silk", "file": ".bin"}
        ext = ext_map.get(media_type, ".bin")
        file_name = f"wechat_{media_type}_{int(time.time())}{ext}"

    save_dir = base_dir / "workspace" / "wechat_files"
    save_dir.mkdir(parents=True, exist_ok=True)
    save_path = save_dir / file_name

    # Avoid overwrite: append suffix if exists
    counter = 0
    while save_path.exists():
        stem = Path(file_name).stem
        suffix = Path(file_name).suffix
        counter += 1
        save_path = save_dir / f"{stem}_{counter}{suffix}"

    save_path.write_bytes(data)
    logger.info(f"[WeChat] Saved {media_type} ({len(data)} bytes) to {save_path}")
    return f"workspace/wechat_files/{save_path.name}"


# ─── Message Processing ───────────────────────────────────────────


async def _process_wechat_message(agent_id: uuid.UUID, msg: dict[str, Any], config: ChannelConfig) -> None:
    from app.api.feishu import _call_agent_llm
    from app.services.activity_logger import log_activity

    from_user_id = str(msg.get("from_user_id") or "").strip()
    msg_id = str(msg.get("msg_id") or msg.get("client_msg_id") or "")[:40]
    logger.info(f"[WeChat] Processing msg_id={msg_id} from={from_user_id[:40]} agent={str(agent_id)[:8]}")

    if not from_user_id:
        logger.warning(f"[WeChat] Dropping message — empty from_user_id (msg_id={msg_id})")
        return
    if from_user_id == (config.app_id or "").strip():
        logger.warning(f"[WeChat] Dropping message — from_user_id matches bot's own app_id ({from_user_id[:40]})")
        return

    item_list = msg.get("item_list") or []
    user_text = _extract_text(item_list)
    media_items = _extract_media_info(item_list)

    # Build enhanced text with media info
    saved_paths: list[str] = []
    for media in media_items:
        try:
            saved_path = await _download_and_save_media(agent_id, media)
            if saved_path:
                saved_paths.append(saved_path)
                mtype = media.get("type", "file")
                fname = media.get("file_name", saved_path.split("/")[-1])
                if not user_text:
                    user_text = f"[用户发送了{mtype}: {fname}]"
                else:
                    user_text += f"\n[用户发送了{mtype}: {fname}]"
                user_text += f"\n文件已保存到: {saved_path}"
            else:
                mtype = media.get("type", "file")
                if not user_text:
                    user_text = f"[用户发送了{mtype}]"
                else:
                    user_text += f"\n[用户发送了{mtype}]"
        except Exception as exc:
            logger.error(f"[WeChat] Media download failed, continuing without file: {exc}")
            mtype = media.get("type", "file")
            if not user_text:
                user_text = f"[用户发送了{mtype}（下载失败）]"
            else:
                user_text += f"\n[用户发送了{mtype}（下载失败）]"

    if not user_text:
        logger.warning(f"[WeChat] Dropping message — no text extracted from item_list, agent={str(agent_id)[:8]}, from={from_user_id[:40]}, items={_describe_item_list(item_list)}")
        return

    context_token = str(msg.get("context_token") or "").strip()
    if not context_token:
        logger.warning(f"[WeChat] Missing context_token for agent {agent_id}, message skipped")
        return

    # Cache context_token for proactive file sending via send_channel_file
    await save_context_token(agent_id, from_user_id, context_token)

    async with async_session() as db:
        agent_r = await db.execute(select(AgentModel).where(AgentModel.id == agent_id))
        agent_obj = agent_r.scalar_one_or_none()
        if not agent_obj:
            return

        extra_info = {
            "name": f"WeChat User {from_user_id[:8]}",
            "external_id": from_user_id,
        }

        # Parallel: resolve user + detect magic command
        conv_key = str(msg.get("session_id") or from_user_id).strip()
        conv_id = f"wechat_{conv_key}"

        platform_user, (cmd_handled, cmd_reply, cmd_rewritten) = await asyncio.gather(
            channel_user_service.resolve_channel_user(
                db=db, agent=agent_obj, channel_type="wechat",
                external_user_id=from_user_id, extra_info=extra_info,
            ),
            detect_and_handle_command(
                db, agent_id, user_text, conv_id,
                tenant_id=agent_obj.tenant_id,
                current_model_id=agent_obj.primary_model_id,
            ),
        )
        platform_user_id = platform_user.id

        # ── Magic command detection (/model, /stop, /skill) ──
        cmd_handled, cmd_reply, cmd_rewritten = await detect_and_handle_command(
            db, agent_id, user_text, conv_id,
            tenant_id=agent_obj.tenant_id if agent_obj else None,
            current_model_id=agent_obj.primary_model_id if agent_obj else None,
        )
        if cmd_handled:
            if cmd_reply is not None:
                _cmd_token = str((config.extra_config or {}).get("bot_token") or "").strip()
                _cmd_base_url = str((config.extra_config or {}).get("baseurl") or WECHAT_ILINK_BASE_URL).strip()
                _cmd_route_tag = str((config.extra_config or {}).get("route_tag") or "").strip() or None
                await send_wechat_text_message(
                    token=_cmd_token, base_url=_cmd_base_url, to_user_id=from_user_id,
                    context_token=context_token, text=cmd_reply, route_tag=_cmd_route_tag,
                )
                return
            elif cmd_rewritten is not None:
                user_text = cmd_rewritten

        sess = await find_or_create_channel_session(
            db=db, agent_id=agent_id, user_id=platform_user_id,
            external_conv_id=conv_id, source_channel="wechat",
            first_message_title=user_text[:80],
        )
        session_conv_id = str(sess.id)

        history_r = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.agent_id == agent_id, ChatMessage.conversation_id == session_conv_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(agent_obj.context_window_size or DEFAULT_CONTEXT_WINDOW_SIZE)
        )
        # Build history same as WebSocket: convert tool_call records to assistant summaries
        from app.api.websocket import _build_tool_call_summary
        _history_msgs = list(reversed(history_r.scalars().all()))
        history: list[dict] = []
        _tc_buf: list[dict] = []
        for m in _history_msgs:
            if m.role == "tool_call":
                try:
                    _tc_buf.append(json.loads(m.content))
                except Exception:
                    pass
                continue
            if m.role in ("user", "assistant"):
                if _tc_buf:
                    summary = _build_tool_call_summary(_tc_buf)
                    if summary:
                        history.append({"role": "assistant", "content": summary})
                    _tc_buf.clear()
                history.append({"role": m.role, "content": m.content or ""})
        if _tc_buf:
            summary = _build_tool_call_summary(_tc_buf)
            if summary:
                history.append({"role": "assistant", "content": summary})

        db.add(ChatMessage(
            agent_id=agent_id, user_id=platform_user_id,
            role="user", content=user_text, conversation_id=session_conv_id,
        ))
        sess.last_message_at = datetime.now(timezone.utc)
        await db.commit()

        # Set channel_file_sender so send_channel_file tool can send files back
        from app.services.agent_tools import channel_file_sender as _cfs

        _token = str((config.extra_config or {}).get("bot_token") or "").strip()
        _base_url = str((config.extra_config or {}).get("baseurl") or WECHAT_ILINK_BASE_URL).strip()
        _route_tag = str((config.extra_config or {}).get("route_tag") or "").strip() or None

        async def _wechat_file_sender(file_path, msg: str = ""):
            data = Path(file_path).read_bytes()
            fname = Path(file_path).name
            ext = Path(file_path).suffix.lower()
            if ext in (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"):
                await send_wechat_image_message(
                    token=_token, base_url=_base_url, to_user_id=from_user_id,
                    context_token=context_token, image_data=data, route_tag=_route_tag,
                )
            else:
                await send_wechat_file_message(
                    token=_token, base_url=_base_url, to_user_id=from_user_id,
                    context_token=context_token, file_data=data,
                    file_name=fname, route_tag=_route_tag,
                )
            if msg:
                await send_wechat_text_message(
                    token=_token, base_url=_base_url, to_user_id=from_user_id,
                    context_token=context_token, text=msg, route_tag=_route_tag,
                )

        _cfs_token = _cfs.set(_wechat_file_sender)

        # Fire ACK + typing in background — don't block LLM startup
        _ilink_uid = str((config.extra_config or {}).get("ilink_user_id") or "").strip()

        async def _send_ack_and_typing():
            try:
                await send_wechat_text_message(
                    token=_token, base_url=_base_url, to_user_id=from_user_id,
                    context_token=context_token, text="✓ 已收到，正在思考...", route_tag=_route_tag,
                )
            except Exception as _ack_err:
                logger.warning(f"[WeChat] Failed to send ack message: {_ack_err}")
            if _ilink_uid:
                try:
                    await send_wechat_typing(
                        token=_token, base_url=_base_url, ilink_user_id=_ilink_uid,
                        context_token=context_token, route_tag=_route_tag,
                    )
                except Exception as _typing_err:
                    logger.warning(f"[WeChat] Failed to send typing: {_typing_err}")

        asyncio.create_task(_send_ack_and_typing())

        async def _wechat_on_tool_call(evt: dict):
            """Persist tool_call records so Web UI can display them."""
            if (evt.get("status") or "").lower() != "done":
                return
            try:
                import json as _json_tc
                from app.utils.text import truncate_head_tail
                async with async_session() as _tc_db:
                    _tc_db.add(ChatMessage(
                        agent_id=agent_id,
                        user_id=platform_user_id,
                        role="tool_call",
                        content=_json_tc.dumps({
                            "name": evt.get("name") or "unknown_tool",
                            "args": evt.get("args"),
                            "status": "done",
                            "result": truncate_head_tail(evt.get("result") or "", 500, tail_chars=200),
                        }),
                        conversation_id=session_conv_id,
                    ))
                    await _tc_db.commit()
            except Exception as _tc_err:
                logger.warning(f"[WeChat] Failed to save tool_call: {_tc_err}")

        llm_task = asyncio.ensure_future(_call_agent_llm(
            db=db, agent_id=agent_id, user_text=user_text,
            history=history, user_id=platform_user_id,
            session_id=session_conv_id,
            on_tool_call=_wechat_on_tool_call,
        ))
        register_running_task(conv_id, llm_task)
        try:
            try:
                reply_text = await llm_task
            except asyncio.CancelledError:
                reply_text = "*[Generation stopped by user]*"
                logger.info(f"[WeChat] LLM task cancelled via /stop for conv_id={conv_id}")
        finally:
            _cfs.reset(_cfs_token)
            unregister_running_task(conv_id)

        # Send reply first (per SDK: message before stop_typing)
        await send_wechat_text_message(
            token=_token, base_url=_base_url, to_user_id=from_user_id,
            context_token=context_token, text=reply_text, route_tag=_route_tag,
        )

        # Fire-and-forget: stop typing in background (don't block the user)
        if _ilink_uid:
            asyncio.create_task(
                _stop_typing_bg(_token, _base_url, _ilink_uid, context_token, _route_tag)
            )

        db.add(ChatMessage(
            agent_id=agent_id, user_id=platform_user_id,
            role="assistant", content=reply_text, conversation_id=session_conv_id,
        ))
        sess.last_message_at = datetime.now(timezone.utc)
        await db.commit()

        await log_activity(
            agent_id, "chat_reply",
            f"Replied to WeChat message: {reply_text[:80]}",
            detail={"channel": "wechat", "user_text": user_text[:200], "reply": reply_text[:500]},
        )


# ─── Poll Manager ─────────────────────────────────────────────────


class WeChatPollManager:
    """Manage WeChat iLink long-poll workers per agent."""

    _DEDUP_TTL = 600  # 10 minutes

    def __init__(self) -> None:
        self._tasks: dict[uuid.UUID, asyncio.Task] = {}
        self._connected: dict[uuid.UUID, bool] = {}
        self._processed_ids: collections.deque[str] = collections.deque(maxlen=2000)
        self._dedup_lock = asyncio.Lock()

    async def _is_duplicate(self, dedup_key: str) -> bool:
        """Redis-backed dedup with in-memory fallback. Returns True if duplicate."""
        try:
            from app.core.events import get_redis
            r = await get_redis()
            return not await r.set(f"wechat:dedup:{dedup_key}", "1", nx=True, ex=self._DEDUP_TTL)
        except Exception:
            async with self._dedup_lock:
                if dedup_key in self._processed_ids:
                    return True
                self._processed_ids.append(dedup_key)
                return False

    @staticmethod
    def _build_dedup_key(msg: dict[str, Any]) -> str:
        """Build a time-stable dedup key.

        Uses msg_id if available, otherwise from_user_id + text hash.
        Timestamp intentionally excluded — iLink may deliver the same
        message with different timestamps across getupdates calls.
        """
        mid = msg.get("msg_id") or msg.get("client_msg_id")
        if mid:
            return f"mid:{mid}"

        uid = str(msg.get("from_user_id") or "")[:32]
        text_hash = hashlib.md5(
            _extract_text(msg.get("item_list") or []).encode("utf-8", errors="replace")
        ).hexdigest()[:12]
        return f"{uid}:{text_hash}"

    async def start_client(self, agent_id: uuid.UUID, stop_existing: bool = True) -> None:
        # If task is already running, skip unless explicit stop requested
        existing = self._tasks.get(agent_id)
        if existing and not existing.done():
            if not stop_existing:
                return
        if stop_existing:
            await self.stop_client(agent_id)
        task = asyncio.create_task(self._run_client(agent_id), name=f"wechat-poll-{str(agent_id)[:8]}")
        self._tasks[agent_id] = task
        self._connected[agent_id] = False

    async def stop_client(self, agent_id: uuid.UUID) -> None:
        task = self._tasks.pop(agent_id, None)
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._connected[agent_id] = False
        await self._set_connected(agent_id, False)

    # Stagger delay between consecutive agent connections (seconds)
    _STAGGER_DELAY = 0.5

    async def start_all(self) -> None:
        async with async_session() as db:
            result = await db.execute(
                select(ChannelConfig).where(
                    ChannelConfig.channel_type == "wechat",
                    ChannelConfig.is_configured == True,
                )
            )
            for i, cfg in enumerate(result.scalars().all()):
                if i > 0:
                    await asyncio.sleep(self._STAGGER_DELAY)
                token = str((cfg.extra_config or {}).get("bot_token") or "").strip()
                if token:
                    await self.start_client(cfg.agent_id)

    async def _run_client(self, agent_id: uuid.UUID) -> None:
        retry_delay = 2
        max_retry_delay = 30
        try:
            while True:
                config = await self._load_config(agent_id)
                if not config:
                    logger.info(f"[WeChat] Channel config missing for agent {agent_id}, stopping poller")
                    return

                extra = config.extra_config or {}
                token = str(extra.get("bot_token") or "").strip()
                base_url = str(extra.get("baseurl") or WECHAT_ILINK_BASE_URL).strip()
                route_tag = str(extra.get("route_tag") or "").strip() or None
                cursor = str(extra.get("get_updates_buf") or "")

                if not token:
                    logger.info(f"[WeChat] No bot token for agent {agent_id}, stopping poller")
                    await self._set_connected(agent_id, False)
                    return

                try:
                    data = await self._fetch_updates(token=token, base_url=base_url, cursor=cursor, route_tag=route_tag)
                    self._connected[agent_id] = True
                    await self._set_connected(agent_id, True)
                    if extra.get("session_expired"):
                        await self._update_extra(agent_id, {"session_expired": False})
                    retry_delay = 2

                    new_cursor = str(data.get("get_updates_buf") or "")
                    if new_cursor and new_cursor != cursor:
                        await self._update_extra(agent_id, {"get_updates_buf": new_cursor})

                    msgs = data.get("msgs", []) or []
                    if msgs:
                        logger.info(f"[WeChat] Poll received {len(msgs)} message(s) for agent {str(agent_id)[:8]}")

                    for msg in msgs:
                        dedup_key = self._build_dedup_key(msg)
                        if dedup_key and await self._is_duplicate(dedup_key):
                            logger.debug(f"[WeChat] Skipping duplicate msg: {dedup_key[:60]}")
                            continue
                        try:
                            await _process_wechat_message(agent_id, msg, config)
                        except Exception as exc:
                            logger.error(f"[WeChat] Failed to process message for {agent_id}: {exc}")

                    # Small delay to prevent racing getupdates calls
                    await asyncio.sleep(0.5)
                except WeChatSessionExpiredError:
                    logger.warning(f"[WeChat] Session expired for agent {agent_id}")
                    await self._set_connected(agent_id, False)
                    await self._update_extra(agent_id, {"get_updates_buf": "", "session_expired": True})
                    return
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    self._connected[agent_id] = False
                    await self._set_connected(agent_id, False)
                    logger.error(f"[WeChat] Poll error for {agent_id}: {exc}")
                    await asyncio.sleep(retry_delay)
                    retry_delay = min(retry_delay * 2, max_retry_delay)
        except asyncio.CancelledError:
            await self._set_connected(agent_id, False)
            raise

    async def _fetch_updates(self, *, token: str, base_url: str, cursor: str, route_tag: str | None) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=40) as client:
            resp = await client.post(
                f"{base_url.rstrip('/')}/ilink/bot/getupdates",
                headers=build_wechat_headers(token, route_tag=route_tag),
                json={
                    "get_updates_buf": cursor,
                    "base_info": {"channel_version": WECHAT_CHANNEL_VERSION},
                },
            )
            data = resp.json()
            if resp.status_code >= 400:
                raise RuntimeError(f"WeChat getupdates HTTP {resp.status_code}: {str(data)[:300]}")
            ret = data.get("ret", 0)
            errcode = data.get("errcode", 0)
            if ret == -14 or errcode == -14:
                raise WeChatSessionExpiredError(data.get("errmsg") or "session expired")
            if ret not in (0, None) or errcode not in (0, None):
                raise RuntimeError(data.get("errmsg") or f"WeChat getupdates failed: ret={ret}, errcode={errcode}")
            return data

    async def _load_config(self, agent_id: uuid.UUID) -> ChannelConfig | None:
        async with async_session() as db:
            result = await db.execute(
                select(ChannelConfig).where(
                    ChannelConfig.agent_id == agent_id,
                    ChannelConfig.channel_type == "wechat",
                )
            )
            return result.scalar_one_or_none()

    async def _update_extra(self, agent_id: uuid.UUID, updates: dict[str, Any]) -> None:
        async with async_session() as db:
            result = await db.execute(
                select(ChannelConfig).where(
                    ChannelConfig.agent_id == agent_id,
                    ChannelConfig.channel_type == "wechat",
                )
            )
            config = result.scalar_one_or_none()
            if not config:
                return
            extra = dict(config.extra_config or {})
            extra.update(updates)
            config.extra_config = extra
            await db.commit()

    async def _set_connected(self, agent_id: uuid.UUID, connected: bool) -> None:
        async with async_session() as db:
            result = await db.execute(
                select(ChannelConfig).where(
                    ChannelConfig.agent_id == agent_id,
                    ChannelConfig.channel_type == "wechat",
                )
            )
            config = result.scalar_one_or_none()
            if not config:
                return
            config.is_connected = connected
            await db.commit()


wechat_poll_manager = WeChatPollManager()
