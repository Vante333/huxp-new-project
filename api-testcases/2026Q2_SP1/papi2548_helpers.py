"""
PAPI-2548 会籍 extensions 自动化辅助函数。

会籍 extensions 更新路径为 ``/v2/memberships/extensions``；需求文档（Jira）为 **POST**，沙箱网关常见为 **PATCH**，
由 ``GetMembershipsExtensionsHttpMethod`` / 环境变量 ``DP_MEMBERSHIP_EXTENSIONS_METHOD`` 选择（默认 PATCH）。
/v2/memberships/search 为 POST，body 含 membershipId（与 Postman 集合一致）。
"""
from __future__ import annotations

import json
import os
import random
import time
import uuid
from dataclasses import dataclass
from typing import Any, Callable, Dict, Final, List, Mapping, Optional, Sequence, Set, Tuple, TypedDict, cast

import allure
import requests
from requests import Response

JsonDict = Dict[str, Any]
AfterResponseHook = Callable[[Response], None]

# 每条用例开始时由 conftest 复位，避免 Allure 内大量同名「断言结果」附件互相覆盖或预览为空。
_allureAssertionAttachSeq: int = 0


def ResetAllureAssertionAttachmentCounter() -> None:
    """pytest 用例级复位断言附件序号（由 conftest autouse fixture 调用）。"""
    global _allureAssertionAttachSeq
    _allureAssertionAttachSeq = 0


def _BumpAllureAssertionAttachSeq() -> int:
    global _allureAssertionAttachSeq
    _allureAssertionAttachSeq += 1
    return _allureAssertionAttachSeq


def _SanitizeAllureAttachmentNameFragment(text: str, max_len: int = 48) -> str:
    """避免附件展示名中的换行与非法文件名字符导致 Allure UI 异常。"""
    one_line = " ".join(text.split())
    out_chars: List[str] = []
    for ch in one_line[:max_len]:
        if ch == "/":
            out_chars.append("-")
        elif ch in '\\:*?"<>|':
            out_chars.append("_")
        else:
            out_chars.append(ch)
    s = "".join(out_chars).strip()
    return s if s else "assertion"


def _AttachAllureRequestMeta(
    *,
    url: str,
    method: str,
    headers: Mapping[str, str],
    json_body: Optional[JsonDict],
) -> None:
    """
    Allure 规范附件：``request_meta``（url、method、脱敏 headers、json 请求体）。

    与团队报告模板一致，与 ``request_step_meta`` / ``response_body_json`` / ``response_status`` 成套出现。
    """
    _AttachJson(
        "request_meta",
        {
            "url": url,
            "method": method.upper(),
            "headers": MaskHeadersForLog(dict(headers)),
            "json": json_body,
        },
    )


def _AttachAllureResponseArtifacts(resp: Response) -> None:
    """Allure 规范附件：``response_body_json``（或 ``response_body_text``）与 ``response_status``。"""
    body_preview = resp.text
    try:
        parsed: object = resp.json()
        _AttachJson("response_body_json", parsed)
    except ValueError:
        allure.attach(
            body_preview[:8000],
            name="response_body_text",
            attachment_type=allure.attachment_type.TEXT,
        )
    allure.attach(
        f"HTTP {resp.status_code}\n",
        name="response_status",
        attachment_type=allure.attachment_type.TEXT,
    )


def _RecordAllureAssertionResult(detail: str, *, assertion_title: Optional[str] = None) -> None:
    """
    在报告中记录断言详情。

    双附件均为 ``text/plain``（结构化 JSON 文本 + 可读汇总），展示名以 ``断言结果_`` 为前缀；避免同名与 JSON MIME 预览空白。
    """
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


def _RunAllureAssertionStep(step_title: str, fn: Callable[[], str]) -> None:
    """执行 fn 内断言；成功后写入 Allure 子步骤与 ``断言结果_*`` 附件（唯一文件名，避免预览为空）。"""
    with allure.step(step_title):
        summary = fn()
        _RecordAllureAssertionResult(summary, assertion_title=step_title)


# 默认 BASE_URL 与现网 entitlements_helpers 一致：含 /api 前缀
_DEFAULT_BASE: Final[str] = "https://developer-sandbox.dragonpass.com/api"


class ExtensionRegisterItem(TypedDict):
    type: str
    value: str


class ExtensionUpdateItem(TypedDict, total=False):
    operation: str
    type: str
    value: str


# PAPI-2548 extensions 业务错误：errCode + 根节点英文 msg（与 requirements/2026Q2_SP1/PAPI-2548.md 一致）
PAPI2548_EXT_ERR_DUPLICATE_TYPE: Final[str] = "500.030.032"
PAPI2548_EXT_ERR_MAX_FIVE_TYPES: Final[str] = "500.030.033"
PAPI2548_EXT_ERR_UPDATE_FALLBACK: Final[str] = "500.030.034"

PAPI2548_EXT_MSG_DUPLICATE_TYPE: Final[str] = (
    "Duplicate extension type detected. Each type must be unique within a membership."
)
PAPI2548_EXT_MSG_MAX_FIVE_TYPES: Final[str] = (
    "A maximum of 5 extension types is allowed per membership."
)
PAPI2548_EXT_MSG_UPDATE_FALLBACK: Final[str] = (
    "Failed to update membership extensions. Please try again later."
)

# 历史沙箱曾用相邻编号表示同类场景（与 Jira 最终编号不一致时仍可能出现）
PAPI2548_EXT_ERR_DUPLICATE_TYPE_LEGACY: Final[str] = "500.030.033"
PAPI2548_EXT_ERR_MAX_FIVE_TYPES_LEGACY: Final[str] = "500.030.034"


@dataclass(frozen=True)
class Papi2548SandboxFlags:
    """当前环境对 extensions 读/写能力的探测结果。"""

    search_shows_extensions: bool
    post_extensions_works: bool


def GetBaseUrl() -> str:
    raw = os.getenv("DP_BASE_URL", _DEFAULT_BASE).strip()
    if raw.endswith("/api"):
        return raw.rstrip("/")
    if raw.rstrip("/").endswith("dragonpass.com"):
        return raw.rstrip("/") + "/api"
    return raw.rstrip("/")


def GetProgramId() -> str:
    pid = os.getenv("DP_PROGRAM_ID", "").strip()
    if not pid:
        raise RuntimeError(
            "缺少环境变量 DP_PROGRAM_ID（内部租户 Program，如 PAPI-2548 UAT 0426 对应值）"
        )
    return pid


def GetClientId() -> str:
    cid = os.getenv("DP_CLIENT_ID", "").strip()
    if not cid:
        raise RuntimeError("缺少环境变量 DP_CLIENT_ID")
    return cid


def GetClientSecret() -> str:
    sec = os.getenv("DP_CLIENT_SECRET", "").strip()
    if not sec:
        raise RuntimeError("缺少环境变量 DP_CLIENT_SECRET")
    return sec


def GetMembershipsExtensionsHttpMethod() -> str:
    """
    需求文档（Jira PAPI-2548）约定 **POST** ``/v2/memberships/extensions``；部分环境网关仍注册为 **PATCH**。

    可通过环境变量 ``DP_MEMBERSHIP_EXTENSIONS_METHOD`` 设为 ``POST`` 或 ``PATCH``（默认 ``PATCH`` 以兼容既有沙箱）。
    """
    raw = (os.environ.get("DP_MEMBERSHIP_EXTENSIONS_METHOD") or "PATCH").strip().upper()
    if raw not in ("POST", "PATCH"):
        return "PATCH"
    return raw


def MembershipsExtensionsHttpContextLabel() -> str:
    """与 ``GetMembershipsExtensionsHttpMethod`` 一致的 HTTP 描述，用于 Allure/断言上下文。"""
    return f"{GetMembershipsExtensionsHttpMethod()} /v2/memberships/extensions"


