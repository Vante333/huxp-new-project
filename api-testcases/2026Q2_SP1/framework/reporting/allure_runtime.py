from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple

import allure
from requests import Response

JsonDict = Dict[str, Any]

_allureAssertionAttachSeq: int = 0


def ResetAllureAssertionAttachmentCounter() -> None:
    global _allureAssertionAttachSeq
    _allureAssertionAttachSeq = 0


def _BumpAllureAssertionAttachSeq() -> int:
    global _allureAssertionAttachSeq
    _allureAssertionAttachSeq += 1
    return _allureAssertionAttachSeq


def _SanitizeAllureAttachmentNameFragment(text: str, max_len: int = 48) -> str:
    one_line = " ".join(text.split())
    out_chars: List[str] = []
    for ch in one_line[:max_len]:
        if ch == "/":
            out_chars.append("-")
        elif ch in '\\:*?"<>|':
            out_chars.append("_")
        else:
            out_chars.append(ch)
    result = "".join(out_chars).strip()
    return result if result else "assertion"


def AttachJson(name: str, payload: object) -> None:
    allure.attach(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        name=name,
        attachment_type=allure.attachment_type.TEXT,
    )


def AttachAllureRequestMeta(
    *,
    url: str,
    method: str,
    headers: Mapping[str, str],
    json_body: Optional[JsonDict],
) -> None:
    AttachJson(
        "request_meta",
        {
            "url": url,
            "method": method.upper(),
            "headers": dict(headers),
            "json": json_body,
        },
    )


def AttachAllureResponseArtifacts(resp: Response) -> None:
    try:
        parsed: object = resp.json()
        AttachJson("response_body_json", parsed)
    except ValueError:
        allure.attach(
            resp.text[:8000],
            name="response_body_text",
            attachment_type=allure.attachment_type.TEXT,
        )
    allure.attach(
        f"HTTP {resp.status_code}\n",
        name="response_status",
        attachment_type=allure.attachment_type.TEXT,
    )


def RecordAllureAssertionResult(detail: str, *, assertion_title: Optional[str] = None) -> None:
    seq = _BumpAllureAssertionAttachSeq()
    title = assertion_title or "断言结果"
    frag = _SanitizeAllureAttachmentNameFragment(title, max_len=40)
    display_base = f"断言结果_{seq:03d}_{frag}"
    text_detail = detail.strip()
    text_body = text_detail + ("\n" if text_detail else "")
    text_body += "────────\n状态: 通过"
    payload: JsonDict = {
        "seq": seq,
        "assertion_title": title,
        "detail": text_detail,
        "status": "passed",
        "full_text": text_body,
    }
    allure.attach(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        name=display_base + "_结构化.json.txt",
        attachment_type=allure.attachment_type.TEXT,
    )
    allure.attach(
        text_body + "\n",
        name=display_base + "_可读.txt",
        attachment_type=allure.attachment_type.TEXT,
    )


def RunAllureAssertionStep(step_title: str, fn: Callable[[], str]) -> None:
    with allure.step(step_title):
        summary = fn()
        RecordAllureAssertionResult(summary, assertion_title=step_title)


def FormatAllureHttpStepTitle(
    method: str,
    path: str,
    *,
    step_code: Optional[str] = None,
    step_title: Optional[str] = None,
) -> str:
    parts: List[str] = []
    if step_code:
        parts.append(f"[{step_code}]")
    if step_title:
        parts.append(step_title)
    parts.append(f"{method.upper()} {path}")
    return " · ".join(parts)


@dataclass
class AllureHttpScenarioSteps:
    next_index: int = 1

    def Next(self, brief: str) -> Tuple[str, str]:
        index = self.next_index
        self.next_index += 1
        return f"S{index:02d}", f"步骤{index} · {brief}"
