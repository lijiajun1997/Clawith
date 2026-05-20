"""File upload API for chat — saves files to agent workspace, returns path only."""

import base64
import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Form
from loguru import logger
from app.core.security import get_current_user
from app.models.user import User
from app.config import get_settings

router = APIRouter(prefix="/chat", tags=["chat"])

_settings = get_settings()
WORKSPACE_ROOT = Path(_settings.AGENT_DATA_DIR)

MAX_UPLOAD_SIZE = 20 * 1024 * 1024  # 20 MB

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}

MIME_MAP = {
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".gif": "image/gif", ".webp": "image/webp", ".bmp": "image/bmp",
}


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    agent_id: str = Form(""),
    current_user: User = Depends(get_current_user),
):
    """Upload a file for chat context. Saves to agent workspace/uploads/ and returns path."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename")

    ext = os.path.splitext(file.filename)[1].lower()

    # Stream-read with size guard
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > MAX_UPLOAD_SIZE:
            raise HTTPException(status_code=413, detail=f"File too large (max {MAX_UPLOAD_SIZE // (1024*1024)}MB)")
        chunks.append(chunk)
    content = b"".join(chunks)

    # Save to workspace
    workspace_path = ""
    if agent_id:
        uploads_dir = WORKSPACE_ROOT / agent_id / "workspace" / "uploads"
        uploads_dir.mkdir(parents=True, exist_ok=True)
        save_path = uploads_dir / file.filename
        if save_path.exists():
            stem = save_path.stem
            suffix = save_path.suffix
            counter = 1
            while save_path.exists():
                save_path = uploads_dir / f"{stem}_{counter}{suffix}"
                counter += 1
        save_path.write_bytes(content)
        workspace_path = f"workspace/uploads/{save_path.name}"
    else:
        fallback_dir = Path("/tmp/clawith_uploads")
        fallback_dir.mkdir(exist_ok=True)
        file_id = str(uuid.uuid4())[:8]
        save_path = fallback_dir / f"{file_id}_{file.filename}"
        save_path.write_bytes(content)

    # Only generate base64 for images (vision models)
    is_image = ext in IMAGE_EXTENSIONS
    image_data_url = ""
    if is_image:
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Image too large (max 10MB)")
        mime = MIME_MAP.get(ext, "image/png")
        b64 = base64.b64encode(content).decode("ascii")
        image_data_url = f"data:{mime};base64,{b64}"

    logger.info(f"[Upload] {file.filename} ({len(content)} bytes) -> {workspace_path}")

    return {
        "filename": file.filename,
        "saved_filename": save_path.name,
        "size": len(content),
        "extracted_text": "",
        "workspace_path": workspace_path,
        "is_image": is_image,
        "image_data_url": image_data_url,
    }
