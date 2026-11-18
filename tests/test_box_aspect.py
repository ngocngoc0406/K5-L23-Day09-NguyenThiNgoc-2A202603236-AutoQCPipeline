"""Test cho check thưởng box_aspect (file mới, không thuộc bộ test đề)."""
from pipeline.checks import box_aspect


def run(make_ds, cfg, lines, size=(640, 480)):
    ds = make_ds(images={"a": 1}, labels={"a": lines}, size=size)
    return box_aspect.run(ds, cfg)


def lines_of(issues):
    return [(i.image, i.line) for i in issues if i.code == "BOX_ASPECT_EXTREME"]


def test_normal_boxes_are_silent(make_ds, cfg):
    assert run(make_ds, cfg, ["1 0.5 0.5 0.2 0.6", "0 0.5 0.5 0.4 0.2"]) == []


def test_flat_and_thin_boxes_are_warned(make_ds, cfg):
    # 0.9*640 / (0.05*480) = 24 (dẹt);  0.01*640 = 6.4 px rộng, 0.5*480 = 240 px cao -> 37.5 (mảnh)
    iss = run(make_ds, cfg, ["0 0.5 0.5 0.9 0.05", "1 0.5 0.5 0.2 0.3", "1 0.5 0.5 0.01 0.5"])
    assert lines_of(iss) == [("a", 1), ("a", 3)]
    assert all(i.severity == "warn" for i in iss)
    assert iss[0].extra["class"] == "car" and abs(iss[0].extra["ratio"] - 24.0) < 0.01


def test_ratio_is_measured_in_pixels_not_normalised_units(make_ds, cfg):
    # chuẩn hoá: w/h = 0.6/0.1 = 6 (dưới 8), nhưng ảnh 1280x480 -> 768/48 = 16 px (trên 8)
    assert lines_of(run(make_ds, cfg, ["0 0.5 0.5 0.6 0.1"], size=(1280, 480))) == [("a", 1)]
    assert run(make_ds, cfg, ["0 0.5 0.5 0.6 0.1"], size=(480, 480)) == []


def test_threshold_comes_from_config_with_default(make_ds, cfg):
    line = ["0 0.5 0.5 0.6 0.1"]                                   # 384/48 = 8.0 px trên ảnh 640x480
    assert run(make_ds, cfg, line) == []                           # mặc định 8: bằng ngưỡng thì không báo
    cfg["box_aspect"] = {"max_ratio": 5}
    assert lines_of(run(make_ds, cfg, line)) == [("a", 1)]


def test_broken_lines_do_not_crash_and_keep_line_numbers(make_ds, cfg):
    iss = run(make_ds, cfg, ["garbage", "93 0.5 0.5 0.9 0.01", "0 0.5 0.5 0 0.3", "", "0 0.5 0.5 0.9 0.05"])
    assert lines_of(iss) == [("a", 5)]


def test_image_without_label_file_is_skipped(make_ds, cfg):
    ds = make_ds(images={"a": 1, "b": 2}, labels={"a": ["1 0.5 0.5 0.2 0.3"]})
    assert box_aspect.run(ds, cfg) == []
