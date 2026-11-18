# Báo cáo Day 09 — Nguyễn Thị Ngọc, 2A202603236

## 1. Kết luận trước
Pipeline kết luận **Hold** (mã thoát 10, `08_summary.json`). Đầu vào **224 ảnh**, cửa vào loại **22 ảnh**, còn **202 ảnh** đi tiếp và được xuất thành **bản nháp** `submission/export/clean_v1/` (202 file nhãn, `manifest.json` ghi `decision=Hold`). Bản này **chưa phải bản phát hành**.
Không còn lỗi bắt buộc nào (0 lỗi ERROR trong `07_error_list_v3`). Tuy vậy, **38/202 ảnh (18,8%)** vẫn còn cảnh báo mà chưa ai duyệt, vượt ngưỡng 10%. Nguyên nhân là hàng đợi có 125 ảnh, còn ngân sách duyệt chỉ 80 ảnh.

## 2. Lỗi và phân việc
Số liệu lấy từ `02_error_list_v1` (lỗi trước khi sửa). Mẫu số là 224 ảnh với các lỗi ở cửa vào và 202 ảnh với các lỗi nhãn.

| Mã lỗi | Số ảnh/dòng | Ai sửa (máy/người) | Vì sao |
|---|---:|---|---|
| DUP_IMAGE_EXACT | 8 ảnh / 224 | máy loại ở cửa vào; người kiểm lại `01_intake` | trùng từng byte (md5), quy tắc chắc chắn |
| DUP_IMAGE_NEAR | 4 ảnh / 224 | máy loại ở cửa vào; người mở xem từng cặp | phash ≤ 12; cả 4 cặp mở ra xem đều là trùng thật (§3) |
| LEAK_TEST | 5 ảnh / 224 | máy loại ở cửa vào; người mở xem từng cặp | trùng ảnh test/val, giữ lại thì kết quả đo trên test bị sai |
| CORRUPT_IMAGE / BAD_SIZE | 2 / 3 ảnh | máy loại ở cửa vào | ảnh hỏng hoặc cạnh < 250 px, không dùng được |
| BAD_CLASS_NAME | 2 dòng, 1 file (`data.yaml`) | máy (`rename_classes`); người kiểm lại `03_fixes.csv` | ghi lại `names` cho đúng `cfg.classes` |
| BAD_FORMAT / BAD_CLASS_ID / BOX_ZERO / DUP_BOX | 3 / 6 / 4 / 7 dòng | máy (`drop_line`, 20 dòng); người kiểm lại qua `03_fixes.csv` và hàng đợi duyệt (`FIXED_DROP_LINE`) | dòng hỏng thì không suy ra được box đúng; dòng trùng thì xoá bản sau |
| BOX_OUT_OF_IMAGE | 8 dòng / 8 ảnh | máy (`clip_box`, 8 dòng); người kiểm lại qua hàng đợi duyệt (`FIXED_CLIP_BOX`) | cắt mép box về [0,1], giữ nguyên lớp |
| MISSING_LABEL_FILE | 6 ảnh / 202 | **người** (`needs_label`) | máy không bịa nhãn; ảnh được đẩy lên đầu hàng đợi (trọng số 10) |
| POSSIBLE_MISSING | 53 dòng / 52 ảnh | người | model lớn thấy vật nhưng nhãn không có box (chỉ là ý kiến thứ hai) |
| POSSIBLE_WRONG_CLASS | 18 ảnh | người | lớp hợp lệ nhưng có thể sai nghĩa, quy tắc không bắt được |
| POSSIBLE_LOOSE_BOX | 28 dòng / 24 ảnh | người | box lỏng hoặc lệch so với model |
| POSSIBLE_FALSE_POS | 25 dòng / 24 ảnh | người | box nhãn không khớp vật nào model thấy |
| EMPTY_LABEL / BOX_TINY / BOX_HUGE / CLASS_RARE | 12 ảnh / 6 dòng / 3 dòng / 4 dòng (lớp lạ, cấp dataset) | người | cảnh báo: ảnh nền hay thiếu nhãn, box quá nhỏ hoặc quá to |

