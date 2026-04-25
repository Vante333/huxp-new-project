# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
import re
import sys
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.dirname(__file__))
from fetch_confluence import api_get  # noqa: E402


def _load_dotenv() -> None:
    env_path = os.path.join(ROOT, ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if k and k not in os.environ:
                os.environ[k] = v


def _jira_get_issue(key: str) -> dict:
    import base64

    _load_dotenv()
    email = os.environ.get("JIRA_EMAIL")
    token = os.environ.get("JIRA_API_TOKEN")
    if not email or not token:
        raise RuntimeError("JIRA_EMAIL / JIRA_API_TOKEN missing")
    creds = base64.b64encode(f"{email}:{token}".encode()).decode()
    url = f"https://dragonpass.atlassian.net/rest/api/3/issue/{key}"
    req = Request(url, headers={"Authorization": f"Basic {creds}", "Accept": "application/json"})
    with urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _search_cql(cql: str, limit: int = 25) -> list[dict]:
    path = f"/rest/api/content/search?cql={quote(cql)}&limit={limit}"
    data = api_get(path)
    return list(data.get("results") or [])


def Main() -> int:
    _load_dotenv()
    out_path = os.path.join(ROOT, "tools", "_papi2346_search.txt")
    lines: list[str] = []

    issue = _jira_get_issue("PAPI-2346")
    summ = issue.get("fields", {}).get("summary") or ""
    lines.append(f"Jira summary: {summ}")
    blob = json.dumps(issue, ensure_ascii=False)
    for m in re.finditer(r"https://dragonpass\.atlassian\.net/wiki[^\s\"]+", blob):
        lines.append(f"wiki in issue json: {m.group(0)}")

    # remote links (Confluence)
    import base64

    email = os.environ.get("JIRA_EMAIL")
    token = os.environ.get("JIRA_API_TOKEN")
    assert email and token
    creds = base64.b64encode(f"{email}:{token}".encode()).decode()
    rurl = "https://dragonpass.atlassian.net/rest/api/3/issue/PAPI-2346/remotelink"
    req = Request(rurl, headers={"Authorization": f"Basic {creds}", "Accept": "application/json"})
    try:
        with urlopen(req, timeout=60) as resp:
            rlinks = json.loads(resp.read().decode("utf-8"))
        lines.append(f"\nremotelink count: {len(rlinks)}")
        for item in rlinks[:20]:
            obj = item.get("object") or {}
            lines.append(f"  {obj.get('url')} | {obj.get('title')}")
    except Exception as e:  # noqa: BLE001
        lines.append(f"\nremotelink error: {e}")

    queries = [
        'type=page AND text~"PAPI-2346"',
        'type=page AND title~"2346"',
        'type=page AND text~"价格查询"',
        'type=page AND text~"Aero Blue" AND text~"价格"',
        'type=page AND text~"用户价"',
        'type=page AND text~"价格查询接口"',
        'type=page AND title~"Aero Blue"',
    ]
    for cql in queries:
        try:
            res = _search_cql(cql, 20)
        except Exception as e:  # noqa: BLE001
            lines.append(f"CQL fail {cql!r}: {e}")
            continue
        lines.append(f"\nCQL {cql!r} -> {len(res)} hits")
        for r in res:
            lines.append(f"  id={r.get('id')} title={r.get('title')}")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(Main())
