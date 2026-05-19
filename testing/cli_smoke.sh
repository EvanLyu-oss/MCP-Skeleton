#!/usr/bin/env bash
set -euo pipefail

ROOT="${AIL_REPO_ROOT:-$(cd -- "$(dirname -- "$0")/.." && pwd)}"
export AIL_REPO_ROOT="$ROOT"
export PYTHONPATH="$ROOT"
RESULTS_DIR="$ROOT/testing/results"
RESULTS_JSON="$RESULTS_DIR/cli_smoke_results.json"
TMP_ROOT="$(mktemp -d /tmp/mcp_skeleton_smoke.XXXXXX)"
mkdir -p "$RESULTS_DIR"

cleanup() {
  rm -rf "$TMP_ROOT"
}
trap cleanup EXIT

ok_context_preset_json=false
ok_context_compress_text_json=false
ok_context_compress_text_writing_outline_json=false
ok_context_compress_text_density_json=false
ok_context_restore_text_json=false
ok_context_non_utf8_text_fallback_json=false
ok_context_compress_directory_json=false
ok_context_restore_directory_completeness_audit_json=false
ok_context_directory_filter_ignore_json=false
ok_context_preset_strategy_differentiation_json=false
ok_context_compress_directory_symbols_json=false
ok_context_compress_directory_aggregation_json=false
ok_context_compress_incremental_json=false
ok_context_compress_incremental_clean_diagnostics_json=false
ok_context_inspect_incremental_json=false
ok_context_restore_incremental_json=false
ok_context_bundle_json=false
ok_context_bundle_incremental_json=false
ok_context_apply_check_text_json=false
ok_context_apply_check_text_drift_json=false
ok_context_apply_check_directory_drift_json=false
ok_context_apply_check_incremental_json=false
ok_context_patch_text_json=false
ok_context_patch_incremental_json=false
ok_context_patch_directory_mixed_json=false
ok_context_patch_apply_text_json=false
ok_context_patch_apply_merge_conflict_json=false
ok_context_patch_apply_directory_json=false
ok_context_patch_apply_dry_run_report_json=false
ok_context_patch_apply_policy_template_json=false
ok_context_patch_apply_policy_block_json=false
ok_context_patch_apply_incremental_json=false
ok_context_patch_apply_incremental_dry_run_report_json=false
ok_context_invalid_input_dir_json=false
ok_context_restore_invalid_relpath_json=false
ok_context_scale_benchmark_json=false

assert_json() {
  local file="$1"
  local script="$2"
  python3 - "$file" <<'PY' > /dev/null
import json, sys
from pathlib import Path
payload = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
script = sys.stdin.read()
ns = {'payload': payload}
exec(script, ns)
PY
}

# preset
context_preset_json="$TMP_ROOT/context_preset.json"
python3 -m cli context preset --json > "$context_preset_json"
python3 - "$context_preset_json" <<'PY'
import json, sys
p = json.loads(open(sys.argv[1], encoding='utf-8').read())
assert p['status'] == 'ok'
assert p['selected_preset']['preset_id'] == 'generic'
assert p['preset_count'] >= 5
PY
ok_context_preset_json=true

# text compress / restore
text_file="$TMP_ROOT/long_text.md"
cat > "$text_file" <<'TXT'
# MCP Skeleton

This is one long test paragraph about preserving restore fidelity while shrinking the AI-facing context surface.
TXT
context_text_json="$TMP_ROOT/context_text.json"
python3 -m cli context compress --text-file "$text_file" --json > "$context_text_json"
python3 - "$context_text_json" <<'PY'
import json, sys
p = json.loads(open(sys.argv[1], encoding='utf-8').read())
assert p['status'] == 'ok'
assert p['compression_mode'] == 'text'
assert p['source_kind'] in {'markdown', 'text'}
PY
ok_context_compress_text_json=true

context_text_outline_json="$TMP_ROOT/context_text_outline.json"
python3 -m cli context compress --text-file "$text_file" --focus-mode writing-outline --json > "$context_text_outline_json"
python3 - "$context_text_outline_json" <<'PY'
import json, sys
p = json.loads(open(sys.argv[1], encoding='utf-8').read())
assert p['status'] == 'ok'
assert p['focus_mode'] == 'writing-outline'
assert 'FOCUS_MODE: writing-outline' in p['skeleton_text']
assert 'CHAPTER_FOLDS:' in p['skeleton_text']
assert 'HEADINGS:' in p['skeleton_text']
assert 'SECTIONS:' in p['skeleton_text']
PY
ok_context_compress_text_writing_outline_json=true

large_text_file="$TMP_ROOT/large_text.md"
python3 - "$large_text_file" <<'PY'
from pathlib import Path
import sys
parts = []
for idx in range(1, 181):
    parts.append(
        f"# Chapter {idx}\n\n"
        f"This chapter keeps repeating context compression continuity, exact restore, patch replay, and benchmark harness language {idx}.\n\n"
        "## Notes\n\n"
        "The structure should stay visible while the adaptive skeleton gets more selective on large inputs.\n"
    )
Path(sys.argv[1]).write_text("\n".join(parts), encoding="utf-8")
PY
context_text_standard_json="$TMP_ROOT/context_text_standard.json"
context_text_compact_json="$TMP_ROOT/context_text_compact.json"
python3 -m cli context compress --text-file "$large_text_file" --skeleton-density standard --json > "$context_text_standard_json"
python3 -m cli context compress --text-file "$large_text_file" --skeleton-density compact --json > "$context_text_compact_json"
python3 - "$context_text_standard_json" "$context_text_compact_json" <<'PY'
import json, sys
standard = json.loads(open(sys.argv[1], encoding='utf-8').read())
compact = json.loads(open(sys.argv[2], encoding='utf-8').read())
assert standard['status'] == 'ok'
assert compact['status'] == 'ok'
assert standard['skeleton_density'] == 'standard'
assert compact['skeleton_density'] == 'compact'
assert 'SKELETON_DENSITY: standard' in standard['skeleton_text']
assert 'SKELETON_DENSITY: compact' in compact['skeleton_text']
assert compact['source_summary']['chapter_group_count'] >= 6
assert 'CHAPTER_FOLDS:' in compact['skeleton_text']
assert compact['skeleton_char_count'] < standard['skeleton_char_count']
assert '... (+' in compact['skeleton_text']
PY
ok_context_compress_text_density_json=true

text_bundle_dir="$TMP_ROOT/text_bundle"
python3 -m cli context compress --text-file "$text_file" --output-dir "$text_bundle_dir" --json > /dev/null
text_restore_json="$TMP_ROOT/text_restore.json"
text_restore_file="$TMP_ROOT/restored_text.md"
python3 -m cli context restore --package-file "$text_bundle_dir/context_manifest.json" --output-file "$text_restore_file" --json > "$text_restore_json"
python3 - "$text_restore_json" "$text_file" "$text_restore_file" <<'PY'
import hashlib, json, sys
payload = json.loads(open(sys.argv[1], encoding='utf-8').read())
assert payload['status'] == 'ok'
orig = hashlib.sha256(open(sys.argv[2], 'rb').read()).hexdigest()
rest = hashlib.sha256(open(sys.argv[3], 'rb').read()).hexdigest()
assert orig == rest
PY
ok_context_restore_text_json=true