Tổng cộng máy thực hiện **35 thay đổi** trong `03_fixes.csv`: 20 `drop_line`, 8 `clip_box`, 1 `rename_classes` và 6 `needs_label`. Mỗi thay đổi ghi lại nội dung trước → sau, và không có thay đổi nào chạm vào `data/raw`.
Hai tác dụng phụ đáng chú ý trong `04_error_list_v2`:
- EMPTY_LABEL tăng từ 12 lên 15, vì xoá dòng hỏng làm 3 file nhãn thành rỗng.
- BOX_TINY tăng từ 6 lên 7, vì có một box sau khi cắt chỉ còn rất hẹp.

Cả hai đều chuyển sang cho người xem.

**Hàng đợi.** `05_review_queue.csv` có **125 ảnh**, xếp theo tổng trọng số `review.weights`. Đầu hàng là `img_0020` (11,5 điểm; vừa bị xoá dòng, vừa có MISSING và WRONG_CLASS), tiếp theo là 6 ảnh `NEEDS_LABEL` (10 điểm mỗi ảnh). Sau đó đến các ảnh có WRONG_CLASS (3) và MISSING/FALSE_POS (2).
Với ngân sách **80/125 ảnh (64%)**, người duyệt xử lý hết các ảnh chưa có nhãn và phần lớn các ảnh có cảnh báo ngữ nghĩa nặng. Số ảnh có WRONG_CLASS giảm từ 18 xuống 3 và số ảnh có MISSING giảm từ 52 xuống 12 (`07_error_list_v3`).
45 ảnh còn lại không ai xem. Trong đó 38 ảnh vẫn còn cảnh báo, chủ yếu là LOOSE_BOX và FALSE_POS (trọng số thấp hơn), và chính số này dẫn tới Hold.

## 3. Calibration (2 ngưỡng)
| Tham số | Khởi đầu | Đã chọn | Precision / Recall (trước → sau) | Lý do (đánh đổi) |
|---|---|---|---|---|
| `duplicates.phash_dist` | 2 | **12** | DUP_IMAGE_NEAR: 1.00 / 0.50 → 1.00 / 0.67 (EXACT giữ 1.00 / 1.00) | Đây là lỗi bị **tự động loại ảnh**, nên mình ưu tiên precision (mất một FP là mất một ảnh tốt). Trên calib, các giá trị 4–14 cho kết quả như nhau. Trên raw, mọi cặp bị cờ ở khoảng cách ≤ 10 đều là trùng thật, còn cờ sai đầu tiên xuất hiện ở 16. Chọn 12 để có khoảng an toàn ở cả hai phía. |
| `second_opinion.conf` | 0.25 | **0.6** | WRONG_CLASS 0.56 / 0.83 → 0.62 / 0.83; MISSING 0.50 / 1.00 → 0.57 / 1.00; LOOSE_BOX 0.29 / 0.40 → 0.20 / 0.20; FALSE_POS 0.36 / 1.00 (không đổi, vì dùng `fp_conf`) | Đây là cảnh báo cho người, nên giữ recall. Từ 0.25 lên 0.6, recall của WRONG_CLASS và MISSING không giảm mà precision tăng, và hàng đợi trên raw giảm từ 143 xuống 125 ảnh. Lên 0.7 hoặc 0.8 thì MISSING recall tụt còn 0.88 hoặc 0.75 (bỏ sót 1–2 trên 8 lỗi chèn). Mình không chọn 0.8 dù ngưỡng đó cho **Release** (16/202 = 7,9%), vì làm vậy là hạ recall chỉ để hàng đợi vừa ngân sách. |

