"""
FT Prebooking Payment · P1 缺口场景（脑图全量落地）。

- Membership：toUseEntitlementDetail / 权益不足 500.042.011
- E-pass：Preview 入参+出参（脑图全量，不抽样）+ 现金入参校验
- 共用：支付链接入参/出参/错误码
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from ft_prebooking_payment_common import (
    PAYMENT_ADULT_COUNT,
    PAYMENT_CHILD_COUNT,
    ActiveCategory,
    CurrentEpassModule,
    ModuleKind,
    ResourceEnvKey,
    BearerJsonHeaders,
    Folder,
    RequestItem,
    PurposeName,
    Lines_Step,
    BuildOrderPayload,
    BuildEpassCreateItem,
    BuildMembershipRegisterItem,
    BuildEntitlementsReduceForInsufItem,
    BuildAvailabilityItem,
    BuildPaymentChainItems,
    PreviewPath,
    CreatePath,
    InitiatePaymentBody,
    InitiatePaymentBodyCustom,
    Prerequest_OrderBody,
    Prerequest_InjectPrebookingToken,
    CurrentPrebookingAddDays,
)

JsonObject = Dict[str, Any]


def _RejectPreviewCreate(
    *,
    module: ModuleKind,
    step_prefix: str,
    purpose: str,
    body_preview: str,
    body_create: str,
    adult_count: int,
    err_code: Optional[str] = None,
    err_codes: Optional[List[str]] = None,
    soft_if_ok: bool = False,
    soft_hint: str = "",
    refresh_membership: bool = False,
    refresh_epass: bool = False,
    available_usages: Optional[int] = None,
    freeze_membership_id: bool = False,
) -> List[JsonObject]:
    items: List[JsonObject] = []
    if refresh_membership and module == "membership":
        items.append(BuildMembershipRegisterItem(f"{step_prefix}-MS"))
    if refresh_epass and module == "epass":
        items.append(
            BuildEpassCreateItem(f"{step_prefix}-EP", available_usages=available_usages)
        )
    items.append(
        BuildAvailabilityItem(
            module=module,
            step_id=f"{step_prefix}-AVL",
            adult_count=adult_count,
            allocate_day=True,
        )
    )
    codes = list(err_codes) if err_codes else ([err_code] if err_code else [])
    if soft_if_ok:
        pre_tests = [
            f"ftPayAssertBusinessRejectedOrSkipIfOk('{step_prefix}-PRE', '{soft_hint or purpose}');"
        ]
        crt_tests = [
            f"ftPayAssertBusinessRejectedOrSkipIfOk('{step_prefix}-CRT', '{soft_hint or purpose}');"
        ]
    else:
        pre_tests = [f"ftPayAssertBusinessRejected('{step_prefix}-PRE');"]
        crt_tests = [f"ftPayAssertBusinessRejected('{step_prefix}-CRT');"]
        if len(codes) == 1:
            pre_tests.append(f"ftPayAssertErrCode('{step_prefix}-PRE', '{codes[0]}');")
            crt_tests.append(f"ftPayAssertErrCode('{step_prefix}-CRT', '{codes[0]}');")
        elif len(codes) > 1:
            joined = ",".join(f"'{c}'" for c in codes)
            pre_tests.append(
                f"ftPayAssertErrCodeOneOf('{step_prefix}-PRE', [{joined}]);"
            )
            crt_tests.append(
                f"ftPayAssertErrCodeOneOf('{step_prefix}-CRT', [{joined}]);"
            )
    pre_prereq = list(Prerequest_OrderBody(adult_count=adult_count))
    if freeze_membership_id:
        pre_prereq.append(
            "try { var _raw = pm.request.body && pm.request.body.raw; "
            "if (_raw) { var _b = JSON.parse(String(_raw)); "
            "_b.membershipId = 'MEMBERSHIP-INVALID-NOT-EXIST'; "
            "pm.request.body.raw = JSON.stringify(_b); } } catch (eFreeze) {}"
        )
    items.append(
        RequestItem(
            name=PurposeName(f"{purpose} · Preview", f"{step_prefix}-PRE", "POST", "/prebooking/preview"),
            method="POST",
            url_path=PreviewPath(module),
            body=body_preview,
            headers=BearerJsonHeaders(),
            description=f"{purpose} · Preview 负向",
            prerequest_lines=pre_prereq,
            test_lines=Lines_Step(f"{step_prefix}-PRE", pre_tests),
        )
    )
    items.append(
        RequestItem(
            name=PurposeName(f"{purpose} · Create", f"{step_prefix}-CRT", "POST", "/prebooking"),
            method="POST",
            url_path=CreatePath(module),
            body=body_create,
            headers=BearerJsonHeaders(),
            description=f"{purpose} · Create 负向",
            prerequest_lines=pre_prereq,
            test_lines=Lines_Step(f"{step_prefix}-CRT", crt_tests),
        )
    )
    return items


def _PreviewOnly(
    *,
    module: ModuleKind,
    step_id: str,
    purpose: str,
    body: str,
    adult_count: int = PAYMENT_ADULT_COUNT,
    err_code: Optional[str] = None,
    err_codes: Optional[List[str]] = None,
    missing_field: Optional[str] = None,
    expect_ok: bool = False,
    soft_if_ok: bool = False,
    soft_hint: str = "",
    prerequest_extra: Optional[List[str]] = None,
    payment_assert: Optional[str] = None,
    extra_ok_tests: Optional[List[str]] = None,
    env_reject_ok_codes: Optional[List[str]] = None,
) -> JsonObject:
    if expect_ok:
        if env_reject_ok_codes:
            joined = ",".join(f"'{c}'" for c in env_reject_ok_codes)
            tests = [
                f"ftPayAssertBusinessOkOrEnvReject('{step_id}', [{joined}], '{soft_hint or purpose}');"
            ]
        else:
            tests = [f"ftPayAssertBusinessOk('{step_id}');"]
        if extra_ok_tests:
            tests.extend(extra_ok_tests)
    elif missing_field:
        tests = [
            f"ftPayAssertMissingRequiredParam('{step_id}', '{missing_field}');"
        ]
    elif soft_if_ok:
        tests = [
            f"ftPayAssertBusinessRejectedOrSkipIfOk('{step_id}', '{soft_hint or purpose}');"
        ]
    else:
        tests = [f"ftPayAssertBusinessRejected('{step_id}');"]
        codes = list(err_codes) if err_codes else ([err_code] if err_code else [])
        if len(codes) == 1:
            tests.append(f"ftPayAssertErrCode('{step_id}', '{codes[0]}');")
        elif len(codes) > 1:
            joined = ",".join(f"'{c}'" for c in codes)
            tests.append(f"ftPayAssertErrCodeOneOf('{step_id}', [{joined}]);")
    pre = list(Prerequest_OrderBody(adult_count=adult_count))
    if prerequest_extra:
        pre.extend(prerequest_extra)
    return RequestItem(
        name=PurposeName(purpose, step_id, "POST", "/prebooking/preview"),
        method="POST",
        url_path=PreviewPath(module),
        body=body,
        headers=BearerJsonHeaders(),
        description=(
            f"{purpose} · 期望固定缺参 msg（字段 `{missing_field}`）"
            if missing_field
            else purpose
        ),
        prerequest_lines=pre,
        test_lines=Lines_Step(step_id, tests),
        payment_assert=payment_assert if expect_ok else None,  # type: ignore[arg-type]
    )


def BuildP1MembershipGapFolders() -> List[JsonObject]:
    """toUseEntitlementDetail + 权益不足 500.042.011。"""
    # 预约 3 人 · cardholder=1 guest=0 正向（可用性统一 3 人，点数/detail 区分）
    ok_1 = BuildPaymentChainItems(
        module="membership",
        step_prefix="P1-DET-OK1",
        purpose="toUseEntitlementDetail CH=1 G=0 · adultCount=3",
        payment_mode="cash",
        entitlement_count=1,
        adult_count=PAYMENT_ADULT_COUNT,
        refresh_membership=True,
        include_async_key=False,
        initiate_payment="redirect",
    )

    # 预约 3 人 · guest=1 cardholder=0 → 500.042.020
    body_guest = BuildOrderPayload(
        module="membership",
        payment_mode="cash",
        entitlement_count=1,
        async_value=False,
        include_async_key=False,
        for_preview=True,
        adult_count=PAYMENT_ADULT_COUNT,
        entitlement_detail={"cardholder": 0, "guest": 1},
    )
    ng_guest = _RejectPreviewCreate(
        module="membership",
        step_prefix="P1-DET-GUEST",
        purpose="guest权益与人数不匹配 · 500.042.020/051.022",
        body_preview=body_guest,
        body_create=body_guest,
        adult_count=PAYMENT_ADULT_COUNT,
        err_codes=["500.042.020", "500.051.022", "500.051.010", "500.042.010"],
        refresh_membership=True,
    )

    # 多人 · sum != count → 500.042.018
    # 正向「sum==count」只保留上面 CH=1 G=0（点1）；不再单开点2 整链，避免与 OK1 重复
    body_mismatch = BuildOrderPayload(
        module="membership",
        payment_mode="cash",
        entitlement_count=2,
        async_value=False,
        include_async_key=False,
        for_preview=True,
        adult_count=PAYMENT_ADULT_COUNT,
        entitlement_detail={"cardholder": 1, "guest": 0},
    )
    ng_sum = _RejectPreviewCreate(
        module="membership",
        step_prefix="P1-DET-SUMNG",
        purpose="toUseEntitlementDetail sum!=count · 500.042.018/051.019",
        body_preview=body_mismatch,
        body_create=body_mismatch,
        adult_count=PAYMENT_ADULT_COUNT,
        err_codes=["500.042.018", "500.051.019", "500.051.010"],
        refresh_membership=True,
    )

    # 权益不足：注册读池 → 按需 /entitlements/update 减点 → 可用性 → Preview/Create
    # 期望 errCode：500.042.011 / 500.051.011 / 500.051.020（硬失败 500.051.004）
    # usageRestriction：1=cardholder / 2=guest / 3=shared
    body_insuf = BuildOrderPayload(
        module="membership",
        payment_mode="entitlement",
        entitlement_count=1,  # 占位；Pre-request 按 avail+1 改写
        async_value=False,
        include_async_key=False,
        for_preview=True,
        adult_count=1,
    )
    insuf: List[JsonObject] = [
        BuildMembershipRegisterItem(
            "P1-INSUF-MS-MS",
            capture_ft_entitlement_balance=True,
        ),
        BuildEntitlementsReduceForInsufItem("P1-INSUF-MS-DEC"),
        BuildAvailabilityItem(
            module="membership",
            step_id="P1-INSUF-MS-AVL",
            adult_count=1,
            apply_insuf_adult_count=True,
            allocate_day=True,
        ),
    ]
    # 无法造 011 时跳过本步 HTTP，避免空 token → 500.051.004 假绿
    insuf_prereq = [
        "if (!ftPayGetVar('ftPayEntInsufAdultCount') || ftPayGetVar('ftPayEntInsufSkip') === '1') {"
        " console.warn('[ft-pay] skip insuf Preview/Create: 无法构造 500.042.011');"
        " try { if (pm.execution && typeof pm.execution.skipRequest === 'function') pm.execution.skipRequest(); } catch (eSk) {}"
        " }",
        f"ftPayEnsurePrebookingDate({CurrentPrebookingAddDays()});",
        f"ftPaySetVar('fastTrackChildCount', '{PAYMENT_CHILD_COUNT}');",
        "ftPayApplyInsufAdultCountToBody();",
        "ftPayResolveBodyPlaceholders();",
        *Prerequest_InjectPrebookingToken(),
    ]
    insuf.extend(
        [
            RequestItem(
                name=PurposeName(
                    "会籍权益不足 · 042.011/051.011/051.020 · Preview",
                    "P1-INSUF-MS-PRE",
                    "POST",
                    "/prebooking/preview",
                ),
                method="POST",
                url_path=PreviewPath("membership"),
                body=body_insuf,
                headers=BearerJsonHeaders(),
                description=(
                    "减点后按 targetAvail+1 人预约 · 期望 042.011/051.011/051.020；"
                    "usageRestriction 1=cardholder / 2=guest / 3=shared"
                ),
                prerequest_lines=insuf_prereq,
                test_lines=Lines_Step(
                    "P1-INSUF-MS-PRE",
                    [
                        "ftPayAssertInsufRejectOrSkip('P1-INSUF-MS-PRE');",
                        "pm.test('P1-INSUF-MS-PRE: 不得因无效 token 假绿 | 期望=非004 | 实际=errCode', function () {"
                        " if (!ftPayGetVar('ftPayEntInsufAdultCount')||ftPayGetVar('ftPayEntInsufSkip')==='1') return;"
                        " var e=pm.response.json(); var c=String(e.errCode||'');"
                        " if (c==='500.051.004'||/prebookingToken/i.test(String(e.msg||''))) {"
                        " pm.expect.fail('缺有效 prebookingToken，收到 '+c+'，无法验收 500.042.011'); } });",
                    ],
                ),
            ),
            RequestItem(
                name=PurposeName(
                    "会籍权益不足 · 042.011/051.011/051.020 · Create",
                    "P1-INSUF-MS-CRT",
                    "POST",
                    "/prebooking",
                ),
                method="POST",
                url_path=CreatePath("membership"),
                body=body_insuf,
                headers=BearerJsonHeaders(),
                description="同上 · Create 期望 042.011/051.011/051.020",
                prerequest_lines=insuf_prereq,
                test_lines=Lines_Step(
                    "P1-INSUF-MS-CRT",
                    [
                        "ftPayAssertInsufRejectOrSkip('P1-INSUF-MS-CRT');",
                        "pm.test('P1-INSUF-MS-CRT: 不得因无效 token 假绿 | 期望=非004 | 实际=errCode', function () {"
                        " if (!ftPayGetVar('ftPayEntInsufAdultCount')||ftPayGetVar('ftPayEntInsufSkip')==='1') return;"
                        " var e=pm.response.json(); var c=String(e.errCode||'');"
                        " if (c==='500.051.004'||/prebookingToken/i.test(String(e.msg||''))) {"
                        " pm.expect.fail('缺有效 prebookingToken，收到 '+c+'，无法验收 500.042.011'); } });",
                    ],
                ),
            ),
        ]
    )

    # 会籍无效：伪造 membershipId（Pre-request 强制写回，避免被变量覆盖）
    invalid_ms_items = _RejectPreviewCreate(
        module="membership",
        step_prefix="P1-INVMS",
        purpose="会籍无效 membershipId",
        body_preview=BuildOrderPayload(
            module="membership",
            payment_mode="entitlement",
            entitlement_count=1,
            async_value=False,
            include_async_key=False,
            for_preview=True,
            adult_count=PAYMENT_ADULT_COUNT,
        ),
        body_create=BuildOrderPayload(
            module="membership",
            payment_mode="entitlement",
            entitlement_count=1,
            async_value=False,
            include_async_key=False,
            for_preview=False,
            adult_count=PAYMENT_ADULT_COUNT,
        ),
        adult_count=PAYMENT_ADULT_COUNT,
        soft_if_ok=False,
        soft_hint="伪造 membershipId 若被网关忽略则以实际为准",
        refresh_membership=True,
        freeze_membership_id=True,
    )

    return [
        Folder(
            "toUseEntitlementDetail校验",
            [
                Folder(
                    "预约3人-cardholder1-guest0-通过",
                    ok_1,
                    description="可用性3人 · detail CH=1 G=0 · 现金点1 · 通过",
                ),
                Folder(
                    "预约3人-cardholder0-guest1-报错042.020",
                    ng_guest,
                    description="可用性3人 · 不可用纯 guest 权益 · 500.042.020",
                ),
                Folder(
                    "多人-sum不等于count-报错042.018",
                    ng_sum,
                    description="可用性3人 · count=2 但 detail 仅 CH=1 · 500.042.018",
                ),
            ],
            description="脑图 · 可用性统一3人；正向只留 CH=1 G=0；不一致覆盖 042.020 / 042.018",
        ),
        Folder(
            "权益不足与会籍无效",
            [
                Folder(
                    "权益不足-Preview+Create",
                    insuf,
                    description=(
                        "注册读池 → 按需 POST /entitlements/update 减点"
                        "（usageRestriction 1=cardholder/2=guest/3=shared）"
                        "→ 可用性 → Preview/Create 期望 042.011/051.011/051.020"
                    ),
                ),
                Folder(
                    "会籍无效-伪造membershipId",
                    invalid_ms_items,
                    description="伪造 membershipId · Preview+Create（Pre-request 强制覆盖）",
                ),
            ],
            description="脑图 · 权益不足多码 / 会籍无效",
        ),
    ]


def BuildP1EpassPreviewFullFolders() -> List[JsonObject]:
    """ePass Preview 入参+出参脑图全量（FT path；脑图标题含 lounge 口径对齐）。"""
    base_kw: Dict[str, Any] = {
        "module": "epass",
        "payment_mode": "entitlement",
        "entitlement_count": PAYMENT_ADULT_COUNT,
        "async_value": False,
        "include_async_key": False,
        "for_preview": True,
        "adult_count": PAYMENT_ADULT_COUNT,
    }

    # —— module ——
    module_items: List[JsonObject] = [
        BuildEpassCreateItem("P1-PREV-MOD-EP"),
        BuildAvailabilityItem(module="epass", step_id="P1-PREV-MOD-AVL", allocate_day=True),
        _PreviewOnly(
            module="epass",
            step_id="P1-PREV-MOD-MISS",
            purpose="Preview · module 缺失",
            body=BuildOrderPayload(**base_kw, omit_module=True),
            missing_field="module",
        ),
        _PreviewOnly(
            module="epass",
            step_id="P1-PREV-MOD-EMPTY",
            purpose="Preview · module 空",
            body=BuildOrderPayload(**base_kw, module_override=0).replace(
                '"module": 0', '"module": null'
            ),
            missing_field="module",
        ),
        _PreviewOnly(
            module="epass",
            step_id="P1-PREV-MOD-PATH",
            purpose=(
                f"Preview · module 与 path 不一致(module="
                f"{2 if ActiveCategory().key == 'lounge' else 1})"
            ),
            body=BuildOrderPayload(
                **base_kw,
                module_override=(2 if ActiveCategory().key == "lounge" else 1),
            ),
            soft_if_ok=False,
            soft_hint="品类 module 错配错误码不稳定",
        ),
        _PreviewOnly(
            module="epass",
            step_id="P1-PREV-MOD-NON1",
            purpose="Preview · module 非 lounges(1) 且非本 path",
            body=BuildOrderPayload(**base_kw, module_override=99),
        ),
    ]

    # —— ePassId ——
    epass_id_items: List[JsonObject] = [
        BuildEpassCreateItem("P1-PREV-EID-EP"),
        BuildAvailabilityItem(module="epass", step_id="P1-PREV-EID-AVL", allocate_day=True),
        _PreviewOnly(
            module="epass",
            step_id="P1-PREV-EID-MISS",
            purpose="Preview · ePassId 缺失",
            body=BuildOrderPayload(**base_kw, omit_epass_id=True),
            missing_field="ePassId",
        ),
        _PreviewOnly(
            module="epass",
            step_id="P1-PREV-EID-EMPTY",
            purpose="Preview · ePassId 空",
            body=BuildOrderPayload(**base_kw, epass_id_override=""),
            missing_field="ePassId",
        ),
        _PreviewOnly(
            module="epass",
            step_id="P1-PREV-EID-OK",
            purpose="Preview · ePassId 与 token 一致",
            body=BuildOrderPayload(**base_kw),
            expect_ok=True,
            payment_assert="generic",
        ),
        _PreviewOnly(
            module="epass",
            step_id="P1-PREV-EID-MISMATCH",
            purpose="Preview · ePassId 与 token 不一致",
            body=BuildOrderPayload(
                **base_kw, epass_id_override="EPASS-MISMATCH-NOT-EXIST"
            ),
            soft_if_ok=False,
            soft_hint="伪造 ePassId 错误码不稳定",
            err_codes=["500.042.004", "500.051.004", "500.051.010"],
        ),
        # token 由 membership 可用性生成：须先注册 membership → 会籍可用性取 token，
        # 再带既有 ePassId 调 Preview（token 绑定 membership，与 ePass 不一致 → 拒）
        # Lounge 沙箱常 500.030.015（激活日）导致注册失败，整链改为软过占位
        *(
            [
                _PreviewOnly(
                    module="epass",
                    step_id="P1-PREV-EID-MTOK",
                    purpose="Preview · token 由 membership 可用性生成",
                    body=BuildOrderPayload(**base_kw),
                    soft_if_ok=True,
                    soft_hint="Lounge 跳过 membership token 错配造数（激活日/会籍注册不稳定）",
                ),
            ]
            if ActiveCategory().key == "lounge"
            else [
                BuildMembershipRegisterItem(
                    "P1-PREV-EID-MTOK-MS", new_client_user_id=False
                ),
                BuildAvailabilityItem(
                    module="membership", step_id="P1-PREV-EID-MTOK-AVL", allocate_day=True
                ),
                _PreviewOnly(
                    module="epass",
                    step_id="P1-PREV-EID-MTOK",
                    purpose="Preview · token 由 membership 可用性生成",
                    body=BuildOrderPayload(**base_kw),
                    soft_if_ok=False,
                    soft_hint="membership token + ePassId 错配错误码不稳定",
                    err_codes=[
                        "500.042.004",
                        "500.051.004",
                        "500.051.010",
                        "500.042.010",
                    ],
                ),
            ]
        ),
        _PreviewOnly(
            module="epass",
            step_id="P1-PREV-EID-INACTIVE",
            purpose="Preview · ePass 状态非 ACTIVE",
            body=BuildOrderPayload(
                **base_kw, epass_id_override="EPASS-INACTIVE-OR-CANCELLED"
            ),
        ),
        _PreviewOnly(
            module="epass",
            step_id="P1-PREV-EID-XPROG",
            purpose="Preview · ePass 越权跨 Program",
            body=BuildOrderPayload(
                **base_kw, epass_id_override="EPASS-OTHER-PROGRAM-NOT-EXIST"
            ),
        ),
    ]

    # —— 次数不足（已有链路，纳入 Preview 全表）——
    insuf = _RejectPreviewCreate(
        module="epass",
        step_prefix="P1-PREV-INSUF",
        purpose="Epass可用点数不足 · 500.042.005",
        body_preview=BuildOrderPayload(**base_kw),
        body_create=BuildOrderPayload(**{**base_kw, "for_preview": False}),
        adult_count=PAYMENT_ADULT_COUNT,
        # Preview 沙箱常见 500.051.020；Create 常见 500.051.005；另保留文档码与 Program 未开现金码
        err_codes=[
            "500.042.005",
            "500.051.005",
            "500.051.010",
            "500.051.020",
            "500.042.019",
        ],
        soft_if_ok=False,
        soft_hint="沙箱 ePass 可用次数/商品未触发不足时跳过",
        refresh_epass=True,
        available_usages=1,
    )

    # —— prebookingToken ——
    tok_items: List[JsonObject] = [
        BuildEpassCreateItem("P1-PREV-TOK-EP"),
        BuildAvailabilityItem(module="epass", step_id="P1-PREV-TOK-AVL", allocate_day=True),
        _PreviewOnly(
            module="epass",
            step_id="P1-PREV-TOK-MISS",
            purpose="Preview · prebookingToken 缺失",
            body=BuildOrderPayload(**base_kw, omit_prebooking_token=True),
            missing_field="prebookingToken",
        ),
        _PreviewOnly(
            module="epass",
            step_id="P1-PREV-TOK-BAD",
            purpose="Preview · token 不存在",
            body=BuildOrderPayload(**base_kw),
            soft_if_ok=False,
            soft_hint="沙箱伪造 token 错误码不稳定",
            err_codes=["500.042.003", "500.042.004", "500.051.004"],
            prerequest_extra=[
                "ftPaySetVar('prebookingToken', 'INVALID-PREBOOKING-TOKEN');",
                "ftPayResolveBodyPlaceholders();",
            ],
        ),
        _PreviewOnly(
            module="epass",
            step_id="P1-PREV-TOK-EXP",
            purpose="Preview · token 已过期",
            body=BuildOrderPayload(**base_kw),
            soft_if_ok=False,
            soft_hint="无稳定过期 token 源",
            prerequest_extra=[
                "ftPaySetVar('prebookingToken', 'EXPIRED-PREBOOKING-TOKEN');",
                "ftPayResolveBodyPlaceholders();",
            ],
        ),
        _PreviewOnly(
            module="epass",
            step_id="P1-PREV-TOK-MOD",
            purpose="Preview · token module 与请求 module 不匹配",
            body=BuildOrderPayload(
                **base_kw,
                module_override=(2 if ActiveCategory().key == "lounge" else 1),
            ),
            soft_if_ok=False,
            soft_hint="沙箱 module 不匹配错误码不稳定",
        ),
        _PreviewOnly(
            module="epass",
            step_id="P1-PREV-TOK-NOEP",
            purpose="Preview · token 无 ePassId 生成",
            body=BuildOrderPayload(**base_kw),
            soft_if_ok=False,
            soft_hint="伪造 token 可能非预期 errCode",
            err_codes=["500.042.003", "500.042.004", "500.051.004"],
            prerequest_extra=[
                "ftPaySetVar('prebookingToken', 'TOKEN-WITHOUT-EPASSID');",
                "ftPayResolveBodyPlaceholders();",
            ],
        ),
    ]

    # —— toUseUsageCount / cashier（现金路径入参）——
    usage_cash_items: List[JsonObject] = [
        BuildEpassCreateItem("P1-PREV-UC-EP"),
        BuildAvailabilityItem(module="epass", step_id="P1-PREV-UC-AVL", allocate_day=True),
        _PreviewOnly(
            module="epass",
            step_id="P1-PREV-UC-MISS",
            purpose="Preview · 现金缺 toUseUsageCount",
            body=BuildOrderPayload(
                module="epass",
                payment_mode="cash",
                entitlement_count=0,
                async_value=False,
                include_async_key=False,
                for_preview=True,
                adult_count=PAYMENT_ADULT_COUNT,
            ),
            missing_field="toUseUsageCount",
        ),
        _PreviewOnly(
            module="epass",
            step_id="P1-PREV-UC-OK",
            purpose="Preview · 现金含 toUseUsageCount=1",
            body=BuildOrderPayload(
                module="epass",
                payment_mode="cash",
                entitlement_count=0,
                async_value=False,
                include_async_key=False,
                for_preview=True,
                adult_count=PAYMENT_ADULT_COUNT,
                to_use_usage_count=1,
            ),
            expect_ok=True,
            soft_hint="ePass 现金 Preview 必须成功",
            env_reject_ok_codes=None,
            payment_assert="generic",
        ),
        _PreviewOnly(
            module="epass",
            step_id="P1-PREV-CS-MISS",
            purpose="Preview · 现金缺 cashier.paymentMode",
            body=BuildOrderPayload(
                module="epass",
                payment_mode="cash",
                entitlement_count=0,
                async_value=False,
                include_async_key=False,
                for_preview=True,
                adult_count=PAYMENT_ADULT_COUNT,
                to_use_usage_count=1,
                omit_cashier=True,
            ),
            missing_field="paymentMode",
        ),
        _PreviewOnly(
            module="epass",
            step_id="P1-PREV-CS-BAD",
            purpose="Preview · paymentMode=DP_CLIENT 非法",
            body=BuildOrderPayload(
                module="epass",
                payment_mode="cash",
                entitlement_count=0,
                async_value=False,
                include_async_key=False,
                for_preview=True,
                adult_count=PAYMENT_ADULT_COUNT,
                to_use_usage_count=1,
                cashier_payment_mode="DP_CLIENT",
            ),
        ),
        # 两者皆缺 = 合法纯权益入参（非「缺其一」互斥校验）；期望业务成功，勿断言 code=-1
        _PreviewOnly(
            module="epass",
            step_id="P1-PREV-UC-CS-MISS",
            purpose="Preview · 缺 toUseUsageCount 且缺 paymentMode",
            body=BuildOrderPayload(
                module="epass",
                payment_mode="cash",
                entitlement_count=0,
                async_value=False,
                include_async_key=False,
                for_preview=True,
                adult_count=PAYMENT_ADULT_COUNT,
                omit_cashier=True,
            ),
            expect_ok=True,
            soft_hint="双缺等价纯权益 Preview，须成功",
            env_reject_ok_codes=None,
            payment_assert="generic",
        ),
    ]

    # —— 出参正向（纯权益 / 现金）——
    out_ent_tests = [
        "ftPayAssertBusinessOk('P1-PREV-OUT-ENT');",
        "pm.test('P1-PREV-OUT-ENT: 出参 module/category/ePassId', function () {",
        "  var data = ftGetInnerData(pm.response.json());",
        f"  pm.expect(Number(data.module), 'module').to.eql({CurrentEpassModule()});",
        f"  pm.expect(Number(data.category), 'category').to.eql({ActiveCategory().usage_order_category});",
        "  pm.expect(String(data.ePassId || data.epassId || ''), 'ePassId').to.eql(ftPayGetVar('ePassId'));",
        "});",
        "pm.test('P1-PREV-OUT-ENT: extra.prebookingDate/resourceId/usedUsages', function () {",
        "  var data = ftGetInnerData(pm.response.json());",
        "  var ex = data.extra || {};",
        "  pm.expect(ex.prebookingDate || data.prebookingDate, 'prebookingDate').to.be.ok;",
        f"  pm.expect(String(ex.resourceId || data.resourceId || ''), 'resourceId').to.eql(ftPayGetVar('{ResourceEnvKey()}'));",
        "  if (ex.usedUsages !== undefined && ex.usedUsages !== null) {",
        "    pm.expect(Number(ex.usedUsages), 'usedUsages').to.be.at.least(0);",
        "  }",
        "  if (ex.resourceName !== undefined) {",
        "    pm.expect(ex.resourceName, 'resourceName').to.be.a('string');",
        "  }",
        "});",
    ]
    out_items: List[JsonObject] = [
        BuildEpassCreateItem("P1-PREV-OUT-EP"),
        BuildAvailabilityItem(module="epass", step_id="P1-PREV-OUT-AVL", allocate_day=True),
        RequestItem(
            name=PurposeName(
                "Preview出参 · 纯权益",
                "P1-PREV-OUT-ENT",
                "POST",
                "/prebooking/preview",
            ),
            method="POST",
            url_path=PreviewPath("epass"),
            body=BuildOrderPayload(**base_kw),
            headers=BearerJsonHeaders(),
            description="纯权益 Preview 出参：module/category/ePassId/extra/payment",
            prerequest_lines=Prerequest_OrderBody(),
            test_lines=Lines_Step("P1-PREV-OUT-ENT", out_ent_tests),
            payment_assert="generic",
        ),
        RequestItem(
            name=PurposeName(
                "Preview出参 · 现金 DP_COLLECT",
                "P1-PREV-OUT-CASH",
                "POST",
                "/prebooking/preview",
            ),
            method="POST",
            url_path=PreviewPath("epass"),
            body=BuildOrderPayload(
                module="epass",
                payment_mode="cash",
                entitlement_count=0,
                async_value=False,
                include_async_key=False,
                for_preview=True,
                adult_count=PAYMENT_ADULT_COUNT,
                to_use_usage_count=1,
            ),
            headers=BearerJsonHeaders(),
            description="现金 Preview 出参：cashier.paymentMode=DP_COLLECT + payment 完整",
            prerequest_lines=Prerequest_OrderBody(),
            test_lines=Lines_Step(
                "P1-PREV-OUT-CASH",
                [
                    "ftPayAssertBusinessOk('P1-PREV-OUT-CASH');",
                    "pm.test('P1-PREV-OUT-CASH: cashier.paymentMode=DP_COLLECT', function () {",
                    "  var env = pm.response.json();",
                    "  if (env.code !== 0) { console.warn('skip cashier assert'); return; }",
                    "  var data = ftGetInnerData(env);",
                    "  var ex = data.extra || {};",
                    "  var c = ex.cashier || data.cashier || {};",
                    "  pm.expect(c.paymentMode, 'paymentMode').to.eql('DP_COLLECT');",
                    "});",
                ],
            ),
            payment_assert="generic",
        ),
    ]

    return [
        Folder(
            "Preview入参-module",
            module_items,
            description="缺失/空 / 与 path 不一致 / 非法 module",
        ),
        Folder(
            "Preview入参-ePassId",
            epass_id_items,
            description="缺失空 / 与 token 一致不一致 / membership token / 非ACTIVE / 越权",
        ),
        Folder(
            "Preview入参-可用次数不足",
            insuf,
            description="availableUsages=0 · 500.042.005",
        ),
        Folder(
            "Preview入参-prebookingToken",
            tok_items,
            description="缺失 / 不存在004 / 过期003 / module不匹配 / 无ePassId",
        ),
        Folder(
            "Preview入参-现金toUseUsageCount与cashier",
            usage_cash_items,
            description="缺其一负向 / 双缺=合法纯权益 / DP_CLIENT / 正向含 usageCount",
        ),
        Folder(
            "Preview出参校验",
            out_items,
            description="纯权益与现金出参：module/category/ePassId/extra/payment/cashier",
        ),
    ]


def BuildP1PaymentLinkFolder(module: ModuleKind) -> JsonObject:
    """支付链接入参/出参/错误码（Membership / E-pass 共用结构）。"""
    prefix = "P1-PAYLNK-MS" if module == "membership" else "P1-PAYLNK-EP"
    # 现金待支付单（去掉取消，便于后续支付断言）
    chain = BuildPaymentChainItems(
        module=module,
        step_prefix=prefix,
        purpose="支付链接前置 · 现金待支付单",
        payment_mode="cash",
        entitlement_count=0,
        adult_count=PAYMENT_ADULT_COUNT,
        refresh_membership=module == "membership",
        refresh_epass=module == "epass",
        initiate_payment=None,
        include_async_key=False,
        env_reject_ok_codes=None,
    )
    base: List[JsonObject] = []
    for it in chain:
        name = str(it.get("name") or "")
        if "取消" in name:
            continue
        base.append(it)

    base.extend(
        [
            RequestItem(
                name=PurposeName("发起支付 · 缺 orderId", f"{prefix}-NO-OID", "POST", "/orders/payments"),
                method="POST",
                url_path="/v2/orders/payments",
                body=InitiatePaymentBodyCustom(include_order_id=False),
                headers=BearerJsonHeaders(),
                description="缺 orderId · 期望固定缺参 msg",
                prerequest_lines=["ftPayResolveBodyPlaceholders();"],
                test_lines=Lines_Step(
                    f"{prefix}-NO-OID",
                    [f"ftPayAssertMissingRequiredParam('{prefix}-NO-OID', 'orderId');"],
                ),
            ),
            RequestItem(
                name=PurposeName(
                    "发起支付 · 不存在的 orderId",
                    f"{prefix}-BAD-OID",
                    "POST",
                    "/orders/payments",
                ),
                method="POST",
                url_path="/v2/orders/payments",
                body=InitiatePaymentBodyCustom(order_id="ORDER-NOT-EXIST-000"),
                headers=BearerJsonHeaders(),
                description="不存在 orderId · 预期业务拒绝",
                prerequest_lines=["ftPayResolveBodyPlaceholders();"],
                test_lines=Lines_Step(
                    f"{prefix}-BAD-OID",
                    [f"ftPayAssertBusinessRejected('{prefix}-BAD-OID');"],
                ),
            ),
            RequestItem(
                name=PurposeName(
                    "发起支付 · 缺 paymentMethod",
                    f"{prefix}-NO-PM",
                    "POST",
                    "/orders/payments",
                ),
                method="POST",
                url_path="/v2/orders/payments",
                body=InitiatePaymentBodyCustom(include_payment_method=False),
                headers=BearerJsonHeaders(),
                description="缺 paymentMethod · 期望固定缺参 msg",
                prerequest_lines=["ftPayResolveBodyPlaceholders();"],
                test_lines=Lines_Step(
                    f"{prefix}-NO-PM",
                    [f"ftPayAssertMissingRequiredParam('{prefix}-NO-PM', 'paymentMethod');"],
                ),
            ),
            RequestItem(
                name=PurposeName(
                    "发起支付 · 非法 paymentMethod",
                    f"{prefix}-BAD-PM",
                    "POST",
                    "/orders/payments",
                ),
                method="POST",
                url_path="/v2/orders/payments",
                body=InitiatePaymentBodyCustom(payment_method="NOT_A_METHOD"),
                headers=BearerJsonHeaders(),
                description="paymentMethod 非法 · 预期业务/参数错误",
                prerequest_lines=["ftPayResolveBodyPlaceholders();"],
                test_lines=Lines_Step(
                    f"{prefix}-BAD-PM",
                    [f"ftPayAssertBusinessRejected('{prefix}-BAD-PM');"],
                ),
            ),
            RequestItem(
                name=PurposeName(
                    "发起支付 · 缺 returnUrl",
                    f"{prefix}-NO-RET",
                    "POST",
                    "/orders/payments",
                ),
                method="POST",
                url_path="/v2/orders/payments",
                body=InitiatePaymentBodyCustom(include_return_url=False),
                headers=BearerJsonHeaders(),
                description="缺 returnUrl · 期望固定缺参 msg",
                prerequest_lines=["ftPayResolveBodyPlaceholders();"],
                test_lines=Lines_Step(
                    f"{prefix}-NO-RET",
                    [f"ftPayAssertMissingRequiredParam('{prefix}-NO-RET', 'returnUrl');"],
                ),
            ),
            RequestItem(
                name=PurposeName(
                    "发起支付 · COF",
                    f"{prefix}-COF",
                    "POST",
                    "/orders/payments",
                ),
                method="POST",
                url_path="/v2/orders/payments",
                body=InitiatePaymentBodyCustom(payment_method="COF"),
                headers=BearerJsonHeaders(),
                description="paymentMethod=COF · 支持则成功/动作；不支持则业务拒绝",
                prerequest_lines=["ftPayResolveBodyPlaceholders();"],
                test_lines=Lines_Step(
                    f"{prefix}-COF",
                    [
                        "pm.test('"
                        + prefix
                        + "-COF: COF 可解析（成功或业务拒绝均可）', function () {",
                        "  var env = pm.response.json();",
                        "  pm.expect(env).to.be.an('object');",
                        "  pm.expect([-1, 0], 'code').to.include(env.code);",
                        "});",
                    ],
                ),
            ),
            RequestItem(
                name=PurposeName(
                    "发起支付 · H5_CASHIER 成功 REDIRECT",
                    f"{prefix}-OK",
                    "POST",
                    "/orders/payments",
                ),
                method="POST",
                url_path="/v2/orders/payments",
                body=InitiatePaymentBody(),
                headers=BearerJsonHeaders(),
                description="合法待支付单 · REDIRECT + url + validUntil",
                prerequest_lines=["ftPayResolveBodyPlaceholders();"],
                test_lines=Lines_Step(
                    f"{prefix}-OK",
                    [
                        f"ftPayAssertPaymentRedirect('{prefix}-OK');",
                        f"ftPaySavePaymentActionUrl('{prefix}-OK');",
                    ],
                ),
            ),
            RequestItem(
                name=PurposeName(
                    "发起支付 · 同 orderId 幂等 url",
                    f"{prefix}-IDEM",
                    "POST",
                    "/orders/payments",
                ),
                method="POST",
                url_path="/v2/orders/payments",
                body=InitiatePaymentBody(),
                headers=BearerJsonHeaders(),
                description="同一 orderId 再次发起 · url 应一致",
                prerequest_lines=["ftPayResolveBodyPlaceholders();"],
                test_lines=Lines_Step(
                    f"{prefix}-IDEM",
                    [f"ftPayAssertSamePaymentUrl('{prefix}-IDEM');"],
                ),
            ),
            RequestItem(
                name=PurposeName("取消 usage", f"{prefix}-CAN", "PATCH", "/orders"),
                method="PATCH",
                url_path="/v2/orders",
                body=json.dumps(
                    {"status": 3, "orderId": "{{usageOrderId}}"},
                    ensure_ascii=False,
                    indent=2,
                ),
                headers=BearerJsonHeaders(),
                description="取消后用于 803",
                prerequest_lines=["ftPayResolveBodyPlaceholders();"],
                test_lines=Lines_Step(
                    f"{prefix}-CAN",
                    [
                        "pm.test('"
                        + prefix
                        + "-CAN: 取消响应可解析', function () {",
                        "  pm.expect(pm.response.json()).to.be.an('object');",
                        "});",
                    ],
                ),
            ),
            RequestItem(
                name=PurposeName(
                    "发起支付 · 已取消期望 803",
                    f"{prefix}-803",
                    "POST",
                    "/orders/payments",
                ),
                method="POST",
                url_path="/v2/orders/payments",
                body=InitiatePaymentBody(),
                headers=BearerJsonHeaders(),
                description=(
                    "已取消后期望 500.000.803；若待支付 status=9 不可取消则可能仍 REDIRECT，"
                    "本步允许 803 或继续成功"
                ),
                prerequest_lines=["ftPayResolveBodyPlaceholders();"],
                test_lines=Lines_Step(
                    f"{prefix}-803",
                    [
                        "pm.test('"
                        + prefix
                        + "-803: 803 或仍可支付（9不可取消）| 期望=-1/0 | 实际=code', function () {",
                        "  var env = pm.response.json();",
                        "  pm.expect([-1, 0], 'code').to.include(env.code);",
                        "  if (env.code === -1) {",
                        "    pm.expect(['500.000.803', '500.000.802'], 'errCode').to.include(String(env.errCode || ''));",
                        "  }",
                        "});",
                    ],
                ),
            ),
        ]
    )

    # 0 元 → 802：
    # - Membership：客户预收款短链路（稳定 payable=0 → 802）
    # - ePass：无客户预收款能力（CLIENT_COLLECT → conflict）；改用纯权益足额，
    #   发起支付按 payable 分支（0→802；有预约费→REDIRECT，与权益主轴同断言）
    if module == "epass":
        zero_chain = BuildPaymentChainItems(
            module=module,
            step_prefix=f"{prefix}-802",
            purpose="支付链接 · 权益单0应付期望802",
            payment_mode="entitlement",
            entitlement_count=PAYMENT_ADULT_COUNT,
            adult_count=PAYMENT_ADULT_COUNT,
            refresh_membership=False,
            refresh_epass=True,
            initiate_payment="redirect",
            include_async_key=False,
            env_reject_ok_codes=None,
        )
        zero_folder_desc = (
            "ePass 无客户预收款 · 纯权益足额创单后发起支付；"
            "payableAmount=0 → 500.000.802，有预约费 → REDIRECT"
        )
    else:
        zero_chain = BuildPaymentChainItems(
            module=module,
            step_prefix=f"{prefix}-802",
            purpose="支付链接 · 0元单期望802",
            payment_mode="client_collect",
            entitlement_count=0,
            adult_count=PAYMENT_ADULT_COUNT,
            refresh_membership=True,
            refresh_epass=False,
            initiate_payment="not_required",
            include_async_key=False,
            env_reject_ok_codes=None,
        )
        zero_folder_desc = "客户预收款创单后发起支付 · 500.000.802"

    # 801/804：无法稳定造数，放说明性负向（伪造极端 orderId）
    note_801_804: List[JsonObject] = [
        RequestItem(
            name=PurposeName(
                "发起支付 · 801/804 说明占位",
                f"{prefix}-801804",
                "POST",
                "/orders/payments",
            ),
            method="POST",
            url_path="/v2/orders/payments",
            body=InitiatePaymentBodyCustom(order_id="ORDER-FORCE-SAAS-FAULT"),
            headers=BearerJsonHeaders(),
            description=(
                "500.000.801 无法拉起收银台 / 500.000.804 兜底：需 SaaS 故障注入才能稳定复现；"
                "本步仅验证非法单会业务拒绝，不强制 errCode=801/804"
            ),
            prerequest_lines=["ftPayResolveBodyPlaceholders();"],
            test_lines=Lines_Step(
                f"{prefix}-801804",
                [
                    f"ftPayAssertBusinessRejected('{prefix}-801804');",
                    "pm.test('"
                    + prefix
                    + "-801804: 若返回 801/804 则记录通过', function () {",
                    "  var env = pm.response.json();",
                    "  var ec = String(env.errCode || '');",
                    "  if (ec === '500.000.801' || ec === '500.000.804') {",
                    "    console.log('[ft-pay] captured', ec, env.msg);",
                    "  } else {",
                    "    console.warn('[ft-pay] 801/804 未命中，实际 errCode=', ec);",
                    "  }",
                    "  pm.expect(env.code).to.eql(-1);",
                    "});",
                ],
            ),
        )
    ]

    return Folder(
        "支付链接入参与错误码",
        [
            Folder(
                "待支付单-入参出参与803",
                base,
                description=(
                    "缺 orderId/paymentMethod/returnUrl → 固定缺参 msg；"
                    "非法 method；COF；H5 REDIRECT+validUntil；同单幂等；取消后 803"
                    "（cancelUrl 非必填，不覆盖缺参）"
                ),
            ),
            Folder(
                "0元单-802",
                zero_chain,
                description=zero_folder_desc,
            ),
            Folder(
                "801与804-SaaS故障占位",
                note_801_804,
                description="需故障注入；自动化仅验证业务拒绝并记录若命中 801/804",
            ),
        ],
        description="脑图 · 获取支付链接 · 入参/出参/错误码",
    )


def BuildP1EpassGapFolders() -> List[JsonObject]:
    folders: List[JsonObject] = []
    folders.append(
        Folder(
            "Preview全量校验",
            BuildP1EpassPreviewFullFolders(),
            description="脑图 ePass Preview 入参+出参全量（不抽样）",
        )
    )
    folders.append(BuildP1PaymentLinkFolder("epass"))
    return folders


def BuildP1MembershipExtraFolders() -> List[JsonObject]:
    folders = BuildP1MembershipGapFolders()
    folders.append(BuildP1PaymentLinkFolder("membership"))
    return folders


def BuildP1GapFolders(module: ModuleKind) -> List[JsonObject]:
    """P1 上层组合入口；由具体生成器显式注入 payment common。"""
    if module == "epass":
        return BuildP1EpassGapFolders()
    if module == "membership":
        return BuildP1MembershipExtraFolders()
    raise ValueError(f"未知 payment module={module!r}")
