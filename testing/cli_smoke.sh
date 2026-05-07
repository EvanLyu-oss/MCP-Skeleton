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
ok_context_restore_text_json=false
ok_context_compress_directory_json=false
ok_context_compress_directory_symbols_json=false
ok_context_compress_incremental_json=false
ok_context_inspect_incremental_json=false
ok_context_restore_incremental_json=false
ok_context_bundle_json=false
ok_context_bundle_incremental_json=false
ok_context_apply_check_text_json=false
ok_context_apply_check_incremental_json=false
ok_context_patch_text_json=false
ok_context_patch_incremental_json=false
ok_context_patch_directory_mixed_json=false
ok_context_patch_apply_text_json=false
ok_context_patch_apply_directory_json=false
ok_context_patch_apply_dry_run_report_json=false
ok_context_patch_apply_policy_template_json=false
ok_context_patch_apply_incremental_json=false
ok_context_patch_apply_incremental_dry_run_report_json=false
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
assert 'HEADINGS:' in p['skeleton_text']
assert 'SECTIONS:' in p['skeleton_text']
PY
ok_context_compress_text_writing_outline_json=true

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
PY
ok_context_compress_incremental_json=true

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
assert p['summaries']['incremental_comparison']
assert all(case['restore_verified'] is True for case in p['directory_cases'])
assert all(case['restore_verified'] is True for case in p['directory_incremental_cases'])
PY
ok_context_scale_benchmark_json=true

export CLI_SMOKE_OK_CONTEXT_PRESET_JSON="$ok_context_preset_json"
export CLI_SMOKE_OK_CONTEXT_COMPRESS_TEXT_JSON="$ok_context_compress_text_json"
export CLI_SMOKE_OK_CONTEXT_COMPRESS_TEXT_WRITING_OUTLINE_JSON="$ok_context_compress_text_writing_outline_json"
export CLI_SMOKE_OK_CONTEXT_RESTORE_TEXT_JSON="$ok_context_restore_text_json"
export CLI_SMOKE_OK_CONTEXT_COMPRESS_DIRECTORY_JSON="$ok_context_compress_directory_json"
export CLI_SMOKE_OK_CONTEXT_COMPRESS_DIRECTORY_SYMBOLS_JSON="$ok_context_compress_directory_symbols_json"
export CLI_SMOKE_OK_CONTEXT_COMPRESS_INCREMENTAL_JSON="$ok_context_compress_incremental_json"
export CLI_SMOKE_OK_CONTEXT_INSPECT_INCREMENTAL_JSON="$ok_context_inspect_incremental_json"
export CLI_SMOKE_OK_CONTEXT_RESTORE_INCREMENTAL_JSON="$ok_context_restore_incremental_json"
export CLI_SMOKE_OK_CONTEXT_BUNDLE_JSON="$ok_context_bundle_json"
export CLI_SMOKE_OK_CONTEXT_BUNDLE_INCREMENTAL_JSON="$ok_context_bundle_incremental_json"
export CLI_SMOKE_OK_CONTEXT_APPLY_CHECK_TEXT_JSON="$ok_context_apply_check_text_json"
export CLI_SMOKE_OK_CONTEXT_APPLY_CHECK_INCREMENTAL_JSON="$ok_context_apply_check_incremental_json"
export CLI_SMOKE_OK_CONTEXT_PATCH_TEXT_JSON="$ok_context_patch_text_json"
export CLI_SMOKE_OK_CONTEXT_PATCH_INCREMENTAL_JSON="$ok_context_patch_incremental_json"
export CLI_SMOKE_OK_CONTEXT_PATCH_DIRECTORY_MIXED_JSON="$ok_context_patch_directory_mixed_json"
export CLI_SMOKE_OK_CONTEXT_PATCH_APPLY_TEXT_JSON="$ok_context_patch_apply_text_json"
export CLI_SMOKE_OK_CONTEXT_PATCH_APPLY_DIRECTORY_JSON="$ok_context_patch_apply_directory_json"
export CLI_SMOKE_OK_CONTEXT_PATCH_APPLY_DRY_RUN_REPORT_JSON="$ok_context_patch_apply_dry_run_report_json"
export CLI_SMOKE_OK_CONTEXT_PATCH_APPLY_POLICY_TEMPLATE_JSON="$ok_context_patch_apply_policy_template_json"
export CLI_SMOKE_OK_CONTEXT_PATCH_APPLY_INCREMENTAL_JSON="$ok_context_patch_apply_incremental_json"
export CLI_SMOKE_OK_CONTEXT_PATCH_APPLY_INCREMENTAL_DRY_RUN_REPORT_JSON="$ok_context_patch_apply_incremental_dry_run_report_json"
export CLI_SMOKE_OK_CONTEXT_RESTORE_INVALID_RELPATH_JSON="$ok_context_restore_invalid_relpath_json"
export CLI_SMOKE_OK_CONTEXT_SCALE_BENCHMARK_JSON="$ok_context_scale_benchmark_json"

