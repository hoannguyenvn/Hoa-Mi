#!/usr/bin/env python3
"""Kiểm tra "context drift" của dự án Hoa Mi.

Vì sao có file này: người dùng chuyển giữa nhiều AI model. Context phải nằm trong
repo và phải tự phát hiện khi tài liệu/skill nói về symbol/file không còn tồn tại.

Việc kiểm tra (không cần mạng, không cần model, không mở UI):
  1. Các file tài liệu bắt buộc tồn tại và còn mục neo.
  2. Symbol Python được nhắc trong docs/context-map.json vẫn tồn tại (AST).
  3. VERSION trong app.py khớp README.
  4. (nếu có) file bài học JSON hợp lệ + audio mẫu tồn tại.
  5. config.json (nếu có trên máy) chỉ chứa khóa trong DEFAULT_CFG.
  6. requirements.txt có các gói bắt buộc.
  7. Số lượng asset tối thiểu.
  8. Mỗi skill có SKILL.md, frontmatter name/description, ID hợp lệ, body <= 500 dòng.

Dùng:
    python tools/context_check.py
    python tools/context_check.py --snapshot
    python tools/context_check.py --json

Exit code 0 = PASS, 1 = có FAIL.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAP_PATH = ROOT / "docs" / "context-map.json"
SKILLS_DIR = ROOT / ".opencode" / "skills"
SNAPSHOT_PATH = ROOT / "docs" / "CONTEXT-SNAPSHOT.md"


class Report:
    def __init__(self) -> None:
        self.items: list[tuple[str, str]] = []  # (level, message)

    def ok(self, msg: str) -> None:
        self.items.append(("OK", msg))

    def fail(self, msg: str) -> None:
        self.items.append(("FAIL", msg))

    def warn(self, msg: str) -> None:
        self.items.append(("WARN", msg))

    @property
    def failures(self) -> list[str]:
        return [m for lv, m in self.items if lv == "FAIL"]

    @property
    def warnings(self) -> list[str]:
        return [m for lv, m in self.items if lv == "WARN"]

    def print(self) -> None:
        for level, msg in self.items:
            print(f"[{level}] {msg}")
        print()
        print(
            "TỔNG: %d OK · %d WARN · %d FAIL"
            % (
                sum(1 for lv, _ in self.items if lv == "OK"),
                len(self.warnings),
                len(self.failures),
            )
        )


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")


def module_index(tree: ast.Module) -> dict[str, ast.AST]:
    idx: dict[str, ast.AST] = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            idx[node.name] = node
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    idx[target.id] = node
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            idx[node.target.id] = node
    return idx


def has_symbol(tree: ast.Module, dotted: str) -> bool:
    parts = dotted.split(".")
    node = module_index(tree).get(parts[0])
    if node is None:
        return False
    for part in parts[1:]:
        if not isinstance(node, ast.ClassDef):
            return False
        node = next(
            (
                n
                for n in node.body
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                and n.name == part
            ),
            None,
        )
        if node is None:
            return False
    return True


def assignment_value(tree: ast.Module, name: str):
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    try:
                        return ast.literal_eval(node.value)
                    except Exception:
                        return None
    return None


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Trả (metadata, body). Frontmatter đơn giản key: value, không multiline."""
    if not text.startswith("---"):
        return {}, text
    lines = text.splitlines()
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() in ("---", "..."):
            end = i
            break
    if end is None:
        return {}, text
    meta: dict[str, str] = {}
    for line in lines[1:end]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        meta[key.strip()] = value
    return meta, "\n".join(lines[end + 1 :])


def line_count(text: str) -> int:
    return len(text.splitlines())


def check_docs(report: Report, spec: dict, cache: dict[str, str]) -> None:
    for rel in spec.get("docs", []):
        path = ROOT / rel
        if not path.exists():
            report.fail(f"Thiếu tài liệu: {rel}")
            continue
        text = cache.setdefault(rel, read_text(path))
        report.ok(f"Tài liệu tồn tại: {rel} ({line_count(text)} dòng)")

    for rel, needles in (spec.get("docs_required_text") or {}).items():
        if rel not in cache:
            continue
        text = cache[rel]
        missing = [n for n in needles if n not in text]
        if missing:
            report.fail(f"{rel} thiếu mục neo: {missing}")
        else:
            report.ok(f"{rel} còn đủ mục neo")