# non-UTF-8 text decode fallback with exact byte restore
non_utf8_root="$TMP_ROOT/non_utf8"
mkdir -p "$non_utf8_root/project/docs"
python3 - "$non_utf8_root/gbk_notes.md" "$non_utf8_root/project/docs/japanese.txt" "$non_utf8_root/project/docs/latin1.txt" <<'PY'
from pathlib import Path
import sys
Path(sys.argv[1]).write_bytes("# 标题\n\n这是 GBK 编码文本，用于测试无损恢复。\n".encode("gb18030"))
Path(sys.argv[2]).write_bytes("第一章\n\nこれは Shift-JIS の文章です。\n".encode("shift_jis"))
Path(sys.argv[3]).write_bytes("Résumé\n\nCafé naïve façade.\n".encode("latin-1"))
PY
non_utf8_text_json="$TMP_ROOT/non_utf8_text.json"
non_utf8_text_bundle="$TMP_ROOT/non_utf8_text_bundle"
non_utf8_text_restore="$TMP_ROOT/non_utf8_restored.md"
python3 -m cli context compress --text-file "$non_utf8_root/gbk_notes.md" --output-dir "$non_utf8_text_bundle" --json > "$non_utf8_text_json"
python3 -m cli context restore --package-file "$non_utf8_text_bundle/context_manifest.json" --output-file "$non_utf8_text_restore" --json > /dev/null
non_utf8_dir_json="$TMP_ROOT/non_utf8_dir.json"
python3 -m cli context compress --input-dir "$non_utf8_root/project" --json > "$non_utf8_dir_json"
python3 - "$non_utf8_text_json" "$non_utf8_root/gbk_notes.md" "$non_utf8_text_restore" "$non_utf8_dir_json" <<'PY'
import hashlib
import json
import sys
from pathlib import Path

text_payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
original = Path(sys.argv[2])
restored = Path(sys.argv[3])
dir_payload = json.loads(Path(sys.argv[4]).read_text(encoding="utf-8"))

assert text_payload["status"] == "ok"
assert text_payload["compression_mode"] == "text"
assert text_payload["source_summary"]["source_encoding"] == "gb18030"
assert text_payload["source_summary"]["heading_count"] == 1
assert "标题" in text_payload["skeleton_text"]
assert hashlib.sha256(original.read_bytes()).hexdigest() == hashlib.sha256(restored.read_bytes()).hexdigest()

entries = {item["relative_path"]: item for item in dir_payload["source_summary"]["entries"]}
assert dir_payload["source_summary"]["binary_files"] == 0
assert dir_payload["source_summary"]["text_files"] == 2
assert entries["docs/japanese.txt"]["kind"] == "text"
assert entries["docs/latin1.txt"]["kind"] == "text"
assert entries["docs/japanese.txt"]["summary"]["source_encoding"] in {"shift_jis", "gb18030"}
assert entries["docs/latin1.txt"]["summary"]["source_encoding"] in {"cp1252", "latin-1"}
PY
ok_context_non_utf8_text_fallback_json=true

# directory bundle baseline
project_dir="$TMP_ROOT/project"
mkdir -p "$project_dir/src" "$project_dir/docs"
cat > "$project_dir/src/app.py" <<'TXT'
from pathlib import Path

def run() -> str:
    return "alpha"
TXT
cat > "$project_dir/src/utils.py" <<'TXT'
def helper() -> int:
    return 3
TXT
cat > "$project_dir/docs/notes.md" <<'TXT'
Initial note.
TXT
cd "$project_dir"
git init -q
git config user.email smoke@example.com
git config user.name smoke
git add .
git commit -qm "initial"
cd "$ROOT"

dir_bundle="$TMP_ROOT/dir_bundle"
context_dir_json="$TMP_ROOT/context_dir.json"
python3 -m cli context compress --preset codebase --input-dir "$project_dir" --output-dir "$dir_bundle" --json > "$context_dir_json"
python3 - "$context_dir_json" <<'PY'
import json, sys
p = json.loads(open(sys.argv[1], encoding='utf-8').read())
assert p['status'] == 'ok'
assert p['compression_mode'] == 'directory'
assert p['source_summary']['total_files'] == 3
PY
ok_context_compress_directory_json=true

# directory restore completeness audit
audit_dir="$TMP_ROOT/restore_audit_project"
mkdir -p \
  "$audit_dir/src/nested/deep" \
  "$audit_dir/assets" \
  "$audit_dir/empty/leaf" \
  "$audit_dir/.git/objects" \
  "$audit_dir/__pycache__" \
  "$audit_dir/.pytest_cache/v"
cat > "$audit_dir/src/main.py" <<'TXT'
def main() -> str:
    return "restore-audit"
TXT
cat > "$audit_dir/src/nested/deep/notes.md" <<'TXT'
# Audit

Directory restore should preserve every included payload.
TXT
python3 - "$audit_dir/assets/blob.bin" <<'PY'
from pathlib import Path
import sys
Path(sys.argv[1]).write_bytes(bytes(range(64)))
PY
cat > "$audit_dir/.git/config" <<'TXT'
[core]
	repositoryformatversion = 0
TXT
cat > "$audit_dir/__pycache__/ignored.pyc" <<'TXT'
ignored bytecode placeholder
TXT
cat > "$audit_dir/.pytest_cache/v/cache" <<'TXT'
ignored pytest cache placeholder
TXT
ln -s "../assets/blob.bin" "$audit_dir/src/blob-link.bin"
audit_bundle="$TMP_ROOT/restore_audit_bundle"
audit_compress_json="$TMP_ROOT/restore_audit_compress.json"
audit_restore_json="$TMP_ROOT/restore_audit_restore.json"
audit_restore_root="$TMP_ROOT/restore_audit_output"
python3 -m cli context compress --input-dir "$audit_dir" --output-dir "$audit_bundle" --json > "$audit_compress_json"
python3 -m cli context restore --package-file "$audit_bundle/context_manifest.json" --output-dir "$audit_restore_root" --json > "$audit_restore_json"
python3 - "$audit_compress_json" "$audit_restore_json" "$audit_dir" "$audit_restore_root/restore_audit_project" <<'PY'
import base64
import hashlib
import json
import os
import sys
import zlib
from pathlib import Path

compress = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
restore = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
original = Path(sys.argv[3])
restored = Path(sys.argv[4])
skip_names = {".git", "__pycache__", ".pytest_cache"}

assert compress["status"] == "ok"
assert restore["status"] == "ok"
summary = compress["source_summary"]
assert set(summary["skip_dir_names"]) == skip_names
assert summary["skipped_dir_count"] == 3
assert summary["skipped_dirs"] == [".git", ".pytest_cache", "__pycache__"]

blob = compress["restore_package"]
decoded = json.loads(zlib.decompress(base64.b64decode(blob["payload"])).decode("utf-8"))
restore_file_paths = sorted(item["relative_path"] for item in decoded["files"])
restore_symlink_paths = sorted(item["relative_path"] for item in decoded["symlinks"])
restore_empty_dirs = sorted(decoded["empty_dirs"])

expected_files = []
expected_symlinks = []
expected_empty_dirs = []
skipped_original_paths = []
for root, dirnames, filenames in os.walk(original):
    root_path = Path(root)
    skipped_here = sorted(name for name in dirnames if name in skip_names)
    for dirname in skipped_here:
        skipped_original_paths.append((root_path / dirname).relative_to(original).as_posix())
    dirnames[:] = [name for name in dirnames if name not in skip_names]
    rel_dir = "." if root_path == original else root_path.relative_to(original).as_posix()
    if not filenames and not dirnames and rel_dir != ".":
        expected_empty_dirs.append(rel_dir)
    for filename in sorted(filenames):
        item = root_path / filename
        rel_path = item.relative_to(original).as_posix()
        if item.is_symlink():
            expected_symlinks.append(rel_path)
        else:
            expected_files.append(rel_path)

assert skipped_original_paths == [".git", ".pytest_cache", "__pycache__"]
assert restore_file_paths == sorted(expected_files)
assert restore_symlink_paths == sorted(expected_symlinks)
assert restore_empty_dirs == sorted(expected_empty_dirs)

restored_files = []
restored_symlinks = []
restored_empty_dirs = []
for root, dirnames, filenames in os.walk(restored, followlinks=False):
    root_path = Path(root)
    rel_dir = "." if root_path == restored else root_path.relative_to(restored).as_posix()
    if not filenames and not dirnames and rel_dir != ".":
        restored_empty_dirs.append(rel_dir)
    for filename in sorted(filenames):
        item = root_path / filename
        rel_path = item.relative_to(restored).as_posix()
        if item.is_symlink():
            restored_symlinks.append(rel_path)
        else:
            restored_files.append(rel_path)

