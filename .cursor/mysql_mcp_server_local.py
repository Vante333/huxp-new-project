"""
本地 MySQL MCP（stdio）：避免上游包 stderr 噪声；默认不枚举 resources。
在部分 Windows 环境下 mysql-connector-python 连接会触发原生崩溃，故统一使用 PyMySQL。
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import pymysql
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Resource, TextContent, Tool
from pydantic import AnyUrl
from pymysql.connections import Connection

# stdio 传输下，stderr 的杂项输出可能被宿主误解析；仅记录 WARNING 及以上。
logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
for _name in ("mcp", "mcp.server", "mcp.server.lowlevel", "mysql_mcp_server_local"):
    logging.getLogger(_name).setLevel(logging.WARNING)

_logger = logging.getLogger("mysql_mcp_server_local")
app = Server("mysql_mcp_server_local")


def GetDbConfig() -> dict[str, Any]:
    """从环境变量组装 pymysql.connect 参数。"""
    host: str = os.getenv("MYSQL_HOST", "localhost")
    port_raw: str = os.getenv("MYSQL_PORT", "3306")
    user: str | None = os.getenv("MYSQL_USER")
    password: str | None = os.getenv("MYSQL_PASSWORD")
    database: str | None = os.getenv("MYSQL_DATABASE")
    if not user or not password or not database:
        _logger.error("缺少 MYSQL_USER / MYSQL_PASSWORD / MYSQL_DATABASE")
        raise ValueError("缺少必需的数据库环境变量：MYSQL_USER、MYSQL_PASSWORD、MYSQL_DATABASE")
    try:
        port: int = int(port_raw)
    except ValueError as exc:
        raise ValueError(f"MYSQL_PORT 无效: {port_raw!r}") from exc
    cfg: dict[str, Any] = {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "database": database,
        "connect_timeout": int(os.getenv("MYSQL_CONNECT_TIMEOUT", "10")),
        "charset": "utf8mb4",
        "cursorclass": pymysql.cursors.Cursor,
    }
    ssl_ca: str | None = os.getenv("MYSQL_SSL_CA")
    ssl_disabled_env: str = os.getenv("MYSQL_SSL_DISABLED", "").strip().lower()
    if ssl_ca:
        cfg["ssl"] = {"ca": ssl_ca}
    if ssl_disabled_env in ("1", "true", "yes"):
        cfg["ssl_disabled"] = True
    elif ssl_disabled_env in ("0", "false", "no"):
        cfg["ssl_disabled"] = False
    else:
        # 未显式配置时：与此前在本仓库终端验证可连 UAT 的行为一致（避免默认 SSL 握手差异导致失败）
        cfg["ssl_disabled"] = True
    return cfg


@contextmanager
def OpenDbConnection(connect_kw: dict[str, Any] | None = None) -> Iterator[Connection]:
    kw: dict[str, Any] = connect_kw if connect_kw is not None else GetDbConfig()
    conn: Connection = pymysql.connect(**kw)
    try:
        yield conn
    finally:
        conn.close()


def ShouldListTablesAsResources() -> bool:
    return os.getenv("MYSQL_MCP_LIST_TABLES", "").strip().lower() in ("1", "true", "yes")


@app.list_resources()
async def ListResources() -> list[Resource]:
    """默认返回空列表，避免 Cursor 在列举资源时长时间连库或解析异常。"""
    if not ShouldListTablesAsResources():
        return []
    try:
        connect_kw = GetDbConfig()
    except ValueError:
        return []
    try:
        with OpenDbConnection(connect_kw) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SHOW TABLES")
                tables = cursor.fetchall()
        out: list[Resource] = []
        for row in tables:
            table_name = str(row[0])
            out.append(
                Resource(
                    uri=f"mysql://{table_name}/data",
                    name=f"table:{table_name}",
                    mimeType="text/plain",
                    description=f"MySQL 表 {table_name}（前 100 行）",
                )
            )
        return out
    except pymysql.Error as exc:
        _logger.warning("列举表失败: %s", exc)
        return []
    except Exception as exc:
        _logger.warning("列举表未预期错误: %s", exc, exc_info=True)
        return []


@app.read_resource()
async def ReadResource(uri: AnyUrl) -> str:
    """仅在开启 MYSQL_MCP_LIST_TABLES 时由宿主读取资源；解析 mysql://{table}/data。"""
    uri_str = str(uri)
    if not uri_str.startswith("mysql://"):
        raise ValueError(f"不支持的 URI: {uri_str}")
    parts = uri_str[8:].split("/")
    table = parts[0] if parts else ""
    if not table or "`" in table:
        raise ValueError(f"非法表名: {table!r}")
    safe_table = table.replace("`", "``")
    connect_kw = GetDbConfig()
    try:
        with OpenDbConnection(connect_kw) as conn:
            with conn.cursor() as cursor:
                cursor.execute(f"SELECT * FROM `{safe_table}` LIMIT 100")
                if cursor.description is None:
                    return ""
                columns = [d[0] for d in cursor.description]
                rows = cursor.fetchall()
                lines = [",".join(str(c) for c in columns)]
                lines.extend(",".join(map(str, r)) for r in rows)
                return "\n".join(lines)
    except pymysql.Error as exc:
        raise RuntimeError(f"读取表失败: {exc}") from exc


@app.list_tools()
async def ListTools() -> list[Tool]:
    return [
        Tool(
            name="execute_sql",
            description="在已配置的 MySQL 库上执行 SQL（优先 SELECT/SHOW/DESCRIBE；写操作请谨慎）",
            inputSchema={
                "type": "object",
                "properties": {"query": {"type": "string", "description": "SQL 语句"}},
                "required": ["query"],
            },
        )
    ]


@app.call_tool()
async def CallTool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    if name != "execute_sql":
        return [TextContent(type="text", text=f"未知工具: {name}")]
    query = arguments.get("query")
    if not query or not isinstance(query, str):
        return [TextContent(type="text", text="缺少或无效的 query 参数")]
    try:
        connect_kw = GetDbConfig()
    except ValueError as exc:
        return [TextContent(type="text", text=str(exc))]
    try:
        with OpenDbConnection(connect_kw) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query)
                q_upper = query.strip().upper()
                if q_upper.startswith("SHOW TABLES"):
                    tables = cursor.fetchall()
                    dbname = str(connect_kw["database"])
                    header = "Tables_in_" + dbname
                    body = "\n".join([header] + [str(t[0]) for t in tables])
                    return [TextContent(type="text", text=body)]
                if cursor.description is not None:
                    columns = [d[0] for d in cursor.description]
                    try:
                        rows = cursor.fetchall()
                    except pymysql.Error as fetch_exc:
                        return [
                            TextContent(
                                type="text",
                                text=f"查询已执行但取结果失败: {fetch_exc}",
                            )
                        ]
                    lines = [",".join(str(c) for c in columns)]
                    lines.extend(",".join(map(str, r)) for r in rows)
                    return [TextContent(type="text", text="\n".join(lines))]
                conn.commit()
                return [
                    TextContent(
                        type="text",
                        text=f"执行成功，影响行数: {cursor.rowcount}",
                    )
                ]
    except pymysql.Error as exc:
        return [TextContent(type="text", text=f"数据库错误: {exc}")]
    except Exception as exc:
        _logger.exception("execute_sql 未预期错误")
        return [TextContent(type="text", text=f"未预期错误: {exc}")]


async def RunMain() -> None:
    try:
        GetDbConfig()
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


def Main() -> None:
    asyncio.run(RunMain())


if __name__ == "__main__":
    Main()