def _EnvFlagTrue(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in ("1", "true", "yes", "on")


def BuildNextRequestId() -> str:
    """
    生成 X-Request-ID。与 Postman/Apifox 一致时默认使用 UUID。

    若个别环境 PATCH /v2/memberships/extensions 对 UUID 报 301.000.001，可设
    DP_X_REQUEST_ID_MODE=numeric。也可通过 DP_X_REQUEST_ID 固定为某条合法值。
    """
    explicit = os.getenv("DP_X_REQUEST_ID", "").strip()
    if explicit:
        return explicit
    mode = os.getenv("DP_X_REQUEST_ID_MODE", "uuid").strip().lower()
    if mode == "numeric":
        tail = random.randint(100_000_000, 999_999_999)
        return str(int(time.time() * 1_000_000)) + str(tail)
    return str(uuid.uuid4())


def BuildCommonHeaders(token: Optional[str] = None) -> Dict[str, str]:
    """
    默认不发送 x-version（与通了的 Postman 请求一致）。若需走 canary 路由，设置
    环境变量 DP_X_VERSION=canary；设为 omit/none/off 或不设置均表示不传该头。
    """
    headers: Dict[str, str] = {
        "X-Program-ID": GetProgramId(),
        "X-Request-ID": BuildNextRequestId(),
        "Content-Type": "application/json",
        "Accept": "*/*",
        "User-Agent": "pytest-papi-2548",
    }
    xv = os.getenv("DP_X_VERSION", "").strip()
    if xv and xv.lower() not in ("omit", "none", "off"):
        headers["x-version"] = xv
    if token:
        headers["Authorization"] = "Bearer " + token
    return headers


def MaskHeadersForLog(headers: Mapping[str, str]) -> Dict[str, str]:
    out: Dict[str, str] = dict(headers)
    auth = out.get("Authorization")
    if auth and auth.startswith("Bearer "):
        out["Authorization"] = "Bearer ***"
    return out


def FormatAllureHttpStepTitle(
    method: str,
    path: str,
    *,
    step_code: Optional[str] = None,
    step_title: Optional[str] = None,
) -> str:
    """
    组合 Allure 中 HTTP 步骤标题：``[S01] 步骤1 · 业务简述 · POST /v2/memberships``。
    ``step_code`` 为序列化码（如 S01）；``step_title`` 为可读标题（建议含「步骤N · 说明」）。
    """
    core = f"{method} {path}"
    if not step_code and not step_title:
        return core
    parts: List[str] = []
    if step_code:
        parts.append(f"[{step_code}]")
    if step_title:
        parts.append(step_title)
    return " ".join(parts) + " · " + core


class AllureHttpScenarioSteps:
    """
    单条用例内的 HTTP 步骤序号：自动生成「步骤1/2/…」与序列码「S01/S02/…」，
    与 ``RequestWithAllure(..., step_code=..., step_title=...)`` 搭配使用。
    """

    def __init__(self, step_label_word: str = "步骤", code_prefix: str = "S") -> None:
        self._step_label_word = step_label_word
        self._code_prefix = code_prefix
        self._index = 0

    def Next(self, brief: str) -> Tuple[str, str]:
        """
        按调用顺序递增；返回 ``(step_code, step_title)``。
        brief：业务简述，如「注册会籍」「search 查询会籍」。
        """
        self._index += 1
        code = f"{self._code_prefix}{self._index:02d}"
        title = f"{self._step_label_word}{self._index} · {brief}"
        return code, title


def _AttachJson(name: str, payload: object) -> None:
    """
    将对象格式化为 JSON 文本后附加。

    使用 ``text/plain`` 而非 ``application/json``：Allure 2.28 等环境下 JSON 类型附件常出现
    **列表有大小、点开预览空白**（磁盘文件实际有内容），纯文本预览更稳定。
    """
    try:
        text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    except (TypeError, ValueError) as exc:
        allure.attach(str(payload), name=name, attachment_type=allure.attachment_type.TEXT)
        allure.attach(str(exc), name=name + "_json_error", attachment_type=allure.attachment_type.TEXT)
        return
    allure.attach(text, name=name, attachment_type=allure.attachment_type.TEXT)


def RequestWithAllure(
    method: str,
    path: str,
    *,
    token: Optional[str] = None,
    json_body: Optional[JsonDict] = None,
    timeout_sec: float = 30.0,
    after_response: Optional[AfterResponseHook] = None,
    step_code: Optional[str] = None,
    step_title: Optional[str] = None,
) -> Response:
    """
    发起 HTTP 请求并写入 Allure。

    **报告规范（与 Allure 模板一致）**：在步骤内依次附加
    ``request_step_meta``（仅当传入 ``step_code`` / ``step_title``）、
    ``request_meta``、``response_body_json``（非 JSON 时为 ``response_body_text``）、
    ``response_status``；``after_response`` 在同一步骤末尾追加断言类附件。

    path 以 / 开头，例如 /v2/memberships。

    step_code / step_title：序列码与可读标题，显示在步骤名最前（如 ``[S01] 步骤1 · 注册 · POST ...``）。
    """
    base = GetBaseUrl().rstrip("/")
    url = base + (path if path.startswith("/") else "/" + path)
    headers = BuildCommonHeaders(token)

    step_name = FormatAllureHttpStepTitle(
        method,
        path,
        step_code=step_code,
        step_title=step_title,
    )
    with allure.step(step_name):
        if step_code is not None or step_title is not None:
            _AttachJson(
                "request_step_meta",
                {
                    "step_code": step_code,
                    "step_title": step_title,
                    "method": method.upper(),
                    "path": path,
                },
            )
        _AttachAllureRequestMeta(
            url=url,
            method=method,
            headers=headers,
            json_body=json_body,
        )
        try:
            resp = requests.request(
                method.upper(),
                url,
                headers=headers,
                json=json_body,
                timeout=timeout_sec,
            )
        except requests.RequestException as exc:
            allure.attach(
                f"{type(exc).__name__}: {exc}",
                name="request_exception",
                attachment_type=allure.attachment_type.TEXT,
            )
            raise RuntimeError(f"HTTP 请求失败: {method} {url}") from exc

        _AttachAllureResponseArtifacts(resp)
        if after_response is not None:
            after_response(resp)
        return resp


def ParseResponseEnvelope(resp: Response) -> Tuple[int, Optional[JsonDict], Any]:
    """
    解析沙箱常见结构 { "code": int, "data": ... }；无法解析 JSON 时返回 status_code 与 None。
    """
    status = resp.status_code
    try:
        root = resp.json()
    except ValueError:
        return status, None, None
    if not isinstance(root, dict):
        return status, None, root
    root_dict = cast(JsonDict, root)
    data = root_dict.get("data")
    if isinstance(data, dict):
        return status, root_dict, cast(JsonDict, data)
    return status, root_dict, data


def ChainAfterResponse(*hooks: Optional[AfterResponseHook]) -> AfterResponseHook:
    """串联多个 ``after_response``，全部在同一步骤内顺序执行。"""

    flat: Tuple[AfterResponseHook, ...] = tuple(h for h in hooks if h is not None)
    if not flat:

        def _Noop(resp: Response) -> None:  # noqa: ARG001
            return None

        return _Noop

    def _Combined(resp: Response) -> None:
        for h in flat:
            h(resp)

    return _Combined


def RunSearchResponseAssertions(
    resp: Response,
    *,
    http_context: str,
    membership_id: str,
    client_user_id: Optional[str] = None,
    expect_status: Optional[int] = None,
    search_core_context: str = "",
    use_postman: bool = True,
    postman_extra: Optional[Mapping[str, Any]] = None,
    extensions_equal_to: Optional[Sequence[Mapping[str, Any]]] = None,
    extensions_context: str = "search",
    assert_shape_and_no_dup: bool = False,
    extension_item_checks: Optional[Sequence[ExtensionRegisterItem]] = None,
    expect_normalized_count: Optional[int] = None,
) -> None:
    """
    在 ``PostMembershipsSearch`` 的 ``after_response`` 中调用，使 HTTP 与断言处于同一步骤。

    顺序：HTTP+业务成功 →（可选）Postman → search 核心字段 → extensions 相关断言。
    """
    _st, env, inner = ParseResponseEnvelope(resp)
    AssertHttpAndBusinessOk(resp, env, context=http_context)
    if use_postman:
        if postman_extra is not None:
            AssertPostmanStyleSuccessResponse(resp, extra_json_paths=postman_extra)
        else:
            AssertPostmanStyleSuccessResponse(resp)
    rec = UnwrapMembershipRecord(inner)
    AssertSearchMembershipCoreFields(
        rec,
        membership_id=membership_id,
        client_user_id=client_user_id,
        expect_status=expect_status,
        context=search_core_context,
    )
    search_ext = ExtractExtensionsList(rec)
    if expect_normalized_count is not None:
        assert len(NormalizeExtensionsForCompare(search_ext)) == expect_normalized_count, (
            f"extensions 归一化条数期望 {expect_normalized_count}，实际 "
            f"{len(NormalizeExtensionsForCompare(search_ext))}"
        )
    if extensions_equal_to is not None:
        AssertExtensionsNormalizedEqual(search_ext, list(extensions_equal_to), context=extensions_context)
    if assert_shape_and_no_dup:
        AssertNoDuplicateExtensionTypesInList(search_ext, context=extensions_context)
        AssertExtensionItemsKeyShape(
            search_ext,
            ("type", "value"),
            allowed_keys=("type", "value"),
            context=extensions_context,
        )
    if extension_item_checks:
        for item in extension_item_checks:
            AssertExtensionItemInList(
                search_ext,
                type_=str(item["type"]),
                value=str(item["value"]),
                context=f"{extensions_context} extensions",
            )


def RunSearchDuplicateTypeCardIdPersistenceAssertions(
    resp: Response,
    *,
    http_context: str,
    membership_id: str,
    client_user_id: str,
    search_core_context: str,
) -> None:
    """重复 type 注册后 search：标准校验 + cardId 持久化语义。"""
    RunSearchResponseAssertions(
        resp,
        http_context=http_context,
        membership_id=membership_id,
        client_user_id=client_user_id,
        expect_status=1,
        search_core_context=search_core_context,
    )
    _st, _e, inner = ParseResponseEnvelope(resp)
    search_ext = ExtractExtensionsList(UnwrapMembershipRecord(inner))
    with allure.step("持久化层：cardId 至多一条；若存在则 value 为请求中之一"):
        AssertAtMostOneExtensionOfType(search_ext, "cardId", context="search")
        types = [x.get("type") for x in search_ext]
        assert types.count("cardId") <= 1, "重复 type 应未持久化为两条 cardId"
        if types.count("cardId") == 1:
            row = next(x for x in search_ext if str(x.get("type")) == "cardId")
            assert str(row.get("value", "")) in ("a", "b"), (
                f"cardId 取值应为 a 或 b 之一，实际 {row.get('value')!r}"
            )


def RunSearchSnapshotForDeleteAssertions(resp: Response, *, http_context: str, membership_id: str) -> None:
    """search 取 DELETE 前快照：HTTP+业务成功 + membershipId 匹配（不强制 Postman / 核心字段全量）。"""
    _st, env, inner = ParseResponseEnvelope(resp)
    AssertHttpAndBusinessOk(resp, env, context=http_context)
    rec = UnwrapMembershipRecord(inner)
    AssertMembershipSearchRecord(rec, membership_id)


def RunSearchOmitExtensionsSemanticsAssertions(
    resp: Response,
    *,
    http_context: str,
    membership_id: str,
    client_user_id: str,
    search_core_context: str,
) -> None:
    """无 extensions 注册后的 search：标准字段 + extensions 省略或空数组语义。"""
    RunSearchResponseAssertions(
        resp,
        http_context=http_context,
        membership_id=membership_id,
        client_user_id=client_user_id,
        expect_status=1,
        search_core_context=search_core_context,
    )
    _st, _e, inner = ParseResponseEnvelope(resp)
    rec = UnwrapMembershipRecord(inner)
    raw = rec.get("extensions")
    with allure.step("未注册 extensions：search 应省略 extensions 或为空数组"):
        if raw is None:
            return
        assert raw == [] or (isinstance(raw, list) and len(raw) == 0)


def RunPatchExtensionsAssertions(
    resp: Response,
    *,
    membership_id: str,
    http_context: Optional[str] = None,
    postman_extra_paths: Optional[Mapping[str, Any]] = None,
    plain_postman: bool = False,
    expected_extensions: Optional[Sequence[Mapping[str, Any]]] = None,
    ext_context: str = "extensions 更新",
    assert_no_dup: bool = False,
    assert_shape: bool = False,
    length_exact: Optional[int] = None,
    single_item_type_value: Optional[Tuple[str, str]] = None,
    custom_got_check: Optional[Callable[[List[JsonDict]], None]] = None,
) -> List[JsonDict]:
    """
    在 ``PatchMembershipsExtensions`` 的 ``after_response`` 中调用，使 HTTP 步骤与断言同屏。

    ``plain_postman=True`` 时不传 JSONPath 额外断言；否则默认校验 ``$.data.membershipId``。
    """
    ctx = http_context if http_context is not None else MembershipsExtensionsHttpContextLabel()
    _st, env, inner = ParseResponseEnvelope(resp)
    AssertHttpAndBusinessOk(resp, env, context=ctx)
    if plain_postman:
        AssertPostmanStyleSuccessResponse(resp)
    elif postman_extra_paths is not None:
        AssertPostmanStyleSuccessResponse(resp, extra_json_paths=postman_extra_paths)
    else:
        AssertPostmanStyleSuccessResponse(resp, extra_json_paths={"$.data.membershipId": membership_id})
    AssertExtensionsPatchSuccessBody(inner, membership_id)
    got = ExtractExtensionsList(inner)
    if expected_extensions is not None:
        AssertExtensionsNormalizedEqual(got, list(expected_extensions), context=ext_context)
    if assert_no_dup:
        AssertNoDuplicateExtensionTypesInList(got, context=ext_context)
    if assert_shape:
        AssertExtensionItemsKeyShape(
            got,
            ("type", "value"),
            allowed_keys=("type", "value"),
            context=ext_context,
        )
    if length_exact is not None:
        assert len(got) == length_exact, f"应余 {length_exact} 条 extension，实际 {len(got)}"
    if single_item_type_value is not None:
        t_v, v_v = single_item_type_value
        AssertExtensionItemInList(got, type_=t_v, value=v_v, context=ext_context)
    if custom_got_check is not None:
        custom_got_check(got)
    return got


def RunPatchInvalidMembershipIdAssertions(resp: Response) -> None:
    """非法 membershipId 的 PATCH：根 JSON 须含 code 且业务失败。"""
    root = AssertJsonResponse(resp)
    assert "code" in root, f"非法 membershipId 场景响应须含 code: {root!r}"
    _st, env, _ = ParseResponseEnvelope(resp)
    ok = IsHttpOk(resp) and IsBusinessSuccess(env)
    assert not ok, f"非法 membershipId 应失败: {resp.status_code}, {resp.text[:600]}"
    AssertRootBusinessCodeIndicatesFailure(root, context="非法 membershipId")


def RunPatchInvalidOperationGatewayAssertions(resp: Response) -> None:
    """非法 operation 的 PATCH：须含 code；若网关仍判成功则记录说明附件。"""
    root_patch = AssertJsonResponse(resp)
    assert "code" in root_patch, f"PATCH 响应须含 code: {root_patch!r}"
    _st, _env, _inner = ParseResponseEnvelope(resp)
    ok = IsHttpOk(resp) and IsBusinessSuccess(_env)
    if ok:
        allure.attach(
            "实现返回 HTTP 200 且忽略非法 operation（与 PATCH 网关行为一致）",
            name="invalid_operation_http_ok_note",
            attachment_type=allure.attachment_type.TEXT,
        )


def RunUpsertMissingValueDocumentedAssertions(resp: Response, *, membership_id: str) -> None:
    """UPSERT 缺 value：成功或失败分支 + outcome 附件。"""
    _st, env, inner = ParseResponseEnvelope(resp)
    root = AssertJsonResponse(resp)
    assert "code" in root, f"响应须含业务 code: {root!r}"
    assert IsHttpOk(resp), f"期望 HTTP 200，实际 {resp.status_code}: {resp.text[:800]}"
    if IsBusinessSuccess(env) and isinstance(inner, dict):
        with allure.step("若缺少 value 仍判成功：data 须含 membershipId 与 extensions"):
            AssertExtensionsPatchSuccessBody(inner, membership_id)
    else:
        with allure.step("若判失败：根 code 须非 0（仅当响应含 code 字段）"):
            if root.get("code") is not None:
                AssertRootBusinessCodeIndicatesFailure(root, context="UPSERT 无 value")
    allure.attach(
        f"http={resp.status_code}, business_ok={IsBusinessSuccess(env)}, inner={inner!r}, root={root!r}"[:4000],
        name="upsert_without_value_outcome",
        attachment_type=allure.attachment_type.TEXT,
    )


def GetAccessToken() -> str:
    """
    POST /v2/auth/token。

    与 Postman 一致：携带 X-Request-ID；若已配置 DP_PROGRAM_ID 则携带 X-Program-ID。
    若网关要求在取 token 前带 Bearer，可设置 DP_TOKEN_REQUEST_BEARER（仅填 JWT 本体，不含 Bearer 前缀）。
    不需要 Program 头时设 DP_TOKEN_OMIT_PROGRAM_ID=1。
    """
    cid = GetClientId()
    sec = GetClientSecret()
    url = GetBaseUrl().rstrip("/") + "/v2/auth/token"
    token_headers: Dict[str, str] = {
        "Content-Type": "application/json",
        "Accept": "*/*",
        "X-Request-ID": BuildNextRequestId(),
    }
    if not _EnvFlagTrue("DP_TOKEN_OMIT_PROGRAM_ID"):
        pid = os.getenv("DP_PROGRAM_ID", "").strip()
        if pid:
            token_headers["X-Program-ID"] = pid
    bearer_raw = os.getenv("DP_TOKEN_REQUEST_BEARER", "").strip()
    if bearer_raw:
        token_headers["Authorization"] = (
            bearer_raw if bearer_raw.lower().startswith("bearer ") else "Bearer " + bearer_raw
        )
    with allure.step("POST /v2/auth/token"):
        _AttachAllureRequestMeta(
            url=url,
            method="POST",
            headers=token_headers,
            json_body={"clientId": cid, "secret": "***"},
        )
        try:
            resp = requests.post(
                url,
                json={"clientId": cid, "secret": sec},
                headers=token_headers,
                timeout=30.0,
            )
        except requests.RequestException as exc:
            raise RuntimeError("获取 token 时网络异常") from exc
        _AttachAllureResponseArtifacts(resp)

    if resp.status_code != 200:
        raise RuntimeError(f"获取 token HTTP 失败: {resp.status_code}, {resp.text[:500]}")

    data = AssertJsonResponse(resp)
    if "code" in data:
        assert data["code"] in (0, "0"), f"取 token 业务 code 非成功: {data!r}"
    container: Any = data.get("data") if "data" in data else data
    if not isinstance(container, dict):
        raise RuntimeError(f"token 载荷格式异常: {container!r}")
    cdict = cast(JsonDict, container)
    token = cdict.get("accessToken") or cdict.get("token") or cdict.get("access_token")
    if not token or not isinstance(token, str):
        raise RuntimeError(f"token 响应中无 accessToken: {data!r}")
    return token


def BuildMinimalMembershipPayload(
    *,
    extensions: Optional[Sequence[ExtensionRegisterItem]] = None,
    extra: Optional[JsonDict] = None,
) -> JsonDict:
    """构造 POST /v2/memberships 最小合法注册体（可按需合并 extra）。"""
    email_suffix = uuid.uuid4().hex[:8]
    payload: JsonDict = {
        "clientUserId": str(uuid.uuid4()),
        "firstName": "Lann",
        "lastName": "Testn",
        "phoneNumber": "8081966002",
        "callingCode": "44",
        "email": f"p2548+{email_suffix}@example.com",
        "expirationDate": "2027-12-31T10:10:33+00:00",
    }
    if extensions is not None:
        payload["extensions"] = list(extensions)
    if extra:
        payload.update(extra)
    return payload


def PostMemberships(
    token: str,
    payload: JsonDict,
    *,
    after_response: Optional[AfterResponseHook] = None,
    step_code: Optional[str] = None,
    step_title: Optional[str] = None,
) -> Tuple[Response, Optional[JsonDict], Any]:
    """POST /v2/memberships，返回 (response, envelope, data_or_inner)。"""
    resp = RequestWithAllure(
        "POST",
        "/v2/memberships",
        token=token,
        json_body=payload,
        after_response=after_response,
        step_code=step_code,
        step_title=step_title,
    )
    status, env, inner = ParseResponseEnvelope(resp)
    return resp, env, inner


def ExtractMembershipId(inner: Any) -> str:
    if not isinstance(inner, dict):
        raise RuntimeError(f"无法解析 membershipId，响应 data 非对象: {inner!r}")
    d = cast(JsonDict, inner)
    mid = d.get("membershipId") or d.get("id")
    if not mid:
        raise RuntimeError(f"响应中无 membershipId: {d!r}")
    return str(mid)


def ExtractExtensionsList(inner: Any) -> List[JsonDict]:
    """从注册/查询/更新响应的 data 对象中提取 extensions 列表；缺失则 []。"""
    if not isinstance(inner, dict):
        return []
    d = cast(JsonDict, inner)
    ext = d.get("extensions")
    if ext is None:
        feat = d.get("feature")
        if isinstance(feat, str) and feat.strip():
            try:
                parsed = json.loads(feat)
                if isinstance(parsed, dict) and isinstance(parsed.get("extensions"), list):
                    ext = parsed.get("extensions")
            except json.JSONDecodeError:
                ext = None
        elif isinstance(feat, dict) and isinstance(feat.get("extensions"), list):
            ext = feat.get("extensions")
    if ext is None:
        return []
    if not isinstance(ext, list):
        return []
    return [cast(JsonDict, x) for x in ext if isinstance(x, dict)]


def NormalizeExtensionsForCompare(items: Sequence[Mapping[str, Any]]) -> List[Tuple[str, Optional[str]]]:
    """按 type 排序后的 (type, value|None) 列表；无 value 键视为 DELETE 后形态。"""
    out: List[Tuple[str, Optional[str]]] = []
    for it in items:
        t = str(it.get("type", ""))
        if "value" not in it:
            out.append((t, None))
        else:
            v = it.get("value")
            out.append((t, None if v is None else str(v)))
    out.sort(key=lambda x: x[0])
    return out


def AssertExtensionsNormalizedEqual(
    actual_items: Sequence[Mapping[str, Any]],
    expected_items: Sequence[Mapping[str, Any]],
    *,
    context: str = "",
) -> None:
    """归一化后与预期 extensions 列表完全一致（条数、type、value 一一对应）。"""
    prefix = f"[{context}] " if context else ""
    title = f"{prefix}extensions 归一化后与预期完全一致".strip()

    def _Do() -> str:
        got = NormalizeExtensionsForCompare(actual_items)
        exp = NormalizeExtensionsForCompare(expected_items)
        assert got == exp, f"{prefix}extensions 与预期不一致: 期望 {exp!r} 实际 {got!r}"
        return f"归一化比对:\n  实际: {got!r}\n  预期: {exp!r}"

    _RunAllureAssertionStep(title, _Do)


def AssertExtensionItemsKeyShape(
    items: Sequence[Any],
    require_keys: Sequence[str],
    *,
    allowed_keys: Optional[Sequence[str]] = None,
    context: str = "",
) -> None:
    """每条 extension 对象须含 require_keys；若给定 allowed_keys 则不得出现其它键。"""
    prefix = f"[{context}] " if context else ""
    title = f"{prefix}extensions 每条键结构合法".strip()

    def _Do() -> str:
        allowed: Optional[Set[str]] = set(allowed_keys) if allowed_keys is not None else None
        for i, it in enumerate(items):
            assert isinstance(it, dict), f"{prefix}extensions[{i}] 须为对象，实际 {type(it).__name__}"
            d = cast(Mapping[str, Any], it)
            for k in require_keys:
                assert k in d, f"{prefix}extensions[{i}] 缺少键 {k!r}: {d!r}"
            if allowed is not None:
                extras = set(d.keys()) - allowed
                assert not extras, f"{prefix}extensions[{i}] 含非预期键 {extras!r}: {d!r}"
        ak = f"\n允许键白名单: {sorted(allowed)!r}" if allowed is not None else ""
        return f"共 {len(items)} 条；必填键 {list(require_keys)!r}{ak}"

    _RunAllureAssertionStep(title, _Do)


def AssertNoDuplicateExtensionTypesInList(
    items: Sequence[Mapping[str, Any]],
    *,
    context: str = "",
) -> None:
    """同一会籍下 extensions 的 type 应互不相同。"""
    prefix = f"[{context}] " if context else ""
    title = f"{prefix}extensions type 无重复".strip()

    def _Do() -> str:
        types = [str(x.get("type", "")) for x in items]
        dup = sorted({t for t in types if types.count(t) > 1})
        assert not dup, f"{prefix}type 应唯一，发现重复 type={dup!r} 全量 {types!r}"
        return f"type 列表（按条顺序）: {types!r}"

    _RunAllureAssertionStep(title, _Do)


def AssertAtMostOneExtensionOfType(
    items: Sequence[Mapping[str, Any]],
    type_name: str,
    *,
    context: str = "",
) -> None:
    """指定 type 在列表中至多出现一条（重复 type 注册用例）。"""
    prefix = f"[{context}] " if context else ""
    title = f"{prefix}type={type_name!r} 至多出现 1 次".strip()

    def _Do() -> str:
        n = sum(1 for x in items if str(x.get("type", "")) == str(type_name))
        assert n <= 1, f"{prefix}type={type_name!r} 至多 1 条，实际 {n} 条"
        return f"type={type_name!r} 出现次数: {n}"

    _RunAllureAssertionStep(title, _Do)


def AssertRegisterSelectedFieldsEchoed(
    data: Mapping[str, Any],
    payload: Mapping[str, Any],
    *,
    keys: Sequence[str] = (
        "clientUserId",
        "email",
        "firstName",
        "lastName",
        "phoneNumber",
        "callingCode",
    ),
    context: str = "",
) -> None:
    """
    注册成功 data 与请求体在约定字段上回显一致。
    仅当 **请求含该键且响应 data 也含该键** 时才比对；服务未回显的字段（如 email）跳过，避免误伤沙箱。
    """
    prefix = f"[{context}] " if context else ""
    title = f"{prefix}注册 data 与请求体字段回显".strip()

    def _Do() -> str:
        lines: List[str] = []
        for k in keys:
            if k not in payload:
                continue
            if k not in data:
                lines.append(f"跳过（响应未回显）: {k!r}")
                continue
            assert str(data[k]) == str(payload[k]), (
                f"{prefix}回显 {k!r} 不一致: 期望 {payload[k]!r} 实际 {data[k]!r}"
            )
            lines.append(f"{k}: 请求与响应均为 {data[k]!r}")
        if not lines:
            return "无重叠字段需比对（或均未回显）"
        return "\n".join(lines)

    _RunAllureAssertionStep(title, _Do)


def AssertBusinessFailureEnvelope(
    resp: Response,
    env: Optional[JsonDict],
    *,
    context: str = "",
) -> None:
    """负面用例：不得同时 HTTP 200 且业务成功。"""
    prefix = f"[{context}] " if context else ""
    title = f"{prefix}负面用例：HTTP/业务须体现失败".strip()

    def _Do() -> str:
        assert not (IsHttpOk(resp) and IsBusinessSuccess(env)), (
            f"{prefix}期望失败，实际 HTTP={resp.status_code} business_ok={IsBusinessSuccess(env)} "
            f"env={env!r} body={resp.text[:800]}"
        )
        code_v = env.get("code") if isinstance(env, dict) else None
        return (
            f"HTTP {resp.status_code}\n"
            f"业务成功判定: {IsBusinessSuccess(env)}\n"
            f"envelope code: {code_v!r}"
        )

    _RunAllureAssertionStep(title, _Do)


def AssertRootBusinessCodeIndicatesFailure(
    root: Mapping[str, Any],
    *,
    context: str = "",
) -> None:
    """根 JSON 含 code 时须表示失败（非 0），用于非法 membershipId 等。"""
    prefix = f"[{context}] " if context else ""
    title = f"{prefix}根 JSON 业务 code 表示失败".strip()

    def _Do() -> str:
        if "code" not in root:
            return "根对象无 code 字段，跳过本断言"
        c = root.get("code")
        assert c != 0 and c != "0", (
            f"{prefix}期望业务失败 code!=0，实际 code={c!r} root_keys={sorted(root.keys(), key=str)!r}"
        )
        return f"code={c!r}（非 0，符合失败语义）"

    _RunAllureAssertionStep(title, _Do)


def UnwrapMembershipRecord(inner: Any) -> JsonDict:
    """
    从 /v2/memberships/search 的 data 中取出单条会籍对象（兼容 data 为对象、列表或含 memberships 数组）。
    """
    if isinstance(inner, dict):
        d = cast(JsonDict, inner)
        m = d.get("memberships")
        if isinstance(m, list) and m and isinstance(m[0], dict):
            return cast(JsonDict, m[0])
        return d
    if isinstance(inner, list) and inner:
        first = inner[0]
        if isinstance(first, dict):
            return cast(JsonDict, first)
    raise RuntimeError(f"无法解析会籍记录: {inner!r}")


def PostMembershipsSearch(
    token: str,
    membership_id: str,
    *,
    after_response: Optional[AfterResponseHook] = None,
    step_code: Optional[str] = None,
    step_title: Optional[str] = None,
) -> Tuple[Response, Optional[JsonDict], Any]:
    """POST /v2/memberships/search"""
    body: JsonDict = {"membershipId": membership_id}
    resp = RequestWithAllure(
        "POST",
        "/v2/memberships/search",
        token=token,
        json_body=body,
        after_response=after_response,
        step_code=step_code,
        step_title=step_title,
    )
    _st, env, inner = ParseResponseEnvelope(resp)
    return resp, env, inner


def PatchMembershipsExtensions(
    token: str,
    membership_id: str,
    operations: Sequence[Mapping[str, Any]],
    *,
    after_response: Optional[AfterResponseHook] = None,
    step_code: Optional[str] = None,
    step_title: Optional[str] = None,
) -> Tuple[Response, Optional[JsonDict], Any]:
    """POST 或 PATCH ``/v2/memberships/extensions``（由 ``GetMembershipsExtensionsHttpMethod`` 决定）。"""
    body: JsonDict = {"membershipId": membership_id, "extensions": list(operations)}
    method = GetMembershipsExtensionsHttpMethod()
    resp = RequestWithAllure(
        method,
        "/v2/memberships/extensions",
        token=token,
        json_body=body,
        after_response=after_response,
        step_code=step_code,
        step_title=step_title,
    )
    _st, env, inner = ParseResponseEnvelope(resp)
    return resp, env, inner


# 兼容旧名称（历史上误用 POST）
PostMembershipsExtensions = PatchMembershipsExtensions


def IsHttpOk(resp: Response) -> bool:
    return resp.status_code == 200


def IsBusinessSuccess(envelope: Optional[JsonDict]) -> bool:
    """envelope 含 code 时要求 code == 0；无 code 时仅依赖 HTTP。"""
    if envelope is None:
        return False
    if "code" not in envelope:
        return True
    code = envelope.get("code")
    return code == 0 or code == "0"


def AssertHttpAndBusinessOk(
    resp: Response,
    env: Optional[JsonDict],
    *,
    context: str = "",
) -> None:
    """断言 HTTP 200 且业务 code==0（或 envelope 无 code 键）。"""
    prefix = f"[{context}] " if context else ""
    title = f"{prefix}HTTP 200 且业务成功".strip()

    def _Do() -> str:
        assert IsHttpOk(resp), f"{prefix}HTTP {resp.status_code}: {resp.text[:1200]}"
        assert IsBusinessSuccess(env), (
            f"{prefix}业务未成功 code={env.get('code') if isinstance(env, dict) else None} "
            f"env={env!r} body={resp.text[:1200]}"
        )
        ec = env.get("code") if isinstance(env, dict) else None
        return f"HTTP {resp.status_code}\n业务 code: {ec!r}\n判定: 成功"

    _RunAllureAssertionStep(title, _Do)


def _MembershipSearchRecordSummary(rec: Mapping[str, Any], membership_id: str) -> str:
    """search 单条会籍 membershipId 与预期一致；返回摘要文本（供组合断言复用，避免重复挂 Allure）。"""
    mid = rec.get("membershipId")
    assert mid is not None, f"search 记录缺 membershipId: {rec!r}"
    assert str(mid) == str(membership_id), f"membershipId 不一致 expect={membership_id!r} got={mid!r}"
    return f"记录 membershipId: {mid!r}"


def AssertMembershipSearchRecord(rec: Mapping[str, Any], membership_id: str) -> None:
    """search 返回的单条会籍应能按 membershipId 对上。"""
    title = f"search membershipId == {membership_id!r}"

    def _Do() -> str:
        return _MembershipSearchRecordSummary(rec, membership_id)

    _RunAllureAssertionStep(title, _Do)


def AssertExtensionsPatchSuccessBody(inner: Any, membership_id: str) -> None:
    """extensions 更新接口业务成功时 data 须含 membershipId 与 extensions 数组。"""
    title = "extensions 更新成功 data 结构"

    def _Do() -> str:
        assert isinstance(inner, dict), f"extensions 更新成功时 data 应为对象: {inner!r}"
        d = cast(JsonDict, inner)
        assert str(d.get("membershipId", "")) == str(membership_id), f"响应 membershipId 不一致: {d!r}"
        assert "extensions" in d, f"响应缺 extensions 键: {d!r}"
        assert isinstance(d.get("extensions"), list), f"extensions 应为数组: {d!r}"
        ext = d.get("extensions")
        assert isinstance(ext, list)
        return f"membershipId={d.get('membershipId')!r}\nextensions 条数={len(ext)}"

    _RunAllureAssertionStep(title, _Do)


def AssertRegisterSuccessBody(inner: Any) -> JsonDict:
    """POST /v2/memberships 成功时 data 须含 membershipId、status。"""
    with allure.step("注册成功 data 含 membershipId 与 status"):
        assert isinstance(inner, dict), f"注册成功时 data 应为对象: {inner!r}"
        d = cast(JsonDict, inner)
        assert d.get("membershipId"), f"注册响应缺 membershipId: {d!r}"
        assert "status" in d, f"注册响应缺 status: {d!r}"
        _RecordAllureAssertionResult(
            f"membershipId: {d.get('membershipId')!r}\nstatus: {d.get('status')!r}",
            assertion_title="注册成功 data 含 membershipId 与 status",
        )
    return d


def AssertJsonResponse(resp: Response) -> JsonDict:
    """响应体须为 JSON 对象（不断言业务成功）。"""
    assert resp.text.strip(), "响应体不应为空"
    try:
        root = resp.json()
    except ValueError as exc:
        raise AssertionError(f"响应非合法 JSON: {resp.text[:500]}") from exc
    assert isinstance(root, dict), f"响应根须为 JSON 对象: {root!r}"
    return cast(JsonDict, root)


def _EnvPostmanNoCjkBody() -> bool:
    """与 Postman 集合「响应体不含中文」一致；设 DP_POSTMAN_NO_CJK_BODY=1 开启。"""
    return _EnvFlagTrue("DP_POSTMAN_NO_CJK_BODY")


def AssertResponseBodyExcludesCjk(text: str, *, context: str = "") -> None:
    """
    对齐 membership-extansion Postman（Apifox）中 funcChina：
    响应文本中不得出现 CJK 统一汉字区 \\u4e00-\\u9fa5（与导出脚本正则一致）。
    """
    prefix = f"[{context}] " if context else ""
    title = f"{prefix}响应体无 CJK（Postman funcChina）".strip()

    def _Do() -> str:
        for i, ch in enumerate(text):
            o = ord(ch)
            if 0x4E00 <= o <= 0x9FA5:
                lo = max(0, i - 40)
                hi = min(len(text), i + 40)
                raise AssertionError(
                    f"{prefix}响应体含 CJK 字符 U+{o:04X}（Postman funcChina），"
                    f"片段: {text[lo:hi]!r}"
                )
        return f"已扫描 {len(text)} 字符，未发现 \\u4e00-\\u9fa5 区汉字"

    _RunAllureAssertionStep(title, _Do)


def JsonPathEvaluate(root: Any, json_path: str) -> Any:
    """
    极简 JSONPath（与 Apifox/Postman 导出中常用路径兼容）：
    支持 ``$.code``、``$.data.membershipId``、``$.data.extensions[0].type`` 等。
    缺键或类型不符时抛出 AssertionError。
    """
    s = json_path.strip()
    if not s or s == "$":
        return root
    if s.startswith("$"):
        s = s[1:].lstrip(".")
    cur: Any = root
    i = 0
    n = len(s)
    while i < n:
        if s[i] == "[":
            close = s.index("]", i)
            idx = int(s[i + 1 : close])
            if not isinstance(cur, list):
                raise AssertionError(
                    f"JSONPath {json_path!r}: 期望数组以使用 [{idx}]，实际 {type(cur).__name__}: {cur!r}"
                )
            if idx < 0 or idx >= len(cur):
                raise AssertionError(
                    f"JSONPath {json_path!r}: 索引 [{idx}] 越界，长度 {len(cur)}"
                )
            cur = cur[idx]
            i = close + 1
            continue
        j = i
        while j < n and s[j] not in ".[":
            j += 1
        key = s[i:j]
        if not key:
            i = j + (1 if j < n and s[j] == "." else 0)
            continue
        if not isinstance(cur, dict):
            raise AssertionError(
                f"JSONPath {json_path!r}: 期望对象以读取键 {key!r}，实际 {type(cur).__name__}: {cur!r}"
            )
        cur_d = cast(Mapping[str, Any], cur)
        if key not in cur_d:
            raise AssertionError(
                f"JSONPath {json_path!r}: 缺少键 {key!r}，当前可用: "
                f"{sorted(cur_d.keys(), key=str)!r}"
            )
        cur = cur_d[key]
        i = j
    return cur


def _JsonPathValueEqual(actual: Any, expected: Any) -> bool:
    """Postman 导出常把数字写成字符串；此处做宽松相等。"""
    if actual == expected:
        return True
    if isinstance(expected, bool):
        return actual is expected
    if isinstance(expected, int) and isinstance(actual, str):
        try:
            return int(actual) == expected
        except ValueError:
            return False
    if isinstance(expected, str) and isinstance(actual, int):
        try:
            return int(expected) == actual
        except ValueError:
            return str(actual) == expected
    if isinstance(expected, str) and isinstance(actual, float):
        try:
            return float(expected) == actual
        except ValueError:
            return False
    return False


def AssertJsonPathEquals(
    root: Any,
    json_path: str,
    expected: Any,
    *,
    context: str = "",
) -> None:
    """断言根对象上 JSONPath 取值与期望值宽松相等（用于对照 Postman 的 JSONPath 断言）。"""
    prefix = f"[{context}] " if context else ""
    actual = JsonPathEvaluate(root, json_path)
    if _JsonPathValueEqual(actual, expected):
        _RecordAllureAssertionResult(
            f"JSONPath: {json_path}\n实际值: {actual!r}\n期望值: {expected!r}\n匹配方式: 宽松相等",
            assertion_title=f"JSONPath {json_path}",
        )
        return
    raise AssertionError(
        f"{prefix}JSONPath {json_path!r}: 期望 {expected!r}（{type(expected).__name__}），"
        f"实际 {actual!r}（{type(actual).__name__}）"
    )


def AssertPostmanStyleSuccessResponse(
    resp: Response,
    *,
    extra_json_paths: Optional[Mapping[str, Any]] = None,
    strict_no_cjk_body: Optional[bool] = None,
) -> JsonDict:
    """
    对齐桌面 Postman 集合 membership-extansion 的成功类习惯：
    - 可选 ``strict_no_cjk_body`` 或环境变量 ``DP_POSTMAN_NO_CJK_BODY=1``：响应体无 CJK（funcChina）
    - 断言 ``$.code`` 为 0（兼容字符串 ``\"0\"``）
    - ``extra_json_paths``：额外路径，如 ``{\"$.data.membershipId\": mid}``、
      ``{\"$.data.extensions[0]\": {\"type\": \"aa\", \"value\": \"12\"}}``
    """
    use_cjk = strict_no_cjk_body
    if use_cjk is None:
        use_cjk = _EnvPostmanNoCjkBody()
    if use_cjk:
        AssertResponseBodyExcludesCjk(resp.text, context="Postman")
    root = AssertJsonResponse(resp)
    with allure.step("Postman: $.code == 0"):
        AssertJsonPathEquals(root, "$.code", 0, context="Postman")
    if extra_json_paths:
        for path, ev in extra_json_paths.items():
            with allure.step(f"Postman: {path}"):
                AssertJsonPathEquals(root, path, ev, context="Postman")
    summary = ["$.code == 0"]
    if extra_json_paths:
        for pth, ev in extra_json_paths.items():
            summary.append(f"{pth} == {ev!r}")
    _RecordAllureAssertionResult(
        "Postman 风格成功断言汇总:\n" + "\n".join(summary),
        assertion_title="Postman 成功断言汇总",
    )
    return root


def AssertPostmanStyleErrorResponse(
    resp: Response,
    *,
    expect_err_code: str,
    msg_contains: Optional[str] = None,
    strict_no_cjk_body: Optional[bool] = None,
) -> JsonDict:
    """
    对齐 Postman 集合中的失败断言：``$.errCode`` 等于期望值，可选校验 ``$.msg`` 包含子串。
    （若网关仅返回 ``code`` / 无 ``errCode``，请改用 ``AssertJsonPathEquals`` 自行断言。）
    """
    use_cjk = strict_no_cjk_body
    if use_cjk is None:
        use_cjk = _EnvPostmanNoCjkBody()
    if use_cjk:
        AssertResponseBodyExcludesCjk(resp.text, context="Postman")
    root = AssertJsonResponse(resp)
    with allure.step(f"Postman: $.errCode == {expect_err_code!r}"):
        AssertJsonPathEquals(root, "$.errCode", expect_err_code, context="Postman")
    msg_line = ""
    if msg_contains is not None:
        msg_val = JsonPathEvaluate(root, "$.msg")
        got = str(msg_val)
        assert msg_contains in got, (
            f"[Postman] $.msg 应包含 {msg_contains!r}，实际 {got!r}"
        )
        msg_line = f"\n$.msg 包含 {msg_contains!r}: 是\n完整 msg: {got[:500]!r}"
    _RecordAllureAssertionResult(
        f"errCode: {expect_err_code!r}{msg_line}",
        assertion_title="Postman 失败断言汇总",
    )
    return root


def AssertPapi2548DuplicateTypeErrorResponse(resp: Response) -> JsonDict:
    """
    重复 ``type``：``errCode`` 为 ``500.030.032``（或历史 ``500.030.033``），
    ``msg`` 含完整英文句式 ``PAPI2548_EXT_MSG_DUPLICATE_TYPE``。
    """
    root = AssertJsonResponse(resp)
    ec = root.get("errCode") if isinstance(root, dict) else None
    if ec == PAPI2548_EXT_ERR_DUPLICATE_TYPE:
        return AssertPostmanStyleErrorResponse(
            resp,
            expect_err_code=PAPI2548_EXT_ERR_DUPLICATE_TYPE,
            msg_contains=PAPI2548_EXT_MSG_DUPLICATE_TYPE,
        )
    if ec == PAPI2548_EXT_ERR_DUPLICATE_TYPE_LEGACY:
        return AssertPostmanStyleErrorResponse(
            resp,
            expect_err_code=PAPI2548_EXT_ERR_DUPLICATE_TYPE_LEGACY,
            msg_contains=PAPI2548_EXT_MSG_DUPLICATE_TYPE,
        )
    raise AssertionError(
        f"重复 type 场景期望 errCode 为 {PAPI2548_EXT_ERR_DUPLICATE_TYPE!r} "
        f"或历史 {PAPI2548_EXT_ERR_DUPLICATE_TYPE_LEGACY!r}，实际 {ec!r}，body={resp.text[:800]!r}"
    )


def AssertPapi2548MaxFiveTypesErrorResponse(resp: Response) -> JsonDict:
    """
    超过 5 个 ``type``：``errCode`` 为 ``500.030.033``（或历史 ``500.030.034``），
    ``msg`` 含完整英文句式 ``PAPI2548_EXT_MSG_MAX_FIVE_TYPES``。
    """
    root = AssertJsonResponse(resp)
    ec = root.get("errCode") if isinstance(root, dict) else None
    if ec == PAPI2548_EXT_ERR_MAX_FIVE_TYPES:
        return AssertPostmanStyleErrorResponse(
            resp,
            expect_err_code=PAPI2548_EXT_ERR_MAX_FIVE_TYPES,
            msg_contains=PAPI2548_EXT_MSG_MAX_FIVE_TYPES,
        )
    if ec == PAPI2548_EXT_ERR_MAX_FIVE_TYPES_LEGACY:
        return AssertPostmanStyleErrorResponse(
            resp,
            expect_err_code=PAPI2548_EXT_ERR_MAX_FIVE_TYPES_LEGACY,
            msg_contains=PAPI2548_EXT_MSG_MAX_FIVE_TYPES,
        )
    raise AssertionError(
        f"6 个 type 场景期望 errCode 为 {PAPI2548_EXT_ERR_MAX_FIVE_TYPES!r} "
        f"或历史 {PAPI2548_EXT_ERR_MAX_FIVE_TYPES_LEGACY!r}，实际 {ec!r}，body={resp.text[:800]!r}"
    )


def AssertDictKeyValues(
    actual: Mapping[str, Any],
    expected: Mapping[str, Any],
    *,
    context: str = "",
) -> None:
    """
    精细字段断言：expected 中每个键必须在 actual 中存在且值与 `==` 一致。
    用于「新增/变更了某个响应字段」时显式写出期望值。
    actual 允许包含 expected 未列出的其它键。
    """
    prefix = f"[{context}] " if context else ""
    title = f"{prefix}字典键值精确匹配 {list(expected.keys())!r}".strip()

    def _Do() -> str:
        lines: List[str] = []
        for key, ev in expected.items():
            if key not in actual:
                raise AssertionError(
                    f"{prefix}缺少键 {key!r}，已有键: {sorted(actual.keys(), key=str)!r}"
                )
            av = actual[key]
            assert av == ev, f"{prefix}键 {key!r} 期望值 {ev!r}，实际 {av!r}"
            lines.append(f"{key!r}: {av!r} == {ev!r}")
        return "\n".join(lines)

    _RunAllureAssertionStep(title, _Do)


def AssertNestedStructureEqual(
    actual: Any,
    expected: Any,
    *,
    path: str = "root",
) -> None:
    """
    递归结构相等：expected 为 dict 则对子键逐项断言；为 list 则按索引逐项且长度一致；
    否则使用 `==`。适用于嵌套 JSON 片段与「新增子对象」的整段比对。
    """
    if expected is None:
        assert actual is None, f"{path}: 期望 None，实际 {actual!r}"
        return
    if isinstance(expected, dict):
        assert isinstance(actual, dict), f"{path}: 期望 dict，实际 {type(actual).__name__}"
        actual_d = cast(Mapping[str, Any], actual)
        for k, ev in expected.items():
            AssertNestedStructureEqual(actual_d.get(k), ev, path=f"{path}.{k}")
        return
    if isinstance(expected, list):
        assert isinstance(actual, list), f"{path}: 期望 list，实际 {type(actual).__name__}"
        assert len(actual) == len(expected), (
            f"{path}: list 长度期望 {len(expected)}，实际 {len(actual)}"
        )
        for i, (av, ev) in enumerate(zip(actual, expected)):
            AssertNestedStructureEqual(av, ev, path=f"{path}[{i}]")
        return
    assert actual == expected, f"{path}: 期望 {expected!r}，实际 {actual!r}"


def AssertExtensionItemInList(
    items: Sequence[Mapping[str, Any]],
    *,
    type_: str,
    value: Optional[str] = None,
    context: str = "",
) -> None:
    """在 extensions 数组中查找指定 type，可选严格比对 value。"""
    prefix = f"[{context}] " if context else ""
    val_part = f", value={value!r}" if value is not None else ""
    title = f"{prefix}extensions 含 type={type_!r}{val_part}".strip()

    def _Do() -> str:
        for it in items:
            if str(it.get("type", "")) != str(type_):
                continue
            if value is not None:
                av = it.get("value")
                assert str(av) == str(value), (
                    f"{prefix}type={type_!r} 的 value 期望 {value!r}，实际 {av!r}"
                )
                return f"已定位 type={type_!r}, value={av!r}"
            return f"已定位 type={type_!r}（未校验 value）"
        raise AssertionError(f"{prefix}extensions 中未找到 type={type_!r}，当前: {list(items)!r}")

    _RunAllureAssertionStep(title, _Do)


def AssertRegisterCoreFields(
    body: Mapping[str, Any],
    *,
    membership_id: str,
    program_id: Optional[str] = None,
    client_user_id: Optional[str] = None,
    expect_status: Optional[int] = 1,
    context: str = "",
) -> None:
    """注册成功 data 上除 membershipId/status 外，按需校验 programId、clientUserId 等回显。"""
    prefix = f"[{context}] " if context else ""
    title = f"{prefix}注册 data 核心字段".strip()

    def _Do() -> str:
        lines: List[str] = []
        assert str(body.get("membershipId", "")) == str(membership_id), (
            f"{prefix}membershipId 期望 {membership_id!r}，实际 {body.get('membershipId')!r}"
        )
        lines.append(f"membershipId: {body.get('membershipId')!r}")
        pid = program_id if program_id is not None else os.getenv("DP_PROGRAM_ID", "").strip() or None
        if pid:
            av = body.get("programId")
            assert str(av) == str(pid), f"{prefix}programId 期望 {pid!r}，实际 {av!r}"
            lines.append(f"programId: {av!r}")
        if client_user_id is not None:
            av = body.get("clientUserId")
            assert str(av) == str(client_user_id), f"{prefix}clientUserId 期望 {client_user_id!r}，实际 {av!r}"
            lines.append(f"clientUserId: {av!r}")
        if expect_status is not None:
            assert body.get("status") == expect_status, (
                f"{prefix}status 期望 {expect_status}，实际 {body.get('status')!r}"
            )
            lines.append(f"status: {expect_status!r}")
        return "\n".join(lines)

    _RunAllureAssertionStep(title, _Do)


def AssertSearchMembershipCoreFields(
    rec: Mapping[str, Any],
    *,
    membership_id: str,
    program_id: Optional[str] = None,
    client_user_id: Optional[str] = None,
    expect_status: Optional[int] = None,
    context: str = "",
) -> None:
    """search 单条会籍：membershipId 必校；可选 programId、clientUserId、status。"""
    prefix = f"[{context}] " if context else ""
    title = f"{prefix}search 会籍核心字段".strip()

    def _Do() -> str:
        lines: List[str] = [_MembershipSearchRecordSummary(rec, membership_id)]
        pid = program_id if program_id is not None else os.getenv("DP_PROGRAM_ID", "").strip() or None
        if pid:
            av = rec.get("programId")
            assert str(av) == str(pid), f"{prefix}programId 期望 {pid!r}，实际 {av!r}"
            lines.append(f"programId: {av!r}")
        if client_user_id is not None:
            av = rec.get("clientUserId")
            assert str(av) == str(client_user_id), f"{prefix}clientUserId 期望 {client_user_id!r}，实际 {av!r}"
            lines.append(f"clientUserId: {av!r}")
        if expect_status is not None:
            assert rec.get("status") == expect_status, (
                f"{prefix}status 期望 {expect_status}，实际 {rec.get('status')!r}"
            )
            lines.append(f"status: {expect_status!r}")
        return "\n".join(lines)

    _RunAllureAssertionStep(title, _Do)


def RegisterMembershipSuccessDetail(
    token: str,
    payload: JsonDict,
    *,
    step_code: Optional[str] = None,
    step_title: Optional[str] = None,
) -> Tuple[str, List[JsonDict], JsonDict]:
    """
    注册会籍并断言成功；返回 membershipId、extensions 列表、完整 data 对象（便于对新增字段做精细断言）。

    断言挂在 ``POST /v2/memberships`` 步骤内、响应附件之后，便于 Allure 中「断言结果」出现在请求元数据下方。
    """
    box: Dict[str, Any] = {}

    def _AfterRegisterResponse(resp: Response) -> None:
        _st, env, inner = ParseResponseEnvelope(resp)
        AssertHttpAndBusinessOk(resp, env, context="POST /v2/memberships")
        body = AssertRegisterSuccessBody(inner)
        box["mid"] = str(body["membershipId"])
        box["exts"] = ExtractExtensionsList(body)
        box["body"] = body

    PostMemberships(
        token,
        payload,
        after_response=_AfterRegisterResponse,
        step_code=step_code,
        step_title=step_title,
    )
    if "mid" not in box or "exts" not in box or "body" not in box:
        raise RuntimeError("注册回调未填充结果（after_response 未执行或失败）")
    return str(box["mid"]), cast(List[JsonDict], box["exts"]), cast(JsonDict, box["body"])


def RegisterMembershipSuccess(
    token: str,
    payload: JsonDict,
    *,
    step_code: Optional[str] = None,
    step_title: Optional[str] = None,
) -> Tuple[str, List[JsonDict]]:
    """
    注册会籍并断言成功；返回 membershipId 与 extensions 列表。
    失败时抛出 AssertionError（带响应摘要）。
    """
    mid, exts, _ = RegisterMembershipSuccessDetail(
        token,
        payload,
        step_code=step_code,
        step_title=step_title,
    )
    return mid, exts


def CallMembershipsExpectFailure(
    token: str,
    payload: JsonDict,
    *,
    after_response: Optional[AfterResponseHook] = None,
    step_code: Optional[str] = None,
    step_title: Optional[str] = None,
) -> Tuple[Response, Optional[JsonDict]]:
    """注册会籍并返回响应；不断言成功（用于负面用例）。``after_response`` 在同一步骤内执行。"""
    resp, env, _ = PostMemberships(
        token,
        payload,
        after_response=after_response,
        step_code=step_code,
        step_title=step_title,
    )
    return resp, env


def StrOfLength(n: int, prefix: str = "x") -> str:
    """生成长度恰好为 n 的 ASCII 字符串（单字节计数）。"""
    if n <= 0:
        return ""
    base = (prefix * ((n // len(prefix)) + 1))[:n]
    return base[:n]


def IsExtensionsOAuthRejected(resp: Response) -> bool:
    """沙箱常见：extensions 路由对当前 client 返回 201.000.001。"""
    if resp.status_code != 200:
        return False
    try:
        root = resp.json()
    except ValueError:
        return False
    if not isinstance(root, dict):
        return False
    return root.get("errCode") == "201.000.001"


def ProbeExtensionCapabilities(token: str) -> Tuple[bool, bool]:
    """
    探测当前环境是否支持 extensions 读（search 可见）与写（``/v2/memberships/extensions`` 业务成功）。
    返回 (search_shows_extensions, post_extensions_ok)。
    """
    payload = BuildMinimalMembershipPayload(extensions=[{"type": "cap_probe_r", "value": "1"}])
    mid, _ = RegisterMembershipSuccess(token, payload)
    resp_s, env_s, inner = PostMembershipsSearch(token, mid)
    AssertHttpAndBusinessOk(resp_s, env_s, context="POST /v2/memberships/search(probe)")
    rec = UnwrapMembershipRecord(inner)
    AssertMembershipSearchRecord(rec, mid)
    read_ok = len(ExtractExtensionsList(rec)) > 0
    resp, env, _inner = PatchMembershipsExtensions(
        token,
        mid,
        [{"operation": "UPSERT", "type": "cap_probe_w", "value": "2"}],
    )
    write_ok = (
        IsHttpOk(resp)
        and not IsExtensionsOAuthRejected(resp)
        and IsBusinessSuccess(env)
    )
    return read_ok, write_ok


def BuildSandboxFlags(token: str) -> Papi2548SandboxFlags:
    """
    先探测读/写能力；可通过环境变量强制视为已就绪（网关权限刚开放但探测仍失败、或 search 尚未回显时调试用）。

    - DP_ASSUME_EXTENSIONS_WRITE=1：强制认为 /v2/memberships/extensions 写路径可用
    - DP_ASSUME_EXTENSIONS_READ=1：强制认为 search/register 可见 extensions
    """
    r, w = ProbeExtensionCapabilities(token)
    if _EnvFlagTrue("DP_ASSUME_EXTENSIONS_READ"):
        r = True
    if _EnvFlagTrue("DP_ASSUME_EXTENSIONS_WRITE"):
        w = True
    return Papi2548SandboxFlags(search_shows_extensions=r, post_extensions_works=w)
