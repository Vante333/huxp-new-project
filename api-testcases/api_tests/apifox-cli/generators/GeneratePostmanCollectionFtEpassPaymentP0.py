"""生成 FT E-pass Prebooking Payment · P0 冒烟 Postman Collection。"""
from __future__ import annotations

from ft_prebooking_payment_common import Generate
from collection_builder_common import PREBOOKING_ADD_DAYS_START, PrebookingDateApifoxExpr

PREBOOKING_DATE_APIFOX = PrebookingDateApifoxExpr(PREBOOKING_ADD_DAYS_START)


def Main() -> None:
    out = Generate(
        "epass",
        "p0",
        prebooking_date_apifox=PREBOOKING_DATE_APIFOX,
    )
    print(f"Wrote {out}")


if __name__ == "__main__":
    Main()
