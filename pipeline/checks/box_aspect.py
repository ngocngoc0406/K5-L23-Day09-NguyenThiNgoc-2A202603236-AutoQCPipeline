"""CHECK THƯỞNG — Box có tỉ lệ khung hình bất thường (rất dẹt hoặc rất mảnh).   (thêm ngoài đề)

Test:  pytest tests/test_box_aspect.py -q

Box hợp lệ về cú pháp nhưng có tỉ lệ cạnh dài / cạnh ngắn (tính theo PIXEL, không theo toạ độ chuẩn hoá) quá lớn
thường là box vẽ hỏng: kéo nhầm một đường thẳng, bấm nhầm hai điểm sát nhau theo một trục, hoặc box của vật bị che gần hết.
Quy tắc không biết box đó đúng hay sai nghĩa nên chỉ CẢNH BÁO -> người xem.

| code               | severity | khi nào                                                             |
|--------------------|----------|---------------------------------------------------------------------|
| BOX_ASPECT_EXTREME | WARN     | max(w_px/h_px, h_px/w_px) > `max_ratio`; extra={"ratio", "class"}   |

Ngưỡng đọc từ `cfg["box_aspect"]["max_ratio"]`. `configs/pipeline.yaml` là file cố định của dự án (RULES.md: chỉ được đổi 2 khoá
CALIBRATE) nên khi cfg không có mục này thì dùng mặc định `DEFAULT_MAX_RATIO` = 8. Lý do chọn 8: trên nhãn người của tập val (40 ảnh),
99% box có tỉ lệ <= 6,5 (cá biệt một xe bị che có tỉ lệ 11,4); trên bộ calibration (nhãn người, sạch) tối đa 4,0.
(Số liệu này đo một lần bằng tay khi chọn ngưỡng; check KHÔNG đọc các tập đó lúc chạy.)

Vì `pipeline/checks/__init__.py` đã ghim, check này không nằm trong QC_CHECKS; chạy riêng bằng `python scripts/extra_checks.py`.
"""
from ..common import WARN, Issue, parse_yolo_line

NAME = "box_aspect"
DEFAULT_MAX_RATIO = 8.0


def run(ds, cfg):
    max_ratio = float((cfg.get("box_aspect") or {}).get("max_ratio", DEFAULT_MAX_RATIO))
    issues = []
    for img in ds.image_files():
        stem = img.stem
        size = ds.image_size(stem)
        if size is None:                                  # ảnh hỏng: check images báo
            continue
        W, H = size
        for ln_no, text in ds.read_label_lines(stem) or []:
            try:
                cls, _, _, w, h = parse_yolo_line(text)
            except ValueError:
                continue                                  # dòng hỏng: label_format báo
            if not 0 <= cls < len(ds.classes) or w <= 0 or h <= 0:
                continue                                  # BAD_CLASS_ID / BOX_ZERO: label_format báo
            wp, hp = w * W, h * H
            ratio = max(wp / hp, hp / wp)
            if ratio > max_ratio:
                shape = "dẹt (rộng >> cao)" if wp > hp else "mảnh (cao >> rộng)"
                issues.append(Issue(NAME, WARN, "BOX_ASPECT_EXTREME", stem,
                                    f"box lớp {ds.classes[cls]} {shape}: tỉ lệ {ratio:.1f} > {max_ratio:g}",
                                    line=ln_no, extra={"ratio": round(ratio, 2), "class": ds.classes[cls]}))
    return issues
