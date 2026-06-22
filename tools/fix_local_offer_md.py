# -*- coding: utf-8 -*-
"""修复 Q2-Local-Offer Confluence 拉取 Markdown 的安全格式问题（不自动重建表格）。"""
from __future__ import annotations

import re
from pathlib import Path


def ReplaceHtmlEntities(text: str) -> str:
    replacements = {
        "&mdash;": "——",
        "&rsquo;": "'",
        "&ldquo;": '"',
        "&rdquo;": '"',
        "&rarr;": "->",
        "&nbsp;": " ",
        "&ndash;": "–",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def FixApiPathCodeBlocks(text: str) -> str:
    def _Repl(match: re.Match[str]) -> str:
        body = match.group(1).strip()
        if body.startswith("/v2/") or body.startswith("/api/"):
            return f"```text\n{body}\n```"
        return match.group(0)

    return re.sub(r"```json\n(.*?)\n```", _Repl, text, flags=re.DOTALL)


def FixMergedHeadings(text: str) -> str:
    replacements: list[tuple[str, str]] = [
        (
            "## 一、概述1.1 基础信息![](images/image-20260413-022146.png)UAT可以用上面这个项目",
            "## 一、概述\n\n### 1.1 基础信息\n\n![](images/image-20260413-022146.png)\n\nUAT可以用上面这个项目",
        ),
        (
            "![](images/image-20260412-033809.png)OptionList（可用卡券列表），在BOSS通用卡券服务包管理中，与Resource关联",
            "![](images/image-20260412-033809.png)\n\nOptionList（可用卡券列表），在BOSS通用卡券服务包管理中，与Resource关联",
        ),
        (
            "![](images/image-20260412-035308.png)Option，SKU开头的编码，在BOSS卡券服务管理中，和通用卡券服务包关联",
            "![](images/image-20260412-035308.png)\n\nOption，SKU开头的编码，在BOSS卡券服务管理中，和通用卡券服务包关联",
        ),
        (
            "![](images/image-20260412-034615.png)项目默认配置",
            "![](images/image-20260412-034615.png)\n\n项目默认配置",
        ),
        (
            "![](images/image-20260511-033655.png)SAAS也是配置核销商品（通用卡卷）",
            "![](images/image-20260511-033655.png)\n\nSAAS也是配置核销商品（通用卡卷）",
        ),
        (
            "## 二、接口2.1 资源查询相关接口",
            "## 二、接口\n\n### 2.1 资源查询相关接口",
        ),
        (
            "![](images/image-20260511-025322.png)2.1.2 资源列表BOSS接口，",
            "![](images/image-20260511-025322.png)\n\n### 2.1.2 资源列表\n\nBOSS接口，",
        ),
        (
            "tag![](images/image-20260413-022653.png)原始表达",
            "tag\n\n![](images/image-20260413-022653.png)",
        ),
        (
            "### 2.2 聚合搜索相关2.2.1 品类名称翻译映射表",
            "### 2.2 聚合搜索相关\n\n#### 2.2.1 品类名称翻译映射表",
        ),
        (
            "### 2.2.2 数据拉取可以从之前生消的已有接口直接拉取",
            "#### 2.2.2 数据拉取\n\n可以从之前生消的已有接口直接拉取",
        ),
        (
            "### 2.2 订单相关 E-pass接口",
            "### 2.2 订单相关 E-pass 接口",
        ),
        (
            "### 2.2.3 订单列表与订单详情订单详情返回与创建订单的返回完全一致，通过订单号查单",
            "### 2.2.3 订单列表与订单详情\n\n订单详情返回与创建订单的返回完全一致，通过订单号查单",
        ),
        (
            "### 2.2.5 取消接口500.110.030",
            "### 2.2.5 取消接口",
        ),
        (
            "### 2.3.2 创建LO订单/订单详情暂时不需要考虑boss的权益下单限制，目前都配无限",
            "### 2.3.2 创建 LO 订单/订单详情\n\n暂时不需要考虑 boss 的权益下单限制，目前都配无限",
        ),
        (
            "### 2.3.3 取消接口500.110.030",
            "### 2.3.3 取消接口",
        ),
        (
            "### 2.4 价格与可用性相关价格只支持在",
            "### 2.4 价格与可用性相关\n\n价格只支持在",
        ),
        (
            "2. 产品需求- module值=11",
            "## 2. 产品需求\n\n- module 值 = 11",
        ),
        (
            "![](images/image-20260412-053001.png)错误码500.020.011",
            "![](images/image-20260412-053001.png)",
        ),
        (
            "### 2.2.1 创建E-pass与查询详情新增module枚举值11=local offer",
            "### 2.2.1 创建 E-pass 与查询详情\n\n新增 module 枚举值 11 = local offer",
        ),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def FixSubsectionBossLinks(text: str) -> str:
    text = re.sub(
        r"### 2\.1\.1 资源详情BOSS接口，",
        "### 2.1.1 资源详情\n\nBOSS接口，",
        text,
    )
    text = re.sub(
        r"### 2\.1\.3 option列表BOSS接口，",
        "### 2.1.3 option 列表\n\nBOSS接口，",
        text,
    )
    text = re.sub(
        r"### 2\.2\.2 创建E-pass local offer订单，创建bundle订单",
        "### 2.2.2 创建 E-pass local offer 订单，创建 bundle 订单",
        text,
    )
    text = re.sub(
        r"### 2\.2\.4 查询可用性无特殊，",
        "### 2.2.4 查询可用性\n\n无特殊，",
        text,
    )
    text = re.sub(
        r"### 2\.3\.2 订单列表获取订单，",
        "### 2.3.2 订单列表\n\n获取订单，",
        text,
    )
    text = re.sub(
        r"### 2\.3\.1 权益更新/权限概览/权限明细/注册接口新增权益支持，支持module=11",
        "### 2.3.1 权益更新/权限概览/权限明细/注册接口\n\n新增权益支持，支持 module = 11",
        text,
    )
    return text


def CompressListBlankLines(text: str) -> str:
    lines = text.splitlines()
    out: list[str] = []
    for idx, line in enumerate(lines):
        if line.strip() == "" and idx + 1 < len(lines):
            if re.match(r"^-\s", lines[idx + 1]) and out and re.match(r"^-\s", out[-1]):
                continue
        out.append(line)
    return "\n".join(out)


def RemoveTrailingGarbage(text: str) -> str:
    text = re.sub(r"\}bash-5\.2#\s*$", "}", text.rstrip())
    return text + "\n"


def FixLocalOfferMarkdown(path: Path) -> None:
    raw = path.read_text(encoding="utf-8")
    steps = [
        ReplaceHtmlEntities,
        FixMergedHeadings,
        FixSubsectionBossLinks,
        FixApiPathCodeBlocks,
        CompressListBlankLines,
        RemoveTrailingGarbage,
    ]
    result = raw
    for fn in steps:
        result = fn(result)
    path.write_text(result, encoding="utf-8")


if __name__ == "__main__":
    target = Path(__file__).resolve().parent.parent / "requirements" / "2026Q2_SP3" / "Q2-Local-Offer.md"
    FixLocalOfferMarkdown(target)
    print(f"Fixed: {target}")