**Một chỗ calibration có thể đánh lừa.** Nếu chỉ nhìn calib, `phash_dist = 16` là tốt nhất (DUP_IMAGE_NEAR F1 = 0.91, cao nhất bảng sweep). Nhưng khi chạy check trên **raw** với 16, số LEAK_TEST nhảy từ 5 lên 11 và DUP_IMAGE_NEAR từ 4 lên 7. Mình ghép ảnh từng cặp để xem: trong 9 cờ mới thì **8 cờ sai**, ví dụ `img_0011` (tennis) bị coi là trùng `img_0008` (trượt tuyết), `img_0013` (bàn làm việc) bị coi là trùng `test_087` (bóng chày). Chỉ có `img_0084` ≈ `img_0074` là trùng thật.
Ở 20 thì tệ hơn nữa: 105 ảnh bị báo LEAK_TEST, tức gần nửa lô bị loại. Lý do là calib chỉ có 6 ca gần trùng nên một ca đổi đã làm recall nhảy 17%, và calib không có ca LEAK_TEST nào để lộ ra việc so với 140 ảnh test/val sinh nhiều cờ sai hơn hẳn.
Tương tự, LOOSE_BOX trên calib chỉ có 5 lỗi chèn, nên P/R nhảy theo bậc 20%. Không nên tin con số 0.20 như một ước lượng chính xác.

## 4. Cửa chặn và điều pipeline KHÔNG bắt được
**(a) Gate chặn đúng.** Mình chạy `python -m pipeline.run --budget 0 --reports work/rep_nb --export-dir work/exp_nb`. Không có người duyệt nên 6 ảnh `MISSING_LABEL_FILE` vẫn còn lỗi. Kết quả:
- log ghi `kết luận: REWORK — còn 6 lỗi bắt buộc trên 6 ảnh/mục (MISSING_LABEL_FILE)` rồi `Bước 5/5 KHÔNG xuất: còn lỗi bắt buộc (Rework)`;
- **mã thoát 20**;
- thư mục `work/exp_nb` **không được tạo**, tức không có dataset nào được xuất.

Unit test `test_error_cannot_be_hidden_by_reviewed` cũng cho thấy lỗi bắt buộc không thể bị "che" chỉ vì ảnh đã qua người duyệt.

**(b) Điểm mù có bằng chứng.**
1. **Ảnh trùng bị biến đổi mạnh.** `img_0084` và `img_0074` là cùng một ảnh nhưng cách nhau phash 16, lớn hơn ngưỡng 12, nên lọt qua. Đẩy ngưỡng lên để bắt cặp này thì xoá nhầm 8 ảnh khác (§3). Trên calib, DUP_IMAGE_NEAR cũng chỉ đạt recall 0.67 (bỏ sót 2/6 ca biến đổi mạnh nhất).
2. **Box lỏng nhẹ.** POSSIBLE_LOOSE_BOX chỉ có recall **0.20** trên calib (bắt 1/5) với ngưỡng đã chọn. Box lệch nhẹ (IoU với model vẫn ≥ `iou_loose` = 0.5) không bị cờ. Box hẹp xuất hiện sau `clip_box` cũng chỉ thành cảnh báo BOX_TINY.
3. **Nhầm lớp mà model lớn cũng nhầm.** Second opinion chỉ là một model khác: trên calib, WRONG_CLASS bỏ sót 1/6 ca. Thêm nữa, nhãn raw được pre-label bằng yolo26n, cùng họ với yolo26l, nên lỗi chung của cả họ model sẽ không bị cờ. Calib lại chủ yếu là person→car, trong khi raw nghiêng về nhầm car/truck/bus.
4. **Nhãn đúng cú pháp nhưng sai nghĩa** (ví dụ box bao nhầm vật) ở 45 ảnh không được duyệt sẽ đi thẳng vào bản xuất, xem hai ví dụ cụ thể ở (c).