python3 - "$RESULTS_JSON" <<'PY'
import json, os, sys
checks = {
    'context_preset_json_ok': os.environ['CLI_SMOKE_OK_CONTEXT_PRESET_JSON'] == 'true',
    'context_compress_text_json_ok': os.environ['CLI_SMOKE_OK_CONTEXT_COMPRESS_TEXT_JSON'] == 'true',
    'context_compress_text_writing_outline_json_ok': os.environ['CLI_SMOKE_OK_CONTEXT_COMPRESS_TEXT_WRITING_OUTLINE_JSON'] == 'true',
    'context_restore_text_json_ok': os.environ['CLI_SMOKE_OK_CONTEXT_RESTORE_TEXT_JSON'] == 'true',
    'context_compress_directory_json_ok': os.environ['CLI_SMOKE_OK_CONTEXT_COMPRESS_DIRECTORY_JSON'] == 'true',
    'context_compress_directory_symbols_json_ok': os.environ['CLI_SMOKE_OK_CONTEXT_COMPRESS_DIRECTORY_SYMBOLS_JSON'] == 'true',
    'context_compress_incremental_json_ok': os.environ['CLI_SMOKE_OK_CONTEXT_COMPRESS_INCREMENTAL_JSON'] == 'true',
    'context_inspect_incremental_json_ok': os.environ['CLI_SMOKE_OK_CONTEXT_INSPECT_INCREMENTAL_JSON'] == 'true',
    'context_restore_incremental_json_ok': os.environ['CLI_SMOKE_OK_CONTEXT_RESTORE_INCREMENTAL_JSON'] == 'true',
    'context_bundle_json_ok': os.environ['CLI_SMOKE_OK_CONTEXT_BUNDLE_JSON'] == 'true',
    'context_bundle_incremental_json_ok': os.environ['CLI_SMOKE_OK_CONTEXT_BUNDLE_INCREMENTAL_JSON'] == 'true',
    'context_apply_check_text_json_ok': os.environ['CLI_SMOKE_OK_CONTEXT_APPLY_CHECK_TEXT_JSON'] == 'true',
    'context_apply_check_incremental_json_ok': os.environ['CLI_SMOKE_OK_CONTEXT_APPLY_CHECK_INCREMENTAL_JSON'] == 'true',
    'context_patch_text_json_ok': os.environ['CLI_SMOKE_OK_CONTEXT_PATCH_TEXT_JSON'] == 'true',
    'context_patch_incremental_json_ok': os.environ['CLI_SMOKE_OK_CONTEXT_PATCH_INCREMENTAL_JSON'] == 'true',
    'context_patch_directory_mixed_json_ok': os.environ['CLI_SMOKE_OK_CONTEXT_PATCH_DIRECTORY_MIXED_JSON'] == 'true',
    'context_patch_apply_text_json_ok': os.environ['CLI_SMOKE_OK_CONTEXT_PATCH_APPLY_TEXT_JSON'] == 'true',
    'context_patch_apply_directory_json_ok': os.environ['CLI_SMOKE_OK_CONTEXT_PATCH_APPLY_DIRECTORY_JSON'] == 'true',
    'context_patch_apply_dry_run_report_json_ok': os.environ['CLI_SMOKE_OK_CONTEXT_PATCH_APPLY_DRY_RUN_REPORT_JSON'] == 'true',
    'context_patch_apply_policy_template_json_ok': os.environ['CLI_SMOKE_OK_CONTEXT_PATCH_APPLY_POLICY_TEMPLATE_JSON'] == 'true',
    'context_patch_apply_incremental_json_ok': os.environ['CLI_SMOKE_OK_CONTEXT_PATCH_APPLY_INCREMENTAL_JSON'] == 'true',
    'context_patch_apply_incremental_dry_run_report_json_ok': os.environ['CLI_SMOKE_OK_CONTEXT_PATCH_APPLY_INCREMENTAL_DRY_RUN_REPORT_JSON'] == 'true',
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
