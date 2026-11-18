"""CHECK 2 — Dòng nhãn YOLO: sai định dạng, ID lớp lạ, box tràn ảnh, box rỗng, box lặp.   (Script 2 trong slide)   ★★

Test:  pytest tests/test_label_format.py -q

Mỗi dòng nhãn: `id cx cy w h` (5 số, toạ độ 0–1). Trả về list[Issue]; `Issue.line` = số dòng (đếm từ 1).

| code             | severity | khi nào                                                                  |
|------------------|----------|--------------------------------------------------------------------------|
| BAD_FORMAT       | ERROR    | không đúng 5 cột số (dùng `parse_yolo_line`, bắt `ValueError`)           |
| BAD_CLASS_ID     | ERROR    | id lớp ngoài 0..len(ds.classes)-1                                        |
| BOX_ZERO         | ERROR    | w <= 0 hoặc h <= 0                                                       |
| BOX_OUT_OF_IMAGE | ERROR    | mép box vượt [0,1] quá `cfg["label_format"]["overflow_tol"]`; extra={"overflow": mức tràn} |
| DUP_BOX          | ERROR    | cùng lớp với một dòng TRƯỚC ĐÓ và IoU > `dup_box_iou`; báo ở dòng SAU    |
| BOX_TINY         | WARN     | cạnh ngắn của box (px) < `min_box_px`  (cần `ds.image_size(stem)`)       |
| BOX_HUGE         | WARN     | w*h > `max_box_frac`                                                     |

Gợi ý
- Mép trái = x - w/2, mép phải = x + w/2 (xem câu hỏi "dòng YOLO nào lỗi?" trong slide).
- Một dòng hỏng (BAD_FORMAT, BAD_CLASS_ID, BOX_ZERO) thì `continue`, đừng kiểm tiếp hình học của dòng đó.
- Dòng thiếu cột làm script của slide dừng giữa chừng: đây là lý do phải `try/except`.
- `iou_xywh(a, b)` có sẵn trong common.py.
- Ngưỡng nằm trong `cfg["label_format"]` — đừng viết cứng số vào code.
"""
from ..common import ERROR, WARN, Issue, iou_xywh, parse_yolo_line  # noqa: F401


NAME = "label_format"


def _overflow(cx, cy, w, h) -> float:
    """Mức tràn lớn nhất của 4 mép box ra ngoài [0, 1] (0 nếu nằm trong ảnh)."""
    return max(0.0, -(cx - w / 2), (cx + w / 2) - 1.0, -(cy - h / 2), (cy + h / 2) - 1.0)


def run(ds, cfg):
    c = cfg["label_format"]
    n_classes = len(ds.classes)
    issues = []
    for lf in ds.label_files():
        stem = lf.stem
        size = ds.image_size(stem) if ds.image_path(stem) is not None else None
        seen = []                                    # [(số dòng, box)] các dòng hợp lệ trước đó
        for ln_no, text in ds.read_label_lines(stem) or []:
            # 1) định dạng
            try:
                cls, cx, cy, w, h = parse_yolo_line(text)
            except ValueError as e:
                issues.append(Issue(NAME, ERROR, "BAD_FORMAT", stem, f"dòng sai định dạng ({e}): {text.strip()!r}", line=ln_no))
                continue
            # 2) id lớp
            if not 0 <= cls < n_classes:
                issues.append(Issue(NAME, ERROR, "BAD_CLASS_ID", stem, f"id lớp {cls} ngoài 0..{n_classes - 1}",
                                    line=ln_no, extra={"class_id": cls}))
                continue
            # 3) box rỗng
            if w <= 0 or h <= 0:
                issues.append(Issue(NAME, ERROR, "BOX_ZERO", stem, f"box rỗng w={w} h={h}", line=ln_no))
                continue
            box = (cx, cy, w, h)
            # 4) tràn ảnh
            over = _overflow(*box)
            if over > c["overflow_tol"]:
                issues.append(Issue(NAME, ERROR, "BOX_OUT_OF_IMAGE", stem, f"box tràn ra ngoài ảnh {over:.4f}",
                                    line=ln_no, extra={"overflow": round(over, 6)}))
            # 5) box lặp với một dòng TRƯỚC ĐÓ cùng lớp
            for prev_no, (pcls, pbox) in seen:
                if pcls == cls:
                    iou = iou_xywh(pbox, box)
                    if iou > c["dup_box_iou"]:
                        issues.append(Issue(NAME, ERROR, "DUP_BOX", stem, f"trùng dòng {prev_no} (IoU={iou:.3f})",
                                            line=ln_no, extra={"dup_of": prev_no, "iou": round(iou, 4)}))
                        break
            seen.append((ln_no, (cls, box)))
            # 6) cảnh báo kích thước
            if size is not None:
                short_px = min(w * size[0], h * size[1])
                if short_px < c["min_box_px"]:
                    issues.append(Issue(NAME, WARN, "BOX_TINY", stem, f"cạnh ngắn {short_px:.1f}px < {c['min_box_px']}px",
                                        line=ln_no, extra={"short_px": round(short_px, 2)}))
            if w * h > c["max_box_frac"]:
                issues.append(Issue(NAME, WARN, "BOX_HUGE", stem, f"box chiếm {w * h:.0%} ảnh", line=ln_no,
                                    extra={"area_frac": round(w * h, 4)}))
    return issues