**(c) 3 lỗi tự nhìn thấy** (mở 10 ảnh raw bằng `scripts/viz_labels.py`, rồi đối chiếu với báo cáo của pipeline):

| Ảnh | Mình thấy gì | Pipeline có bắt không? | Số phận trong `clean_v1` |
|---|---|---|---|
| `img_0001` | Người lính bên phải ảnh, thấy rất rõ, nhưng **không có box** (thiếu nhãn) | Có: `POSSIBLE_MISSING` (conf 0.95) | Ảnh nằm trong 80 ảnh đã duyệt nên **đã được sửa**. |
| `img_0111` | Box **bus** nhỏ vẽ lên dòng chữ watermark "054_263" ở góc dưới trái; trong ảnh không có xe buýt (đúng cú pháp nhưng sai nghĩa) | Có: `POSSIBLE_FALSE_POS` (dòng 2, IoU 0.00) | Ưu tiên chỉ 2.0, nằm **ngoài ngân sách 80 ảnh** nên **vẫn còn trong bản xuất**. |
| `img_0149` | Box **car** trên mặt đường trống bên trái, không có xe nào | Có: `POSSIBLE_FALSE_POS` (dòng 3, IoU 0.00) | Như `img_0111`: không ai duyệt, **vẫn còn trong bản xuất**. |

Hai bài học:
- **Máy thấy cái mắt bỏ qua.** Ở `img_0001` còn có một `DUP_BOX` (dòng 3 trùng dòng 1, IoU 0.995) mà mình không nhìn ra trên ảnh, vì hai box chồng khít lên nhau. Máy bắt và tự xoá dòng đó.
- **Cờ đúng nhưng không ai xem thì vẫn lọt.** Hai lỗi ở `img_0111` và `img_0149` được pipeline cờ chính xác, nhưng vì không được duyệt nên vẫn nằm trong dataset. Đây là bằng chứng cụ thể cho kết luận **Hold**: dataset chưa nên phát hành khi còn các cảnh báo kiểu này chưa ai xem.

## 5. Train: raw vs clean (tùy chọn, chấm riêng)
**Cách chạy.** Mình train **trên máy** bằng GPU RTX 3050 Laptop (4 GB) thay cho Colab, dùng `scripts/train_compare.py --variants raw clean --seeds 0 1 --epochs 20 --batch 8`, rồi tổng hợp bằng `scripts/summarize_results.py`.
- Model là yolo26n, 20 epoch, imgsz 640, 2 seed cho mỗi biến thể. Mọi lượt dùng cùng val (gold_val 40 ảnh) và cùng test (100 ảnh).
- `batch = 8` thay vì 16 mặc định: ở batch 16, GPU 4 GB bị hết bộ nhớ và ultralytics **tự** hạ batch. Như vậy file JSON sẽ ghi sai batch và các lượt có thể không cùng batch, nên mình dừng lại và đặt `batch = 8` cố định cho **cả 4 lượt**.
- `clean` là bản xuất `clean_v1` có kết luận **Hold**, nên đây là bản nháp, chưa phải bản phát hành.
- **Train lại 2 lượt `clean`:** trên Windows, `manifest.json` được ghi với CRLF, nên `manifest_sha1` trong lần đầu là sha1 của bản CRLF và không khớp bản LF mà git lưu. Mình chuyển file về LF (nội dung không đổi) rồi train lại 2 lượt `clean`. Số đo giống hệt lần đầu nhờ `deterministic=True`. Không có file JSON nào bị sửa tay.

| biến thể | #ảnh train | số seed | map50 (TB ± độ lệch) | map50_95 (TB ± độ lệch) | precision (TB ± độ lệch) | recall (TB ± độ lệch) |
|---|---|---|---|---|---|---|
| raw | 224 | 2 | 0.702 ± 0.014 | 0.488 ± 0.018 | 0.784 ± 0.082 | 0.597 ± 0.010 |
| clean | 202 | 2 | 0.703 ± 0.012 | 0.498 ± 0.007 | 0.730 ± 0.028 | 0.618 ± 0.003 |

