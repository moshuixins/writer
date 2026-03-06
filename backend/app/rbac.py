from __future__ import annotations

ROLE_ADMIN = "admin"
ROLE_WRITER = "writer"

PERMISSION_DEFINITIONS = [
    {"code": "accounts:read", "name": "查看账户", "description": "查看账户、用户、角色和邀请码信息"},
    {"code": "accounts:write", "name": "管理账户", "description": "管理账户、用户、角色和邀请码"},
    {"code": "books:read", "name": "查看书籍学习", "description": "查看书籍学习任务和导入记录"},
    {"code": "books:write", "name": "管理书籍学习", "description": "发起书籍学习和导入任务"},
    {"code": "chat:read", "name": "查看会话", "description": "查看写作会话和消息"},
    {"code": "chat:write", "name": "写作对话", "description": "创建和发送写作会话消息"},
    {"code": "documents:read", "name": "查看文档", "description": "查看导出文档和历史"},
    {"code": "documents:write", "name": "管理文档", "description": "导出和保存文档"},
    {"code": "materials:read", "name": "查看素材", "description": "查看和搜索素材"},
    {"code": "materials:write", "name": "管理素材", "description": "上传、编辑和删除素材"},
    {"code": "preferences:read", "name": "查看偏好", "description": "查看用户偏好与设置"},
    {"code": "preferences:write", "name": "管理偏好", "description": "修改用户偏好与设置"},
]

ALL_PERMISSION_CODES = [item["code"] for item in PERMISSION_DEFINITIONS]

SYSTEM_ROLE_DEFINITIONS = [
    {
        "code": ROLE_ADMIN,
        "name": "管理员",
        "description": "账户管理员，可管理本账户内的用户、角色、邀请码和业务资源。",
        "permissions": list(ALL_PERMISSION_CODES),
    },
    {
        "code": ROLE_WRITER,
        "name": "写作人员",
        "description": "写作用户，可使用聊天、素材、文档、偏好和书籍学习功能。",
        "permissions": [
            "books:read",
            "books:write",
            "chat:read",
            "chat:write",
            "documents:read",
            "documents:write",
            "materials:read",
            "materials:write",
            "preferences:read",
            "preferences:write",
        ],
    },
]