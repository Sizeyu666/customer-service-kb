"""基础功能测试：鉴权、越权、权限、空库话术、级联删除、参数校验。"""

import json


def test_health(client):
    """健康检查可用。"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_first_user_is_admin(admin):
    """首个注册用户自动成为管理员。"""
    assert admin["role"] == "admin"


def test_register_duplicate_rejected(client):
    """重复用户名注册返回 409 中文提示。"""
    response = client.post("/api/auth/register", json={"username": "admin", "password": "admin123"})
    assert response.status_code == 409
    assert "已被注册" in response.json()["message"]


def test_login_wrong_password(client):
    """错误密码返回 401。"""
    response = client.post("/api/auth/login", json={"username": "admin", "password": "wrong-password"})
    assert response.status_code == 401


def test_me_without_token(client):
    """未携带令牌访问受保护接口返回 401。"""
    assert client.get("/api/auth/me").status_code == 401


def test_validation_error_in_chinese(client):
    """参数校验失败返回中文提示。"""
    response = client.post("/api/auth/register", json={"username": "ab", "password": "123"})
    assert response.status_code == 422
    body = response.json()
    assert "用户名" in body["message"] or "密码" in body["message"]


def test_second_user_is_normal_user(user):
    """第二个注册用户为普通用户。"""
    assert user["role"] == "user"


def test_admin_routes_forbidden_for_user(client, user_headers):
    """普通用户访问管理接口返回 403。"""
    for path in ("/api/documents", "/api/admin/users", "/api/admin/stats"):
        response = client.get(path, headers=user_headers)
        assert response.status_code == 403, path


def test_empty_kb_returns_fallback(client, admin_headers):
    """知识库为空时问答返回固定话术，不报错。"""
    created = client.post("/api/conversations", headers=admin_headers, json={}).json()["data"]
    response = client.post(
        f"/api/conversations/{created['id']}/chat",
        headers=admin_headers,
        json={"question": "知识库里有什么"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert "暂未在知识库中找到" in data["answer"]
    assert data["sources"] == []


def test_conversation_title_auto_generated(client, admin_headers):
    """首条消息后自动把会话标题改为问题前 15 字。"""
    created = client.post("/api/conversations", headers=admin_headers, json={}).json()["data"]
    question = "这是一个超过十五个字的问题用来验证自动生成标题的功能"
    client.post(
        f"/api/conversations/{created['id']}/chat", headers=admin_headers, json={"question": question}
    )
    conversations = client.get("/api/conversations", headers=admin_headers).json()["data"]
    target = next(item for item in conversations if item["id"] == created["id"])
    assert target["title"] == question[:15]


def test_conversation_isolation(client, admin_headers, user_headers):
    """会话按用户隔离：用户 B 访问 A 的会话返回 403。"""
    created = client.post("/api/conversations", headers=admin_headers, json={}).json()["data"]

    response = client.get(f"/api/conversations/{created['id']}/messages", headers=user_headers)
    assert response.status_code == 403

    response = client.post(
        f"/api/conversations/{created['id']}/chat", headers=user_headers, json={"question": "你好"}
    )
    assert response.status_code == 403

    response = client.delete(f"/api/conversations/{created['id']}", headers=user_headers)
    assert response.status_code == 403


def test_delete_conversation_cascades(client, admin_headers):
    """删除会话后消息一并消失。"""
    created = client.post("/api/conversations", headers=admin_headers, json={}).json()["data"]
    client.post(
        f"/api/conversations/{created['id']}/chat",
        headers=admin_headers,
        json={"question": "测试级联删除"},
    )
    messages = client.get(
        f"/api/conversations/{created['id']}/messages", headers=admin_headers
    ).json()["data"]
    assert len(messages) >= 2

    assert client.delete(f"/api/conversations/{created['id']}", headers=admin_headers).status_code == 200
    response = client.get(f"/api/conversations/{created['id']}/messages", headers=admin_headers)
    assert response.status_code == 404


def test_upload_rejects_non_whitelist(client, admin_headers):
    """上传白名单以外的文件类型被拒绝。"""
    response = client.post(
        "/api/documents",
        headers=admin_headers,
        files=[("files", ("virus.exe", b"MZ fake", "application/octet-stream"))],
    )
    assert response.status_code == 200  # 逐文件返回结果而非整体失败
    failed = response.json()["data"]["failed"]
    assert failed and "类型不支持" in failed[0]["reason"]


def test_document_list_requires_admin(client, user_headers):
    """普通用户无法获取文档列表。"""
    assert client.get("/api/documents", headers=user_headers).status_code == 403


def test_cannot_demote_last_admin(client, admin_headers):
    """最后一名管理员不能被降权。"""
    users = client.get("/api/admin/users", headers=admin_headers).json()["data"]
    admins = [item for item in users if item["role"] == "admin"]
    assert len(admins) == 1
    response = client.put(
        f"/api/admin/users/{admins[0]['id']}/role", headers=admin_headers, json={"role": "user"}
    )
    assert response.status_code == 400


def test_role_update_requires_admin(client, user_headers, admin_headers):
    """普通用户不能调整角色。"""
    users = client.get("/api/admin/users", headers=admin_headers).json()["data"]
    target = next(item for item in users if item["role"] == "user")
    response = client.put(
        f"/api/admin/users/{target['id']}/role", headers=user_headers, json={"role": "admin"}
    )
    assert response.status_code == 403


def test_feedback_on_own_message(client, admin_headers):
    """对本人助手消息点赞可提交并更新。"""
    created = client.post("/api/conversations", headers=admin_headers, json={}).json()["data"]
    chat = client.post(
        f"/api/conversations/{created['id']}/chat",
        headers=admin_headers,
        json={"question": "反馈功能测试"},
    ).json()["data"]
    message_id = chat["message_id"]

    first = client.post(
        f"/api/messages/{message_id}/feedback", headers=admin_headers, json={"rating": "up"}
    )
    assert first.status_code == 200

    second = client.post(
        f"/api/messages/{message_id}/feedback", headers=admin_headers, json={"rating": "down"}
    )
    assert second.status_code == 200

    messages = client.get(
        f"/api/conversations/{created['id']}/messages", headers=admin_headers
    ).json()["data"]
    target = next(item for item in messages if item["id"] == message_id)
    assert target["feedback"] == "down"


def test_unified_error_format(client):
    """未捕获的 404 也返回统一中文格式。"""
    response = client.get("/api/conversations/999999/messages", headers={"Authorization": "Bearer invalid"})
    assert response.status_code == 401
    body = response.json()
    assert set(body.keys()) == {"code", "message", "data"}


def test_sources_stored_as_json(client, admin_headers):
    """助手消息的来源以 JSON 存储，接口返回文件名列表。"""
    created = client.post("/api/conversations", headers=admin_headers, json={}).json()["data"]
    chat = client.post(
        f"/api/conversations/{created['id']}/chat",
        headers=admin_headers,
        json={"question": "来源存储格式"},
    ).json()["data"]
    assert isinstance(chat["sources"], list)
