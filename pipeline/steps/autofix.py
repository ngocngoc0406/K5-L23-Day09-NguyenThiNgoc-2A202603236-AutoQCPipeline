"""BƯỚC 2/4 — Sửa tự động những lỗi bắt buộc mà máy sửa được AN TOÀN.   ★★

Test:  pytest tests/test_autofix.py -q

`fix(ds, issues, cfg) -> list[dict]`: duyệt `issues` (chỉ lỗi severity ERROR), sửa thẳng vào thư mục `ds`,
và trả về danh sách thay đổi; mỗi phần tử có khoá: image, line, action, before, after
(đây chính là file `03_fixes.csv` — bằng chứng pipeline đã làm gì, người có thể kiểm lại).

| code lỗi                                       | cách sửa                                    | action           |
|------------------------------------------------|---------------------------------------------|------------------|
| BAD_FORMAT, BAD_CLASS_ID, BOX_ZERO, DUP_BOX    | xoá dòng đó khỏi file nhãn                  | "drop_line"      |
| BOX_OUT_OF_IMAGE                               | cắt box về trong [0,1] (giữ nguyên lớp)     | "clip_box"       |
| MISSING_LABEL_FILE                             | KHÔNG sửa file (máy không thể bịa nhãn): ghi 1 dòng fix, before="(không có file)", after="chuyển người gán" | "needs_label" |
| BAD_CLASS_NAME                                 | ghi lại `names` trong data.yaml đúng `cfg["classes"]` | "rename_classes" |
| DUP_IMAGE_*, LEAK_TEST, CORRUPT_IMAGE, BAD_SIZE| xoá ảnh + nhãn khỏi `ds`                    | "remove_image"   |

Bẫy cần nghĩ tới (có test cho từng cái)
- Một file có NHIỀU dòng lỗi: số dòng trong `issues` là số dòng GỐC. Nếu xoá từng dòng một thì số dòng lệch.
  Gom theo file, rồi ghi lại MỘT lần.
- Sau khi cắt, box có thể không còn diện tích (nằm hẳn ngoài ảnh): lúc đó xoá dòng thay vì ghi box rỗng.
- Một dòng có 2 lỗi (vd. BOX_OUT_OF_IMAGE + DUP_BOX): xoá dòng thắng, chỉ ghi 1 fix `drop_line`, không ghi thêm `clip_box`. Dòng trống ở giữa file vẫn đếm vào số dòng gốc.
- Ảnh vừa bị xoá (DUP_IMAGE_*...) mà còn issue dòng của chính nó: bỏ qua êm, không được báo lỗi/chết.
- Không động tới lỗi WARN (cảnh báo là việc của người). Không sửa file ở `data/raw/` — chỉ sửa `ds`.
- Chạy lần 2 trên dữ liệu đã sửa phải không làm gì thêm (idempotent) — NGOẠI LỆ duy nhất: `needs_label` được ghi lại mỗi lần còn lỗi `MISSING_LABEL_FILE` (vì ảnh vẫn chưa có nhãn).

- `needs_label` KHÔNG tạo file nhãn rỗng (rỗng = "ảnh nền", khác với "chưa gán"). `review_queue` sẽ đẩy ảnh này lên đầu hàng đợi cho người.

Gợi ý: `yaml.safe_load / safe_dump`.
"""
from collections import defaultdict  # noqa: F401

import yaml  # noqa: F401

from ..common import ERROR, parse_yolo_line  # noqa: F401


DROP_CODES = {"BAD_FORMAT", "BAD_CLASS_ID", "BOX_ZERO", "DUP_BOX"}
CLIP_CODES = {"BOX_OUT_OF_IMAGE"}
REMOVE_CODES = {"LEAK_TEST", "CORRUPT_IMAGE", "BAD_SIZE"}          # + mọi mã bắt đầu bằng DUP_IMAGE_


def _is_remove(code: str) -> bool:
    return code in REMOVE_CODES or code.startswith("DUP_IMAGE_")


def _fmt(v: float) -> str:
    return f"{v:.6f}".rstrip("0").rstrip(".") if v else "0"