**So với nhiễu.** Chênh mAP50 (clean − raw) = **+0.001**, nhỏ hơn khoảng 12 lần độ lệch giữa hai seed (0.012–0.014). Chênh mAP50-95 là +0.010, cũng chỉ cỡ độ lệch của raw (0.018).
Nhiễu theo seed rất lớn ở mức từng lớp: AP50 của lớp truck với clean là 0.654 ở seed 0 nhưng 0.549 ở seed 1. Precision của raw dao động ±0.082.
**Kết luận trung thực:** với 2 seed và 100 ảnh test, **chưa thể nói clean tốt hơn raw**, vì khác biệt nằm trong nhiễu. Recall của clean nhỉnh hơn (0.618 so với 0.597, độ lệch 0.003–0.010), nhưng precision lại thấp hơn, nên mình không coi đây là bằng chứng.

**Giả thuyết và cách kiểm.**
1. **Raw được lợi nhờ rò rỉ test.** Raw còn 5 ảnh LEAK_TEST trùng với tập test, nên điểm test của raw có thể bị thổi phồng, và cái lợi của việc làm sạch bị che đi. Cách kiểm: đo lại cả hai biến thể trên test **sau khi bỏ** 5 ảnh `test_*` bị rò, rồi so lại khoảng chênh.
2. **Nhãn clean vẫn phần lớn là nhãn máy.** Chỉ 80/202 ảnh được người duyệt. 38 ảnh còn cảnh báo, và các lỗi ngữ nghĩa như box lỏng hay thiếu box ở 45 ảnh không được duyệt vẫn nằm trong clean. Ngoài ra clean ít hơn 22 ảnh train. Cách kiểm: train thêm biến thể `oracle` (nhãn người) làm trần và `auto` (`--budget 0`) làm sàn, xem clean đứng ở đâu giữa hai mức đó.
3. **Model đã được pretrain trên COCO, train ít.** yolo26n đã biết cả 4 lớp, nên 20 epoch trên khoảng 200 ảnh ít bị nhiễu nhãn ảnh hưởng. Cách kiểm: tăng lên ≥ 5 seed và 40 epoch, hoặc train từ đầu, rồi xem khoảng chênh có vượt độ lệch không.

**Việc tiếp theo:** chạy ≥ 5 seed, thêm biến thể `oracle` và `auto`, đo trên test đã bỏ ảnh rò rỉ. Chỉ kết luận khi |chênh| > 2 × độ lệch.

## 6. Quyết định và ghi chú AI
**(a) Quyết định: Hold.** Không phát hành `clean_v1`. Có ba cách để chuyển sang Release:
1. Người duyệt thêm ít nhất 18 trong 45 ảnh còn lại của hàng đợi, sao cho số ảnh còn cảnh báo chưa duyệt < 10% (tức < 20,2/202 ảnh). Chạy `--no-review` rồi `--resume-after-review` để ghi nhận.
2. Hoặc, ở lô sau, tăng ngân sách duyệt lên khoảng 100 ảnh.
3. **Không** đổi `conf` lên 0.8 chỉ để Release, vì sẽ mất khoảng 25% recall của MISSING (§3).

Bản nháp `clean_v1` chỉ dùng cho thí nghiệm train ở §5, không phải bản phát hành.

