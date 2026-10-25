---
name: Skill Authoring (Repo Convention)
description: Tạo hoặc sửa skill trong .opencode/skills của Hoa Mi — frontmatter name/description, độ dài, cấu trúc mục, đăng ký trong docs/context-map.json và cập nhật AGENTS.md. Dùng khi người dùng muốn thêm skill mới, sửa skill, đổi trigger/description, hoặc khi context_check báo lỗi skill.
---

# Skill Authoring

Skill là **hướng dẫn thao tác**, không phải bản sao tài liệu. Một skill tốt giúp
model khác sửa đúng chỗ trong 1–2 lần đọc, không cần grep cả `app.py` 150 KB.

## 1. Vị trí và hợp đồng

```
.opencode/skills/<id>/SKILL.md
```

| Thành phần | Luật |
|---|---|
| `<id>` | kebab-case `^[a-z0-9]+(-[a-z0-9]+)*$`, **là ID thật** khi nạp skill |
| `name` | tiêu đề người đọc, không cần trùng id |
| `description` | 1 câu, ≤ 1024 ký tự, nêu **việc** + **từ khóa kích hoạt** |
| body | ≤ 500 dòng, **phải** có ít nhất một mục `## ` |
| ngôn ngữ | tiếng Việt; identifier/code tiếng Anh |

Frontmatter tối thiểu:

```markdown
---
name: App Something
description: Sửa ... trong Hoa Mi. Dùng khi người dùng nhắc tới ..., ..., hoặc tên file/module.
---

# Something

...
```

Không dùng YAML nhiều dòng, không thêm khóa lạ: `context_check.parse_frontmatter`
chỉ đọc `key: value` một dòng và cắt dấu nháy hai đầu.

## 2. `description` — phần quan trọng nhất

Description là thứ duy nhất model thấy trước khi quyết định nạp skill.

Nên:
- Bắt đầu bằng hành động: "Sửa ...", "Thêm ...", "Chẩn đoán ...".
- Liệt kê 4–8 từ khóa người dùng thật sẽ nói: "micro", "thu âm", "tín hiệu yếu",
  "WDM-KS", "chất lượng bản ghi".
- Nêu tên file/symbol nếu là điểm vào: `prosody.py`, `_prac_done`, `Tab 2`.

Không nên:
- "Tài liệu về ..." (không có hành động).
- Liệt kê toàn bộ chức năng của app.
- Viết quá ngắn kiểu "Code pronunciation" — model không biết khi nào dùng.

## 3. Cấu trúc body

Thứ tự gợi ý, bỏ mục không cần:

1. **Một đoạn định vị**: skill này chịu trách nhiệm gì, **không** chịu trách nhiệm gì.
2. **Đọc trước**: link `docs/...` + bất biến `I#` + quyết định `D-##`.
3. **Bảng symbol**: symbol → hợp đồng/ý nghĩa. Không dán code dài.
4. **Luồng hoặc công thức**: số cụ thể, ngưỡng, thứ tự bước.
5. **Hợp đồng dữ liệu**: khóa dict, kiểu, ai đọc.
6. **Khi sửa — checklist**: thứ tự sửa, test cần thêm, tài liệu cần cập nhật.
7. **Cạm bẫy**: bảng `Triệu chứng | Nguyên nhân`.
8. **Tiêu chí nghiệm thu** (nếu là tính năng có hành vi người dùng).

Quy tắc nội dung:
- **Số liệu phải lấy từ code**, không đoán. Nếu không chắc, mở file đọc rồi viết.
- Trích **tên symbol**, không trích số dòng (dòng trôi).
- Nêu lý do cho ngưỡng quan trọng ("0.32 vì ..."), để người sau không đổi bừa.
- Nêu rõ việc **không** được làm, đặc biệt khi có bất biến.
- Liên kết skill khác thay vì lặp nội dung: `app-pronunciation` giữ điểm,
  `app-prosody` giữ ngữ điệu.

## 4. Tạo skill mới — các bước

1. Kiểm tra đã có skill nào phủ chưa. Nếu chỉ thêm 1 mục nhỏ, sửa skill cũ.
2. Tạo thư mục + `SKILL.md` theo template §3.
3. Thêm ID vào `docs/context-map.json → skills` (đúng thứ tự nhóm).
4. Thêm dòng vào bảng §6 `AGENTS.md` (Skill ID | Dùng khi).
5. Nếu skill mô tả tính năng mới: cập nhật `docs/FEATURES.md`.
6. Chạy:
   ```powershell
   $env:PYTHONIOENCODING='utf-8'
   & "C:\Users\ADMIN\miniforge3\python.exe" tools\context_check.py
   ```
   - Thiếu trong `context-map` → `FAIL: Skill chưa đăng ký`.
   - Quá 500 dòng/thiếu `## `/description rỗng → FAIL.
7. Đọc lại bằng mắt: một model chưa biết repo có làm đúng chỉ với file này không?

## 5. Sửa skill cũ

- Code đổi trước, skill đổi sau **trong cùng phiên**.
- Nếu symbol bị đổi tên: sửa skill + `docs/context-map.json` + mọi `docs/` nhắc tới.
- Nếu hành vi đổi: thêm ghi chú "Trước đây ..." chỉ khi cần tránh tái phạm.
- Không để skill mâu thuẫn `AGENTS.md`; nếu mâu thuẫn, **code là sự thật**, sửa cả hai.

## 6. Chống drift

`tools/context_check.py` kiểm tra:
- mỗi ID trong `context-map.json → skills` có `SKILL.md`;
- không có skill thừa ngoài danh sách;
- frontmatter có `name` + `description`;
- `description` ≤ 1024 ký tự;
- body ≤ 500 dòng và có `## `;
- ID kebab-case.

Nó **không** kiểm tra nội dung đúng/sai. Vì vậy sau khi sửa code, phải tự đối chiếu
skill với code; đừng coi "context_check xanh" là đủ.

## 7. Cạm bẫy

| Triệu chứng | Nguyên nhân |
|---|---|
| Skill không bao giờ được nạp | description không chứa từ người dùng nói |
| `context_check` báo thiếu skill | quên thêm ID vào `skills` |
| `context_check` báo skill thừa | đổi tên thư mục nhưng chưa sửa `context-map.json` |
| Body bị cắt/không nạp | quá 500 dòng, hoặc frontmatter không đóng bằng `---` |
| Hai skill mâu thuẫn | copy nội dung thay vì link skill gốc |
| Skill mô tả hàm không còn | đổi tên symbol mà không chạy `context_check` |
| ID có dấu cách/underscore | vi phạm kebab-case |
| Description có dấu `:` | vẫn được, nhưng phải nằm trên **một dòng** |

## 8. Template ngắn

```markdown
---
name: App X
description: Sửa X trong Hoa Mi — <3-4 việc cụ thể>. Dùng khi người dùng nhắc tới <từ khóa>, <tên file>, hoặc <tên tab>.
---

# X

Một đoạn: X chịu trách nhiệm gì; không chịu trách nhiệm gì.

## Đọc trước

- `docs/ARCHITECTURE.md` §...
- Bất biến I..., quyết định D-...

## Symbol

| Symbol | Hợp đồng |
|---|---|
| ... | ... |

## Luồng / công thức

...

## Khi sửa — checklist

1. ...
2. Thêm case vào `tools/smoke_test.py`.
3. Chạy `py_compile` + `smoke_test.py` + `context_check.py`.

## Cạm bẫy

| Triệu chứng | Nguyên nhân |
|---|---|
| ... | ... |
```
