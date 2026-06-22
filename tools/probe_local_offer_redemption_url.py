"""CLI 入口：轮询 Local Offer 各网点 redemptionUrl（逻辑与 pytest 探测用例一致）。

用法（PowerShell）::

    $env:PYTHONPATH = (Resolve-Path "api-testcases\\api_tests").Path
    $env:DP_PROFILE = "canary"
    python tools/probe_local_offer_redemption_url.py

结果写入 ``reports/local-offer-redemption-url-probe.json``，并打印 Markdown 摘要。
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict
from pathlib import Path

from clients import GetAccessTokenForEpass
from framework.config import InitializeRuntimeEnv
from framework.reporting import AllureHttpScenarioSteps
from services.local_offer_epass_service import (
    FormatRedemptionUrlProbeSummaryMarkdown,
    ProbeLocalOfferRedemptionUrlCatalog,
)


def _RepoRoot() -> Path:
    return Path(__file__).resolve().parents[1]


def _Probe() -> None:
    InitializeRuntimeEnv()
    token = GetAccessTokenForEpass()
    steps = AllureHttpScenarioSteps()
    catalog = ProbeLocalOfferRedemptionUrlCatalog(
        token,
        steps,
        language=os.getenv("DP_LO_EPASS_PROBE_LANGUAGE", "").strip() or None,
    )
    summary = FormatRedemptionUrlProbeSummaryMarkdown(
        catalog,
        language=os.getenv("DP_LO_EPASS_PROBE_LANGUAGE", "").strip() or None,
    )
    print(summary)

    out_path = _RepoRoot() / "reports" / "local-offer-redemption-url-probe.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "resourceCount": catalog.ResourceCount,
        "availabilityOkPairCount": catalog.AvailabilityOkPairCount,
        "probedOrderCount": catalog.ProbedOrderCount,
        "withRedemptionUrl": [asdict(r) for r in catalog.WithRedemptionUrl],
        "results": [asdict(r) for r in catalog.Results],
    }
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"\n[saved] {out_path}")


if __name__ == "__main__":
    _Probe()