**(b) Dùng AI: có** (Claude Code, hỗ trợ viết 4 module, check `box_aspect` và các script chạy thí nghiệm).
1. **Prompt chính:** yêu cầu AI phân tích đề rồi làm lần lượt từng bước theo GUIDE. 4 ý của `docs/PROMPTING.md` không được viết riêng trong prompt mà lấy từ docstring của từng stub, bộ test và `RULES.md`: vào/ra, quy tắc kiểm, kiểu kết quả, và giới hạn an toàn (không sửa `data/raw`, test hay file đã ghim; ngưỡng đọc từ `cfg`).
2. **Cách mình kiểm:**
   - chạy `pytest` (79/79 xanh) và `make calibrate` trên lỗi chèn sẵn (mọi lỗi cú pháp đạt P = R = 1.00);
   - kiểm 3 ca "test xanh chưa chắc đúng" mà slide nêu:
     - một dòng dính 2 lỗi: xoá một lần, không cắt thêm;
     - dòng trống ở giữa file: số dòng gốc vẫn giữ đúng;
     - một ảnh có nhiều dự đoán: đủ issue, đúng thứ tự.
     
     Cả 3 đều có test riêng trong `tests/test_autofix.py`, `tests/test_label_format.py` và `tests/test_second_opinion.py`, và đều xanh. Sau đó chạy cả pipeline và xem lại nhãn bằng `viz_labels.py`;
   - đọc `03_fixes.csv` và mở xem các ảnh bị cờ;
   - tự duyệt 20 ảnh trên CVAT;
   - đối chiếu từng con số trong REPORT với các file do script sinh ra. Lần đối chiếu này tìm ra và sửa 2 chỗ ghi sai.
3. **Một lần AI sai:** AI bỏ qua bước 1 của GUIDE (chạy `pytest` trên code gốc, phải ra 55 failed / 24 passed) mà viết code luôn. Mình phát hiện ra và yêu cầu chạy bù trên bản sao của commit gốc; kết quả ra đúng 55 failed / 24 passed.

**(c) Thưởng: check mới `box_aspect`** ([pipeline/checks/box_aspect.py](../pipeline/checks/box_aspect.py), test ở [tests/test_box_aspect.py](../tests/test_box_aspect.py), 6/6 xanh).
- **Quy tắc:** cảnh báo `BOX_ASPECT_EXTREME` (WARN) khi cạnh dài / cạnh ngắn **tính theo pixel** > 8.
- **Ngưỡng 8:** trên nhãn người của gold_val, 99% box có tỉ lệ ≤ 6,5 (chỉ có một xe bị che khuất ở 11,4); trên calib, tỉ lệ cao nhất là 4,0.
- **Vì sao tính theo pixel:** cùng toạ độ chuẩn hoá 0,6 × 0,1 là tỉ lệ 16 trên ảnh 1280×480 nhưng chỉ 6 trên ảnh vuông. Có test riêng cho ca này.
- **Cách chạy:** `pipeline/checks/__init__.py` và `configs/pipeline.yaml` đều bị ghim, nên check chạy riêng bằng `python scripts/extra_checks.py`, ghi ra `reports/09_box_aspect.*`. Ngưỡng được đọc từ `cfg["box_aspect"]["max_ratio"]`, không có thì dùng mặc định.
- **Kết quả:** trên raw có 3 cảnh báo trên 3/224 ảnh, đều là người rất mảnh (`img_0042`, `img_0076` là bản trùng của `img_0042`, và `img_0155`). Sau pipeline còn 2 cảnh báo trên 2/202 ảnh:
  - `img_0042` (người, tỉ lệ 9,6);
  - `img_0124` (xe, tỉ lệ 9,1).
- **Khi mở xem bằng mắt:** box ở `img_0155` là một lát người bị cắt ở mép phải ảnh, đúng là ca mơ hồ nên để người xem. Ảnh này đã được duyệt nên không còn trong kết quả sau pipeline.

