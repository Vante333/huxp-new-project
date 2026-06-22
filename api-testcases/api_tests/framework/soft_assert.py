"""
Local Offer 套件软断言：E2E 中途断言失败仍继续后续 HTTP，用例末尾一次性汇总。

与 ``P2515E2ESoftAssert`` 同构；通过 ``ContextVar`` 在 ``local_offer_epass`` / ``local_offers`` 用例内生效。
"""
from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Callable, List, Optional, TypeVar

import allure
import pytest
from _pytest.outcomes import Failed

_T = TypeVar("_T")

_ACTIVE: ContextVar[Optional["LocalOfferE2ESoftAssert"]] = ContextVar(
    "local_offer_soft_assert",
    default=None,
)


@dataclass
class LocalOfferE2ESoftAssert:
    """软断言容器：捕获 ``AssertionError`` / ``pytest.fail``，不中断用例主流程。"""

    errors: List[str] = field(default_factory=list)

    def Run(self, label: str, fn: Callable[[], None]) -> None:
        """在 Allure 子步骤 ``label`` 下执行 ``fn``；失败仅记录。"""
        with allure.step(label):
            try:
                fn()
            except (AssertionError, Failed) as exc:
                self.errors.append(f"{label}\n{exc}")

    def Record(self, message: str) -> None:
        """记录非断言类失败说明。"""
        self.errors.append(message)

    def RaiseIfAnyFailure(
        self,
        *,
        header: str = "Local Offer 用例已跑完，下列断言未通过（后续步骤已继续执行）：",
    ) -> None:
        """若存在记录则 ``pytest.fail`` 汇总输出。"""
        if not self.errors:
            return
        pytest.fail(header + "\n\n" + "\n\n---\n\n".join(self.errors))


def GetActiveLocalOfferSoftAssert() -> Optional[LocalOfferE2ESoftAssert]:
    return _ACTIVE.get()


def SetActiveLocalOfferSoftAssert(soft: Optional[LocalOfferE2ESoftAssert]) -> object:
    return _ACTIVE.set(soft)


def ResetActiveLocalOfferSoftAssert(token: object) -> None:
    _ACTIVE.reset(token)


def LocalOfferFailOrRecord(message: str) -> None:
    """``pytest.fail`` 的软断言感知版本：活跃时记入列表并继续。"""
    soft = GetActiveLocalOfferSoftAssert()
    if soft is None:
        pytest.fail(message)
    soft.Record(message)


def RunWithSoftCapture(label: str, fn: Callable[[], _T], *, fallback: Callable[[], _T]) -> _T:
    """执行 ``fn``；软断言活跃且失败时返回 ``fallback()``。"""
    try:
        return fn()
    except (AssertionError, Failed) as exc:
        soft = GetActiveLocalOfferSoftAssert()
        if soft is None:
            raise
        soft.errors.append(f"{label}\n{exc}")
        return fallback()


def RunSoftAwareAllureAssertionStep(step_title: str, fn: Callable[[], str]) -> None:
    """与 ``RunAllureAssertionStep`` 同构；软断言活跃时失败不向外抛。"""
    from framework.reporting.allure_runtime import RecordAllureAssertionResult

    soft = GetActiveLocalOfferSoftAssert()
    with allure.step(step_title):
        try:
            summary = fn()
        except (AssertionError, Failed) as exc:
            if soft is None:
                raise
            soft.errors.append(f"{step_title}\n{exc}")
            allure.attach(
                str(exc),
                name="soft_assert_failed",
                attachment_type=allure.attachment_type.TEXT,
            )
            return
        RecordAllureAssertionResult(summary, assertion_title=step_title)


__all__ = [
    "GetActiveLocalOfferSoftAssert",
    "LocalOfferE2ESoftAssert",
    "LocalOfferFailOrRecord",
    "ResetActiveLocalOfferSoftAssert",
    "RunSoftAwareAllureAssertionStep",
    "RunWithSoftCapture",
    "SetActiveLocalOfferSoftAssert",
]
