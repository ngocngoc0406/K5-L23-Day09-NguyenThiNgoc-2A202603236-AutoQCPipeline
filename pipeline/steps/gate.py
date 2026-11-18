"""BƯỚC 4 — Cửa chặn: quyết định Release / Hold / Rework.   ★

Test:  pytest tests/test_gate.py -q

Cây quyết định Day 07 (slide Day 09: "Lỗi bắt buộc chặn pipeline; lỗi cảnh báo chuyển người xem"):

  còn ≥ 1 lỗi bắt buộc (severity ERROR)                          -> "Rework"
  không còn lỗi bắt buộc, nhưng tỉ lệ ẢNH còn cảnh báo
      >= cfg["gate"]["warn_ratio_hold"]                          -> "Hold"
  còn lại                                                        -> "Release"

Tỉ lệ cảnh báo = (số ẢNH khác nhau có ≥ 1 cảnh báo) / (tổng số ảnh).  Chú ý:
- chỉ đếm issue có `image` nằm trong `image_stems` (bỏ "<dataset>", "data.yaml");
- bỏ qua ảnh nằm trong `reviewed` (người đã xem, cảnh báo của ảnh đó coi như đã xử lý) — nhưng LỖI BẮT BUỘC thì không bao giờ được bỏ qua;
- mẫu số là số ảnh, không phải số issue.

Trả về dict: decision, n_errors, n_warn_images, n_images, warn_ratio (làm tròn 4 chữ số), reasons (list[str], giải thích bằng tiếng Việt, có số liệu).
"""
from ..common import ERROR, WARN  # noqa: F401


_EPS = 1e-9      # tránh sai số float ở đúng ngưỡng (vd 3/30 so với 0.10)


def decide(issues, image_stems, cfg, reviewed=frozenset()):
    hold_at = cfg["gate"]["warn_ratio_hold"]
    stems = set(image_stems)
    reviewed = set(reviewed)
    n_images = len(stems)

    # Lỗi bắt buộc: đếm TẤT CẢ (kể cả cấp dataset như data.yaml) và không bao giờ bỏ qua vì đã duyệt.
    errors = [i for i in issues if i.severity == ERROR]
    warn_images = {i.image for i in issues
                   if i.severity == WARN and i.image in stems and i.image not in reviewed}
    n_warn = len(warn_images)
    ratio = n_warn / n_images if n_images else 0.0

    reasons = []
    if errors:
        decision = "Rework"
        codes = sorted({i.code for i in errors})
        n_err_img = len({i.image for i in errors})
        reasons.append(f"còn {len(errors)} lỗi bắt buộc trên {n_err_img} ảnh/mục ({', '.join(codes)}) -> phải sửa lại")
    elif ratio >= hold_at - _EPS:
        decision = "Hold"
        reasons.append(f"không còn lỗi bắt buộc nhưng {n_warn}/{n_images} ảnh ({ratio:.1%}) còn cảnh báo chưa người duyệt "
                       f">= ngưỡng {hold_at:.0%}")
    else:
        decision = "Release"
        reasons.append(f"không còn lỗi bắt buộc; {n_warn}/{n_images} ảnh ({ratio:.1%}) còn cảnh báo chưa duyệt "
                       f"< ngưỡng {hold_at:.0%}")
    if reviewed:
        reasons.append(f"{len(reviewed & stems)} ảnh đã được người duyệt (cảnh báo của chúng coi như đã xử lý)")

    return {
        "decision": decision,
        "n_errors": len(errors),
        "n_warn_images": n_warn,
        "n_images": n_images,
        "warn_ratio": round(ratio, 4),
        "reasons": reasons,
    }
