"""安全相关工具：密码哈希、JWT 生成与校验。

密码哈希直接使用 bcrypt 库（不使用 passlib，避免与新版 bcrypt 的兼容问题）。
"""

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.config import get_settings

settings = get_settings()

ALGORITHM = "HS256"


def _truncate(password: str) -> bytes:
    """bcrypt 只处理前 72 字节，超长部分会被静默丢弃，这里显式截断并说明。"""
    return password.encode("utf-8")[:72]


def hash_password(plain_password: str) -> str:
    """生成 bcrypt 密码哈希。"""
    return bcrypt.hashpw(_truncate(plain_password), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """校验明文密码与哈希是否匹配，异常时视为不匹配。"""
    try:
        return bcrypt.checkpw(_truncate(plain_password), hashed_password.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def validate_password_strength(password: str) -> None:
    """密码强度校验：至少 6 位；不满足时抛出 ValueError（调用方转中文提示）。"""
    if len(password) < 6:
        raise ValueError("密码长度至少 6 位")


def create_access_token(subject: str, role: str) -> str:
    """签发 JWT 访问令牌。

    :param subject: 用户 ID 字符串
    :param role: 用户角色（便于前端快速判断，权限仍以数据库为准）
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": str(subject), "role": role, "iat": now, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """解析 JWT，失败时抛出 jwt 异常（由调用方转为 401）。"""
    return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