def check_python(report: Report, spec: dict, cache: dict[str, ast.Module]) -> None:
    for rel, symbols in (spec.get("python") or {}).items():
        path = ROOT / rel
        if not path.exists():
            report.fail(f"Thiếu file Python: {rel}")
            continue
        try:
            tree = ast.parse(read_text(path), filename=rel)
        except SyntaxError as exc:
            report.fail(f"{rel} sai cú pháp: {exc}")
            continue
        cache[rel] = tree
        missing = [s for s in symbols if not has_symbol(tree, s)]
        if missing:
            report.fail(f"{rel} thiếu symbol: {', '.join(missing)}")
        else:
            report.ok(f"{rel}: {len(symbols)} symbol còn tồn tại")


def check_version(report: Report, spec: dict, trees: dict[str, ast.Module]) -> str | None:
    source = (spec.get("project") or {}).get("version_source") or "app.py:VERSION"
    if ":" not in source:
        report.fail(f"version_source không hợp lệ: {source}")
        return None
    rel, attr = source.split(":", 1)
    tree = trees.get(rel)
    if tree is None:
        report.fail(f"Không đọc được {rel} để lấy VERSION")
        return None
    version = assignment_value(tree, attr)
    if not isinstance(version, str) or not version:
        report.fail(f"{rel}:{attr} không phải chuỗi")
        return None
    readme_rel = (spec.get("project") or {}).get("readme")
    if readme_rel:
        readme = ROOT / readme_rel
        if not readme.exists():
            report.warn(f"Thiếu {readme_rel} để đối chiếu version")
        else:
            head = read_text(readme)[:400]
            if f"v{version}" in head:
                report.ok(f"VERSION {version} khớp {readme_rel}")
            else:
                report.fail(f"VERSION {version} không thấy trong đầu {readme_rel}")
    return version


def check_lessons(report: Report, rel: str, cfg: dict) -> int:
    path = ROOT / rel
    try:
        data = json.loads(read_text(path))
    except Exception as exc:
        report.fail(f"{rel} không parse được: {exc}")
        return 0
    lessons = data.get("lessons") if isinstance(data, dict) else None
    if not isinstance(lessons, list):
        report.fail(f"{rel}: thiếu mảng 'lessons'")
        return 0
    minimum = int(cfg.get("min_lessons") or 0)
    if len(lessons) < minimum:
        report.fail(f"{rel}: chỉ có {len(lessons)} bài, cần >= {minimum}")
    else:
        report.ok(f"{rel}: {len(lessons)} bài")

    required = cfg.get("required_fields") or []
    sample_dir = ROOT / (cfg.get("sample_dir") or "mau/en")
    seen: set[str] = set()
    problems: list[str] = []
    for i, lesson in enumerate(lessons):
        if not isinstance(lesson, dict):
            problems.append(f"bài #{i} không phải object")
            continue
        lid = str(lesson.get("id") or "")
        if not lid:
            problems.append(f"bài #{i} thiếu id")
            continue
        if lid in seen:
            problems.append(f"id trùng: {lid}")
        seen.add(lid)
        for field in required:
            # `pairs` được phép rỗng (bài không có cặp tối thiểu), nhưng phải có khóa.
            if field not in lesson or lesson[field] in (None, ""):
                problems.append(f"{lid}: thiếu '{field}'")
        for field in ("words", "tips", "pairs"):
            if field in lesson and not isinstance(lesson[field], list):
                problems.append(f"{lid}: '{field}' phải là list")
        target = str(lesson.get("target") or "").strip()
        if not target:
            problems.append(f"{lid}: target rỗng")
        samples = lesson.get("samples") or {}
        for kind in ("normal", "slow"):
            name = samples.get(kind) if isinstance(samples, dict) else None
            if not name:
                problems.append(f"{lid}: thiếu samples.{kind}")
            elif not (sample_dir / str(name)).exists():
                problems.append(f"{lid}: thiếu audio {sample_dir.name}/{name}")
        for word in (lesson.get("words") or [])[:2]:
            f = sample_dir / f"w_{word}.wav"
            if not f.exists():
                problems.append(f"{lid}: thiếu audio từ khóa {f.name}")

    if problems:
        for p in problems[:12]:
            report.fail(f"{rel}: {p}")
        if len(problems) > 12:
            report.fail(f"{rel}: … và {len(problems) - 12} lỗi nữa")
    else:
        report.ok(f"{rel}: cấu trúc + audio mẫu đầy đủ")
    return len(lessons)


