import os
import uuid

import requests


BASE_URL = os.getenv("DP_BASE_URL", "https://developer-sandbox.dragonpass.com/api")
PROGRAM_ID = os.getenv("DP_PROGRAM_ID", "1981485059617792")
CLIENT_ID = os.getenv("DP_CLIENT_ID", "WFW2K82MJYYQWPH3QHTS")
CLIENT_SECRET = os.getenv("DP_CLIENT_SECRET", "309C8FB8D85E432EB8132BDA1DF1138B")


def common_headers(token=None) -> dict:
    """
    公共请求头封装，供各测试文件复用。
    """
    headers = {
        "x-version": "canary",
        "X-Program-ID": PROGRAM_ID,
        "X-Request-ID": str(uuid.uuid4()),
        "Content-Type": "application/json",
        "Accept": "*/*",
        "User-Agent": "pytest-entitlement-tests",
    }
    if token:
        headers["Authorization"] = "Bearer " + token
    return headers


def get_access_token() -> str:
    """
    POST /v2/auth/token
    """
    url = BASE_URL.rstrip("/") + "/v2/auth/token"
    payload = {
        "clientId": CLIENT_ID,
        "secret": CLIENT_SECRET,
    }
    resp = requests.post(
        url,
        json=payload,
        headers={
            "Content-Type": "application/json",
            "Accept": "*/*",
        },
        timeout=10,
    )
    assert resp.status_code == 200, f"get token failed: {resp.status_code}, {resp.text}"
    data = resp.json()
    # 沙箱环境实际返回结构示例：
    # {"code":0,"data":{"validUntil":..., "accessToken":"xxx", "tokenType":"Bearer"}}
    token_container = data.get("data") if isinstance(data, dict) and "data" in data else data
    token = (
        token_container.get("accessToken")
        or token_container.get("token")
        or token_container.get("access_token")
        if isinstance(token_container, dict)
        else None
    )
    assert token, f"no token in response: {data}"
    return token


def create_membership(token: str) -> str:
    """
    POST /v2/memberships
    """
    url = BASE_URL.rstrip("/") + "/v2/memberships"
    email_suffix = uuid.uuid4().hex[:8]
    payload = {
        "clientUserId": str(uuid.uuid4()),
        "firstName": "Lann",
        "lastName": "Testn",
        "phoneNumber": "8081966002",
        "callingCode": "44",
        "email": f"auto+{email_suffix}@example.com",
        "expirationDate": "2026-03-06T10:10:33+00:00",
    }
    resp = requests.post(url, json=payload, headers=common_headers(token), timeout=10)
    assert resp.status_code == 200, f"create membership failed: {resp.status_code}, {resp.text}"
    data = resp.json()
    data_obj = data.get("data") if isinstance(data, dict) and "data" in data else data
    membership_id = (
        data_obj.get("membershipId") or data_obj.get("id")
        if isinstance(data_obj, dict)
        else None
    )
    assert membership_id, f"no membershipId in response: {data}"
    return membership_id


def get_entitlements_details(token: str, membership_id: str, module="3") -> dict:
    """
    POST /v2/entitlements/details
    """
    url = BASE_URL.rstrip("/") + "/v2/entitlements/details"
    payload = {
        "membershipId": membership_id,
        "module": str(module),
    }
    resp = requests.post(url, json=payload, headers=common_headers(token), timeout=10)
    assert resp.status_code == 200, f"details failed: {resp.status_code}, {resp.text}"
    return resp.json()


def get_entitlements_search(token: str, membership_id: str, module=None) -> dict:
    """
    POST /v2/entitlements/search
    如果接口支持 module，可根据需要补充。
    """
    url = BASE_URL.rstrip("/") + "/v2/entitlements/search"
    payload = {
        "membershipId": membership_id,
    }
    if module is not None:
        payload["module"] = str(module)
    resp = requests.post(url, json=payload, headers=common_headers(token), timeout=10)
    assert resp.status_code == 200, f"search failed: {resp.status_code}, {resp.text}"
    return resp.json()


def update_entitlements(
    token: str,
    membership_id: str,
    module,
    quantity=None,
    purchased_quantity=None,
    usage_restriction=None,
    tier=None,
) -> dict:
    """
    POST /v2/entitlements/update
    """
    url = BASE_URL.rstrip("/") + "/v2/entitlements/update"
    payload = {
        "membershipId": membership_id,
        "module": str(module),
    }
    if quantity is not None:
        payload["quantity"] = quantity
    if purchased_quantity is not None:
        payload["purchasedQuantity"] = purchased_quantity
    if usage_restriction is not None:
        payload["usageRestriction"] = usage_restriction
    if tier is not None:
        payload["tier"] = tier

    resp = requests.post(url, json=payload, headers=common_headers(token), timeout=10)
    assert resp.status_code == 200, f"update failed: {resp.status_code}, {resp.text}"
    return resp.json()

