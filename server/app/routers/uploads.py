"""用户上传的图片（日记配图等）。

设计取舍：
- 鉴权：仅登录用户可上传，文件落到 `server/uploads/records/{user_id}/` 下；
  读取由 main.py 的 `/uploads` 静态挂载暴露。文件名用 uuid，路径不可枚举，
  demo / 自托管场景可接受；生产需再叠加签名 URL 或防盗链。
- 安全：校验 content-type 在白名单内 + 大小上限，避免任意文件上传；
  文件名由服务端生成（uuid + 真实扩展名），杜绝路径穿越与覆盖。
"""
import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from ..config import BACKEND_DIR
from ..deps import get_current_user
from ..models import User

router = APIRouter(prefix="/api/upload", tags=["upload"])

UPLOAD_ROOT = os.path.join(BACKEND_DIR, "uploads", "records")

_ALLOWED = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/gif": "gif",
    "image/webp": "webp",
}
_MAX_BYTES = 10 * 1024 * 1024  # 10MB


@router.post("/image", status_code=201)
async def upload_image(
    file: UploadFile = File(...),
    current: User = Depends(get_current_user),
):
    ext = _ALLOWED.get(file.content_type)
    if not ext:
        raise HTTPException(status_code=400, detail="仅支持 jpg/png/gif/webp 图片")

    data = await file.read()
    if len(data) > _MAX_BYTES:
        raise HTTPException(status_code=413, detail="图片不能超过 10MB")

    user_dir = os.path.join(UPLOAD_ROOT, str(current.id))
    os.makedirs(user_dir, exist_ok=True)
    fn = f"{uuid.uuid4().hex}.{ext}"
    with open(os.path.join(user_dir, fn), "wb") as f:
        f.write(data)

    return {"url": f"/uploads/records/{current.id}/{fn}"}