def check_config(report: Report, rel: str, cfg: dict, trees: dict[str, ast.Module]) -> None:
    path = ROOT / rel
    if not path.exists():
        report.ok(f"{rel}: chưa có (tự tạo khi chạy app) — bỏ qua")
        return
    try:
        data = json.loads(read_text(path))
    except Exception as exc:
        report.fail(f"{rel} không parse được: {exc}")
        return
    if not isinstance(data, dict):
        report.fail(f"{rel} phải là object JSON")
        return
    source = str(cfg.get("defaults_symbol") or "")
    if ":" in source:
        mod_rel, attr = source.split(":", 1)
        tree = trees.get(mod_rel)
        defaults = assignment_value(tree, attr) if tree else None
        if isinstance(defaults, dict):
            unknown = sorted(set(data) - set(defaults))
            if unknown:
                report.fail(f"{rel} có khóa lạ ngoài DEFAULT_CFG: {unknown}")
            else:
                report.ok(f"{rel}: {len(data)} khóa đều hợp lệ")
        else:
            report.warn(f"Không đọc được {source} để đối chiếu config")
    else:
        report.ok(f"{rel}: JSON hợp lệ")


def check_requirements(report: Report, rel: str, cfg: dict) -> None:
    path = ROOT / rel
    if not path.exists():
        report.fail(f"Thiếu {rel}")
        return
    names: set[str] = set()
    for line in read_text(path).splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or line.startswith("-"):
            continue
        name = re.split(r"[<>=!~\[\s;]", line, maxsplit=1)[0].strip().lower()
        if name:
            names.add(name)
    missing = [p for p in (cfg.get("required") or []) if p.lower() not in names]
    if missing:
        report.fail(f"{rel} thiếu gói: {', '.join(missing)}")
    else:
        report.ok(f"{rel}: đủ gói bắt buộc")


def check_assets(report: Report, spec: dict) -> None:
    for pattern, minimum in (spec.get("globs") or {}).items():
        files = list(ROOT.glob(pattern))
        if len(files) < int(minimum):
            report.fail(f"{pattern}: có {len(files)} file, cần >= {minimum}")
        else:
            report.ok(f"{pattern}: {len(files)} file")
    for pattern in spec.get("required") or []:
        if not (ROOT / pattern).exists():
            report.fail(f"Thiếu asset bắt buộc: {pattern}")


