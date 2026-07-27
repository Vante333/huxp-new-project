"""生成 FT Membership Prebooking Payment · P1 全量 Postman Collection。"""
from __future__ import annotations

from ft_prebooking_payment_common import Generate


def Main() -> None:
    out = Generate("membership", "p1")
    print(f"Wrote {out}")


if __name__ == "__main__":
    Main()
