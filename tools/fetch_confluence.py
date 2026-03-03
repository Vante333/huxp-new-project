# -*- coding: utf-8 -*-
import json
import os
import sys
import base64
import re
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from html.parser import HTMLParser

EMAIL = "liudx@dragonpass.com.cn"
TOKEN = "ATATT3xFfGF0h_POV1Yr82zJWLLvhiztw_cYOd3iFD-Fp6-oLtyfu6CxXTtiR4zi13b41MkWuev01U07SKFAhcC8qCcWMOozUImiRAJXQ2PEkictRYPJZFGEwA0ge_z5yjRWGwp0ElRoc1uGcjG2K84-cr23ZF1K_6SWrUa7TCfMusEUGe78_bU=9708D2A0"
BASE_URL = "https://dragonpass.atlassian.net/wiki"
PAGE_ID = "1492779221"

def get_auth_header():
    creds = base64.b64encode(f"{EMAIL}:{TOKEN}".encode("ascii")).decode("ascii")
    return {"Authorization": f"Basic {creds}", "Accept": "application/json"}

def api_get(path):
    url = f"{BASE_URL}{path}"
    req = Request(url, headers=get_auth_header())
    resp = urlopen(req, timeout=120)
    return json.loads(resp.read().decode("utf-8"))

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "content"

    if mode == "content":
        data = api_get(f"/rest/api/content/{PAGE_ID}?expand=body.storage,title")
        output = {
            "title": data["title"],
            "body": data["body"]["storage"]["value"]
        }
        out_path = os.path.join(os.path.dirname(__file__), "..", "tech-docs", "page_content.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"Page content saved to {out_path}")
        print(f"Title: {data['title']}")

    elif mode == "attachments":
        data = api_get(f"/rest/api/content/{PAGE_ID}/child/attachment?limit=50")
        for att in data.get("results", []):
            print(f"FILE: {att['title']} | DOWNLOAD: {att['_links']['download']}")

    elif mode == "download_images":
        img_dir = os.path.join(os.path.dirname(__file__), "..", "tech-docs", "2026Q1_SP4", "images")
        os.makedirs(img_dir, exist_ok=True)
        data = api_get(f"/rest/api/content/{PAGE_ID}/child/attachment?limit=50")
        for att in data.get("results", []):
            filename = att["title"]
            if not filename.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".svg")):
                continue
            download_url = BASE_URL + att["_links"]["download"]
            print(f"Downloading: {filename}")
            req = Request(download_url, headers=get_auth_header())
            resp = urlopen(req, timeout=120)
            filepath = os.path.join(img_dir, filename)
            with open(filepath, "wb") as f:
                f.write(resp.read())
            print(f"  Saved: {filepath}")
        print("All images downloaded.")

if __name__ == "__main__":
    main()