assert sorted(restored_files) == sorted(expected_files)
assert sorted(restored_symlinks) == sorted(expected_symlinks)
assert sorted(restored_empty_dirs) == sorted(expected_empty_dirs)
for rel_path in expected_files:
    assert hashlib.sha256((original / rel_path).read_bytes()).hexdigest() == hashlib.sha256((restored / rel_path).read_bytes()).hexdigest()
for rel_path in expected_symlinks:
    assert os.readlink(original / rel_path) == os.readlink(restored / rel_path)
for skipped_dir in skipped_original_paths:
    assert not (restored / skipped_dir).exists()
    assert all(not path.startswith(f"{skipped_dir}/") and path != skipped_dir for path in restore_file_paths + restore_symlink_paths + restore_empty_dirs)
PY
ok_context_restore_directory_completeness_audit_json=true

# directory filtering with .mcp-skeletonignore and --exclude
filter_dir="$TMP_ROOT/filter_project"
mkdir -p "$filter_dir/src" "$filter_dir/logs" "$filter_dir/node_modules/pkg" "$filter_dir/dist" "$filter_dir/tmp"
cat > "$filter_dir/.mcp-skeletonignore" <<'TXT'
# MCP-Skeleton local ignore
logs/
node_modules/
*.tmp
TXT
cat > "$filter_dir/README.md" <<'TXT'
# Filter Project
TXT
cat > "$filter_dir/src/app.py" <<'TXT'
def keep() -> str:
    return "included"
TXT
cat > "$filter_dir/logs/debug.log" <<'TXT'
ignored log
TXT
cat > "$filter_dir/node_modules/pkg/index.js" <<'TXT'
ignored dependency
TXT
cat > "$filter_dir/dist/app.js" <<'TXT'
ignored build
TXT
cat > "$filter_dir/src/app.py.map" <<'TXT'
ignored map
TXT
cat > "$filter_dir/tmp/cache.tmp" <<'TXT'
ignored tmp
TXT
filter_json="$TMP_ROOT/filter_context.json"
filter_bundle="$TMP_ROOT/filter_bundle"
filter_restore_root="$TMP_ROOT/filter_restore"
python3 -m cli context compress --input-dir "$filter_dir" --exclude "dist/" --exclude "*.map" --output-dir "$filter_bundle" --json > "$filter_json"
python3 -m cli context restore --package-file "$filter_bundle/context_manifest.json" --output-dir "$filter_restore_root" --json > /dev/null
python3 - "$filter_json" "$filter_restore_root/filter_project" <<'PY'
import base64
import json
import sys
import zlib
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
restored = Path(sys.argv[2])
summary = payload["source_summary"]
assert payload["status"] == "ok"
assert summary["filter_patterns"] == ["logs/", "node_modules/", "*.tmp", "dist/", "*.map"]
assert summary["filtered_dir_count"] == 3
assert summary["filtered_file_count"] == 2
assert summary["filtered_path_count"] == 5
for rel in ["logs", "node_modules", "dist", "src/app.py.map", "tmp/cache.tmp"]:
    assert rel in summary["filtered_paths_preview"]
blob = payload["restore_package"]
decoded = json.loads(zlib.decompress(base64.b64decode(blob["payload"])).decode("utf-8"))
paths = sorted(item["relative_path"] for item in decoded["files"]) + sorted(item["relative_path"] for item in decoded["symlinks"])
assert "README.md" in paths
assert "src/app.py" in paths
assert ".mcp-skeletonignore" in paths
assert all(not path.startswith(("logs/", "node_modules/", "dist/")) for path in paths)
assert "src/app.py.map" not in paths
assert "tmp/cache.tmp" not in paths
assert (restored / "src/app.py").exists()
assert not (restored / "logs").exists()
assert not (restored / "node_modules").exists()
assert not (restored / "dist").exists()
assert not (restored / "src/app.py.map").exists()
assert not (restored / "tmp/cache.tmp").exists()
PY
ok_context_directory_filter_ignore_json=true

# preset strategy differentiation on mixed large directories
preset_strategy_dir="$TMP_ROOT/preset_strategy_project"
mkdir -p "$preset_strategy_dir/src" "$preset_strategy_dir/docs"
python3 - "$preset_strategy_dir" <<'PY'
from pathlib import Path
import sys
root = Path(sys.argv[1])
for idx in range(1, 46):
    (root / "src" / f"module_{idx}.py").write_text(
        f"import json\n\n"
        f"def symbol_{idx}() -> str:\n"
        f"    return 'module-{idx}'\n",
        encoding="utf-8",
    )
for idx in range(1, 46):
    (root / "docs" / f"chapter_{idx}.md").write_text(
        f"# Chapter {idx}\n\n"
        f"This chapter keeps narrative continuity for preset strategy testing {idx}.\n\n"
        f"## Scene {idx}\n\n"
        "The writing preset should prefer these prose anchors when the directory is folded.\n",
        encoding="utf-8",
    )
PY
preset_codebase_json="$TMP_ROOT/preset_codebase.json"
preset_writing_json="$TMP_ROOT/preset_writing.json"
python3 -m cli context compress --preset codebase --input-dir "$preset_strategy_dir" --skeleton-density compact --json > "$preset_codebase_json"
python3 -m cli context compress --preset writing --input-dir "$preset_strategy_dir" --skeleton-density compact --json > "$preset_writing_json"
python3 - "$preset_codebase_json" "$preset_writing_json" <<'PY'
import json
import re
import sys
from pathlib import Path

codebase = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
writing = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
assert codebase["status"] == "ok"
assert writing["status"] == "ok"
assert codebase["preset_skeleton_strategy"]
assert writing["preset_skeleton_strategy"]
assert "PRESET_STRATEGY:" in codebase["skeleton_text"]
assert "PRESET_EXCLUDE_HINTS:" in codebase["skeleton_text"]
assert "spend more skeleton budget on imports" in codebase["skeleton_text"]
assert "spend more skeleton budget on chapter folds" in writing["skeleton_text"]
codebase_files = re.findall(r"FILE\[[^\]]+\]: ([^\n]+)", codebase["skeleton_text"])
writing_files = re.findall(r"FILE\[[^\]]+\]: ([^\n]+)", writing["skeleton_text"])
assert codebase_files
assert writing_files
assert codebase_files[0].startswith("src/")
assert writing_files[0].startswith("docs/")
assert "SYMBOLS:" in codebase["skeleton_text"]
assert "CHAPTER_FOLDS:" in writing["skeleton_text"]
PY
ok_context_preset_strategy_differentiation_json=true

context_dir_symbols_json="$TMP_ROOT/context_dir_symbols.json"
python3 -m cli context compress --preset codebase --focus-mode symbols --input-dir "$project_dir" --json > "$context_dir_symbols_json"
python3 - "$context_dir_symbols_json" <<'PY'
import json, sys
p = json.loads(open(sys.argv[1], encoding='utf-8').read())
assert p['status'] == 'ok'
assert p['focus_mode'] == 'symbols'
assert 'FOCUS_MODE: symbols' in p['skeleton_text']
assert 'SYMBOLS:' in p['skeleton_text']
assert 'IMPORTS:' not in p['skeleton_text']
assert 'TREE:' not in p['skeleton_text']
PY
ok_context_compress_directory_symbols_json=true

large_project_dir="$TMP_ROOT/large_project"
mkdir -p \
  "$large_project_dir/src/api" \
  "$large_project_dir/src/core" \
  "$large_project_dir/docs" \
  "$large_project_dir/tests" \
  "$large_project_dir/scripts" \
  "$large_project_dir/examples"
python3 - "$large_project_dir" <<'PY'
from pathlib import Path
import sys
root = Path(sys.argv[1])
for idx in range(1, 51):
    (root / "src" / "api" / f"handler_{idx}.py").write_text(
        "from pathlib import Path\n\n"
        f"def handler_{idx}() -> str:\n"
        f"    return 'api-{idx}'\n",
        encoding="utf-8",
    )
for idx in range(1, 51):
    (root / "src" / "core" / f"service_{idx}.py").write_text(
        "import json\n\n"
        f"def service_{idx}() -> str:\n"
        f"    return 'core-{idx}'\n",
        encoding="utf-8",
    )
