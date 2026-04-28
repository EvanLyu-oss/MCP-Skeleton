from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import zlib
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MANIFEST_VERSION = "mcp_context_bundle.v1"
SKELETON_LANGUAGE = "MCP-SKL.v1"
SKIP_DIR_NAMES = {".git", "__pycache__", ".pytest_cache"}
CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".vue", ".go", ".rs", ".java", ".c", ".cpp", ".h", ".hpp",
    ".css", ".scss", ".html", ".json", ".yaml", ".yml", ".toml", ".sh", ".bash", ".zsh", ".rb", ".php",
    ".swift", ".kt", ".sql", ".mdx",
}
TEXT_EXTENSIONS = {
    ".txt", ".md", ".rst", ".csv", ".tsv", ".json", ".yaml", ".yml", ".toml", ".xml", ".html", ".css",
    ".scss", ".py", ".js", ".ts", ".tsx", ".jsx", ".vue", ".go", ".rs", ".java", ".sql",
}
STOPWORDS = {
    "the", "and", "for", "that", "with", "this", "from", "into", "your", "have", "will", "more", "than",
    "what", "when", "where", "which", "their", "them", "they", "about", "would", "could", "should",
    "write", "make", "build", "using", "into", "onto", "while", "include", "包含", "一个", "我们", "你们",
    "以及", "可以", "这个", "那个", "需要", "进行", "通过", "作为", "用于", "项目", "内容",
}


