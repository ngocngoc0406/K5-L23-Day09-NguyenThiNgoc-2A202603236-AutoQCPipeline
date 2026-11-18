#!/usr/bin/env python3
"""Chạy check thưởng `box_aspect` (không nằm trong QC_CHECKS vì pipeline/checks/__init__.py đã ghim).

    python -m pipeline.run                # trước: để có work/run/ds (dataset sau sửa tự động + người duyệt)
    python scripts/extra_checks.py        # -> submission/reports/09_box_aspect.csv|txt

Chỉ ĐỌC dữ liệu (data/raw và work/run/ds), không sửa gì.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.checks import box_aspect  # noqa: E402
from pipeline.common import Dataset, load_config, write_issues_csv  # noqa: E402


def main():
    cfg = load_config()
    out = ROOT / "submission" / "reports"
    lines = ["# Check thưởng box_aspect — box có tỉ lệ khung hình bất thường (WARN)", ""]
    after = []
    for label, d in [("raw (trước pipeline)", ROOT / "data" / "raw"), ("sau pipeline (work/run/ds)", ROOT / "work" / "run" / "ds")]:
        ds = Dataset(d, cfg["classes"])
        if not ds.image_files():
            lines.append(f"{label}: không có ảnh (chưa chạy `python -m pipeline.run`?)")
            continue
        iss = box_aspect.run(ds, cfg)
        lines.append(f"{label}: quét {len(ds.image_files())} ảnh -> {len(iss)} cảnh báo trên {len({i.image for i in iss})} ảnh")
        for i in iss:
            lines.append(f"  [WARN ] {i.code:20} {i.image}.txt:{i.line}  {i.message}")
        if d.name == "ds":
            after = iss
    write_issues_csv(after, out / "09_box_aspect.csv")
    (out / "09_box_aspect.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
