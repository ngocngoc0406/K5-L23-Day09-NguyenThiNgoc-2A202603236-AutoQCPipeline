# Báo cáo Day 09 — Nguyễn Thị Ngọc, 2A202603236

## 1. Kết luận trước
Pipeline kết luận **Hold** (mã thoát 10, `08_summary.json`). Đầu vào **224 ảnh**, cửa vào loại **22 ảnh**, còn **202 ảnh** đi tiếp và được xuất thành **bản nháp** `submission/export/clean_v1/` (202 file nhãn, `manifest.json` ghi `decision=Hold`). Bản này **chưa phải bản phát hành**.
Không còn lỗi bắt buộc nào (0 lỗi ERROR trong `07_error_list_v3`). Tuy vậy, **38/202 ảnh (18,8%)** vẫn còn cảnh báo mà chưa ai duyệt, vượt ngưỡng 10%. Nguyên nhân là hàng đợi có 125 ảnh, còn ngân sách duyệt chỉ 80 ảnh.

## 2. Lỗi và phân việc
Số liệu lấy từ `02_error_list_v1` (lỗi trước khi sửa). Mẫu số là 224 ảnh với các lỗi ở cửa vào và 202 ảnh với các lỗi nhãn.

| Mã lỗi | Số ảnh/dòng | Ai sửa (máy/người) | Vì sao |
|---|---:|---|---|
| DUP_IMAGE_EXACT | 8 ảnh / 224 | máy (loại ở cửa vào) | trùng từng byte (md5), quy tắc chắc chắn |
| DUP_IMAGE_NEAR | 4 ảnh / 224 | máy (loại ở cửa vào) | phash ≤ 12; mình đã mở xem cả 4 cặp, đều là trùng thật (§3) |
| LEAK_TEST | 5 ảnh / 224 | máy (loại ở cửa vào) | trùng ảnh test/val, giữ lại thì kết quả đo trên test bị sai |
| CORRUPT_IMAGE / BAD_SIZE | 2 / 3 ảnh | máy (loại ở cửa vào) | ảnh hỏng hoặc cạnh < 250 px, không dùng được |
| BAD_CLASS_NAME | 2 dòng, 1 file (`data.yaml`) | máy (`rename_classes`) | ghi lại `names` cho đúng `cfg.classes` |
| BAD_FORMAT / BAD_CLASS_ID / BOX_ZERO / DUP_BOX | 3 / 6 / 4 / 7 dòng | máy (`drop_line`, 20 dòng) | dòng hỏng thì không suy ra được box đúng; dòng trùng thì xoá bản sau |
| BOX_OUT_OF_IMAGE | 8 dòng / 8 ảnh | máy (`clip_box`, 8 dòng) | cắt mép box về [0,1], giữ nguyên lớp |
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
4. **Dòng trống, nhãn đúng cú pháp nhưng sai nghĩa** (ví dụ box bao nhầm vật) ở 45 ảnh không được duyệt sẽ đi thẳng vào bản xuất.

## 5. Train: raw vs clean (tùy chọn, chấm riêng)
**Chưa chạy.** Phần train cần GPU (Colab T4, khoảng 20 phút) và chưa thực hiện ở lượt nộp này. `make check-core` bỏ qua phần này, nên chưa có số liệu và chưa có kết luận nào về việc clean có tốt hơn raw hay không.

## 6. Quyết định và ghi chú AI
**(a) Quyết định: Hold.** Không phát hành `clean_v1`. Có ba cách để chuyển sang Release:
1. Người duyệt thêm ít nhất 18 trong 45 ảnh còn lại của hàng đợi, sao cho số ảnh còn cảnh báo chưa duyệt < 10% (tức < 20,2/202 ảnh). Chạy `--no-review` rồi `--resume-after-review` để ghi nhận.
2. Hoặc, ở lô sau, tăng ngân sách duyệt lên khoảng 100 ảnh.
3. **Không** đổi `conf` lên 0.8 chỉ để Release, vì sẽ mất khoảng 25% recall của MISSING (§3).

Nếu muốn train thử thì dùng bản nháp hiện tại và ghi rõ là Hold.

**(b) Dùng AI: có** (Claude Code, trong VS Code).
- **Prompt chính:** "Viết lần lượt 4 module `label_format`, `gate`, `autofix`, `second_opinion` theo đúng docstring (đầu vào là `ds`, `cfg`, issues; đầu ra là list[Issue] hoặc dict). Mọi ngưỡng phải đọc từ `cfg`, không sửa `data/raw`, không sửa test hay file đã ghim. Dòng hỏng không được làm script chết. Chạy pytest sau mỗi module."
- **Cách kiểm:**
  - chạy `pytest` sau từng module (79/79 xanh);
  - chạy `make calibrate` để so với lỗi chèn trong calib (tất cả lỗi cú pháp đạt P = R = 1.00);
  - đọc `03_fixes.csv` để chắc rằng mỗi dòng bị xoá hoặc cắt đều đúng như ghi trong log;
  - ghép ảnh các cặp bị cờ trùng để mở xem bằng mắt.
- **Một lần AI sai:** bản đầu của `autofix._fix_yaml` luôn thêm khoá `nc` vào `data.yaml`, kể cả khi file gốc không có. Đó là một thay đổi không được yêu cầu và không được ghi vào log. Khi đọc lại code mình phát hiện ra, và đã sửa thành chỉ cập nhật `nc` khi khoá này đã có sẵn.

*Ghi chú môi trường:* trên Windows, `check_submission.py --no-train` báo sai rằng `pipeline\calibrate.py` "nhắc tới MANIFEST/data/calib". Lý do là script so đường dẫn có dấu `\` với danh sách file ghim dùng dấu `/`. File `pipeline/calibrate.py` là file đã viết sẵn, được ghim trong `scripts/_protected.json`, và chưa bị sửa.