for idx in range(1, 21):
    (root / "docs" / f"chapter_{idx}.md").write_text(
        f"# Chapter {idx}\n\nThis chapter describes context compression structure {idx}.\n",
        encoding="utf-8",
    )
for idx in range(1, 21):
    (root / "tests" / f"test_case_{idx}.py").write_text(
        f"def test_case_{idx}() -> None:\n    assert True\n",
        encoding="utf-8",
    )
for idx in range(1, 11):
    (root / "scripts" / f"task_{idx}.sh").write_text(
        "#!/bin/sh\n"
        f"echo task-{idx}\n",
        encoding="utf-8",
    )
for idx in range(1, 11):
    (root / "examples" / f"snippet_{idx}.md").write_text(
        f"# Example {idx}\n\nThis example mirrors compression usage {idx}.\n",
        encoding="utf-8",
    )
PY
context_dir_standard_json="$TMP_ROOT/context_dir_standard.json"
context_dir_adaptive_json="$TMP_ROOT/context_dir_adaptive.json"
python3 -m cli context compress --preset codebase --input-dir "$large_project_dir" --skeleton-density standard --json > "$context_dir_standard_json"
python3 -m cli context compress --preset codebase --input-dir "$large_project_dir" --skeleton-density adaptive --json > "$context_dir_adaptive_json"
python3 - "$context_dir_standard_json" "$context_dir_adaptive_json" <<'PY'
import json, sys
standard = json.loads(open(sys.argv[1], encoding='utf-8').read())
adaptive = json.loads(open(sys.argv[2], encoding='utf-8').read())
assert standard['status'] == 'ok'
assert adaptive['status'] == 'ok'
assert adaptive['source_summary']['directory_groups']
assert adaptive['source_summary']['extension_mix']
assert 'DIRECTORY_GROUPS:' in adaptive['skeleton_text']
assert 'HOT_SUBTREES:' in adaptive['skeleton_text']
assert 'COLLAPSED_SUBTREES:' in adaptive['skeleton_text']
assert 'EXTENSION_MIX:' in adaptive['skeleton_text']
assert 'sample_paths=' in adaptive['skeleton_text']
assert 'roots=' in adaptive['skeleton_text']
assert adaptive['skeleton_char_count'] < standard['skeleton_char_count']
assert '... (+' in adaptive['skeleton_text']
PY
ok_context_compress_directory_aggregation_json=true

# incremental compress / inspect / restore
cat > "$project_dir/src/app.py" <<'TXT'
from pathlib import Path

def run() -> str:
    return "beta"
TXT
cat > "$project_dir/src/new.py" <<'TXT'
def created() -> str:
    return "new"
TXT
rm "$project_dir/docs/notes.md"

incremental_bundle="$TMP_ROOT/incremental_bundle"
context_incremental_json="$TMP_ROOT/context_incremental.json"
python3 -m cli context compress --input-dir "$project_dir" --incremental --output-dir "$incremental_bundle" --json > "$context_incremental_json"
python3 - "$context_incremental_json" <<'PY'
import json, sys
p = json.loads(open(sys.argv[1], encoding='utf-8').read())
assert p['status'] == 'ok'
assert p['incremental_mode'] is True
assert p['incremental_changed_paths'] == ['src/app.py']
assert p['incremental_added_paths'] == ['src/new.py']
assert p['incremental_removed_paths'] == ['docs/notes.md']
assert p['incremental_diagnostics']['effective_changed_count'] == 1
assert p['incremental_diagnostics']['effective_added_count'] == 1
assert p['incremental_diagnostics']['effective_removed_count'] == 1
assert p['incremental_diagnostics']['no_changes_detected'] is False
PY
ok_context_compress_incremental_json=true

clean_incremental_dir="$TMP_ROOT/clean_incremental_project"
mkdir -p "$clean_incremental_dir/src"
cat > "$clean_incremental_dir/src/app.py" <<'TXT'
def clean() -> str:
    return "clean"
TXT
cd "$clean_incremental_dir"
git init -q
git config user.email smoke@example.com
git config user.name smoke
git add .
git commit -qm "clean baseline"
cd "$ROOT"
clean_incremental_json="$TMP_ROOT/clean_incremental.json"
python3 -m cli context compress --input-dir "$clean_incremental_dir" --incremental --json > "$clean_incremental_json"
python3 - "$clean_incremental_json" <<'PY'
import json, sys
p = json.loads(open(sys.argv[1], encoding='utf-8').read())
assert p['status'] == 'ok'
assert p['incremental_mode'] is True
assert p['incremental_path_count'] == 0
assert p['incremental_changed_paths'] == []
assert p['incremental_added_paths'] == []
assert p['incremental_removed_paths'] == []
assert p['incremental_diagnostics']['no_changes_detected'] is True
assert p['incremental_diagnostics']['notes']
assert 'No git changes were detected' in p['incremental_diagnostics']['notes'][0]
PY
ok_context_compress_incremental_clean_diagnostics_json=true

context_incremental_inspect_json="$TMP_ROOT/context_incremental_inspect.json"
python3 -m cli context inspect --package-file "$incremental_bundle/context_manifest.json" --json > "$context_incremental_inspect_json"
python3 - "$context_incremental_inspect_json" <<'PY'
import json, sys
p = json.loads(open(sys.argv[1], encoding='utf-8').read())
assert p['status'] == 'ok'
assert p['incremental_mode'] is True
assert p['incremental_path_count'] == 3
PY
ok_context_inspect_incremental_json=true

incremental_restore_root="$TMP_ROOT/incremental_restore"
context_incremental_restore_json="$TMP_ROOT/context_incremental_restore.json"
python3 -m cli context restore --package-file "$incremental_bundle/context_manifest.json" --output-dir "$incremental_restore_root" --json > "$context_incremental_restore_json"
python3 - "$context_incremental_restore_json" "$incremental_restore_root" <<'PY'
import json, sys
from pathlib import Path
p = json.loads(open(sys.argv[1], encoding='utf-8').read())
root = Path(sys.argv[2]) / 'project'
assert p['status'] == 'ok'
assert (root / 'src/app.py').exists()
assert (root / 'src/new.py').exists()
manifest = json.loads((root / '.ail_incremental_manifest.json').read_text(encoding='utf-8'))
assert manifest['removed_paths'] == ['docs/notes.md']
PY
ok_context_restore_incremental_json=true

# bundle + incremental bundle
context_bundle_json="$TMP_ROOT/context_bundle.json"
python3 -m cli context bundle --input-dir "$project_dir" --output-dir "$TMP_ROOT/context_bundle" --json > "$context_bundle_json"
python3 - "$context_bundle_json" <<'PY'
import json, sys
p = json.loads(open(sys.argv[1], encoding='utf-8').read())
assert p['status'] == 'ok'
assert p['entrypoint'] == 'context-bundle'
assert p['file_count'] >= 7
PY
ok_context_bundle_json=true

context_bundle_incremental_json="$TMP_ROOT/context_bundle_incremental.json"
python3 -m cli context bundle --input-dir "$project_dir" --incremental --output-dir "$TMP_ROOT/context_bundle_incremental" --json > "$context_bundle_incremental_json"
python3 - "$context_bundle_incremental_json" <<'PY'
import json, sys
p = json.loads(open(sys.argv[1], encoding='utf-8').read())
assert p['status'] == 'ok'
assert p['incremental_mode'] is True
assert p['incremental_removed_paths'] == ['docs/notes.md']
PY
ok_context_bundle_incremental_json=true

# apply-check text
apply_check_json="$TMP_ROOT/apply_check.json"
python3 -m cli context apply-check --package-file "$text_bundle_dir/context_manifest.json" --text-file "$text_file" --json > "$apply_check_json"
python3 - "$apply_check_json" <<'PY'
import json, sys
p = json.loads(open(sys.argv[1], encoding='utf-8').read())
assert p['status'] == 'ok'
assert p['apply_check_passed'] is True
PY
ok_context_apply_check_text_json=true

