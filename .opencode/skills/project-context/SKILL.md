---
name: Project Context & Handoff
description: Quản lý bộ nhớ dài hạn của dự án Hoa Mi qua nhiều phiên và nhiều AI model. Dùng khi bắt đầu hoặc kết thúc phiên, khi chuyển sang model khác, khi cần khôi phục việc đang làm dở, khi cập nhật PROJECT-STATE/HANDOFF/DECISIONS, hoặc khi nghi tài liệu đã lệch code.
---

# Project Context & Handoff

Mục tiêu: một model **chưa từng thấy repo** đọc 3 file là tiếp tục được công việc,
không hỏi lại người dùng, không phá quyết định cũ.

## Khi nào dùng

- Bắt đầu phiên mới hoặc được người dùng chuyển từ model khác sang.
- Kết thúc một thay đổi lớn, trước khi bàn giao.
- Người dùng hỏi "đang làm đến đâu", "còn gì dở", "context nằm ở đâu".
- `tools/context_check.py` báo FAIL.
- Cần thêm symbol/file/skill mới nên phải cập nhật `docs/context-map.json`.

Không dùng skill này để code tính năng; nó chỉ quản lý tri thức và bàn giao.

## Nguồn sự thật (theo thứ tự)

| Thứ tự | File | Trả lời câu hỏi |
|---|---|---|
| 1 | code (`app.py`, module) | hiện tại **thực sự** chạy gì |
| 2 | `docs/context-map.json` | symbol/file/skill nào được coi là quan trọng |
| 3 | `docs/ARCHITECTURE.md` | dữ liệu chảy thế nào, sửa ở đâu |
| 4 | `docs/DECISIONS.md` | vì sao làm vậy, điều gì bị cấm |
| 5 | `docs/PROJECT-STATE.md` | đang ở đâu, tiếp theo làm gì |
| 6 | `docs/HANDOFF.md` | phiên trước đã làm gì, còn treo gì |
| 7 | `README.md` | người dùng thấy gì |

Code > tài liệu. Nhưng nếu lệch, **sửa tài liệu trong cùng phiên**; không để drift.

## Quy trình mở phiên

1. Chạy:
   ```powershell
   $env:PYTHONIOENCODING='utf-8'
   & "C:\Users\ADMIN\miniforge3\python.exe" tools\context_check.py
   ```
2. Nếu FAIL: phân loại
   - Symbol/file biến mất → code đã đổi: cập nhật map hoặc khôi phục.
   - Skill thiếu/description sai → sửa skill.
   - Version lệch → sửa README hoặc `VERSION`.
3. Đọc `docs/PROJECT-STATE.md` mục 1–2.
4. Đọc **mục cuối** `docs/HANDOFF.md`.
5. Đọc các `D-xx` liên quan trong `docs/DECISIONS.md`.
6. Nạp skill tính năng tương ứng (bảng trong `AGENTS.md` §6).
7. Tóm tắt cho người dùng: hiện trạng · việc dở · rủi ro · đề xuất bước tiếp.
   Không bắt đầu sửa trước khi tóm tắt nếu việc lớn.

## Quy trình đóng phiên

1. **PROJECT-STATE**: cập nhật
   - "Cập nhật lần cuối" → hôm nay.
   - Mục 1: tối đa 3 việc, việc nào xong thì bỏ, việc mới thêm vào.
   - Mục 2: đổi trạng thái ✅/🟡/⛔ nếu hành vi đổi.
   - Mục 3: thêm nợ kỹ thuật mới (chỉ khi thật sự mới).
2. **HANDOFF**: thêm một mục ở cuối theo template trong file. Không sửa mục cũ.
   Ghi rõ:
   - file + symbol đã đổi,
   - đã kiểm chứng gì / **chưa** kiểm chứng gì,
   - cảnh báo cho model sau.
