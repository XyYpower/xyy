"""V4.1 安全与正确性修复的单元测试。

覆盖：
- Pydantic email 校验
"""

import pytest

pytestmark = pytest.mark.asyncio


# ── Email 校验 ──────────────────────


async def test_update_profile_email_validation():
    """验证 UpdateProfileRequest 邮箱格式校验。"""
    from pydantic import ValidationError
    from app.schemas.auth import UpdateProfileRequest

    # 正常邮箱
    req = UpdateProfileRequest(email="user@example.com")
    assert req.email == "user@example.com"

    # None 邮箱
    req = UpdateProfileRequest(email=None)
    assert req.email is None

    # 空字符串转为 None
    req = UpdateProfileRequest(email="   ")
    assert req.email is None

    # 缺少 @ 的邮箱
    with pytest.raises(ValidationError, match="邮箱格式不正确"):
        UpdateProfileRequest(email="invalid-email")

    # 缺少域名后缀
    with pytest.raises(ValidationError, match="邮箱格式不正确"):
        UpdateProfileRequest(email="user@")

    # 正常邮箱带子域名
    req = UpdateProfileRequest(email="user@sub.example.com")
    assert req.email == "user@sub.example.com"

    # 带空格的邮箱应该被 trim
    req = UpdateProfileRequest(email="  user@example.com  ")
    assert req.email == "user@example.com"