def build_context_compress_payload(
    *,
    inline_text: str | None,
    text_file: Path | None,
    input_file: Path | None,
    input_dir: Path | None,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    source_count = sum(1 for item in [inline_text.strip() if inline_text else "", text_file, input_file, input_dir] if item)
    if source_count != 1:
        raise ValueError("context compress requires exactly one input source: --text, --text-file, --input-file, or --input-dir")

    if inline_text is not None and inline_text.strip():
        source = _build_inline_text_source(inline_text)
    elif text_file is not None:
        source = _build_text_file_source(text_file)
    elif input_file is not None:
        source = _build_file_source(input_file)
    elif input_dir is not None:
        source = _build_directory_source(input_dir)
    else:
        raise ValueError("context compress did not receive a usable input source")

    skeleton_text = _render_skeleton_text(source)
    restore_blob = _encode_restore_blob(source["restore_blob"])
    payload = {
        "status": "ok",
        "entrypoint": "context-compress",
        "manifest_version": MANIFEST_VERSION,
        "bundle_created_at": _utc_now(),
        "skeleton_language": SKELETON_LANGUAGE,
        "compression_mode": source["compression_mode"],
        "source_kind": source["source_kind"],
        "source_label": source["source_label"],
        "source_path": source.get("source_path", ""),
        "source_summary": source["source_summary"],
        "skeleton_text": skeleton_text,
        "skeleton_char_count": len(skeleton_text),
        "restore_package": restore_blob,
        "compression_ratio": round(len(skeleton_text) / max(1, source["source_summary"].get("total_chars", 1)), 4),
        "next_steps": [
            "feed skeleton_text to the target AI or IDE instead of the original raw context",
            "keep the restore package together with the skeleton so the original source can be reconstructed exactly",
            "run `python3 -m cli context restore --package-file /absolute/path/to/context_manifest.json ...` when you need the original content back",
        ],
    }
    if output_dir is not None:
        package_files = _write_context_package(output_dir, payload)
        payload["output_dir"] = str(output_dir.resolve())
        payload["files"] = {key: str(value) for key, value in package_files.items()}
        payload["next_steps"].insert(0, f"open {package_files['skeleton_file']}")
    return payload


def restore_context_from_package(
    package_payload: dict[str, Any],
    *,
    output_dir: Path | None = None,
    output_file: Path | None = None,
) -> tuple[dict[str, Any], str | None]:
    restore_package = package_payload.get("restore_package") or {}
    decoded = _decode_restore_blob(restore_package)
    mode = str(decoded.get("mode") or "")
    source_label = str(package_payload.get("source_label") or decoded.get("source_label") or "restored-context")
    restore_summary: dict[str, Any] = {
        "status": "ok",
        "entrypoint": "context-restore",
        "manifest_version": package_payload.get("manifest_version", MANIFEST_VERSION),
        "skeleton_language": package_payload.get("skeleton_language", SKELETON_LANGUAGE),
        "compression_mode": package_payload.get("compression_mode", mode),
        "source_kind": package_payload.get("source_kind", decoded.get("source_kind", "text")),
        "source_label": source_label,
        "restored_at": _utc_now(),
        "restore_mode": mode,
        "restored_paths": [],
        "next_steps": [],
    }

    if mode == "text":
        text = str(decoded.get("text") or "")
        if output_file is not None:
            _write_text(output_file, text)
            restore_summary["restored_paths"].append(str(output_file.resolve()))
            restore_summary["next_steps"].append(f"open {output_file.resolve()}")
            return restore_summary, None
        return restore_summary, text

    if mode == "file":
        target_path = _resolve_restore_file_path(
            output_dir=output_dir,
            output_file=output_file,
            suggested_name=str(decoded.get("file_name") or source_label),
        )
        _restore_file_blob(target_path, decoded)
        restore_summary["restored_paths"].append(str(target_path.resolve()))
        restore_summary["next_steps"].append(f"open {target_path.resolve()}")
        return restore_summary, None

    if mode == "directory":
        if output_dir is None:
            raise ValueError("context restore requires --output-dir when restoring a directory package")
        root_name = str(decoded.get("root_name") or source_label or "restored-context")
        restore_root = output_dir.expanduser().resolve() / root_name
        _restore_directory_blob(restore_root, decoded)
        restore_summary["restored_paths"].append(str(restore_root))
        restore_summary["next_steps"].append(f"open {restore_root}")
        return restore_summary, None

    raise ValueError(f"Unsupported restore mode: {mode}")


def load_context_package(package_file: Path) -> dict[str, Any]:
    return json.loads(package_file.read_text(encoding="utf-8"))


def inspect_context_package(package_payload: dict[str, Any]) -> dict[str, Any]:
    restore_package = package_payload.get("restore_package") or {}
    decoded = _decode_restore_blob(restore_package)
    restore_mode = str(decoded.get("mode") or "")
    source_summary = package_payload.get("source_summary") or {}
    tree_preview = list((source_summary.get("tree") or [])[:12])
    inspect_payload = {
        "status": "ok",
        "entrypoint": "context-inspect",
        "manifest_version": package_payload.get("manifest_version", MANIFEST_VERSION),
        "bundle_created_at": package_payload.get("bundle_created_at", ""),
        "skeleton_language": package_payload.get("skeleton_language", SKELETON_LANGUAGE),
        "compression_mode": package_payload.get("compression_mode", restore_mode),
        "source_kind": package_payload.get("source_kind", decoded.get("source_kind", "")),
        "source_label": package_payload.get("source_label", decoded.get("source_label", "")),
        "source_path": package_payload.get("source_path", ""),
        "restore_mode": restore_mode,
        "skeleton_char_count": int(package_payload.get("skeleton_char_count", 0) or 0),
        "restore_encoding": restore_package.get("encoding", ""),
        "restore_raw_byte_count": int(restore_package.get("raw_byte_count", 0) or 0),
        "restore_compressed_byte_count": int(restore_package.get("compressed_byte_count", 0) or 0),
        "compression_ratio": package_payload.get("compression_ratio", 0),
        "source_summary": source_summary,
        "tree_preview": tree_preview,
        "has_restore_package": bool(restore_package),
        "next_steps": [
            "use context_skeleton.mcp or skeleton_text as the AI-facing context surface",
            "keep the manifest and restore blob together if you need exact reconstruction later",
            "run context restore when you want the original text, file, or directory tree back",
        ],
    }
    inspect_payload["summary_text"] = _build_context_inspect_summary_text(inspect_payload)
    return inspect_payload


def _build_inline_text_source(text: str) -> dict[str, Any]:
    normalized = text.rstrip("\n")
    summary = _text_summary(normalized, label="inline-text")
    return {
        "compression_mode": "text",
        "source_kind": summary["source_kind"],
        "source_label": "inline-text",
        "source_summary": summary,
        "restore_blob": {
            "mode": "text",
            "source_label": "inline-text",
            "source_kind": summary["source_kind"],
            "text": normalized,
        },
    }


def _build_text_file_source(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    summary = _text_summary(text, label=path.name)
    return {
        "compression_mode": "text",
        "source_kind": summary["source_kind"],
        "source_label": path.name,
        "source_path": str(path.resolve()),
        "source_summary": summary,
        "restore_blob": {
            "mode": "text",
            "source_label": path.name,
            "source_kind": summary["source_kind"],
            "text": text,
        },
    }


def _build_file_source(path: Path) -> dict[str, Any]:
    path = path.expanduser().resolve()
    data = path.read_bytes()
    is_text = _looks_like_text(path, data)
    if is_text:
        text = data.decode("utf-8")
        source_kind = "code" if _is_code_path(path) else "text"
        summary = _code_summary(text, path.name) if source_kind == "code" else _text_summary(text, label=path.name)
    else:
        source_kind = "binary"
        summary = {
            "source_kind": "binary",
            "label": path.name,
            "bytes": len(data),
            "sha256": _sha256_bytes(data),
            "total_chars": 0,
            "notes": ["binary payload preserved for exact restore", "skeleton only exposes metadata for non-text content"],
        }
    return {
        "compression_mode": "file",
        "source_kind": source_kind,
        "source_label": path.name,
        "source_path": str(path),
        "source_summary": summary,
        "restore_blob": {
            "mode": "file",
            "source_label": path.name,
            "source_kind": source_kind,
            "file_name": path.name,
            "content_b64": base64.b64encode(data).decode("ascii"),
            "sha256": _sha256_bytes(data),
        },
    }


def _build_directory_source(path: Path) -> dict[str, Any]:
    path = path.expanduser().resolve()
    files: list[dict[str, Any]] = []
    symlinks: list[dict[str, Any]] = []
    empty_dirs: list[str] = []
    text_files = 0
    code_files = 0
    binary_files = 0
    total_bytes = 0
    total_chars = 0
    skeleton_entries: list[dict[str, Any]] = []

    for current_root, dirnames, filenames in os.walk(path):
        dirnames[:] = [name for name in dirnames if name not in SKIP_DIR_NAMES]
        current_path = Path(current_root)
        rel_dir = "." if current_path == path else current_path.relative_to(path).as_posix()
        if not filenames and not dirnames and rel_dir != ".":
            empty_dirs.append(rel_dir)
        for filename in sorted(filenames):
            item_path = current_path / filename
            rel_path = item_path.relative_to(path).as_posix()
            if item_path.is_symlink():
                symlinks.append({"relative_path": rel_path, "link_target": os.readlink(item_path)})
                skeleton_entries.append({"relative_path": rel_path, "kind": "symlink", "summary": {"target": os.readlink(item_path)}})
                continue
            data = item_path.read_bytes()
            total_bytes += len(data)
            file_record = {
                "relative_path": rel_path,
                "content_b64": base64.b64encode(data).decode("ascii"),
                "sha256": _sha256_bytes(data),
            }
            files.append(file_record)
            is_text = _looks_like_text(item_path, data)
            if is_text:
                text = data.decode("utf-8")
                total_chars += len(text)
                if _is_code_path(item_path):
                    code_files += 1
                    summary = _code_summary(text, rel_path)
                    kind = "code"
                else:
                    text_files += 1
                    summary = _text_summary(text, label=rel_path)
                    kind = "text"
            else:
                binary_files += 1
                kind = "binary"
                summary = {
                    "source_kind": "binary",
                    "label": rel_path,
                    "bytes": len(data),
                    "sha256": _sha256_bytes(data),
                    "total_chars": 0,
                    "notes": ["binary payload preserved for exact restore"],
                }
            skeleton_entries.append({"relative_path": rel_path, "kind": kind, "summary": summary})

    source_summary = {
        "source_kind": "directory",
        "label": path.name,
        "root_path": str(path),
        "total_files": len(files) + len(symlinks),
        "text_files": text_files,
        "code_files": code_files,
        "binary_files": binary_files,
        "symlink_count": len(symlinks),
        "empty_dir_count": len(empty_dirs),
        "total_bytes": total_bytes,
        "total_chars": total_chars,
        "tree": [entry["relative_path"] for entry in sorted(skeleton_entries, key=lambda item: item["relative_path"])],
        "entries": sorted(skeleton_entries, key=lambda item: item["relative_path"]),
    }
    return {
        "compression_mode": "directory",
        "source_kind": "mixed_project",
        "source_label": path.name,
        "source_path": str(path),
        "source_summary": source_summary,
        "restore_blob": {
            "mode": "directory",
            "source_label": path.name,
            "source_kind": "mixed_project",
            "root_name": path.name,
            "files": files,
            "symlinks": symlinks,
            "empty_dirs": empty_dirs,
        },
    }


def _write_context_package(output_dir: Path, payload: dict[str, Any]) -> dict[str, Path]:
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    files = {
        "manifest_file": output_dir / "context_manifest.json",
        "skeleton_file": output_dir / "context_skeleton.mcp",
        "restore_file": output_dir / "context_restore.json",
        "readme_file": output_dir / "README.txt",
    }
    files["manifest_file"].write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    files["skeleton_file"].write_text(str(payload.get("skeleton_text") or ""), encoding="utf-8")
    files["restore_file"].write_text(json.dumps(payload.get("restore_package") or {}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    files["readme_file"].write_text(_build_context_readme_text(payload, files), encoding="utf-8")
    return files


def _build_context_readme_text(payload: dict[str, Any], files: dict[str, Path]) -> str:
    return "\n".join(
        [
            "AIL Builder Context Compression Bundle",
            "",
            f"manifest_version: {payload.get('manifest_version', MANIFEST_VERSION)}",
            f"bundle_created_at: {payload.get('bundle_created_at', '')}",
            f"compression_mode: {payload.get('compression_mode', '')}",
            f"source_kind: {payload.get('source_kind', '')}",
            f"source_label: {payload.get('source_label', '')}",
            f"skeleton_language: {payload.get('skeleton_language', SKELETON_LANGUAGE)}",
            "",
            "Files:",
            f"- context_manifest.json: full machine-readable compression bundle and restore package",
            f"- context_skeleton.mcp: AI-facing high-density skeleton language output",
            f"- context_restore.json: restore blob only",
            f"- README.txt: this usage note",
            "",
            "Suggested flow:",
            f"1. feed {files['skeleton_file']} to the target AI or IDE instead of the raw long context",
            "2. keep the manifest and restore blob together so exact restoration stays possible",
            "3. run context restore when you need the original text, file, or project tree back",
        ]
    ) + "\n"


def _build_context_inspect_summary_text(payload: dict[str, Any]) -> str:
    lines = [
        f"status: {payload.get('status', '')}",
        f"compression_mode: {payload.get('compression_mode', '')}",
        f"source_kind: {payload.get('source_kind', '')}",
        f"source_label: {payload.get('source_label', '')}",
        f"restore_mode: {payload.get('restore_mode', '')}",
        f"skeleton_language: {payload.get('skeleton_language', '')}",
        f"skeleton_char_count: {payload.get('skeleton_char_count', 0)}",
        f"restore_encoding: {payload.get('restore_encoding', '')}",
        f"restore_raw_byte_count: {payload.get('restore_raw_byte_count', 0)}",
        f"restore_compressed_byte_count: {payload.get('restore_compressed_byte_count', 0)}",
        f"compression_ratio: {payload.get('compression_ratio', 0)}",
    ]
    source_summary = payload.get("source_summary") or {}
    for key in ["total_files", "text_files", "code_files", "binary_files", "total_bytes", "total_chars", "paragraph_count", "lines"]:
        if key in source_summary:
            lines.append(f"{key}: {source_summary.get(key)}")
    tree_preview = payload.get("tree_preview") or []
    if tree_preview:
        lines.append(f"tree_preview_count: {len(tree_preview)}")
        lines.append(f"first_tree_item: {tree_preview[0]}")
    return "\n".join(lines)


def _encode_restore_blob(payload: dict[str, Any]) -> dict[str, Any]:
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    compressed = zlib.compress(raw, level=9)
    return {
        "encoding": "zlib+base64+json",
        "sha256": hashlib.sha256(raw).hexdigest(),
        "raw_byte_count": len(raw),
        "compressed_byte_count": len(compressed),
        "payload": base64.b64encode(compressed).decode("ascii"),
    }


def _decode_restore_blob(payload: dict[str, Any]) -> dict[str, Any]:
    if str(payload.get("encoding") or "") != "zlib+base64+json":
        raise ValueError("Unsupported context restore encoding")
    compressed = base64.b64decode(str(payload.get("payload") or "").encode("ascii"))
    raw = zlib.decompress(compressed)
    decoded = json.loads(raw.decode("utf-8"))
    expected_sha = str(payload.get("sha256") or "")
    actual_sha = hashlib.sha256(raw).hexdigest()
    if expected_sha and expected_sha != actual_sha:
        raise ValueError("Context restore blob checksum mismatch")
    return decoded


def _render_skeleton_text(source: dict[str, Any]) -> str:
    lines = [
        SKELETON_LANGUAGE,
        f"MODE: {source['compression_mode']}",
        f"SOURCE_KIND: {source['source_kind']}",
        f"SOURCE_LABEL: {source['source_label']}",
    ]
    if source.get("source_path"):
        lines.append(f"SOURCE_PATH: {source['source_path']}")
    lines.append("CORE:")
    lines.extend(_render_core_summary_lines(source["source_summary"], indent="  "))
    lines.append("SKELETON:")
    lines.extend(_render_structural_lines(source["source_summary"], indent="  "))
    return "\n".join(lines).rstrip() + "\n"


def _render_core_summary_lines(summary: dict[str, Any], *, indent: str) -> list[str]:
    lines = []
    for key in [
        "label", "root_path", "source_kind", "total_files", "text_files", "code_files", "binary_files", "symlink_count",
        "empty_dir_count", "bytes", "total_bytes", "lines", "paragraph_count", "bullet_count", "heading_count", "total_chars", "sha256",
    ]:
        if key in summary and summary[key] not in (None, "", [], {}):
            lines.append(f"{indent}- {key}: {summary[key]}")
    if summary.get("top_terms"):
        lines.append(f"{indent}- top_terms: {', '.join(summary['top_terms'])}")
    return lines


def _render_structural_lines(summary: dict[str, Any], *, indent: str) -> list[str]:
    source_kind = str(summary.get("source_kind") or "")
    if source_kind == "code":
        lines = []
        if summary.get("imports"):
            lines.append(f"{indent}IMPORTS:")
            lines.extend([f"{indent}  - {item}" for item in summary["imports"]])
        if summary.get("symbols"):
            lines.append(f"{indent}SYMBOLS:")
            lines.extend([f"{indent}  - {item}" for item in summary["symbols"]])
        if summary.get("relationships"):
            lines.append(f"{indent}RELATIONSHIPS:")
            lines.extend([f"{indent}  - {item}" for item in summary["relationships"]])
        return lines or [f"{indent}- no structural code markers were extracted"]
    if source_kind in {"text", "markdown"}:
        lines = []
        if summary.get("headings"):
            lines.append(f"{indent}HEADINGS:")
            lines.extend([f"{indent}  - {item}" for item in summary["headings"]])
        if summary.get("sections"):
            lines.append(f"{indent}SECTIONS:")
            lines.extend([f"{indent}  - {item}" for item in summary["sections"]])
        return lines or [f"{indent}- no section markers were extracted"]
    if source_kind == "directory":
        lines = [f"{indent}TREE:"]
        lines.extend([f"{indent}  - {item}" for item in summary.get("tree", [])])
        entry_blocks = []
        for entry in summary.get("entries", []):
            entry_blocks.append(f"{indent}FILE[{entry['kind']}]: {entry['relative_path']}")
            entry_blocks.extend(_render_core_summary_lines(entry.get("summary") or {}, indent=f"{indent}  "))
            if entry.get("kind") in {"code", "text"}:
                entry_blocks.extend(_render_structural_lines(entry.get("summary") or {}, indent=f"{indent}  "))
        return lines + entry_blocks
    if source_kind == "binary":
        return [f"{indent}- binary payload preserved for exact restore; skeleton intentionally exposes metadata only"]
    return [f"{indent}- no structural renderer available for source_kind={source_kind}"]


def _text_summary(text: str, *, label: str) -> dict[str, Any]:
    paragraphs = [segment.strip() for segment in re.split(r"\n\s*\n", text) if segment.strip()]
    lines = text.splitlines()
    headings = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            headings.append(stripped.lstrip("#").strip())
        elif re.fullmatch(r"[A-Z][A-Z0-9 \-_/]{4,}", stripped):
            headings.append(stripped)
    sections = []
    for idx, paragraph in enumerate(paragraphs[:10], start=1):
        first_sentence = _first_sentence(paragraph)
        sections.append(f"section[{idx}] paragraphs=1 first_sentence={json.dumps(first_sentence, ensure_ascii=False)}")
    source_kind = "markdown" if label.lower().endswith((".md", ".mdx", ".rst")) or any(line.strip().startswith("#") for line in lines) else "text"
    return {
        "source_kind": source_kind,
        "label": label,
        "lines": len(lines),
        "paragraph_count": len(paragraphs),
        "bullet_count": sum(1 for line in lines if line.strip().startswith(("- ", "* ", "+ "))),
        "heading_count": len(headings),
        "headings": headings[:24],
        "sections": sections,
        "top_terms": _top_terms(text),
        "sha256": _sha256_text(text),
        "total_chars": len(text),
    }


def _code_summary(text: str, label: str) -> dict[str, Any]:
    lines = text.splitlines()
    imports = []
    symbols = []
    relationships = []
    for line in lines:
        stripped = line.strip()
        if re.match(r"^(from\s+\S+\s+import\s+.+|import\s+.+|const\s+\w+\s*=\s*require\(|#include\s+.+|use\s+\S+;)", stripped):
            imports.append(stripped)
        if re.match(r"^(export\s+default\s+function\s+\w+|export\s+function\s+\w+|function\s+\w+|async\s+function\s+\w+|class\s+\w+|def\s+\w+|async\s+def\s+\w+|interface\s+\w+|type\s+\w+\s*=|const\s+\w+\s*=\s*\(?[^=]*=>)", stripped):
            symbols.append(stripped)
        if "@PAGE[" in stripped or "router" in stripped.lower() or "route" in stripped.lower() or re.search(r"['\"]/[A-Za-z0-9_\-/{}:]+['\"]", stripped):
            relationships.append(stripped)
        if "<template>" in stripped or "<script" in stripped or "<style" in stripped:
            relationships.append(stripped)
    return {
        "source_kind": "code",
        "label": label,
        "lines": len(lines),
        "imports": imports[:24],
        "symbols": symbols[:40],
        "relationships": relationships[:30],
        "top_terms": _top_terms(text),
        "sha256": _sha256_text(text),
        "total_chars": len(text),
    }


def _looks_like_text(path: Path, data: bytes) -> bool:
    if path.suffix.lower() in TEXT_EXTENSIONS:
        try:
            data.decode("utf-8")
            return True
        except UnicodeDecodeError:
            return False
    if b"\x00" in data[:4096]:
        return False
    try:
        data.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


def _is_code_path(path: Path) -> bool:
    return path.suffix.lower() in CODE_EXTENSIONS


def _top_terms(text: str, *, limit: int = 8) -> list[str]:
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}|[\u4e00-\u9fff]{2,}", text.lower())
    counts = Counter(token for token in tokens if token not in STOPWORDS)
    return [term for term, _count in counts.most_common(limit)]


def _first_sentence(text: str) -> str:
    stripped = re.sub(r"\s+", " ", text.strip())
    if not stripped:
        return ""
    match = re.split(r"(?<=[。！？.!?])\s+", stripped, maxsplit=1)
    return match[0][:160]


def _resolve_restore_file_path(*, output_dir: Path | None, output_file: Path | None, suggested_name: str) -> Path:
    if output_file is not None:
        path = output_file.expanduser()
        return path if path.is_absolute() else (Path.cwd() / path).resolve()
    if output_dir is None:
        raise ValueError("context restore requires --output-file or --output-dir when restoring a file package")
    return output_dir.expanduser().resolve() / suggested_name


def _restore_file_blob(target_path: Path, decoded: dict[str, Any]) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    data = base64.b64decode(str(decoded.get("content_b64") or "").encode("ascii"))
    target_path.write_bytes(data)


def _restore_directory_blob(restore_root: Path, decoded: dict[str, Any]) -> None:
    restore_root.mkdir(parents=True, exist_ok=True)
    for rel_dir in decoded.get("empty_dirs") or []:
        (restore_root / rel_dir).mkdir(parents=True, exist_ok=True)
    for item in decoded.get("files") or []:
        target_path = restore_root / str(item.get("relative_path") or "")
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(base64.b64decode(str(item.get("content_b64") or "").encode("ascii")))
    for item in decoded.get("symlinks") or []:
        target_path = restore_root / str(item.get("relative_path") or "")
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.symlink_to(str(item.get("link_target") or ""))


def _write_text(path: Path, text: str) -> None:
    target = path.expanduser()
    if not target.is_absolute():
        target = (Path.cwd() / target).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
