from entitlements_helpers import (
    get_access_token,
    create_membership,
    get_entitlements_details,
    get_entitlements_search,
    update_entitlements,
)


def test_entitlements_update_flow_for_tiered_membership():
    """
    端到端自动化场景，把你给的 curl 串起来：

    1）获取 token
    2）创建会籍
    3）details/search 查看初始权益
    4）update tier=3 的买点
    5）update tier=1 的 quantity + usageRestriction
    6）再次 details/search 校验基础结构
    """
    token = get_access_token()

    # 1. 创建会籍，拿到 membershipId
    membership_id = create_membership(token)

    # 2. 初始权益：details + search
    details_before = get_entitlements_details(token, membership_id, module="3")
    search_before = get_entitlements_search(token, membership_id)

    assert details_before.get("membershipId") == membership_id
    assert "entitlements" in details_before
    assert "scopeType" in details_before

    # search 响应结构可能与 details 不同，这里只做关键字段存在性校验
    assert "scopeType" in search_before

    # 3. 更新 tier=3 买点（买点权益）
    update_resp_tier3 = update_entitlements(
        token,
        membership_id=membership_id,
        module="3",
        purchased_quantity=5,
        tier=3,
    )
    assert "scopeType" in update_resp_tier3

    # 4. 更新 tier=1 quantity + usageRestriction（共享/非共享权益）
    update_resp_tier1 = update_entitlements(
        token,
        membership_id=membership_id,
        module="3",
        quantity=1,
        usage_restriction=3,
        tier=1,
    )
    assert "scopeType" in update_resp_tier1

    # 5. 更新后再次查询，验证结构 & 关键字段存在
    details_after = get_entitlements_details(token, membership_id, module="3")
    search_after = get_entitlements_search(token, membership_id)

    assert details_after.get("membershipId") == membership_id
    assert "entitlements" in details_after
    assert "scopeType" in details_after
    assert "scopeType" in search_after

    # TODO：如果你有「会籍权益分级」文档中 module=3 的具体点数配置，
    # 可以在这里补充更精确的断言（如共享权益=3 点、买点变化=5 点等），
    # 让该用例完全对齐文档里的测试分析点。