**(d) Thưởng: CVAT, lọc box nhỏ** (slide và `docs/CVAT_FILTER.md` gọi phần này là "mục 6(b)"; mục 6(b) ở đây đã dùng cho ghi chú AI theo mẫu REPORT, nên CVAT được ghi ở 6(d)). Trên CVAT 2.81 cục bộ, mình tạo project "Day09 AutoQC" từ `cvat/labels.json` (4 nhãn kèm thuộc tính `can_review`) và task gồm 20 ảnh đầu `05_review_queue.csv`, rồi import nhãn pipeline dạng YOLO 1.1 (131 box).
- **Kết quả lọc:** bộ lọc `width < 20` khớp **9 box trên 4 ảnh**, đều là lớp person:

  | Ảnh | Số box | Bề rộng (px) |
  |---|---:|---|
  | `img_0020` | 3 | 15,9 · 16,3 · 17,6 |
  | `img_0030` | 3 | 15,0 · 19,0 · 19,3 |
  | `img_0053` | 1 | 16,5 |
  | `img_0135` | 2 | 16,5 · 18,7 |

  Ảnh chụp nằm trong `submission/cvat/`:
  - `01_filter_rule_width_lt_20.png`: luật lọc `Width < 20` trong hộp thoại Filters.
  - `02_width_lt_20_<ảnh>.png`: 4 ảnh sau khi lọc, mỗi ảnh chỉ còn các box hẹp (Items: 3 / 3 / 1 / 2).
  
  Các ảnh được chụp từ giao diện CVAT bằng trình duyệt tự động (Playwright).
- **Đối chiếu với `BOX_TINY`:** pipeline **không** cờ box nào trong 9 box này. Lý do là `BOX_TINY` dùng cạnh ngắn < 12 px (quy tắc dự án), còn cạnh ngắn của các box này là 15–19,3 px. Ngưỡng 20 px của slide rộng hơn, nên bắt thêm cả những người đứng xa mà vẫn gán được.
- **Đánh dấu `can_review`:** khi duyệt bằng mắt, mình tích `can_review` cho **11 box trên 7 ảnh**. Chỉ **3/9** box hẹp được đánh dấu (`img_0030` rộng 19,0 px, `img_0053` 16,5 px, `img_0135` 18,7 px); 6 box hẹp còn lại không đánh dấu. 8 box được đánh dấu còn lại đều rộng ≥ 20 px, tức bộ lọc `width < 20` không bắt được. Có những box rất to, như truck ở `img_0127` (rộng 193 px) hay car ở `img_0004` (rộng 119 px), khó vì bị che hoặc vì ranh giới lớp mơ hồ.
- **Một ca đáng chú ý:** box hẹp duy nhất của `img_0053` (rộng 16,5 px) bao **một người trong tấm ảnh in** đặt trên kệ, cạnh ảnh xe cứu thương, chứ không phải người thật trong cảnh. Đúng cú pháp, đúng lớp hình ảnh, nhưng có nên gán nhãn hay không là câu hỏi về ý nghĩa, phải theo guideline. Bộ lọc kích thước không bao giờ trả lời được câu hỏi này; mình đã đánh dấu `can_review` cho box này.
- **Kết luận:** kích thước box nhỏ không đồng nghĩa với "khó". Bộ lọc theo kích thước chỉ là bước rẻ để thu hẹp chỗ cần xem; quyết định cuối vẫn cần người.
- **Về `can_review`:** người gán bật `can_review` khi tự thấy box khó hoặc không chắc (vật bị che, ở xa, mờ, mơ hồ giữa các lớp) để người kiểm xem lại. Trong pipeline, thông tin tương tự nằm ở các cảnh báo `POSSIBLE_*` của `second_opinion` cùng trọng số `review.weights`, vốn đẩy ảnh lên đầu hàng đợi duyệt. Khác biệt là cờ của pipeline do máy đặt dựa trên bất đồng với model, còn `can_review` là người gán tự đánh dấu.

*Ghi chú môi trường:* trên Windows, `check_submission.py --no-train` báo sai rằng `pipeline\calibrate.py` "nhắc tới MANIFEST/data/calib". Lý do là script so đường dẫn có dấu `\` với danh sách file ghim dùng dấu `/`. File `pipeline/calibrate.py` là file đã viết sẵn, được ghim trong `scripts/_protected.json`, và chưa bị sửa.