drift_text="$TMP_ROOT/drift_text.md"
cat > "$drift_text" <<'TXT'
Tiny unrelated note.
TXT
apply_check_text_drift_json="$TMP_ROOT/apply_check_text_drift.json"
set +e
python3 -m cli context apply-check --package-file "$text_bundle_dir/context_manifest.json" --text-file "$drift_text" --json > "$apply_check_text_drift_json"
rc=$?
set -e
python3 - "$apply_check_text_drift_json" "$rc" <<'PY'
import json, sys
p = json.loads(open(sys.argv[1], encoding='utf-8').read())
assert int(sys.argv[2]) in {0, 3}
assert p['status'] == 'warning'
assert p['apply_check_passed'] is False
assert p['alignment_band'] == 'drifting'
assert p['drift_findings']
assert p['revision_targets']
PY
ok_context_apply_check_text_drift_json=true

drift_dir="$TMP_ROOT/drift_dir"
mkdir -p "$drift_dir/src" "$drift_dir/docs" "$drift_dir/extras"
cat > "$drift_dir/src/app.py" <<'TXT'
from pathlib import Path

def run() -> str:
    return "drifted"
TXT
ln -s "../src/app.py" "$drift_dir/docs/notes.md"
for idx in 1 2 3 4 5; do
  printf 'extra %s\n' "$idx" > "$drift_dir/extras/extra_$idx.txt"
done
apply_check_directory_drift_json="$TMP_ROOT/apply_check_directory_drift.json"
set +e
python3 -m cli context apply-check --package-file "$dir_bundle/context_manifest.json" --input-dir "$drift_dir" --json > "$apply_check_directory_drift_json"
rc=$?
set -e
python3 - "$apply_check_directory_drift_json" "$rc" <<'PY'
import json, sys
p = json.loads(open(sys.argv[1], encoding='utf-8').read())
assert int(sys.argv[2]) in {0, 3}
assert p['status'] == 'warning'
assert p['apply_check_passed'] is False
assert p['alignment_band'] == 'drifting'
assert any('file tree dropped' in finding.lower() for finding in p['drift_findings'])
assert any('large number of files' in finding.lower() for finding in p['drift_findings'])
assert any('file kinds changed' in finding.lower() for finding in p['drift_findings'])
assert p['revision_targets']
PY
ok_context_apply_check_directory_drift_json=true

# patch text
edited_text="$TMP_ROOT/edited_text.md"
cat > "$edited_text" <<'TXT'
# MCP Skeleton

This is one edited paragraph about preserving restore fidelity while shrinking the AI-facing context surface.
TXT
patch_text_json="$TMP_ROOT/patch_text.json"
python3 -m cli context patch --package-file "$text_bundle_dir/context_manifest.json" --text-file "$edited_text" --output-dir "$TMP_ROOT/patch_text" --json > "$patch_text_json"
python3 - "$patch_text_json" <<'PY'
import json, sys
p = json.loads(open(sys.argv[1], encoding='utf-8').read())
assert p['entrypoint'] == 'context-patch'
assert p['patch_mode'] == 'text_unified_diff'
PY
ok_context_patch_text_json=true

# incremental patch
incremental_candidate="$TMP_ROOT/incremental_candidate"
rm -rf "$incremental_candidate"
cp -R "$incremental_restore_root/project" "$incremental_candidate"
mkdir -p "$incremental_candidate/docs"
cat > "$incremental_candidate/src/app.py" <<'TXT'
from pathlib import Path

def run() -> str:
    return "gamma"
TXT
cat > "$incremental_candidate/docs/notes.md" <<'TXT'
Recovered note.
TXT

apply_check_incremental_json="$TMP_ROOT/apply_check_incremental.json"
python3 -m cli context apply-check --package-file "$incremental_bundle/context_manifest.json" --input-dir "$incremental_candidate" --json > "$apply_check_incremental_json"
python3 - "$apply_check_incremental_json" <<'PY'
import json, sys
p = json.loads(open(sys.argv[1], encoding='utf-8').read())
assert p['status'] == 'ok'
assert p['apply_check_passed'] is True
assert p['incremental_mode'] is True
assert p['incremental_changed_paths'] == ['src/app.py']
assert p['incremental_added_paths'] == ['src/new.py']
assert p['incremental_removed_paths'] == []
assert p['incremental_path_count'] == 2
assert 'incremental_changed_count: 1' in p['summary_text']
assert 'incremental_removed_count: 0' in p['summary_text']
PY
ok_context_apply_check_incremental_json=true

patch_incremental_json="$TMP_ROOT/patch_incremental.json"
python3 -m cli context patch --package-file "$incremental_bundle/context_manifest.json" --input-dir "$incremental_candidate" --output-dir "$TMP_ROOT/patch_incremental" --json > "$patch_incremental_json"
python3 - "$patch_incremental_json" <<'PY'
import json, sys
p = json.loads(open(sys.argv[1], encoding='utf-8').read())
assert p['incremental_mode'] is True
assert p['incremental_changed_paths'] == ['src/app.py']
assert p['incremental_added_paths'] == ['src/new.py']
assert p['incremental_removed_paths'] == []
assert p['added_paths'] == ['docs/notes.md']
PY
ok_context_patch_incremental_json=true

# mixed directory patch + apply
original_dir="$TMP_ROOT/mixed_original"
modified_dir="$TMP_ROOT/mixed_modified"
mkdir -p "$original_dir/subdir1" "$original_dir/subdir2" "$modified_dir/subdir1" "$modified_dir/subdir2"
cat > "$original_dir/file1.txt" <<'TXT'
alpha
TXT
cat > "$original_dir/file2.txt" <<'TXT'
remove me
TXT
cat > "$original_dir/subdir1/file3.txt" <<'TXT'
keep me
TXT
cat > "$original_dir/subdir2/file4.txt" <<'TXT'
steady
TXT
cat > "$modified_dir/file1.txt" <<'TXT'
alpha updated
TXT
cat > "$modified_dir/file5.txt" <<'TXT'
brand new
TXT
cat > "$modified_dir/subdir1/file3.txt" <<'TXT'
keep me edited
TXT
cat > "$modified_dir/subdir2/file4.txt" <<'TXT'
steady
TXT
mixed_bundle="$TMP_ROOT/mixed_bundle"
python3 -m cli context bundle --input-dir "$original_dir" --output-dir "$mixed_bundle" --json > /dev/null
patch_mixed_json="$TMP_ROOT/patch_mixed.json"
set +e
python3 -m cli context patch --package-file "$mixed_bundle/context_manifest.json" --input-dir "$modified_dir" --output-dir "$TMP_ROOT/patch_mixed" --json > "$patch_mixed_json"
rc=$?
set -e
python3 - "$patch_mixed_json" "$rc" <<'PY'
import json, sys
p = json.loads(open(sys.argv[1], encoding='utf-8').read())
rc = int(sys.argv[2])
assert rc in {0, 3}
assert p['change_counts']['added_paths'] == 1
assert p['change_counts']['removed_paths'] == 1
assert p['change_counts']['changed_paths'] >= 2
PY
ok_context_patch_directory_mixed_json=true

patch_apply_text_json="$TMP_ROOT/patch_apply_text.json"
python3 -m cli context patch-apply --patch-file "$TMP_ROOT/patch_text/patch_manifest.json" --output-file "$TMP_ROOT/replayed_text.md" --json > "$patch_apply_text_json"
python3 - "$patch_apply_text_json" "$edited_text" "$TMP_ROOT/replayed_text.md" <<'PY'
import hashlib, json, sys
p = json.loads(open(sys.argv[1], encoding='utf-8').read())
assert p['status'] == 'ok'
assert hashlib.sha256(open(sys.argv[2], 'rb').read()).hexdigest() == hashlib.sha256(open(sys.argv[3], 'rb').read()).hexdigest()
PY
ok_context_patch_apply_text_json=true