def check_skills(report: Report, spec: dict, cache: dict[str, str]) -> list[tuple[str, int]]:
    wanted = spec.get("skills") or []
    rules = spec.get("skill_rules") or {}
    id_re = re.compile(rules.get("id_pattern") or r"^[a-z0-9]+(-[a-z0-9]+)*$")
    max_body = int(rules.get("max_body_lines") or 500)
    max_desc = int(rules.get("max_description_chars") or 1024)

    found: dict[str, Path] = {}
    if SKILLS_DIR.exists():
        for path in sorted(SKILLS_DIR.glob("*/SKILL.md")):
            found[path.parent.name] = path

    missing = [s for s in wanted if s not in found]
    extra = sorted(set(found) - set(wanted))
    if missing:
        report.fail(f"Thiếu skill trong .opencode/skills: {', '.join(missing)}")
    if extra:
        report.fail(f"Skill chưa đăng ký trong docs/context-map.json: {', '.join(extra)}")

    rows: list[tuple[str, int]] = []
    for sid, path in found.items():
        text = cache.setdefault(str(path.relative_to(ROOT)), read_text(path))
        meta, body = parse_frontmatter(text)
        lines = line_count(body)
        name = meta.get("name", "").strip()
        desc = meta.get("description", "").strip()
        problems = []
        if not id_re.match(sid):
            problems.append("ID không kebab-case")
        if not name:
            problems.append("thiếu name")
        if not desc:
            problems.append("thiếu description")
        elif len(desc) > max_desc:
            problems.append(f"description {len(desc)} > {max_desc} ký tự")
        if lines > max_body:
            problems.append(f"body {lines} > {max_body} dòng")
        if "## " not in body:
            problems.append("body không có mục '## '")
        if problems:
            report.fail(f"skill {sid}: {'; '.join(problems)}")
        else:
            report.ok(f"skill {sid}: OK ({lines} dòng)")
        rows.append((sid, lines))
    return rows


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def write_snapshot(
    report: Report,
    version: str | None,
    lesson_count: int,
    skill_rows: list[tuple[str, int]],
) -> None:
    targets = [
        "AGENTS.md",
        "README.md",
        "app.py",
        "prosody.py",
        "requirements.txt",
        "docs/context-map.json",
        "docs/PROJECT-STATE.md",
        "docs/HANDOFF.md",
        "docs/DECISIONS.md",
    ]
    lines = [
        "# CONTEXT SNAPSHOT (sinh tự động)",
        "",
        "> File này do `tools/context_check.py --snapshot` sinh ra. **Không sửa tay.**",
        f"> Thời điểm: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"> Phiên bản: {version or '?'}",
        f"> Kết quả: {len(report.failures)} FAIL · {len(report.warnings)} WARN",
        "",
        "## File chính",
        "",
        "| File | Dòng | Byte | SHA256 (12) |",
        "|---|---:|---:|---|",
    ]
    for rel in targets:
        path = ROOT / rel
        if not path.exists():
            lines.append(f"| `{rel}` | — | — | thiếu |")
            continue
        text = read_text(path)
        lines.append(
            f"| `{rel}` | {line_count(text)} | {path.stat().st_size} | `{file_digest(path)}` |"
        )

    lines += [
        "",
        "## Dữ liệu",
        "",
        f"- audio `mau/`: **{len(list((ROOT / 'mau').glob('*.wav')))}** clip",
        f"- skills: **{len(skill_rows)}**",
        "",
        "## Skills",
        "",
        "| ID | Dòng body |",
        "|---|---:|",
    ]
    for sid, n in skill_rows:
        lines.append(f"| `{sid}` | {n} |")

    lines += [
        "",
        "## Việc cần làm ngay",
        "",
        "Xem `docs/PROJECT-STATE.md` mục 1 và mục cuối `docs/HANDOFF.md`.",
        "",
    ]
    SNAPSHOT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Đã ghi {SNAPSHOT_PATH.relative_to(ROOT)}")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Kiểm tra context drift")
    parser.add_argument("--snapshot", action="store_true", help="ghi docs/CONTEXT-SNAPSHOT.md")
    parser.add_argument("--json", action="store_true", help="in kết quả dạng JSON")
    args = parser.parse_args()

    if not MAP_PATH.exists():
        print(f"[FAIL] Thiếu {MAP_PATH}")
        return 1
    try:
        spec = json.loads(read_text(MAP_PATH))
    except Exception as exc:
        print(f"[FAIL] {MAP_PATH} không parse được: {exc}")
        return 1

    report = Report()
    text_cache: dict[str, str] = {}
    trees: dict[str, ast.Module] = {}

    check_docs(report, spec, text_cache)
    check_python(report, spec, trees)
    version = check_version(report, spec, trees)

    lesson_count = 0
    for rel, cfg in (spec.get("data") or {}).items():
        if not isinstance(cfg, dict):
            continue
        kind = cfg.get("type")
        if kind == "lessons":
            lesson_count = check_lessons(report, rel, cfg)
        elif kind == "config":
            check_config(report, rel, cfg, trees)
        elif kind == "requirements":
            check_requirements(report, rel, cfg)
        elif not (ROOT / rel).exists() and cfg.get("optional"):
            report.ok(f"{rel}: chưa có (tự tạo khi chạy app) — bỏ qua")
        else:
            try:
                json.loads(read_text(ROOT / rel))
                report.ok(f"{rel}: JSON hợp lệ")
            except Exception as exc:
                report.fail(f"{rel} không parse được: {exc}")

    check_assets(report, spec.get("assets") or {})
    skill_rows = check_skills(report, spec, text_cache)

    if args.json:
        print(
            json.dumps(
                {
                    "ok": not report.failures,
                    "version": version,
                    "failures": report.failures,
                    "warnings": report.warnings,
                    "items": report.items,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        report.print()

    if args.snapshot:
        write_snapshot(report, version, lesson_count, skill_rows)

    return 0 if not report.failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