def _clip(text: str):
    """Cắt box về [0,1]. Trả về dòng mới, hoặc None nếu box không còn diện tích (nằm hẳn ngoài ảnh) / dòng hỏng."""
    try:
        cls, cx, cy, w, h = parse_yolo_line(text)
    except ValueError:
        return None
    x1, x2 = max(0.0, cx - w / 2), min(1.0, cx + w / 2)
    y1, y2 = max(0.0, cy - h / 2), min(1.0, cy + h / 2)
    if x2 <= x1 or y2 <= y1:
        return None
    return " ".join([str(cls), _fmt((x1 + x2) / 2), _fmt((y1 + y2) / 2), _fmt(x2 - x1), _fmt(y2 - y1)])


def _fix_yaml(ds, cfg):
    data = {}
    if ds.yaml_path.exists():
        data = yaml.safe_load(ds.yaml_path.read_text(encoding="utf-8")) or {}
    before = data.get("names")
    data["names"] = {i: n for i, n in enumerate(cfg["classes"])}
    if "nc" in data:
        data["nc"] = len(cfg["classes"])
    ds.yaml_path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return {"image": "data.yaml", "line": None, "action": "rename_classes",
            "before": str(before), "after": str(data["names"])}


def fix(ds, issues, cfg):
    errors = [i for i in issues if i.severity == ERROR]
    fixes = []

    # 1) Xoá ảnh (trùng / rò rỉ / hỏng / sai cỡ) trước: issue dòng của ảnh đã xoá sẽ bị bỏ qua êm.
    removed = set()
    for i in errors:
        if not _is_remove(i.code) or i.image in removed:
            continue
        img = ds.image_path(i.image)
        lab = ds.label_path(i.image)
        if img is None and not lab.exists():
            continue                                    # đã xoá từ trước (idempotent)
        before = img.name if img is not None else "(không có ảnh)"
        if img is not None:
            img.unlink()
        if lab.exists():
            lab.unlink()
        ds._size_cache.pop(i.image, None)
        removed.add(i.image)
        fixes.append({"image": i.image, "line": None, "action": "remove_image", "before": before,
                      "after": f"đã xoá ảnh + nhãn ({i.code})"})

    # 2) data.yaml: ghi lại names một lần dù có nhiều issue BAD_CLASS_NAME.
    if any(i.code == "BAD_CLASS_NAME" for i in errors):
        fixes.append(_fix_yaml(ds, cfg))

    # 3) Ảnh chưa có nhãn: KHÔNG tạo file, chỉ chuyển người gán.
    for stem in sorted({i.image for i in errors if i.code == "MISSING_LABEL_FILE"} - removed):
        if ds.label_path(stem).exists():
            continue
        fixes.append({"image": stem, "line": None, "action": "needs_label",
                      "before": "(không có file)", "after": "chuyển người gán"})

    # 4) Lỗi theo dòng: gom theo file, số dòng là số dòng GỐC (đếm cả dòng trống), ghi lại MỘT lần.
    drop, clip = defaultdict(set), defaultdict(set)
    for i in errors:
        if i.line is None or i.image in removed:
            continue
        if i.code in DROP_CODES:
            drop[i.image].add(i.line)
        elif i.code in CLIP_CODES:
            clip[i.image].add(i.line)

    for stem in sorted(set(drop) | set(clip)):
        p = ds.label_path(stem)
        if not p.exists():
            continue
        orig = p.read_text(encoding="utf-8", errors="replace").splitlines()
        out, changed = [], False
        for n, text in enumerate(orig, 1):
            if n in drop[stem]:                         # xoá dòng thắng cắt box
                fixes.append({"image": stem, "line": n, "action": "drop_line", "before": text, "after": ""})
                changed = True
                continue
            if n in clip[stem]:
                new = _clip(text)
                if new is None:
                    fixes.append({"image": stem, "line": n, "action": "drop_line", "before": text,
                                  "after": "(box nằm ngoài ảnh sau khi cắt)"})
                    changed = True
                    continue
                if new != text:
                    fixes.append({"image": stem, "line": n, "action": "clip_box", "before": text, "after": new})
                    changed = True
                out.append(new)
                continue
            out.append(text)
        if changed:
            p.write_text("".join(l + "\n" for l in out), encoding="utf-8")
    return fixes