merge_conflict_target="$TMP_ROOT/replayed_text_conflict.md"
cat > "$merge_conflict_target" <<'TXT'
Conflicting local edit before replay.
TXT
patch_apply_merge_conflict_json="$TMP_ROOT/patch_apply_merge_conflict.json"
set +e
python3 -m cli context patch-apply --patch-file "$TMP_ROOT/patch_text/patch_manifest.json" --source-package-file "$text_bundle_dir/context_manifest.json" --merge-mode reject-conflicts --output-file "$merge_conflict_target" --json > "$patch_apply_merge_conflict_json"
rc=$?
set -e
python3 - "$patch_apply_merge_conflict_json" "$rc" <<'PY'
import json, sys
p = json.loads(open(sys.argv[1], encoding='utf-8').read())
assert int(sys.argv[2]) in {0, 3}
assert p['status'] == 'warning'
assert p['apply_mode'] == 'merge_conflict_blocked'
assert p['merge_check_passed'] is False
assert p['merge_conflict_count'] >= 1
assert p['merge_conflicts']
PY
ok_context_patch_apply_merge_conflict_json=true

patch_apply_dir_json="$TMP_ROOT/patch_apply_dir.json"
python3 -m cli context patch-apply --patch-file "$TMP_ROOT/patch_mixed/patch_manifest.json" --source-package-file "$mixed_bundle/context_manifest.json" --policy-mode open --merge-mode overwrite --output-dir "$TMP_ROOT/mixed_output" --json > "$patch_apply_dir_json"
python3 - "$patch_apply_dir_json" "$modified_dir" "$TMP_ROOT/mixed_output/mixed_original" <<'PY'
import hashlib, json, os, sys
from pathlib import Path
p = json.loads(open(sys.argv[1], encoding='utf-8').read())
expected = Path(sys.argv[2])
actual = Path(sys.argv[3])
assert p['status'] == 'ok'
for rel in ['file1.txt', 'file5.txt', 'subdir1/file3.txt', 'subdir2/file4.txt']:
    assert hashlib.sha256((expected / rel).read_bytes()).hexdigest() == hashlib.sha256((actual / rel).read_bytes()).hexdigest()
assert not (actual / 'file2.txt').exists()
PY
ok_context_patch_apply_directory_json=true

# dry-run report
patch_apply_dry_json="$TMP_ROOT/patch_apply_dry.json"
python3 -m cli context patch-apply --patch-file "$TMP_ROOT/patch_mixed/patch_manifest.json" --source-package-file "$mixed_bundle/context_manifest.json" --dry-run --write-dry-run-report "$TMP_ROOT/dry_run_report.json" --output-dir "$TMP_ROOT/dry_output" --json > "$patch_apply_dry_json"
python3 - "$patch_apply_dry_json" "$TMP_ROOT/dry_run_report.json" "$TMP_ROOT/dry_output" <<'PY'
import json, sys
from pathlib import Path
p = json.loads(open(sys.argv[1], encoding='utf-8').read())
report = json.loads(open(sys.argv[2], encoding='utf-8').read())
outdir = Path(sys.argv[3])
assert p['dry_run'] is True
assert report['dry_run'] is True
assert report['surface_size'] >= 1
assert report['risk_band'] in {'small', 'medium', 'large'}
assert not outdir.exists()
PY
ok_context_patch_apply_dry_run_report_json=true

# policy template
policy_template_json="$TMP_ROOT/policy_template.json"
python3 -m cli context patch-apply --sample-policy strict --allow-root src --forbid-root src/generated --emit-policy-template --json > "$policy_template_json"
python3 - "$policy_template_json" <<'PY'
import json, sys
p = json.loads(open(sys.argv[1], encoding='utf-8').read())
assert p['policy_mode'] == 'strict'
assert 'src' in p['policy_template']['allow_roots']
assert 'src/generated' in p['policy_template']['forbid_roots']
PY
ok_context_patch_apply_policy_template_json=true

patch_apply_policy_block_json="$TMP_ROOT/patch_apply_policy_block.json"
set +e
python3 -m cli context patch-apply --patch-file "$TMP_ROOT/patch_incremental/patch_manifest.json" --source-package-file "$incremental_bundle/context_manifest.json" --policy-mode strict --output-dir "$TMP_ROOT/incremental_policy_block" --json > "$patch_apply_policy_block_json"
rc=$?
set -e
python3 - "$patch_apply_policy_block_json" "$rc" <<'PY'
import json, sys
p = json.loads(open(sys.argv[1], encoding='utf-8').read())
assert int(sys.argv[2]) in {0, 3}
assert p['status'] == 'warning'
assert p['apply_mode'] == 'policy_blocked'
assert p['policy_passed'] is False
assert p['policy_mode'] == 'strict'
assert p['policy_findings']
assert any('blocks added paths' in finding.lower() for finding in p['policy_findings'])
PY
ok_context_patch_apply_policy_block_json=true

# incremental patch apply
patch_apply_incremental_json="$TMP_ROOT/patch_apply_incremental.json"
python3 -m cli context patch-apply --patch-file "$TMP_ROOT/patch_incremental/patch_manifest.json" --source-package-file "$incremental_bundle/context_manifest.json" --output-dir "$TMP_ROOT/incremental_replay" --json > "$patch_apply_incremental_json"
python3 - "$patch_apply_incremental_json" "$TMP_ROOT/incremental_replay/project" "$incremental_candidate" <<'PY'
import hashlib, json, sys
from pathlib import Path
p = json.loads(open(sys.argv[1], encoding='utf-8').read())
root = Path(sys.argv[2])
candidate = Path(sys.argv[3])
assert p['status'] == 'ok'
assert p['incremental_mode'] is True
assert p['apply_mode'] == 'directory_incremental_restore_plus_overlay'
assert p['incremental_changed_paths'] == ['src/app.py']
assert p['incremental_added_paths'] == ['src/new.py']
assert p['incremental_removed_paths'] == []
assert p['incremental_path_count'] == 2
for rel_path in ['src/app.py', 'src/new.py', 'docs/notes.md']:
    assert hashlib.sha256((root / rel_path).read_bytes()).hexdigest() == hashlib.sha256((candidate / rel_path).read_bytes()).hexdigest()
manifest = json.loads((root / '.ail_incremental_manifest.json').read_text(encoding='utf-8'))
assert manifest['removed_paths'] == []
PY
ok_context_patch_apply_incremental_json=true

patch_apply_incremental_dry_json="$TMP_ROOT/patch_apply_incremental_dry.json"
incremental_dry_report="$TMP_ROOT/incremental_dry_run_report.json"
python3 -m cli context patch-apply --patch-file "$TMP_ROOT/patch_incremental/patch_manifest.json" --source-package-file "$incremental_bundle/context_manifest.json" --dry-run --write-dry-run-report "$incremental_dry_report" --output-dir "$TMP_ROOT/incremental_dry_output" --json > "$patch_apply_incremental_dry_json"
python3 - "$patch_apply_incremental_dry_json" "$incremental_dry_report" "$TMP_ROOT/incremental_dry_output" <<'PY'
import json, sys
from pathlib import Path
p = json.loads(open(sys.argv[1], encoding='utf-8').read())
report = json.loads(open(sys.argv[2], encoding='utf-8').read())
outdir = Path(sys.argv[3])
assert p['dry_run'] is True
assert p['incremental_mode'] is True
assert 'first_incremental_changed_path: src/app.py' in p['summary_text']
assert report['dry_run'] is True
assert report['incremental_mode'] is True
assert report['incremental_scope'] == 'working_tree'
assert report['incremental_change_counts']['changed_paths'] == 1
assert report['incremental_change_counts']['added_paths'] == 1
assert report['incremental_change_counts']['removed_paths'] == 0
assert report['first_incremental_changed_path'] == 'src/app.py'
assert report['first_incremental_added_path'] == 'src/new.py'
assert report['first_incremental_removed_path'] == ''
assert not outdir.exists()
PY
ok_context_patch_apply_incremental_dry_run_report_json=true