3. **DECISIONS**: nếu có quyết định kiến trúc/đánh đổi mới, thêm `D-xx`.
   Nếu đổi quyết định cũ, thêm mục mới ghi "thay thế D-xx".
4. **context-map**: nếu thêm/xóa symbol quan trọng, file tài liệu, hoặc skill.
5. Chạy lại:
   ```powershell
   & "C:\Users\ADMIN\miniforge3\python.exe" tools\context_check.py --snapshot
   & "C:\Users\ADMIN\miniforge3\python.exe" tools\smoke_test.py
   ```
6. Dán kết quả vào mục handoff.

## Prompt bàn giao cho model mới

> Bạn tiếp quản dự án **Hoa Mi** tại `D:\Hoa Mi`.
> Đọc theo thứ tự: `AGENTS.md` → `docs/PROJECT-STATE.md` → mục cuối
> `docs/HANDOFF.md` → `docs/DECISIONS.md` → skill khớp tính năng.
> Chạy `tools/context_check.py` trước khi sửa. Không đọc toàn bộ `app.py`.
> Tóm tắt hiện trạng và việc đang dở trước khi đề xuất bước tiếp.
> Kết thúc phiên: cập nhật `PROJECT-STATE` + thêm mục `HANDOFF`.

## Cách ghi để model sau dùng được

**Nên:**
- Ghi **symbol**, không ghi số dòng: `App._w_prac`, không phải "dòng 2895".
- Ghi **hành vi**, không ghi cảm nhận: "im lặng <0,8% không chấm", không phải "mic hơi lỗi".
- Ghi **lệnh kiểm chứng** kèm kết quả thật.
- Ghi **chưa kiểm chứng** rõ ràng; đó là thông tin quý, không phải điểm yếu.

**Không:**
- Không chép lại code vào tài liệu (sẽ lệch ngay).
- Không ghi bí mật, token, cookie, dữ liệu cá nhân.
- Không ghi "đã xong" khi chưa chạy thử.
- Không xóa lịch sử handoff; chỉ thêm.

## Cấu trúc thư mục context

```
AGENTS.md                 # luật + nghi thức + bất biến
docs/
  PROJECT-STATE.md        # hiện trạng (sửa mỗi phiên)
  HANDOFF.md              # nhật ký (append)
  DECISIONS.md            # ADR (append)
  ARCHITECTURE.md         # luồng + contract (sửa khi kiến trúc đổi)
  FEATURES.md             # bản đồ tính năng (sửa khi thêm tính năng)
  ROADMAP.md              # thứ tự + tiêu chí xong
  context-map.json        # danh sách symbol/file/skill để kiểm tra drift
  CONTEXT-SNAPSHOT.md     # sinh tự động, KHÔNG sửa tay
.opencode/skills/         # tri thức theo tính năng
tools/context_check.py    # cổng kiểm tra
tools/smoke_test.py       # lưới an toàn
```

## Kiểm chứng

```powershell
$env:PYTHONIOENCODING='utf-8'
& "C:\Users\ADMIN\miniforge3\python.exe" tools\context_check.py
& "C:\Users\ADMIN\miniforge3\python.exe" tools\smoke_test.py
```

- `context_check` PASS nghĩa là tài liệu/skill **không nhắc symbol đã chết**,
  không có skill mồ côi, version khớp, dữ liệu/asset còn đủ.
- Nó **không** chứng minh app chạy đúng; vẫn phải test hành vi.

## Cạm bẫy

1. **Sửa HANDOFF cũ** → mất dấu vết; model sau không biết vì sao đổi.
2. **Ghi số dòng** → lệch sau một lần format.
3. **Thêm skill nhưng quên map** → check FAIL (cố ý).
4. **Đổi version trong code mà quên README** → check FAIL.
5. **Coi snapshot là nguồn sự thật** → nó chỉ là ảnh chụp; nguồn là code + map.
6. **Nhồi cả app.py vào context** → tốn token, dễ bỏ sót; dùng map + skill.
