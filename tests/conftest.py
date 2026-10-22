"""pytest 公共夹具：隔离的临时数据库与目录，不污染开发数据。"""

import os
import tempfile
from pathlib import Path

# 必须在导入 app 之前设置环境变量，确保 config/database 使用测试配置
_TMP = Path(tempfile.mkdtemp(prefix="cs_kb_test_"))
os.environ["DATABASE_URL"] = f"sqlite:///{(_TMP / 'test.db').as_posix()}"
os.environ["UPLOAD_DIR"] = str(_TMP / "uploads")
os.environ["VECTOR_STORE_DIR"] = str(_TMP / "vector_store")
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["EMBEDDING_PROVIDER"] = "local"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    """应用测试客户端（session 级，共享同一内存外 SQLite）。"""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def admin(client):
    """注册并登录首个用户（自动成为管理员）。"""
    client.post("/api/auth/register", json={"username": "admin", "password": "admin123"})
    response = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    data = response.json()["data"]
    return {"token": data["access_token"], "username": data["username"], "role": data["role"]}


@pytest.fixture(scope="session")
def user(client):
    """注册并登录第二个用户（普通用户）。"""
    client.post("/api/auth/register", json={"username": "zhangsan", "password": "user123456"})
    response = client.post("/api/auth/login", json={"username": "zhangsan", "password": "user123456"})
    data = response.json()["data"]
    return {"token": data["access_token"], "username": data["username"], "role": data["role"]}


@pytest.fixture()
def admin_headers(admin):
    """管理员鉴权头。"""
    return {"Authorization": f"Bearer {admin['token']}"}


@pytest.fixture()
def user_headers(user):
    """普通用户鉴权头。"""
    return {"Authorization": f"Bearer {user['token']}"}