# invalid input directory blocked
invalid_input_dir_json="$TMP_ROOT/invalid_input_dir.json"
set +e
python3 -m cli context compress --input-dir "$TMP_ROOT/does-not-exist" --json > "$invalid_input_dir_json"
rc=$?
set -e
python3 - "$invalid_input_dir_json" "$rc" <<'PY'
import json, sys
p = json.loads(open(sys.argv[1], encoding='utf-8').read())
assert int(sys.argv[2]) == 2
assert p['status'] == 'error'
assert p['error']['code'] == 'invalid_usage'
assert 'does not exist' in p['error']['message']
PY
ok_context_invalid_input_dir_json=true

# invalid relpath restore blocked
invalid_manifest="$TMP_ROOT/invalid_manifest.json"
python3 - "$dir_bundle/context_manifest.json" "$invalid_manifest" <<'PY'
import json, sys
payload = json.loads(open(sys.argv[1], encoding='utf-8').read())
blob = payload['restore_package']
import base64, zlib
raw = json.loads(zlib.decompress(base64.b64decode(blob['payload'])).decode('utf-8'))
raw['files'][0]['relative_path'] = '../escape.txt'
blob['payload'] = base64.b64encode(zlib.compress(json.dumps(raw, ensure_ascii=False).encode('utf-8'))).decode('ascii')
payload['restore_package'] = blob
open(sys.argv[2], 'w', encoding='utf-8').write(json.dumps(payload, ensure_ascii=False, indent=2))
PY
invalid_restore_json="$TMP_ROOT/invalid_restore.json"
set +e
python3 -m cli context restore --package-file "$invalid_manifest" --output-dir "$TMP_ROOT/invalid_restore" --json > "$invalid_restore_json"
rc=$?
set -e
python3 - "$invalid_restore_json" "$rc" <<'PY'
import json, sys
p = json.loads(open(sys.argv[1], encoding='utf-8').read())
assert int(sys.argv[2]) == 2
assert p['status'] == 'error'
assert p['error']['code'] == 'invalid_usage'
PY
ok_context_restore_invalid_relpath_json=true

# benchmark harness
benchmark_json="$TMP_ROOT/benchmark.json"
benchmark_md="$TMP_ROOT/benchmark.md"
python3 "$ROOT/testing/context_scale_benchmark.py" --quick --output-json "$benchmark_json" --output-md "$benchmark_md" > /dev/null
python3 - "$benchmark_json" "$benchmark_md" <<'PY'
import json, sys
from pathlib import Path
p = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
assert Path(sys.argv[2]).exists()
assert p['status'] == 'ok'
assert p['directory_cases']
assert p['directory_incremental_cases']
assert p['realistic_directory_cases']
assert p['realistic_text_cases']
assert p['summaries']['incremental_comparison']
assert p['summaries']['directory_focus_comparison']
assert p['summaries']['text_focus_comparison']
assert p['summaries']['realistic_directory_full_cases']
assert p['summaries']['realistic_text_full_cases']
assert any(item['focus_mode'] == 'symbols' for item in p['summaries']['directory_focus_cases'])
assert any(item['focus_mode'] == 'writing-outline' for item in p['summaries']['text_focus_cases'])
assert all(case['restore_verified'] is True for case in p['directory_cases'])
assert all(case['restore_verified'] is True for case in p['realistic_directory_cases'])
assert all(case['restore_verified'] is True for case in p['realistic_text_cases'])
assert all(case['restore_verified'] is True for case in p['directory_incremental_cases'])
PY
ok_context_scale_benchmark_json=true

export CLI_SMOKE_OK_CONTEXT_PRESET_JSON="$ok_context_preset_json"
export CLI_SMOKE_OK_CONTEXT_COMPRESS_TEXT_JSON="$ok_context_compress_text_json"
export CLI_SMOKE_OK_CONTEXT_COMPRESS_TEXT_WRITING_OUTLINE_JSON="$ok_context_compress_text_writing_outline_json"
export CLI_SMOKE_OK_CONTEXT_COMPRESS_TEXT_DENSITY_JSON="$ok_context_compress_text_density_json"
export CLI_SMOKE_OK_CONTEXT_RESTORE_TEXT_JSON="$ok_context_restore_text_json"
export CLI_SMOKE_OK_CONTEXT_NON_UTF8_TEXT_FALLBACK_JSON="$ok_context_non_utf8_text_fallback_json"
export CLI_SMOKE_OK_CONTEXT_COMPRESS_DIRECTORY_JSON="$ok_context_compress_directory_json"
export CLI_SMOKE_OK_CONTEXT_RESTORE_DIRECTORY_COMPLETENESS_AUDIT_JSON="$ok_context_restore_directory_completeness_audit_json"
export CLI_SMOKE_OK_CONTEXT_DIRECTORY_FILTER_IGNORE_JSON="$ok_context_directory_filter_ignore_json"
export CLI_SMOKE_OK_CONTEXT_PRESET_STRATEGY_DIFFERENTIATION_JSON="$ok_context_preset_strategy_differentiation_json"
export CLI_SMOKE_OK_CONTEXT_COMPRESS_DIRECTORY_SYMBOLS_JSON="$ok_context_compress_directory_symbols_json"
export CLI_SMOKE_OK_CONTEXT_COMPRESS_DIRECTORY_AGGREGATION_JSON="$ok_context_compress_directory_aggregation_json"
export CLI_SMOKE_OK_CONTEXT_COMPRESS_INCREMENTAL_JSON="$ok_context_compress_incremental_json"
export CLI_SMOKE_OK_CONTEXT_COMPRESS_INCREMENTAL_CLEAN_DIAGNOSTICS_JSON="$ok_context_compress_incremental_clean_diagnostics_json"
export CLI_SMOKE_OK_CONTEXT_INSPECT_INCREMENTAL_JSON="$ok_context_inspect_incremental_json"
export CLI_SMOKE_OK_CONTEXT_RESTORE_INCREMENTAL_JSON="$ok_context_restore_incremental_json"
export CLI_SMOKE_OK_CONTEXT_BUNDLE_JSON="$ok_context_bundle_json"
export CLI_SMOKE_OK_CONTEXT_BUNDLE_INCREMENTAL_JSON="$ok_context_bundle_incremental_json"
export CLI_SMOKE_OK_CONTEXT_APPLY_CHECK_TEXT_JSON="$ok_context_apply_check_text_json"
export CLI_SMOKE_OK_CONTEXT_APPLY_CHECK_TEXT_DRIFT_JSON="$ok_context_apply_check_text_drift_json"
export CLI_SMOKE_OK_CONTEXT_APPLY_CHECK_DIRECTORY_DRIFT_JSON="$ok_context_apply_check_directory_drift_json"
export CLI_SMOKE_OK_CONTEXT_APPLY_CHECK_INCREMENTAL_JSON="$ok_context_apply_check_incremental_json"
export CLI_SMOKE_OK_CONTEXT_PATCH_TEXT_JSON="$ok_context_patch_text_json"
export CLI_SMOKE_OK_CONTEXT_PATCH_INCREMENTAL_JSON="$ok_context_patch_incremental_json"
export CLI_SMOKE_OK_CONTEXT_PATCH_DIRECTORY_MIXED_JSON="$ok_context_patch_directory_mixed_json"
export CLI_SMOKE_OK_CONTEXT_PATCH_APPLY_TEXT_JSON="$ok_context_patch_apply_text_json"
export CLI_SMOKE_OK_CONTEXT_PATCH_APPLY_MERGE_CONFLICT_JSON="$ok_context_patch_apply_merge_conflict_json"
export CLI_SMOKE_OK_CONTEXT_PATCH_APPLY_DIRECTORY_JSON="$ok_context_patch_apply_directory_json"
export CLI_SMOKE_OK_CONTEXT_PATCH_APPLY_DRY_RUN_REPORT_JSON="$ok_context_patch_apply_dry_run_report_json"
export CLI_SMOKE_OK_CONTEXT_PATCH_APPLY_POLICY_TEMPLATE_JSON="$ok_context_patch_apply_policy_template_json"
export CLI_SMOKE_OK_CONTEXT_PATCH_APPLY_POLICY_BLOCK_JSON="$ok_context_patch_apply_policy_block_json"
export CLI_SMOKE_OK_CONTEXT_PATCH_APPLY_INCREMENTAL_JSON="$ok_context_patch_apply_incremental_json"
export CLI_SMOKE_OK_CONTEXT_PATCH_APPLY_INCREMENTAL_DRY_RUN_REPORT_JSON="$ok_context_patch_apply_incremental_dry_run_report_json"
export CLI_SMOKE_OK_CONTEXT_INVALID_INPUT_DIR_JSON="$ok_context_invalid_input_dir_json"
export CLI_SMOKE_OK_CONTEXT_RESTORE_INVALID_RELPATH_JSON="$ok_context_restore_invalid_relpath_json"
export CLI_SMOKE_OK_CONTEXT_SCALE_BENCHMARK_JSON="$ok_context_scale_benchmark_json"

