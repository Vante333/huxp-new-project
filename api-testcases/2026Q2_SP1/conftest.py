"""PAPI 测试配置与会话级能力探测入口。"""
from __future__ import annotations

import pytest

from framework.config import EnvTruthy, InitializeRuntimeEnv
from framework.reporting import AllureHttpScenarioSteps, ResetAllureAssertionAttachmentCounter

InitializeRuntimeEnv()


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "manual: 需人工/外部系统观测，默认不跑")
    config.addinivalue_line("markers", "needs_extensions_read: 依赖 search/register 返回 extensions")
    config.addinivalue_line("markers", "needs_extensions_write: 依赖 PATCH /v2/memberships/extensions 可用")
    config.addinivalue_line(
        "markers",
        "needs_cross_module_data: PAPI-2515 读侧数据依赖（含注册造数的 doc gap 等；非必等于环境变量探测）",
    )
    config.addinivalue_line(
        "markers",
        "p2515_probe_membership: 仅读探测会籍，需 DP_P2515_PROBE_MEMBERSHIP_ID；"
        "本地默认不收集，需 DP_P2515_INCLUDE_PROBE=1",
    )
    config.addinivalue_line(
        "markers",
        "needs_cross_module_write: PAPI-2515 写链路，注册+entitlements/update+按池 update，会改写沙箱权益数值",
    )
    config.addinivalue_line(
        "markers",
        "needs_p2424_usage_order_id: PAPI-2424 回归用例，依赖环境变量 DP_P2424_USAGE_ORDER_ID（非 MS 开头 usage 订单号）",
    )
def pytest_collection_modifyitems(config: pytest.Config, items: list) -> None:
    """
    本地默认不收集 ``p2515_probe_membership``（避免维护 ``DP_P2515_PROBE_MEMBERSHIP_ID`` 仍出现 Skipped 条）。
    显式开启：``DP_P2515_INCLUDE_PROBE=1``（须同时配置探测会籍 ID）。
    """
    if EnvTruthy("DP_P2515_INCLUDE_PROBE"):
        return
    items[:] = [it for it in items if it.get_closest_marker("p2515_probe_membership") is None]


@pytest.fixture(autouse=True)
def _ResetAllureAssertionAttachmentCounterPerTest() -> None:
    """避免 Allure 中断言附件同名覆盖：每条用例从序号 1 重新计数。"""
    ResetAllureAssertionAttachmentCounter()
    yield


@pytest.fixture
def ScenarioSteps():
    """用例内 HTTP 步骤序号：步骤1/2… 与序列码 S01/S02…，见 ``AllureHttpScenarioSteps``。"""
    return AllureHttpScenarioSteps()


@pytest.fixture(scope="session")
def papi2548_sandbox_flags():
    from papi2548_helpers import BuildSandboxFlags, GetAccessToken, Papi2548SandboxFlags

    try:
        token = GetAccessToken()
    except Exception as exc:
        pytest.skip(f"无法获取 token，跳过会话探测: {exc}")
    flags: Papi2548SandboxFlags = BuildSandboxFlags(token)
    return flags

