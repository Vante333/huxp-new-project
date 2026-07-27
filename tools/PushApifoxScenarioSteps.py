"""
将 ``*.apifox-2.7.43-import.json`` 中的步骤（含 postProcessors）CLI 写入已有场景。

背景：私有化 ``import --format apifox`` 可能只创建场景元数据而 ``steps=[]``；
本工具用 ``test-scenario update --file`` 补全步骤，实现后置 Tests 全量 CLI 化。

用法::

    python tools/PushApifoxScenarioSteps.py ^
      --project 346275 ^
      --scenario-id 365969 ^
      --api-base-url https://apifox.dragonpass.com.cn ^
      --package apifox-reports/papi_2548/generated/PAPI-2548-membership-extensions.apifox-2.7.43-import.json
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

JsonObject = Dict[str, Any]


def FindApifoxCmd() -> str:
    candidates = [
        Path(os.environ.get("APPDATA", "")) / "npm" / "apifox.cmd",
        Path(os.environ.get("APPDATA", "")) / "npm" / "apifox",
    ]
    for path in candidates:
        if path.is_file():
            return str(path)
    return "apifox"


def RunApifoxJson(args: Sequence[str], *, api_base_url: str, token: str) -> JsonObject:
    cmd = [
        FindApifoxCmd(),
        "--api-base-url",
        api_base_url,
        "--access-token",
        token,
        *args,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    text = (proc.stdout or "").strip()
    if not text:
        text = (proc.stderr or "").strip()
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"apifox non-JSON (exit={proc.returncode}): {text[:800]}") from exc
    if proc.returncode != 0 or payload.get("success") is False:
        raise RuntimeError(f"apifox failed: {payload.get('error') or payload}")
    return payload


def ExtractImportScenarioItem(package: Mapping[str, Any]) -> JsonObject:
    collections = package.get("apiTestCaseCollection")
    if not isinstance(collections, list):
        raise ValueError("package missing apiTestCaseCollection")
    for col in collections:
        if not isinstance(col, dict):
            continue
        for item in col.get("items") or []:
            if not isinstance(item, dict):
                continue
            steps = item.get("steps")
            if isinstance(steps, list) and steps:
                return dict(item)
    raise ValueError("no steps found in package")


def ExtractImportSteps(package: Mapping[str, Any]) -> List[JsonObject]:
    item = ExtractImportScenarioItem(package)
    steps = item.get("steps")
    if not isinstance(steps, list):
        raise ValueError("scenario item steps is not a list")
    return [dict(s) for s in steps if isinstance(s, dict)]


def NormalizeCustomHttpBody(request_body: Any) -> JsonObject:
    """客户端导入形 body → customHttpRequest.requestBody。"""
    if not isinstance(request_body, dict):
        return {"type": "none", "data": ""}
    raw_type = str(request_body.get("type") or "none")
    data = request_body.get("data")
    data_s = "" if data is None else str(data)
    if raw_type in ("application/json", "json"):
        return {"type": "json", "data": data_s}
    if raw_type in ("raw", "text/plain"):
        return {"type": "raw", "data": data_s}
    if data_s.strip():
        return {"type": "json", "data": data_s}
    return {"type": "none", "data": ""}


def StepDisplayName(step: Mapping[str, Any]) -> str:
    """读取步骤展示名（customHttp / httpApiCase / group 兼容）。"""
    step_type = str(step.get("type") or "").strip().lower()
    if step_type == "group":
        params = step.get("parameters")
        if isinstance(params, dict):
            gname = str(params.get("name") or "").strip()
            if gname:
                return gname
    name = str(step.get("name") or "").strip()
    if name:
        return name
    case = step.get("httpApiCase")
    if isinstance(case, dict):
        return str(case.get("name") or "").strip()
    custom = step.get("customHttpRequest")
    if isinstance(custom, dict):
        return str(custom.get("name") or "").strip()
    return ""


def FlattenHttpStepNames(steps: Sequence[Mapping[str, Any]]) -> List[str]:
    """递归展开 group.children，仅收集 HTTP/customHttp 叶节点名（目的前置校验用）。"""
    names: List[str] = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        step_type = str(step.get("type") or "").strip().lower()
        children = step.get("children")
        if step_type == "group" and isinstance(children, list):
            names.extend(FlattenHttpStepNames(children))
            continue
        if step_type in ("http", "customhttp", "") or step.get("httpApiCase") or step.get(
            "customHttpRequest"
        ):
            name = StepDisplayName(step)
            if name:
                names.append(name)
    return names


def AssertPurposeFirstNames(names: Sequence[str], *, context: str) -> None:
    """校验目的前置：``【中文目的】| 步骤ID | METHOD ...``。"""
    if not names:
        raise RuntimeError(f"{context}: 步骤名为空")
    bad: List[str] = []
    for index, name in enumerate(names, start=1):
        if not name.startswith("【"):
            bad.append(f"#{index} 未以【开头: {name}")
            continue
        if "】| " not in name:
            bad.append(f"#{index} 缺少 】| 分隔: {name}")
            continue
        purpose = name.split("】| ", 1)[0].lstrip("【").strip()
        if not purpose:
            bad.append(f"#{index} 目的为空: {name}")
            continue
        # 目的段不应再出现旧式 pytest 函数名
        if "test_" in purpose or purpose.startswith("R0") or purpose.startswith("POST /"):
            bad.append(f"#{index} 目的仍像旧命名: {name}")
    if bad:
        preview = "\n".join(bad[:12])
        raise RuntimeError(f"{context}: 目的前置命名校验失败 ({len(bad)}):\n{preview}")


def VerifyRemoteMatchesExpected(
    *,
    expected_names: Sequence[str],
    remote_steps: Sequence[Mapping[str, Any]],
) -> None:
    """推送后：叶 HTTP 条数一致 + 远程名目的前置 + 与包内期望名一致。"""
    remote_names = FlattenHttpStepNames(remote_steps)
    print(f"verify steps_len={len(remote_names)} expected={len(expected_names)}")
    AssertPurposeFirstNames(expected_names, context="package")
    AssertPurposeFirstNames(remote_names, context="remote")
    if len(remote_names) != len(expected_names):
        raise RuntimeError(
            f"步骤条数不一致: remote={len(remote_names)} expected={len(expected_names)}"
        )
    mismatches: List[str] = []
    for index, (exp, got) in enumerate(zip(expected_names, remote_names), start=1):
        if exp != got:
            mismatches.append(f"#{index}\n  expect: {exp}\n  remote: {got}")
    if mismatches:
        preview = "\n".join(mismatches[:8])
        raise RuntimeError(f"远程步骤名未刷新为最新 ({len(mismatches)}):\n{preview}")
    print("verify purpose-first names: OK")
    for index, name in enumerate(remote_names[:5], start=1):
        print(f"  sample[{index}] {name}")
    if len(remote_names) > 5:
        print(f"  ... +{len(remote_names) - 5} more")


def ToCliHttpStep(step: Mapping[str, Any], *, project_id: int, index: int) -> Optional[JsonObject]:
    """单条 HTTP 导入步 → customHttp。"""
    case = step.get("httpApiCase")
    if not isinstance(case, dict):
        return None
    method = str(case.get("method") or "get").lower()
    rel_path = str(case.get("path") or "/")
    if not rel_path.startswith("/"):
        rel_path = "/" + rel_path
    # customHttp 的 path 用带 baseUrl 的完整形态，便于环境切换
    path = "{{baseUrl}}" + rel_path
    name = str(step.get("name") or case.get("name") or f"step-{index}")
    pre = case.get("preProcessors") if isinstance(case.get("preProcessors"), list) else []
    post = case.get("postProcessors") if isinstance(case.get("postProcessors"), list) else []
    for proc in list(pre) + list(post):
        if isinstance(proc, dict) and "id" not in proc:
            proc["id"] = f"step{index}-{proc.get('type', 'script')}"

    parameters = case.get("parameters") if isinstance(case.get("parameters"), dict) else {}
    header = parameters.get("header") if isinstance(parameters.get("header"), list) else []
    query = parameters.get("query") if isinstance(parameters.get("query"), list) else []
    cookie = parameters.get("cookie") if isinstance(parameters.get("cookie"), list) else []
    path_params = parameters.get("path") if isinstance(parameters.get("path"), list) else []

    # 私有化 customHttp 偶发不带 parameters.query：把启用中的 query 拼进 path，保证运行时生效
    if query and "?" not in path:
        pairs: List[str] = []
        for row in query:
            if not isinstance(row, dict):
                continue
            if row.get("enable") is False or row.get("isDelete") is True:
                continue
            qname = str(row.get("name") or row.get("key") or "").strip()
            if not qname:
                continue
            qval = str(row.get("value", ""))
            pairs.append(f"{qname}={qval}")
        if pairs:
            path = path + "?" + "&".join(pairs)

    custom_req: JsonObject = {
        "id": 0,
        "name": name,
        "path": path,
        "method": method,
        "folderId": 0,
        "parameters": {
            "path": path_params,
            "query": query,
            "header": header,
            "cookie": cookie,
        },
        "requestBody": NormalizeCustomHttpBody(case.get("requestBody")),
        "preProcessors": pre,
        "postProcessors": post,
        "auth": {},
        "advancedSettings": {},
        "commonParameters": {},
        "projectId": project_id,
    }
    return {
        "id": f"step-{index}",
        "name": name,
        "type": "customHttp",
        "disable": False,
        "ordering": index,
        "customHttpRequest": custom_req,
    }


def ToCliScenarioSteps(import_steps: Sequence[Mapping[str, Any]], *, project_id: int) -> List[JsonObject]:
    """转为 ``customHttp`` / ``group`` 步骤，避免 ``关联接口无法找到``（不依赖 apiDetailId）。"""
    counter = {"http": 0, "group": 0}

    def ConvertList(steps: Sequence[Mapping[str, Any]]) -> List[JsonObject]:
        out: List[JsonObject] = []
        for step in steps:
            if not isinstance(step, dict):
                continue
            step_type = str(step.get("type") or "").strip().lower()
            children = step.get("children")
            if step_type == "group" and isinstance(children, list):
                counter["group"] += 1
                group_name = StepDisplayName(step) or f"group-{counter['group']}"
                out.append(
                    {
                        "id": f"group-{counter['group']}",
                        "type": "group",
                        "disable": False,
                        "isOpen": True,
                        "parameters": {"name": group_name},
                        "children": ConvertList(children),
                    }
                )
                continue
            counter["http"] += 1
            converted = ToCliHttpStep(step, project_id=project_id, index=counter["http"])
            if converted is not None:
                out.append(converted)
        return out

    return ConvertList(import_steps)


def Main() -> int:
    parser = argparse.ArgumentParser(description="Push Apifox package steps into a scenario via CLI")
    parser.add_argument("--project", type=int, required=True)
    parser.add_argument("--scenario-id", type=int, required=True)
    parser.add_argument("--api-base-url", required=True)
    parser.add_argument("--package", required=True)
    parser.add_argument("--access-token", default="")
    parser.add_argument("--branch", default="main", help="Required by private deploy for automation writes")
    parser.add_argument(
        "--scenario-name",
        default="",
        help="写入 test-scenario update 的 name；默认取 package 内场景名",
    )
    parser.add_argument(
        "--use-data-set-id",
        type=int,
        default=0,
        help="写入 options.useDataSetId（与 2548 共用数据集时必填，否则鉴权 secret 为空）",
    )
    parser.add_argument(
        "--environment-id",
        type=int,
        default=0,
        help="写入 options.environmentId（可选，与 suites.yaml environment_id 对齐）",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--mode",
        choices=("customHttp", "http", "raw"),
        default="customHttp",
        help="customHttp=不关联接口文档（推荐，可运行）；http=绑定 API；raw=原样",
    )
    args = parser.parse_args()

    token = (args.access_token or os.environ.get("APIFOX_ACCESS_TOKEN") or "").strip()
    if not token:
        raise SystemExit("APIFOX_ACCESS_TOKEN missing")

    package = json.loads(Path(args.package).read_text(encoding="utf-8"))
    scenario_item = ExtractImportScenarioItem(package)
    package_scenario_name = str(scenario_item.get("name") or "").strip()
    scenario_name = (args.scenario_name or "").strip() or package_scenario_name
    if not scenario_name:
        raise SystemExit("scenario name missing: pass --scenario-name or set name in package")
    scenario_desc = str(scenario_item.get("description") or "").strip()
    if not scenario_desc:
        scenario_desc = "Repo-first CLI sync; steps include postProcessors/customScript from Postman Tests."
    import_steps = ExtractImportSteps(package)
    if args.mode == "raw":
        steps = list(import_steps)
        for index, step in enumerate(steps, start=1):
            if "id" not in step:
                step["id"] = f"step-{index}"
            case = step.get("httpApiCase")
            if isinstance(case, dict):
                for proc in list(case.get("preProcessors") or []) + list(case.get("postProcessors") or []):
                    if isinstance(proc, dict) and "id" not in proc:
                        proc["id"] = f"step{index}-{proc.get('type', 'script')}"
                if "projectId" not in case:
                    case["projectId"] = args.project
    elif args.mode == "http":
        # 旧绑定模式：易出现「关联接口无法找到」，仅排查时使用
        raise SystemExit("mode=http 已停用（会触发关联接口找不到）。请用默认 customHttp。")
    else:
        steps = ToCliScenarioSteps(import_steps, project_id=args.project)

    update_body: JsonObject = {
        "name": scenario_name,
        "description": scenario_desc,
        "steps": steps,
    }
    # 数据集承载 clientId/secret/ProgramID；仅 steps 更新时勿丢掉 options
    if args.use_data_set_id > 0 or args.environment_id > 0:
        options: JsonObject = {
            "iterationCount": 1,
            "threadCount": 1,
            "runnerId": 0,
            "onError": "ignore",
            "delayItem": 0,
            "saveReportDetail": "all",
            "saveVariables": True,
            "readGlobalCookie": False,
            "saveGlobalCookie": False,
        }
        if args.environment_id > 0:
            options["environmentId"] = int(args.environment_id)
        if args.use_data_set_id > 0:
            options["useDataSetId"] = int(args.use_data_set_id)
        update_body["options"] = options

    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".json",
        delete=False,
    ) as handle:
        # 紧凑 JSON：P1 大场景可避免私有化 update 422001（体积上限）
        json.dump(update_body, handle, ensure_ascii=False, separators=(",", ":"))
        tmp_path = handle.name

    expected_names = FlattenHttpStepNames(steps)
    AssertPurposeFirstNames(expected_names, context="push-payload")

    try:
        print(
            f"top_level_steps={len(steps)} http_leaves={len(expected_names)} "
            f"scenario_name={scenario_name!r} package={args.package}"
        )
        RunApifoxJson(
            ["cli-schema", "validate", "test-scenario-update", "--file", tmp_path],
            api_base_url=args.api_base_url,
            token=token,
        )
        print("cli-schema validate: OK")
        if args.dry_run:
            print(f"DRY-RUN skip update scenario {args.scenario_id}")
            print("DRY-RUN package names sample:")
            for index, name in enumerate(expected_names[:5], start=1):
                print(f"  sample[{index}] {name}")
            return 0
        update_args = [
            "test-scenario",
            "update",
            str(args.scenario_id),
            "--project",
            str(args.project),
            "--file",
            tmp_path,
        ]
        if args.branch:
            update_args.extend(["--branch", args.branch])
        RunApifoxJson(update_args, api_base_url=args.api_base_url, token=token)
        print(f"UPDATED scenario {args.scenario_id} branch={args.branch or 'main'}")
        get_args = [
            "test-scenario",
            "get",
            str(args.scenario_id),
            "--project",
            str(args.project),
            "--with-case-detail",
        ]
        if args.branch:
            get_args.extend(["--branch", args.branch])
        detail = RunApifoxJson(get_args, api_base_url=args.api_base_url, token=token)
        data = detail.get("data") or {}
        got = data.get("steps") or []
        if not isinstance(got, list):
            raise RuntimeError("test-scenario get: steps 非列表")
        VerifyRemoteMatchesExpected(expected_names=expected_names, remote_steps=got)
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(Main())