python3 - "$RESULTS_JSON" <<'PY'
import json, os, sys
checks = {
    'context_preset_json_ok': os.environ['CLI_SMOKE_OK_CONTEXT_PRESET_JSON'] == 'true',
    'context_compress_text_json_ok': os.environ['CLI_SMOKE_OK_CONTEXT_COMPRESS_TEXT_JSON'] == 'true',
    'context_compress_text_writing_outline_json_ok': os.environ['CLI_SMOKE_OK_CONTEXT_COMPRESS_TEXT_WRITING_OUTLINE_JSON'] == 'true',
    'context_compress_text_density_json_ok': os.environ['CLI_SMOKE_OK_CONTEXT_COMPRESS_TEXT_DENSITY_JSON'] == 'true',
    'context_restore_text_json_ok': os.environ['CLI_SMOKE_OK_CONTEXT_RESTORE_TEXT_JSON'] == 'true',
    'context_non_utf8_text_fallback_json_ok': os.environ['CLI_SMOKE_OK_CONTEXT_NON_UTF8_TEXT_FALLBACK_JSON'] == 'true',
    'context_compress_directory_json_ok': os.environ['CLI_SMOKE_OK_CONTEXT_COMPRESS_DIRECTORY_JSON'] == 'true',
    'context_restore_directory_completeness_audit_json_ok': os.environ['CLI_SMOKE_OK_CONTEXT_RESTORE_DIRECTORY_COMPLETENESS_AUDIT_JSON'] == 'true',
    'context_directory_filter_ignore_json_ok': os.environ['CLI_SMOKE_OK_CONTEXT_DIRECTORY_FILTER_IGNORE_JSON'] == 'true',
    'context_preset_strategy_differentiation_json_ok': os.environ['CLI_SMOKE_OK_CONTEXT_PRESET_STRATEGY_DIFFERENTIATION_JSON'] == 'true',
    'context_compress_directory_symbols_json_ok': os.environ['CLI_SMOKE_OK_CONTEXT_COMPRESS_DIRECTORY_SYMBOLS_JSON'] == 'true',
    'context_compress_directory_aggregation_json_ok': os.environ['CLI_SMOKE_OK_CONTEXT_COMPRESS_DIRECTORY_AGGREGATION_JSON'] == 'true',
    'context_compress_incremental_json_ok': os.environ['CLI_SMOKE_OK_CONTEXT_COMPRESS_INCREMENTAL_JSON'] == 'true',
    'context_compress_incremental_clean_diagnostics_json_ok': os.environ['CLI_SMOKE_OK_CONTEXT_COMPRESS_INCREMENTAL_CLEAN_DIAGNOSTICS_JSON'] == 'true',
    'context_inspect_incremental_json_ok': os.environ['CLI_SMOKE_OK_CONTEXT_INSPECT_INCREMENTAL_JSON'] == 'true',
    'context_restore_incremental_json_ok': os.environ['CLI_SMOKE_OK_CONTEXT_RESTORE_INCREMENTAL_JSON'] == 'true',
    'context_bundle_json_ok': os.environ['CLI_SMOKE_OK_CONTEXT_BUNDLE_JSON'] == 'true',
    'context_bundle_incremental_json_ok': os.environ['CLI_SMOKE_OK_CONTEXT_BUNDLE_INCREMENTAL_JSON'] == 'true',
    'context_apply_check_text_json_ok': os.environ['CLI_SMOKE_OK_CONTEXT_APPLY_CHECK_TEXT_JSON'] == 'true',
    'context_apply_check_text_drift_json_ok': os.environ['CLI_SMOKE_OK_CONTEXT_APPLY_CHECK_TEXT_DRIFT_JSON'] == 'true',
    'context_apply_check_directory_drift_json_ok': os.environ['CLI_SMOKE_OK_CONTEXT_APPLY_CHECK_DIRECTORY_DRIFT_JSON'] == 'true',
    'context_apply_check_incremental_json_ok': os.environ['CLI_SMOKE_OK_CONTEXT_APPLY_CHECK_INCREMENTAL_JSON'] == 'true',
    'context_patch_text_json_ok': os.environ['CLI_SMOKE_OK_CONTEXT_PATCH_TEXT_JSON'] == 'true',
    'context_patch_incremental_json_ok': os.environ['CLI_SMOKE_OK_CONTEXT_PATCH_INCREMENTAL_JSON'] == 'true',
    'context_patch_directory_mixed_json_ok': os.environ['CLI_SMOKE_OK_CONTEXT_PATCH_DIRECTORY_MIXED_JSON'] == 'true',
    'context_patch_apply_text_json_ok': os.environ['CLI_SMOKE_OK_CONTEXT_PATCH_APPLY_TEXT_JSON'] == 'true',
    'context_patch_apply_merge_conflict_json_ok': os.environ['CLI_SMOKE_OK_CONTEXT_PATCH_APPLY_MERGE_CONFLICT_JSON'] == 'true',
    'context_patch_apply_directory_json_ok': os.environ['CLI_SMOKE_OK_CONTEXT_PATCH_APPLY_DIRECTORY_JSON'] == 'true',
    'context_patch_apply_dry_run_report_json_ok': os.environ['CLI_SMOKE_OK_CONTEXT_PATCH_APPLY_DRY_RUN_REPORT_JSON'] == 'true',
    'context_patch_apply_policy_template_json_ok': os.environ['CLI_SMOKE_OK_CONTEXT_PATCH_APPLY_POLICY_TEMPLATE_JSON'] == 'true',
    'context_patch_apply_policy_block_json_ok': os.environ['CLI_SMOKE_OK_CONTEXT_PATCH_APPLY_POLICY_BLOCK_JSON'] == 'true',
    'context_patch_apply_incremental_json_ok': os.environ['CLI_SMOKE_OK_CONTEXT_PATCH_APPLY_INCREMENTAL_JSON'] == 'true',
    'context_patch_apply_incremental_dry_run_report_json_ok': os.environ['CLI_SMOKE_OK_CONTEXT_PATCH_APPLY_INCREMENTAL_DRY_RUN_REPORT_JSON'] == 'true',
    'context_invalid_input_dir_json_ok': os.environ['CLI_SMOKE_OK_CONTEXT_INVALID_INPUT_DIR_JSON'] == 'true',
    'context_restore_invalid_relpath_json_ok': os.environ['CLI_SMOKE_OK_CONTEXT_RESTORE_INVALID_RELPATH_JSON'] == 'true',
    'context_scale_benchmark_json_ok': os.environ['CLI_SMOKE_OK_CONTEXT_SCALE_BENCHMARK_JSON'] == 'true',
}
status = 'ok' if all(checks.values()) else 'error'
exit_code = 0 if status == 'ok' else 1
payload = {
    'status': status,
    'exit_code': exit_code,
    'check_count': len(checks),
    'passed': sum(1 for value in checks.values() if value),
    'failed': sum(1 for value in checks.values() if not value),
    'checks': checks,
}
with open(sys.argv[1], 'w', encoding='utf-8') as handle:
    json.dump(payload, handle, indent=2, ensure_ascii=False)
    handle.write('\n')
print(json.dumps(payload, indent=2, ensure_ascii=False))
raise SystemExit(exit_code)
PY
