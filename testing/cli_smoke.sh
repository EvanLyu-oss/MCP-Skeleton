#!/usr/bin/env bash
set -euo pipefail

ROOT="${AIL_REPO_ROOT:-$(cd -- "$(dirname -- "$0")/.." && pwd)}"
export AIL_REPO_ROOT="$ROOT"
RESULTS_DIR="$ROOT/testing/results"
RESULTS_JSON="$RESULTS_DIR/cli_smoke_results.json"
TMP_ROOT="$(mktemp -d /tmp/ail_cli_smoke_gate.XXXXXX)"
export PYTHONPATH="$ROOT"
mkdir -p "$RESULTS_DIR"

ok_compile_json=false
ok_single_page_landing_nav_json=false
ok_after_sales_flow_json=false
ok_ecom_home_surface_json=false
ok_website_check_json=false
ok_website_check_out_of_scope_json=false
ok_website_check_experimental_dynamic_json=false
ok_writing_packs_json=false
ok_writing_check_copy_json=false
ok_writing_check_story_json=false
ok_writing_check_book_json=false
ok_writing_scaffold_copy_json=false
ok_writing_scaffold_story_json=false
ok_writing_scaffold_book_json=false
ok_writing_brief_json=false
ok_writing_brief_emit_prompt_txt=false
ok_writing_expand_copy_json=false
ok_writing_expand_story_json=false
ok_writing_expand_book_json=false
ok_writing_expand_emit_text_txt=false
ok_writing_intent_write_json=false
ok_writing_intent_read_json=false
ok_website_assets_json=false
ok_website_assets_experimental_dynamic_json=false
ok_website_assets_pack_json=false
ok_website_open_asset_json=false
ok_website_open_asset_pack_json=false
ok_website_inspect_asset_json=false
ok_website_inspect_asset_pack_json=false
ok_website_preview_json=false
ok_website_preview_pack_json=false
ok_website_run_inspect_command_json=false
ok_website_run_inspect_command_pack_json=false
ok_website_export_handoff_json=false
ok_website_export_handoff_pack_json=false
ok_website_summary_json=false
ok_website_go_json=false
ok_sync_json=false
ok_compile_error_json=false
ok_sync_conflict_json=false
ok_diagnose_json=false
ok_repair_json=false
ok_post_repair_diagnose_json=false
ok_project_check_json=false
ok_project_check_conflict_json=false
ok_project_doctor_json=false
ok_project_doctor_validation_json=false
ok_project_doctor_apply_safe_noop_json=false
ok_project_doctor_apply_safe_repair_json=false
ok_project_doctor_apply_safe_continue_noop_json=false
ok_project_doctor_apply_safe_continue_repair_json=false
ok_project_continue_auto_repair_json=false
ok_project_continue_auto_no_repair_json=false
ok_project_summary_json=false
ok_project_hooks_json=false
ok_project_hooks_home_json=false
ok_project_hook_init_json=false
ok_project_hook_guide_repo_json=false
ok_project_hook_guide_emit_shell_repo=false
ok_project_hook_guide_copy_command_repo=false
ok_project_hook_guide_run_command_repo=false
ok_project_hook_guide_run_command_yes_repo=false
ok_project_hook_init_text_compact_repo=false
ok_project_hook_init_explain_repo=false
ok_project_hook_init_emit_shell_repo=false
ok_project_hook_init_copy_command_repo=false
ok_project_hook_init_emit_confirm_shell_repo=false
ok_project_hook_init_copy_confirm_command_repo=false
ok_project_hook_init_emit_target_path_repo=false
ok_project_hook_init_copy_target_path_repo=false
ok_project_hook_init_emit_target_dir_repo=false
ok_project_hook_init_copy_target_dir_repo=false
ok_project_hook_init_emit_target_project_root_repo=false
ok_project_hook_init_copy_target_project_root_repo=false
ok_project_hook_init_emit_target_project_name_repo=false
ok_project_hook_init_copy_target_project_name_repo=false
ok_project_hook_init_emit_target_relative_path_repo=false
ok_project_hook_init_copy_target_relative_path_repo=false
ok_project_hook_init_emit_target_bundle_repo=false
ok_project_hook_init_copy_target_bundle_repo=false
ok_project_hook_init_emit_open_shell_repo=false
ok_project_hook_init_copy_open_command_repo=false
ok_project_hook_init_run_command_repo=false
ok_project_hook_init_run_command_yes_repo=false
ok_project_hook_init_run_open_command_repo=false
ok_project_hook_init_run_open_command_yes_repo=false
ok_project_hook_init_inspect_target_repo=false
ok_project_hook_init_inspect_target_text_compact_repo=false
ok_project_hook_init_open_target_repo=false
ok_project_hook_init_open_now_repo=false
ok_project_hook_init_open_now_text_compact_repo=false
ok_project_hook_init_force_json=false
ok_project_hook_init_suggest_json=false
ok_project_hook_init_open_catalog_json=false
ok_project_hook_init_suggest_filtered_json=false
ok_project_hook_init_suggest_slot_filtered_json=false
ok_project_hook_init_suggest_slot_only_json=false
ok_project_hook_init_pick_json=false
ok_project_hook_init_pick_index_json=false
ok_project_hook_init_pick_recommended_json=false
ok_project_hook_init_recent_memory_pick_json=false
ok_project_hook_init_reuse_last_suggest_json=false
ok_project_hook_init_last_suggest_json=false
ok_project_summary_conflict_json=false
ok_project_preview_json=false
ok_project_serve_dry_run_json=false
ok_project_preview_conflict_json=false
ok_project_open_target_json=false
ok_project_open_target_default_json=false
ok_project_inspect_target_json=false
ok_project_inspect_target_default_json=false
ok_project_run_inspect_command_json=false
ok_project_run_inspect_command_default_json=false
ok_project_export_handoff_json=false
ok_project_export_handoff_conflict_json=false
ok_project_go_json=false
ok_project_go_repair_json=false
ok_project_go_conflict_json=false
ok_workspace_status_repo_json=false
ok_workspace_status_project_json=false
ok_workspace_hooks_repo_json=false
ok_workspace_hooks_project_json=false
ok_workspace_hook_init_repo_json=false
ok_workspace_hook_guide_repo_json=false
ok_workspace_hook_guide_emit_shell_repo=false
ok_workspace_hook_guide_copy_command_repo=false
ok_workspace_hook_guide_run_command_repo=false
ok_workspace_hook_guide_run_command_yes_repo=false
ok_workspace_hook_init_text_compact_repo=false
ok_workspace_hook_init_explain_repo=false
ok_workspace_hook_init_emit_shell_repo=false
ok_workspace_hook_init_copy_command_repo=false
ok_workspace_hook_init_emit_confirm_shell_repo=false
ok_workspace_hook_init_copy_confirm_command_repo=false
ok_workspace_hook_init_emit_target_path_repo=false
ok_workspace_hook_init_copy_target_path_repo=false
ok_workspace_hook_init_emit_target_dir_repo=false
ok_workspace_hook_init_copy_target_dir_repo=false
ok_workspace_hook_init_emit_target_project_root_repo=false
ok_workspace_hook_init_copy_target_project_root_repo=false
ok_workspace_hook_init_emit_target_project_name_repo=false
ok_workspace_hook_init_copy_target_project_name_repo=false
ok_workspace_hook_init_emit_target_relative_path_repo=false
ok_workspace_hook_init_copy_target_relative_path_repo=false
ok_workspace_hook_init_emit_target_bundle_repo=false
ok_workspace_hook_init_copy_target_bundle_repo=false
ok_workspace_hook_init_emit_open_shell_repo=false
ok_workspace_hook_init_copy_open_command_repo=false
ok_workspace_hook_init_run_command_repo=false
ok_workspace_hook_init_run_command_yes_repo=false
ok_workspace_hook_init_run_open_command_repo=false
ok_workspace_hook_init_run_open_command_yes_repo=false
ok_workspace_hook_init_inspect_target_repo=false
ok_workspace_hook_init_inspect_target_text_compact_repo=false
ok_workspace_hook_init_open_target_repo=false
ok_workspace_hook_init_open_now_repo=false
ok_workspace_hook_init_open_now_text_compact_repo=false
ok_workspace_hook_init_project_json=false
ok_workspace_hook_init_recommended_repo_json=false
ok_workspace_hook_init_recommended_suggest_repo_json=false
ok_workspace_hook_init_recommended_pick_repo_json=false
ok_workspace_hook_init_follow_recommended_repo_json=false
ok_workspace_hook_init_use_last_project_repo_json=false
ok_workspace_hook_continue_repo_json=false
ok_workspace_hook_continue_broaden_repo_json=false
ok_workspace_hook_continue_auto_repo_json=false
ok_workspace_hook_continue_dry_run_repo_json=false
ok_workspace_hook_continue_text_compact_repo=false
ok_workspace_hook_continue_inspect_target_text_compact_repo=false
ok_workspace_hook_continue_open_target_repo=false
ok_workspace_hook_continue_open_now_repo=false
ok_workspace_hook_continue_open_now_text_compact_repo=false
ok_workspace_hook_continue_open_now_text_compact_has_reason_repo=false
ok_workspace_hook_continue_open_now_preview_repo=false
ok_workspace_hook_continue_explain_repo=false
ok_workspace_hook_continue_emit_shell_repo=false
ok_workspace_hook_continue_emit_confirm_shell_repo=false
ok_workspace_hook_continue_emit_target_path_repo=false
ok_workspace_hook_continue_emit_target_dir_repo=false
ok_workspace_hook_continue_emit_target_project_root_repo=false
ok_workspace_hook_continue_emit_target_project_name_repo=false
ok_workspace_hook_continue_emit_target_relative_path_repo=false
ok_workspace_hook_continue_emit_target_bundle_repo=false
ok_workspace_hook_continue_emit_open_shell_repo=false
ok_workspace_hook_continue_copy_open_command_repo=false
ok_workspace_hook_continue_copy_confirm_command_repo=false
ok_workspace_hook_continue_copy_target_path_repo=false
ok_workspace_hook_continue_copy_target_dir_repo=false
ok_workspace_hook_continue_copy_target_project_root_repo=false
ok_workspace_hook_continue_copy_target_project_name_repo=false
ok_workspace_hook_continue_copy_target_relative_path_repo=false
ok_workspace_hook_continue_copy_target_bundle_repo=false
ok_workspace_hook_continue_copy_command_repo=false
ok_workspace_hook_continue_run_open_command_repo=false
ok_workspace_hook_continue_run_open_command_yes_repo=false
ok_workspace_hook_continue_run_command_repo=false
ok_workspace_hook_continue_run_command_yes_repo=false
ok_workspace_hook_continue_inspect_target_repo=false
ok_workspace_go_repo_json=false
ok_workspace_go_project_json=false
ok_workspace_summary_repo_json=false
ok_workspace_summary_project_json=false
ok_workspace_preview_repo_json=false
ok_workspace_preview_project_json=false
ok_workspace_open_target_repo_json=false
ok_workspace_open_target_project_json=false
ok_workspace_inspect_target_repo_json=false
ok_workspace_inspect_target_project_json=false
ok_workspace_run_inspect_command_repo_json=false
ok_workspace_run_inspect_command_project_json=false
ok_workspace_export_handoff_repo_json=false
ok_workspace_export_handoff_project_json=false
ok_workspace_doctor_repo_json=false
ok_workspace_doctor_project_json=false
ok_workspace_continue_repo_json=false
ok_workspace_continue_project_json=false
ok_rc_check_json=false
ok_rc_check_refresh_json=false
ok_rc_go_json=false
ok_rc_go_refresh_json=false
ok_cloud_status_preview_json=false
ok_build_artifact_preview_json=false

write_results_json() {
  local exit_code="${1:-0}"
  local status="ok"
  if [ "$exit_code" -ne 0 ]; then
    status="error"
  fi

  while IFS= read -r var_name; do
    export "CLI_SMOKE_CAPTURE_${var_name#ok_}=${!var_name}"
  done < <(compgen -A variable ok_)

  export CLI_SMOKE_RESULT_STATUS="$status"
  export CLI_SMOKE_RESULT_EXIT_CODE="$exit_code"
  export CLI_SMOKE_RESULT_TMP_ROOT="$TMP_ROOT"

  python3 - "$RESULTS_JSON" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json
import os
import sys
from pathlib import Path

result_path = Path(sys.argv[1])
checks = {}
for key, value in os.environ.items():
    if not key.startswith("CLI_SMOKE_CAPTURE_"):
        continue
    check_name = key[len("CLI_SMOKE_CAPTURE_"):] + "_ok"
    checks[check_name] = value == "true"

status = os.environ.get("CLI_SMOKE_RESULT_STATUS", "ok")
exit_code = int(os.environ.get("CLI_SMOKE_RESULT_EXIT_CODE", "0"))
checks = dict(sorted(checks.items()))

if status == "ok" and not all(checks.values()):
    status = "error"

failed_checks = [name for name, ok in checks.items() if not ok]
payload = {
    "status": status,
    "tmp_root": os.environ.get("CLI_SMOKE_RESULT_TMP_ROOT", ""),
    "exit_code": exit_code,
    "checks": checks,
}
if failed_checks:
    payload["failed_check_count"] = len(failed_checks)
    payload["failed_checks_preview"] = failed_checks[:20]

result_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
PY
}

cleanup() {
  rm -rf "$TMP_ROOT"
  if [ -n "${workspace_hook_project_dir:-}" ]; then
    rm -rf "$workspace_hook_project_dir"
  fi
}

on_exit() {
  local exit_code="${1:-0}"
  write_results_json "$exit_code" || true
  cleanup || true
}

trap 'rc=$?; trap - EXIT; on_exit "$rc"; exit "$rc"' EXIT

cd "$TMP_ROOT"
python3 -m cli init >/tmp/cli_smoke_init.log 2>&1
python3 -m cli generate '做一个 AI SaaS 官网，包含首页、功能介绍、联系我们。' >/tmp/cli_smoke_generate.log 2>&1

cat > "$TMP_ROOT/bad_alias.ail" <<'EOF'
#PROFILE[landing]
@PAGE[Home,/]
#UI[landing:Header]
#UI[landing:Hero]
#UI[landing:Testimonials]
#UI[landing:FAQ]
#UI[landing:Contact]
#UI[landing:Footer]
EOF

diagnose_json="$TMP_ROOT/diagnose.json"
set +e
python3 -m cli diagnose "$TMP_ROOT/bad_alias.ail" --requirement '做一个官网，包含客户评价、FAQ、联系我们。' --json > "$diagnose_json"
diagnose_exit=$?
set -e
python3 - "$diagnose_json" "$diagnose_exit" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
exit_code = int(sys.argv[2])
assert exit_code == 3, exit_code
assert payload['status'] == 'validation_failed', payload
diagnosis = payload['diagnosis']
assert diagnosis['compile_recommended'] == 'no', payload
assert 'landing:Testimonials->landing:Testimonial' in diagnosis['alias_components'], payload
PY
ok_diagnose_json=true

repair_json="$TMP_ROOT/repair.json"
python3 -m cli repair "$TMP_ROOT/bad_alias.ail" --requirement '做一个官网，包含客户评价、FAQ、联系我们。' --json --write > "$repair_json"
python3 - "$repair_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['wrote'] is True, payload
assert 'landing:Testimonial' in payload['repaired_ail'], payload
assert payload['output_path'].endswith('bad_alias.ail'), payload
PY
ok_repair_json=true

post_repair_diagnose_json="$TMP_ROOT/post_repair_diagnose.json"
python3 -m cli diagnose "$TMP_ROOT/bad_alias.ail" --requirement '做一个官网，包含客户评价、FAQ、联系我们。' --json > "$post_repair_diagnose_json"
python3 - "$post_repair_diagnose_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['diagnosis']['compile_recommended'] == 'yes', payload
PY
ok_post_repair_diagnose_json=true

cat > "$TMP_ROOT/.ail/source.ail" <<'EOF'
#PROFILE[landing]
@PAGE[Home,/]
#UI[landing:Header]
#UI[landing:Hero]
#UI[landing:Testimonials]
#UI[landing:FAQ]
#UI[landing:Contact]
#UI[landing:Footer]
EOF
project_doctor_validation_json="$TMP_ROOT/project_doctor_validation.json"
set +e
python3 -m cli project doctor --fix-plan --json > "$project_doctor_validation_json"
project_doctor_validation_exit=$?
set -e
python3 - "$project_doctor_validation_json" "$project_doctor_validation_exit" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
exit_code = int(sys.argv[2])
assert exit_code == 3, exit_code
assert payload['status'] == 'validation_failed', payload
assert payload['recommended_action'] == 'repair_source', payload
assert payload['source_diagnosis']['diagnosis']['compile_recommended'] == 'no', payload
assert payload['fix_plan']['mode'] == 'guided_recovery', payload
assert len(payload['fix_plan']['steps']) >= 3, payload
PY
ok_project_doctor_validation_json=true

project_doctor_apply_safe_repair_json="$TMP_ROOT/project_doctor_apply_safe_repair.json"
python3 -m cli project doctor --apply-safe-fixes --json > "$project_doctor_apply_safe_repair_json"
python3 - "$project_doctor_apply_safe_repair_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] in {'ok', 'warning'}, payload
assert payload['recommended_action'] in {'refresh_build_state', 'continue_iteration'}, payload
assert payload['safe_fix_result']['status'] == 'applied', payload
assert any(str(item).startswith('repaired_source:') for item in payload['safe_fix_result']['applied_fixes']), payload
assert payload['source_diagnosis']['diagnosis']['compile_recommended'] == 'yes', payload
PY
ok_project_doctor_apply_safe_repair_json=true

cat > "$TMP_ROOT/.ail/source.ail" <<'EOF'
#PROFILE[landing]
@PAGE[Home,/]
#UI[landing:Header]
#UI[landing:Hero]
#UI[landing:Testimonials]
#UI[landing:FAQ]
#UI[landing:Contact]
#UI[landing:Footer]
EOF

project_doctor_apply_safe_continue_repair_json="$TMP_ROOT/project_doctor_apply_safe_continue_repair.json"
AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project doctor --apply-safe-fixes --and-continue --json > "$project_doctor_apply_safe_continue_repair_json"
python3 - "$project_doctor_apply_safe_continue_repair_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['recommended_action'] == 'continue_iteration', payload
assert payload['safe_fix_result']['status'] == 'applied', payload
assert payload['continue_result']['build_id'], payload
assert payload['continue_result']['managed_files_written'] >= 1, payload
assert payload['project_check']['checks']['ready_for_sync'] is True, payload
PY
ok_project_doctor_apply_safe_continue_repair_json=true

cat > "$TMP_ROOT/.ail/source.ail" <<'EOF'
#PROFILE[landing]
@PAGE[Home,/]
#UI[landing:Header]
#UI[landing:Hero]
#UI[landing:Testimonials]
#UI[landing:FAQ]
#UI[landing:Contact]
#UI[landing:Footer]
EOF

project_go_repair_json="$TMP_ROOT/project_go_repair.json"
AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project go --json > "$project_go_repair_json"
python3 - "$project_go_repair_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'project-go', payload
assert payload['route_taken'] == 'project_doctor_apply_safe_fixes_and_continue', payload
assert payload['route_reason'], payload
assert payload['executed_primary_action'] == 'project_doctor_apply_safe_fixes_and_continue', payload
assert payload['result']['status'] == 'ok', payload
assert payload['result']['safe_fix_result']['status'] == 'applied', payload
assert payload['result']['continue_result']['status'] == 'ok', payload
assert payload['result']['continue_result']['managed_files_written'] >= 1, payload
PY
ok_project_go_repair_json=true

python3 -m cli repair .ail/source.ail --requirement '做一个官网，包含客户评价、FAQ、联系我们。' --write >/tmp/cli_smoke_project_doctor_repair.log 2>&1

compile_json="$TMP_ROOT/compile_ok.json"
AIL_CLOUD_BASE_URL=embedded://local python3 -m cli compile --cloud --json > "$compile_json"
python3 - "$compile_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['file_count'] >= 1, payload
assert 'build_id' in payload and payload['build_id'], payload
PY
ok_compile_json=true

single_page_project_dir="$(mktemp -d /tmp/ail_cli_smoke_single_page.XXXXXX)"
single_page_trial_json="$TMP_ROOT/personal_single_page_trial.json"
AIL_CLOUD_BASE_URL=embedded://local python3 -m cli trial-run \
  --requirement '做一个个人独立站，包含首页、自我介绍、作品展示、服务说明、联系方式。' \
  --project-dir "$single_page_project_dir" \
  --base-url embedded://local \
  --json > "$single_page_trial_json"
python3 - "$single_page_trial_json" "$single_page_project_dir" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
from pathlib import Path

payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
project_dir = Path(sys.argv[2])
assert payload['status'] == 'ok', payload
assert payload['detected_profile'] == 'landing', payload

home_vue = (project_dir / 'src/views/generated/Home.vue').read_text(encoding='utf-8')
routes_generated = (project_dir / 'src/router/generated/routes.generated.ts').read_text(encoding='utf-8')

assert 'const singlePageLanding = true' in home_vue, home_vue
assert '>个人作品集<' in home_vue or '>把个人表达收成一张好用的首页<' in home_vue or '>独立设计与开发作品集<' in home_vue, home_vue
assert '"label": "关于我"' in home_vue, home_vue
assert '"target": "#about"' in home_vue, home_vue
assert '"label": "服务说明"' in home_vue, home_vue
assert '"label": "作品展示"' in home_vue, home_vue
assert '"label": "联系方式"' in home_vue, home_vue
assert '"target": "#features"' in home_vue, home_vue
assert '"target": "#contact"' in home_vue, home_vue
assert '"target": "#portfolio"' in home_vue, home_vue
assert 'id="about"' in home_vue, home_vue
assert "关于我" in home_vue, home_vue
assert "我更偏一起编辑一张公开作品的合作方式" in home_vue, home_vue
assert "哪些内容该靠语气去讲，哪些该靠结构去托住" in home_vue, home_vue
assert "hero-persona-row" in home_vue, home_vue
assert "hero-persona-chip" in home_vue, home_vue
assert "独立顾问型合作" in home_vue, home_vue
assert "内容与产品表达" in home_vue, home_vue
assert "结构设计与前端落地" in home_vue, home_vue
assert "更像并肩编辑，而不是外包接单" in home_vue, home_vue
assert "AUTHOR SIGNATURE" in home_vue, home_vue
assert "CURATED SHELF" in home_vue, home_vue
assert 'id="contact"' in home_vue, home_vue
assert "联系我" in home_vue, home_vue
assert "查看作品" in home_vue, home_vue
assert "服务说明" in home_vue, home_vue
assert "作品展示" in home_vue, home_vue
assert "发起联系" in home_vue, home_vue
assert "个人品牌首页梳理" in home_vue, home_vue
assert "适合个人主页、服务页和作品入口" in home_vue, home_vue
assert "独立顾问主页" in home_vue, home_vue
assert "这些案例不是为了证明我做过多少种风格" in home_vue, home_vue
assert "我更偏一起编辑一张公开作品的合作方式" in home_vue, home_vue
assert "项目类型" in home_vue, home_vue
assert "交付范围" in home_vue, home_vue
assert "结果" in home_vue, home_vue
assert "独立顾问 / 个人服务型合作" in home_vue, home_vue
assert "第一次来访就知道你适合哪类合作" in home_vue, home_vue
assert "把个人定位、代表能力和合作方式收成一个更清晰的首页入口" in home_vue, home_vue
assert "首页定位、合作方式、联系入口" in home_vue, home_vue
assert "产品团队 / 单产品官网" in home_vue, home_vue
assert "产品价值和预约动作更快连起来" in home_vue, home_vue
assert "适合对象、价值主张、预约演示" in home_vue, home_vue
assert "内容作者 / 长期内容项目" in home_vue, home_vue
assert "旧内容也能继续被看见、被引用、被重新组织" in home_vue, home_vue
assert "专题结构、内容分层、持续更新" in home_vue, home_vue
assert "const personalPortfolioMode = true" in home_vue, home_vue
assert "font-family: 'Iowan Old Style'" in home_vue, home_vue
assert "landing-page.personal-portfolio .hero-persona-row" in home_vue, home_vue
assert "landing-page.personal-portfolio .landing-header" in home_vue, home_vue
assert "landing-page.personal-portfolio .landing-section h2::before" in home_vue, home_vue
assert "background: linear-gradient(180deg, #f59e0b, #f97316)" in home_vue, home_vue
assert "landing-page.personal-portfolio .portfolio-meta" in home_vue, home_vue
assert "const portfolioDetails =" in home_vue, home_vue
assert "landing-page.personal-portfolio .portfolio-detail" in home_vue, home_vue
assert "@click=\"go('#contact')\"" in home_vue, home_vue
assert "@click=\"go('#portfolio')\"" in home_vue, home_vue
assert 'AilCliSmokeSinglePage' not in home_vue, home_vue
assert '/features' not in routes_generated, routes_generated
assert '/pricing' not in routes_generated, routes_generated
assert '/contact' not in routes_generated, routes_generated
PY
ok_single_page_landing_nav_json=true

after_sales_project_dir="$(mktemp -d /tmp/ail_cli_smoke_after_sales.XXXXXX)"
after_sales_trial_json="$TMP_ROOT/after_sales_trial.json"
AIL_CLOUD_BASE_URL=embedded://local python3 -m cli trial-run \
  --requirement '做一个品牌售后服务网站，包含退款申请、换货申请、投诉提交、进度查询说明、联系客服。' \
  --project-dir "$after_sales_project_dir" \
  --base-url embedded://local \
  --json > "$after_sales_trial_json"
python3 - "$after_sales_trial_json" "$after_sales_project_dir" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
from pathlib import Path

payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
project_dir = Path(sys.argv[2])
assert payload['status'] == 'ok', payload
assert payload['detected_profile'] == 'after_sales', payload
after_sales_view = project_dir / 'src/views/generated/AfterSales.vue'
content = after_sales_view.read_text(encoding='utf-8')
assert 'CASE STATUS' in content, content
assert 'CASE FLOW' in content, content
assert 'STATUS TO FLOW' in content, content
assert '先把当前状态和处理轨道对齐，再进入跟进摘要' in content, content
assert '当前处理流' in content, content
assert 'flow-track' in content, content
assert 'flow-step' in content, content
assert 'flow-ops-strip' in content, content
assert '当前负责人：' in content, content
assert '处理时效：' in content, content
assert '跟进焦点：' in content, content
assert 'caseFlowTrack' in content, content
assert '01' in content and '带入订单' in content, content
assert '确认路径' in content, content
assert '材料核对' in content, content
assert '首次反馈' in content, content
assert 'CASE OPS' in content, content
assert 'CASE HISTORY' in content, content
assert 'case-bridge' in content, content
assert 'OPS TO HISTORY' in content, content
assert 'ops-history-strip' in content, content
assert '最新进展：' in content, content
assert '下一步记录：' in content, content
assert 'HISTORY TO ACTIONS' in content, content
assert 'action-entry-strip' in content, content
assert '记录锚点：' in content, content
assert '当前建议：' in content, content
assert '接下来：' in content, content
assert 'action-panel-strip' in content, content
assert '当前动作：' in content, content
assert 'panel-support-strip' in content, content
assert '当前说明：' in content, content
assert '处理时效：' in content, content
assert 'support-footer-strip' in content, content
assert '当前准备：' in content, content
assert '带着状态层和处理轨道进入跟进摘要' in content, content
assert '先把当前跟进和最近记录对照，再决定具体动作' in content, content
assert '带着当前跟进和最近记录进入具体动作' in content, content
assert '选择动作后会在这里展开当前说明' in content, content
assert '当前：动作选择' in content, content
assert '下一步：查看当前说明' in content, content
assert 'FINAL STEP' in content, content
assert '看完当前说明后，再决定回到入口还是继续联系客服' in content, content
assert 'case-bridge--footer' in content, content
assert 'case-bridge--support' in content, content
assert '带着当前说明继续核对处理节奏和准备材料' in content, content
assert 'card-selected' in content, content
assert 'card-selected-badge' in content, content
assert '当前已选' in content, content
assert '查看当前说明' in content, content
assert 'CASE INTAKE' in content, content
assert '先补这三项，再进入售后动作' in content, content
assert '当前：准备 intake' in content, content
assert '下一步：选择售后动作' in content, content
assert 'context-entry' in content, content
assert 'ENTRY MODE' in content, content
assert 'CASE MODE' in content, content
assert 'entry-mode-strip' in content, content
assert 'order-box--tracked' in content, content
assert 'order-box--intake' in content, content
assert 'CASE SNAPSHOT' in content, content
assert '当前节点' in content, content
assert '当前负责人' in content, content
assert '处理时效' in content, content
assert 'tracked-summary' in content, content
assert 'BOARD SUMMARY' in content, content
assert 'tracked-board-strip' in content, content
assert 'tracked-board-owner' in content, content
assert 'tracked-board-focus' in content, content
assert 'tracked-board-next' in content, content
assert '负责人：' in content, content
assert '当前焦点：' in content, content
assert 'CASE BOARD' in content, content
assert '带着当前快照继续看状态与处理流' in content, content
assert '当前：状态层' in content, content
assert '下一步：查看处理流' in content, content
assert '最近跟进记录' in content, content
assert 'history-list' in content, content
print('ok')
PY
ok_after_sales_flow_json=true

ecom_checkout_project_dir="$(mktemp -d /tmp/ail_cli_smoke_ecom_checkout.XXXXXX)"
ecom_checkout_trial_json="$TMP_ROOT/ecom_checkout_trial.json"
AIL_CLOUD_BASE_URL=embedded://local python3 -m cli trial-run \
  --requirement '做一个电商独立站，包含首页、商品详情、购物车、结算。' \
  --project-dir "$ecom_checkout_project_dir" \
  --json >"$ecom_checkout_trial_json"
python3 - "$ecom_checkout_trial_json" "$ecom_checkout_project_dir" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
from pathlib import Path

payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
project_dir = Path(sys.argv[2])
assert payload['status'] == 'ok', payload
assert payload['detected_profile'] == 'ecom_min', payload
checkout_view = project_dir / 'src/views/generated/Checkout.vue'
content = checkout_view.read_text(encoding='utf-8')
assert 'storefront-announcement' in content, content
assert 'storefront-nav' in content, content
assert 'storefront-footer' in content, content
assert 'checkout-step-strip' in content, content
assert 'FINAL CHECK' in content, content
assert 'FINAL REVIEW' in content, content
assert 'CURRENT STEP' in content, content
assert '已承接购物车金额复核' in content, content
assert 'completion-banner' in content, content
assert 'ORDER STORED' in content, content
assert 'clearRecentOrder' in content, content
assert 'CHECKOUT HANDOFF' in content, content
assert 'checkout-handoff-flow' in content, content
assert '01 购物车已复核' in content, content
assert '03 提交后保留摘要' in content, content
assert 'PURCHASE AXIS' in content, content
assert 'checkout-axis-bridge' in content, content
assert 'checkout-axis-flow' in content, content
assert '01 保留来源上下文' in content, content
assert '03 带着语境完成回流' in content, content
assert 'RETURN AXIS' in content, content
assert 'completion-axis-bridge' in content, content
assert 'completion-axis-flow' in content, content
assert '01 收住购买主轴' in content, content
assert '02 带着来源继续逛' in content, content
assert '03 保留订单摘要' in content, content
assert '回到商品详情' in content, content
assert 'openSourceProduct' in content, content
assert 'sourceProductTitle' in content, content
assert 'sourceShopId' in content, content
assert 'source_kind: sourceKind.value' in content, content
assert "nextParams.set('from', sourceKind.value)" in content, content
assert 'summary-hint' in content, content
assert '这里的最终金额已经接住上一页的来源和复核语境' in content, content
assert 'CONTINUE BROWSING' in content, content
assert '继续看同类商品' in content, content
assert 'openSourceCategory' in content, content
assert 'completion-return-flow' in content, content
assert '01 保留来源' in content, content
assert '03 保留订单摘要' in content, content
assert 'source_category_name' in content, content
print('ok')
PY
ok_ecom_checkout_flow_json=true

ecom_cart_project_dir="$(mktemp -d /tmp/ail_cli_smoke_ecom_cart.XXXXXX)"
ecom_cart_trial_json="$TMP_ROOT/ecom_cart_trial.json"
AIL_CLOUD_BASE_URL=embedded://local python3 -m cli trial-run \
  --requirement '做一个电商独立站，包含首页、商品详情、购物车、结算。' \
  --project-dir "$ecom_cart_project_dir" \
  --json >"$ecom_cart_trial_json"
python3 - "$ecom_cart_trial_json" "$ecom_cart_project_dir" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
from pathlib import Path

payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
project_dir = Path(sys.argv[2])
assert payload['status'] == 'ok', payload
assert payload['detected_profile'] == 'ecom_min', payload
cart_view = project_dir / 'src/views/generated/Cart.vue'
content = cart_view.read_text(encoding='utf-8')
assert 'storefront-tools' in content, content
assert '会员入口（骨架）' in content, content
assert '结算准备' in content, content
assert 'summary-hint' in content, content
assert 'READY CHECK' in content, content
assert '下一步：确认地址与支付方式' in content, content
assert '金额、运费和件数都确认后，再进入下一步会更顺。' in content, content
assert 'PRODUCT HANDOFF' in content, content
assert 'product-handoff-flow' in content, content
assert '带着来源去结算' in content, content
assert 'DISCOVERY MEMORY' in content, content
assert 'cart-discovery-flow' in content, content
assert 'PURCHASE AXIS' in content, content
assert 'purchase-axis-bridge' in content, content
assert 'purchase-axis-flow' in content, content
assert '01 保留发现与来源' in content, content
assert '03 带着语境去结算' in content, content
assert 'ADDRESS PREVIEW' in content, content
assert 'PAYMENT PREVIEW' in content, content
assert 'ORDER INTENT' in content, content
assert '回到搜索结果' in content or '回到分类页' in content, content
assert 'openDiscoverySource' in content, content
assert '回到商品详情' in content, content
assert 'openSourceProduct' in content, content
assert ':to="checkoutLink"' in content, content
assert 'sourceProductTitle' in content, content
assert 'sourceShopId' in content, content
assert 'sourceDiscoveryKind' in content, content
assert "params.set('q', sourceQuery.value)" in content, content
assert "params.set('discovery', sourceDiscoveryKind.value)" in content, content
print('ok')
PY
ok_ecom_cart_flow_json=true

ecom_product_project_dir="$(mktemp -d /tmp/ail_cli_smoke_ecom_product.XXXXXX)"
ecom_product_trial_json="$TMP_ROOT/ecom_product_trial.json"
AIL_CLOUD_BASE_URL=embedded://local python3 -m cli trial-run \
  --requirement '做一个电商独立站，包含首页、商品详情、购物车、结算。' \
  --project-dir "$ecom_product_project_dir" \
  --json >"$ecom_product_trial_json"
python3 - "$ecom_product_trial_json" "$ecom_product_project_dir" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
from pathlib import Path

payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
project_dir = Path(sys.argv[2])
assert payload['status'] == 'ok', payload
assert payload['detected_profile'] == 'ecom_min', payload
checkout_view = project_dir / 'src/views/generated/Checkout.vue'
checkout_content = checkout_view.read_text(encoding='utf-8')
assert 'storefront-announcement' in checkout_content, checkout_content
assert 'CHECKOUT HANDOFF' in checkout_content, checkout_content
assert 'DISCOVERY MEMORY' in checkout_content, checkout_content
assert 'checkout-discovery-bridge' in checkout_content, checkout_content
assert 'PURCHASE AXIS' in checkout_content, checkout_content
assert 'checkout-axis-bridge' in checkout_content, checkout_content
assert 'checkout-axis-flow' in checkout_content, checkout_content
assert 'RETURN AXIS' in checkout_content, checkout_content
assert 'completion-axis-bridge' in checkout_content, checkout_content
assert 'completion-axis-flow' in checkout_content, checkout_content
assert 'ADDRESS SELECTOR' in checkout_content, checkout_content
assert 'PAYMENT SELECTOR' in checkout_content, checkout_content
assert 'SUCCESS RECEIPT' in checkout_content, checkout_content
assert 'addressOptions' in checkout_content, checkout_content
assert 'paymentOptions' in checkout_content, checkout_content
assert 'activeAddress' in checkout_content, checkout_content
assert '回到搜索结果' in checkout_content or '回到分类页' in checkout_content, checkout_content
assert 'source_discovery_kind' in checkout_content, checkout_content
assert "nextParams.set('q', sourceQuery.value)" in checkout_content, checkout_content
assert "nextParams.set('discovery', sourceDiscoveryKind.value)" in checkout_content, checkout_content
assert 'openDiscoverySource' in checkout_content, checkout_content
product_view = project_dir / 'src/views/generated/Product.vue'
content = product_view.read_text(encoding='utf-8')
assert 'storefront-nav' in content, content
assert 'storefront-footer' in content, content
assert 'store-card' in content, content
assert 'LAST_ADDED_KEY' in content, content
assert 'PRODUCT PICK' in content, content
assert 'purchase-strip' in content, content
assert '价格判断' in content, content
assert 'field-grid' in content, content
assert 'CURRENT PICK' in content, content
assert 'PRICE CHECK' in content, content
assert 'NEXT MOVE' in content, content
assert 'const normalizedQuantity = computed(() =>' in content, content
assert 'const selectionTotal = computed(() =>' in content, content
assert 'media-gallery' in content, content
assert 'STYLE VIEW' in content, content
assert 'thumb-rail' in content, content
assert 'GALLERY MODE' in content, content
assert 'variant-selector' in content, content
assert 'quantity-stepper' in content, content
assert 'SPEC TABLE' in content, content
assert 'REVIEW LIST' in content, content
assert 'SERVICE ASSURANCE' in content, content
assert 'NEXT PICKS' in content, content
assert 'related-card-flow' in content, content
assert 'action-hint' in content, content
assert 'cover-fallback' in content, content
assert 'related-fallback' in content, content
assert 'ITEM STORED' in content, content
assert '已加入购物车' in content, content
assert '去看购物车' in content, content
assert '继续去结算' in content, content
assert 'const cartLink = computed(() => {' in content, content
assert "params.set('from', 'product')" in content, content
assert "params.set('product', String(product.value.id || ''))" in content, content
assert "params.set('shop', String(product.value.shop_id || ''))" in content, content
assert "params.set('title', String(product.value.title || ''))" in content, content
assert 'source-shop-link' in content, content
assert 'openSourceShop' in content, content
assert 'sourceShopId' in content, content
assert 'sourceDiscoveryKind' in content, content
assert 'sourceDiscoveryLabel' in content, content
assert 'DISCOVERY MEMORY' in content, content
assert 'openDiscoverySource' in content, content
assert '同店继续看' in content, content
print('ok')
PY
ok_ecom_product_feedback_json=true

ecom_home_project_dir="$(mktemp -d /tmp/ail_cli_smoke_ecom_home.XXXXXX)"
ecom_home_trial_json="$TMP_ROOT/ecom_home_trial.json"
AIL_CLOUD_BASE_URL=embedded://local python3 -m cli trial-run \
  --requirement '做一个电商独立站，包含首页、商品详情、购物车、结算。' \
  --project-dir "$ecom_home_project_dir" \
  --json >"$ecom_home_trial_json"
python3 - "$ecom_home_trial_json" "$ecom_home_project_dir" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
from pathlib import Path

payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
project_dir = Path(sys.argv[2])
assert payload['status'] == 'ok', payload
assert payload['detected_profile'] == 'ecom_min', payload
home_view = project_dir / 'src/views/generated/Home.vue'
content = home_view.read_text(encoding='utf-8')
assert 'storefront-announcement' in content, content
assert 'storefront-nav' in content, content
assert 'storefront-tools' in content, content
assert 'storefront-footer' in content, content
assert 'store-card' in content, content
assert 'card-kicker' in content, content
assert 'PRODUCT PICK' in content, content
assert 'card-flow' in content, content
assert '先看详情' in content, content
assert '再决定是否加入购物车' in content, content
assert 'banner-flow' in content, content
assert '01 先逛热销' in content, content
assert 'ec-promo-strip' in content, content
assert 'PROMO EVENT' in content, content
assert 'category-shortcut-grid' in content, content
assert 'QUICK ENTRY' in content, content
assert '新品上架' in content, content
assert 'NEW ARRIVAL' in content, content
assert 'ec-brand-story' in content, content
assert 'BRAND / FACTORY STORY' in content, content
assert 'ec-testimonial-strip' in content, content
assert 'BUYER VOICE' in content, content
assert 'ec-trust-strip' in content, content
assert 'PAYMENT READY' in content, content
assert 'section-lead' in content, content
assert 'CURRENT FILTER' in content, content
assert '可见商品' in content, content
assert 'filter-surface' in content, content
assert '打开搜索结果页' in content, content
assert 'setCategory' in content, content
category_view = project_dir / 'src/views/generated/Category.vue'
category_content = category_view.read_text(encoding='utf-8')
assert 'storefront-nav' in category_content, category_content
assert 'store-card' in category_content, category_content
assert 'CATEGORY VIEW' in category_content, category_content
assert '01 先看分类' in category_content, category_content
assert '02 再进店看' in category_content, category_content
assert 'FILTER BAR' in category_content, category_content
assert 'SORT RULE' in category_content, category_content
assert 'RESULT COUNT' in category_content, category_content
assert 'RESULT PAGE' in category_content, category_content
assert '100以下' in category_content, category_content
assert '上一页' in category_content, category_content
assert '回到搜索结果' in category_content, category_content
assert 'PRODUCT PICK' in category_content, category_content
assert 'CONTINUE PICK' in category_content, category_content
assert 'shop-link' in category_content, category_content
assert 'openShop' in category_content, category_content
search_view = project_dir / 'src/views/generated/Search.vue'
search_content = search_view.read_text(encoding='utf-8')
assert 'storefront-footer' in search_content, search_content
assert 'store-card' in search_content, search_content
assert 'SEARCH RESULT' in search_content, search_content
assert '01 先搜关键词' in search_content, search_content
assert '02 再进店看' in search_content, search_content
assert 'CURRENT FILTER' in search_content, search_content
assert 'QUICK NARROW' in search_content, search_content
assert 'SORT RULE' in search_content, search_content
assert 'PRICE BAND' in search_content, search_content
assert 'RESULT PAGE' in search_content, search_content
assert '默认相关度' in search_content, search_content
assert '全部价格' in search_content, search_content
assert '上一页' in search_content, search_content
assert '更新结果' in search_content, search_content
assert 'PRODUCT PICK' in search_content, search_content
assert 'CONTINUE PICK' in search_content, search_content
assert 'shop-link' in search_content, search_content
assert 'openShop' in search_content, search_content
shop_view = project_dir / 'src/views/generated/Shop.vue'
shop_content = shop_view.read_text(encoding='utf-8')
assert 'storefront-nav' in shop_content, shop_content
assert 'store-card' in shop_content, shop_content
assert 'SHOP CONTINUITY' in shop_content, shop_content
assert 'CURRENT SHOP' in shop_content, shop_content
assert 'SHOP FOCUS' in shop_content, shop_content
assert 'IN-SHOP COUNT' in shop_content, shop_content
assert 'NEXT MOVE' in shop_content, shop_content
assert '01 先定店铺' in shop_content, shop_content
assert '02 再看店内商品' in shop_content, shop_content
assert 'PRODUCT PICK' in shop_content, shop_content
assert 'CONTINUE PICK' in shop_content, shop_content
assert 'DISCOVERY CONTINUITY' in shop_content, shop_content
assert 'openDiscoverySource' in shop_content, shop_content
assert '回到搜索结果' in shop_content, shop_content
assert '回到分类页' in shop_content, shop_content
about_view = project_dir / 'src/views/generated/About.vue'
about_content = about_view.read_text(encoding='utf-8')
assert 'storefront-nav' in about_content, about_content
assert 'ABOUT STOREFRONT' in about_content, about_content
assert 'COMPANY SNAPSHOT' in about_content, about_content
assert 'BRAND POSTURE' in about_content, about_content
assert 'FACTORY / SUPPLY' in about_content, about_content
assert 'TIMELINE' in about_content, about_content
contact_view = project_dir / 'src/views/generated/Contact.vue'
contact_content = contact_view.read_text(encoding='utf-8')
assert 'storefront-footer' in contact_content, contact_content
assert 'CONTACT ENTRY' in contact_content, contact_content
assert 'CONTACT CHANNELS' in contact_content, contact_content
assert 'MESSAGE FORM' in contact_content, contact_content
assert 'FORM STUB' in contact_content, contact_content
assert 'FORM FEEDBACK' in contact_content, contact_content
assert 'Send skeleton message' in contact_content, contact_content
policy_view = project_dir / 'src/views/generated/Policy.vue'
policy_content = policy_view.read_text(encoding='utf-8')
assert 'POLICY CENTER' in policy_content, policy_content
assert 'COMPLIANCE SURFACE' in policy_content, policy_content
assert 'PRIVACY NOTE' in policy_content, policy_content
assert 'AFTER-SALES TERMS' in policy_content, policy_content
assert 'PAYMENT NOTICE' in policy_content, policy_content
account_view = project_dir / 'src/views/generated/Account.vue'
account_content = account_view.read_text(encoding='utf-8')
assert 'storefront-nav' in account_content, account_content
assert 'MEMBER CENTER' in account_content, account_content
assert 'STATIC MEMBER SHELL' in account_content, account_content
assert 'PROFILE CARD' in account_content, account_content
assert 'ACCOUNT OVERVIEW' in account_content, account_content
assert 'PROFILE READY' in account_content, account_content
assert 'ORDER HUB' in account_content, account_content
assert 'ADDRESS BOOK' in account_content, account_content
assert 'WISHLIST' in account_content, account_content
assert 'SECURITY' in account_content, account_content
assert 'ORDER DETAILS' in account_content, account_content
assert 'ORDER STATES' in account_content, account_content
assert 'ALL ORDERS' in account_content, account_content
assert 'PENDING PAYMENT' in account_content, account_content
assert 'TO SHIP' in account_content, account_content
assert 'TO RECEIVE' in account_content, account_content
assert 'AFTER-SALES' in account_content, account_content
assert '待付款 / 待确认' in account_content, account_content
assert '待发货 / 待收货' in account_content, account_content
assert '已完成 / 售后中' in account_content, account_content
assert 'ORDER CARD / #A20260426-1001' in account_content, account_content
assert 'ORDER CARD / #A20260426-0874' in account_content, account_content
assert '继续支付' in account_content, account_content
assert '查看订单详情' in account_content, account_content
assert '查看物流' in account_content, account_content
assert '确认收货' in account_content, account_content
assert 'ORDER EMPTY STATE' in account_content, account_content
assert 'ADDRESS MODULE' in account_content, account_content
assert 'CHECKOUT REUSE' in account_content, account_content
assert 'DEFAULT ADDRESS CARD' in account_content, account_content
assert 'SYNCED TO CHECKOUT' in account_content, account_content
assert '设为结算默认' in account_content, account_content
assert '编辑地址' in account_content, account_content
assert '默认地址卡' in account_content, account_content
assert '常用地址列表' in account_content, account_content
assert '结算同步位' in account_content, account_content
assert 'ADDRESS ITEM / Office' in account_content, account_content
assert 'ADDRESS ITEM / Warehouse' in account_content, account_content
assert 'DEFAULT' in account_content, account_content
assert 'ALT ADDRESS' in account_content, account_content
assert 'ADDRESS EMPTY STATE' in account_content, account_content
assert 'WISHLIST FLOW' in account_content, account_content
assert 'RETURN FLOW' in account_content, account_content
assert 'ALL SAVED' in account_content, account_content
assert 'PRICE DROP' in account_content, account_content
assert 'SHOP FOLLOW' in account_content, account_content
assert 'RECENT VIEWED' in account_content, account_content
assert 'SAVED ITEM / Air Mesh Runner' in account_content, account_content
assert 'SAVED ITEM / Walnut Floor Lamp' in account_content, account_content
assert 'SHOP FOLLOW / Orange Select' in account_content, account_content
assert '回到商品详情' in account_content, account_content
assert '回到搜索结果' in account_content, account_content
assert '回到店铺页' in account_content, account_content
assert 'RECENT VIEW / Product' in account_content, account_content
assert 'RECENT VIEW / Search' in account_content, account_content
assert 'RECENT VIEW / Shop' in account_content, account_content
assert 'RETURN TO PRODUCT' in account_content, account_content
assert 'RETURN TO SEARCH' in account_content, account_content
assert 'RETURN TO CATEGORY' in account_content, account_content
assert 'RETURN TO SHOP' in account_content, account_content
assert 'EMPTY STATE READY' in account_content, account_content
assert 'SECURITY DETAIL' in account_content, account_content
assert 'AUTH LATER' in account_content, account_content
assert 'EMAIL SIGN-IN' in account_content, account_content
assert 'MOBILE SIGN-IN' in account_content, account_content
assert 'SOCIAL BIND' in account_content, account_content
assert '2FA READY' in account_content, account_content
assert '双重验证与设备管理' in account_content, account_content
assert 'DEVICE CARD / MacBook Air' in account_content, account_content
assert 'DEVICE CARD / iPhone' in account_content, account_content
assert 'NOTIFY LOGIN EVENTS' in account_content, account_content
assert 'EXPORT ACCOUNT DATA' in account_content, account_content
assert 'MARKETING CONSENT' in account_content, account_content
assert 'SESSION REVIEW' in account_content, account_content
assert '更新密码' in account_content, account_content
assert '启用双重验证' in account_content, account_content
assert '管理设备' in account_content, account_content
assert '导出账户数据' in account_content, account_content
assert 'RISK ACTIONS' in account_content, account_content
assert '退出全部设备' in account_content, account_content
assert '冻结账户入口' in account_content, account_content
assert '申请注销' in account_content, account_content
assert 'SECURITY EMPTY STATE' in account_content, account_content
assert 'DYNAMIC BOUNDARY' in account_content, account_content
routes_generated = (project_dir / 'src/router/generated/routes.generated.ts').read_text(encoding='utf-8')
assert '/about' in routes_generated, routes_generated
assert '/contact' in routes_generated, routes_generated
assert '/policy' in routes_generated, routes_generated
assert '/account' in routes_generated, routes_generated
print('ok')
PY
ok_ecom_home_surface_json=true

website_check_json="$TMP_ROOT/website_check_ok.json"
AIL_CLOUD_BASE_URL=embedded://local python3 -m cli website check 'Create a company product website with a home page, features, FAQ, and contact page.' --json > "$website_check_json"
python3 - "$website_check_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
from pathlib import Path
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'website-check', payload
assert payload['support_level'] == 'Supported', payload
assert payload['website_pack'] == 'Company / Product Website Pack', payload
assert payload['expected_profile'] == 'landing', payload
assert payload['delivery_decision'] == 'supported', payload
assert payload['page_realization_mode'] == 'single_page_sections_bias', payload
assert 'sections on one main page' in payload['routing_expectation'], payload
assert '/403' in payload['route_expectation_detail'], payload
assert payload['trial_result']['status'] == 'ok', payload
assert payload['trial_result']['detected_profile'] == 'landing', payload
assert payload['trial_project_path'], payload
home_vue = (Path(payload['trial_project_path']) / 'src/views/generated/Home.vue').read_text(encoding='utf-8')
assert '>品牌官网<' in home_vue or '｜清晰介绍产品价值<' in home_vue, home_vue
assert 'CompanyProductSiteReview 官方网站' not in home_vue, home_vue
assert '"label": "产品能力"' in home_vue, home_vue
assert '"label": "客户评价"' in home_vue, home_vue
assert '"label": "联系我们"' in home_vue, home_vue
assert '产品能力' in home_vue, home_vue
assert '预约演示' in home_vue, home_vue
assert '先看适用场景' in home_vue, home_vue
assert '先把产品价值讲明白' in home_vue, home_vue
assert '先说清适合对象、关键场景和价值差异' in home_vue, home_vue
assert 'PRODUCT SITE / FIT / TRUST' in home_vue, home_vue
assert 'hero-brand-row' in home_vue, home_vue
assert 'hero-brand-mark' in home_vue, home_vue
assert '定位清楚，演示更顺' in home_vue, home_vue
assert 'hero-brand-grid' in home_vue, home_vue
assert 'hero-brand-card' in home_vue, home_vue
assert 'hero-brand-card--fit' in home_vue, home_vue
assert 'hero-brand-card--scenario' in home_vue, home_vue
assert 'hero-brand-card--next' in home_vue, home_vue
assert '01 适合对象' in home_vue, home_vue
assert '适合对象' in home_vue, home_vue
assert '产品团队 / 创业团队' in home_vue, home_vue
assert '先看是否相关' in home_vue, home_vue
assert '02 场景线索' in home_vue, home_vue
assert '场景线索' in home_vue, home_vue
assert '定位澄清 / 价值承接' in home_vue, home_vue
assert '先看问题是否成立' in home_vue, home_vue
assert '03 下一步动作' in home_vue, home_vue
assert '下一步动作' in home_vue, home_vue
assert 'FAQ / 演示 / 联系入口' in home_vue, home_vue
assert '先看怎么继续' in home_vue, home_vue
assert 'hero-copy-block' in home_vue, home_vue
assert 'hero-decision-block' in home_vue, home_vue
assert '.landing-page:not(.personal-portfolio) .landing-hero h1::after' in home_vue, home_vue
assert '.landing-page:not(.personal-portfolio) .hero-actions button:first-child::after' in home_vue, home_vue
assert '.landing-page:not(.personal-portfolio) .hero-actions .ghost::after' in home_vue, home_vue
assert '先看适用场景' in home_vue and '→' in home_vue, home_vue
assert 'hero-signal-strip' in home_vue, home_vue
assert 'hero-signal-card' in home_vue, home_vue
assert '如果你希望官网先把适合对象、价值差异和预约动作讲顺' in home_vue, home_vue
assert '为什么这类官网更容易把产品讲明白' in home_vue, home_vue
assert 'section-path-strip' in home_vue, home_vue
assert 'section-path-current' in home_vue, home_vue
assert 'section-path-next' in home_vue, home_vue
assert '01 产品介绍' in home_vue, home_vue
assert '下一步：产品能力' in home_vue, home_vue
assert '02 产品能力' in home_vue, home_vue
assert '下一步：客户评价' in home_vue, home_vue
assert '03 客户评价' in home_vue, home_vue
assert '下一步：常见问题' in home_vue, home_vue
assert '适合对象先讲透' in home_vue, home_vue
assert '关键场景更容易代入' in home_vue, home_vue
assert '这尤其适合还在持续验证定位' in home_vue, home_vue
assert '常见问题' in home_vue, home_vue
assert '04 常见问题' in home_vue, home_vue
assert '下一步：预约演示 / 联系我们' in home_vue, home_vue
assert '如果团队还在反复解释产品适合谁，官网最先应该讲清什么？' in home_vue, home_vue
assert '产品还在持续迭代，这样的官网会不会很快过时？' in home_vue, home_vue
assert '如果销售和演示还很依赖人工解释，这页实际能帮到什么？' in home_vue, home_vue
assert '如果团队还在早期阶段、客户案例不多，这样的官网也值得先上线吗？' in home_vue, home_vue
assert '定位澄清 / 首次访问承接' in home_vue, home_vue
assert '销售前置 / 演示承接' in home_vue, home_vue
assert '最稳的起点 usually 是：首页主张、产品介绍和 FAQ 用同一套判断逻辑。' in home_vue, home_vue
assert '比较理想的状态是：官网先完成第一轮解释，演示再往更具体的场景里走。' in home_vue, home_vue
assert '官网上线后，第一次来访的客户不用等到演示里才弄清我们适合什么场景' in home_vue, home_vue
assert '增长负责人 / B2B SaaS' in home_vue, home_vue
assert '演示前解释成本明显下降' in home_vue, home_vue
assert '官网开始稳定承接销售动作' in home_vue, home_vue
assert '这些反馈更像真实团队在官网上线后最先感受到的变化' in home_vue, home_vue
assert '把团队在定位、销售前置和上线准备里最常被问到的问题提前讲清' in home_vue, home_vue
assert 'quote-card' in home_vue, home_vue
assert 'TRUST SIGNAL' in home_vue, home_vue
assert 'faq-body' in home_vue, home_vue
assert 'faq-context' in home_vue, home_vue
assert 'faq-followup' in home_vue, home_vue
assert 'faq-scan-strip' in home_vue, home_vue
assert 'faq-summary-hint' in home_vue, home_vue
assert 'faq-copy-block' in home_vue, home_vue
assert 'faq-copy-label' in home_vue, home_vue
assert 'faq-followup-block' in home_vue, home_vue
assert 'faq-followup-label' in home_vue, home_vue
assert 'faq-contact-bridge' in home_vue, home_vue
assert 'faq-contact-bridge-label' in home_vue, home_vue
assert 'faq-contact-bridge-strip' in home_vue, home_vue
assert 'faq-contact-bridge-current' in home_vue, home_vue
assert 'faq-contact-bridge-next' in home_vue, home_vue
assert 'FAQ TO CONTACT' in home_vue, home_vue
assert '如果这些问题已经帮你完成一轮判断' in home_vue, home_vue
assert '带着当前判断进入预约演示 / 联系我们' in home_vue, home_vue
assert '先发阶段、目标和承接动作' in home_vue, home_vue
assert '核心判断' in home_vue, home_vue
assert '下一步建议' in home_vue, home_vue
assert '预约演示 / 联系我们' in home_vue, home_vue
assert '05 预约演示 / 联系我们' in home_vue, home_vue
assert '下一步：发送咨询信息' in home_vue, home_vue
assert 'contact-entry-bridge' in home_vue, home_vue
assert 'contact-entry-bridge-label' in home_vue, home_vue
assert 'FROM FAQ' in home_vue, home_vue
assert '如果你已经完成了适合对象、场景和 FAQ 的一轮判断' in home_vue, home_vue
assert '24 小时内回复' in home_vue, home_vue
assert '定位 / FAQ / 演示承接可拆分讨论' in home_vue, home_vue
assert '先对齐目标，再进入页面制作' in home_vue, home_vue
assert '更适合：官网重写 / 首次上线 / 预约演示前置页' in home_vue, home_vue
assert '官网重写' in home_vue, home_vue
assert '首次上线' in home_vue, home_vue
assert '预约演示前置页' in home_vue, home_vue
assert '回复节奏' in home_vue, home_vue
assert '讨论范围' in home_vue, home_vue
assert '推进方式' in home_vue, home_vue
assert 'cta-close-strip' in home_vue, home_vue
assert 'cta-close-current' in home_vue, home_vue
assert 'cta-close-next' in home_vue, home_vue
assert '01 发来当前阶段与目标' in home_vue, home_vue
assert '02 收到首页建议' in home_vue, home_vue
assert '03 再决定怎么推进' in home_vue, home_vue
assert 'contact-response-strip' in home_vue, home_vue
assert 'contact-handoff-grid' in home_vue, home_vue
assert 'contact-handoff-card' in home_vue, home_vue
assert 'intake-closure-bridge' in home_vue, home_vue
assert 'intake-closure-bridge-label' in home_vue, home_vue
assert 'intake-closure-bridge-strip' in home_vue, home_vue
assert 'intake-closure-bridge-current' in home_vue, home_vue
assert 'intake-closure-bridge-next' in home_vue, home_vue
assert 'INTAKE TO CLOSURE' in home_vue, home_vue
assert '前面已经把阶段、首页目标和承接动作收进咨询 intake' in home_vue, home_vue
assert '当前：已发阶段 / 目标 / 动作' in home_vue, home_vue
assert '下一步：确认建议与推进方式' in home_vue, home_vue
assert 'cta-note' in home_vue, home_vue
assert 'cta-capture-strip' in home_vue, home_vue
assert 'cta-success-bridge' in home_vue, home_vue
assert 'cta-success-bridge-label' in home_vue, home_vue
assert 'cta-success-bridge-strip' in home_vue, home_vue
assert 'cta-success-bridge-current' in home_vue, home_vue
assert 'cta-success-bridge-next' in home_vue, home_vue
assert 'POST SUBMIT' in home_vue, home_vue
assert '咨询已收到，接下来我们会先回一版更短的首页建议' in home_vue, home_vue
assert '已收到当前阶段与目标' in home_vue, home_vue
assert '先看首页建议' in home_vue, home_vue
assert '再决定是否继续推进' in home_vue, home_vue
assert 'cta-landing-bridge' in home_vue, home_vue
assert 'cta-landing-bridge-label' in home_vue, home_vue
assert 'cta-landing-bridge-strip' in home_vue, home_vue
assert 'cta-landing-bridge-current' in home_vue, home_vue
assert 'cta-landing-bridge-next' in home_vue, home_vue
assert 'CLOSURE TO LANDING' in home_vue, home_vue
assert '前面已经确认过建议和推进方式' in home_vue, home_vue
assert '当前：已确认建议与推进方式' in home_vue, home_vue
assert '下一步：进入最终页面落点' in home_vue, home_vue
assert 'footer-success-bridge' in home_vue, home_vue
assert 'footer-success-bridge-label' in home_vue, home_vue
assert 'footer-success-bridge-strip' in home_vue, home_vue
assert 'footer-success-bridge-current' in home_vue, home_vue
assert 'footer-success-bridge-next' in home_vue, home_vue
assert 'FINAL LANDING' in home_vue, home_vue
assert '咨询已经进入后续沟通' in home_vue, home_vue
assert '已进入后续沟通' in home_vue, home_vue
assert '继续回看产品介绍 / 客户评价' in home_vue, home_vue
assert '定位澄清' in home_vue, home_vue
assert '销售前置' in home_vue, home_vue
assert '上线准备' in home_vue, home_vue
assert '{"label": "产品能力", "target": "#features"}' in home_vue, home_vue
assert "landing-page:not(.personal-portfolio) .landing-hero" in home_vue, home_vue
assert "landing-page:not(.personal-portfolio) .hero-brand-row" in home_vue, home_vue
assert "landing-page:not(.personal-portfolio) .hero-brand-mark" in home_vue, home_vue
assert "landing-page:not(.personal-portfolio) .hero-brand-grid" in home_vue, home_vue
assert "landing-page:not(.personal-portfolio) .hero-brand-card" in home_vue, home_vue
assert "landing-page:not(.personal-portfolio) .hero-signal-card" in home_vue, home_vue
assert "landing-page:not(.personal-portfolio) .hero-actions button:first-child" in home_vue, home_vue
assert "font-size: 60px" in home_vue, home_vue
assert "min-height: 48px" in home_vue, home_vue
assert "landing-page:not(.personal-portfolio) #faq" in home_vue, home_vue
assert "landing-page:not(.personal-portfolio) .faq-scan-strip span" in home_vue, home_vue
assert "landing-page:not(.personal-portfolio) .faq-copy-block" in home_vue, home_vue
assert "landing-page:not(.personal-portfolio) .faq-followup-block" in home_vue, home_vue
assert "landing-page:not(.personal-portfolio) .faq-contact-bridge" in home_vue, home_vue
assert "landing-page:not(.personal-portfolio) .faq-contact-bridge-label" in home_vue, home_vue
assert "landing-page:not(.personal-portfolio) .contact-entry-bridge" in home_vue, home_vue
assert "landing-page:not(.personal-portfolio) .contact-entry-bridge-label" in home_vue, home_vue
assert "landing-page:not(.personal-portfolio) .contact-response-strip span" in home_vue, home_vue
assert "landing-page:not(.personal-portfolio) .contact-handoff-card" in home_vue, home_vue
assert "landing-page:not(.personal-portfolio) .intake-closure-bridge" in home_vue, home_vue
assert "landing-page:not(.personal-portfolio) .intake-closure-bridge-label" in home_vue, home_vue
assert "landing-page:not(.personal-portfolio) .cta-note" in home_vue, home_vue
assert "landing-page:not(.personal-portfolio) .cta-capture-strip span" in home_vue, home_vue
assert "landing-page:not(.personal-portfolio) .cta-success-bridge" in home_vue, home_vue
assert "landing-page:not(.personal-portfolio) .cta-success-bridge-label" in home_vue, home_vue
assert "landing-page:not(.personal-portfolio) .cta-landing-bridge" in home_vue, home_vue
assert "landing-page:not(.personal-portfolio) .cta-landing-bridge-label" in home_vue, home_vue
assert "landing-page:not(.personal-portfolio) .footer-success-bridge" in home_vue, home_vue
assert "landing-page:not(.personal-portfolio) .footer-success-bridge-label" in home_vue, home_vue
assert "font-family: 'Avenir Next Condensed'" in home_vue, home_vue
assert "landing-page:not(.personal-portfolio) .landing-section h2::before" in home_vue, home_vue
assert "linear-gradient(180deg, #38bdf8, #2563eb)" in home_vue, home_vue
assert "landing-page:not(.personal-portfolio) .landing-header nav button" in home_vue, home_vue
assert "border-top: 3px solid rgba(14,165,233,0.9)" in home_vue, home_vue
assert "landing-page:not(.personal-portfolio) .faq-item { border-left: 3px solid rgba(14,165,233,0.9); }" in home_vue, home_vue
assert "landing-page:not(.personal-portfolio) .faq-summary-hint" in home_vue, home_vue
PY
ok_website_check_json=true

website_check_out_of_scope_json="$TMP_ROOT/website_check_out_of_scope.json"
set +e
AIL_CLOUD_BASE_URL=embedded://local python3 -m cli website check '做一个带登录、后台管理和订单管理的电商平台。' --json > "$website_check_out_of_scope_json"
website_check_out_of_scope_exit=$?
set -e
python3 - "$website_check_out_of_scope_json" "$website_check_out_of_scope_exit" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
exit_code = int(sys.argv[2])
assert exit_code == 3, exit_code
assert payload['entrypoint'] == 'website-check', payload
assert payload['status'] == 'out_of_scope', payload
assert payload['support_level'] == 'Out of Scope', payload
assert payload['delivery_decision'] == 'out_of_scope', payload
assert payload['trial_result'] is None, payload
assert payload['boundary_findings'], payload
PY
ok_website_check_out_of_scope_json=true

website_check_experimental_dynamic_json="$TMP_ROOT/website_check_experimental_dynamic.json"
AIL_CLOUD_BASE_URL=embedded://local python3 -m cli website check 'Create an ecommerce storefront with product detail, cart, and checkout.' --experimental-dynamic --json > "$website_check_experimental_dynamic_json"
python3 - "$website_check_experimental_dynamic_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['entrypoint'] == 'website-check', payload
assert payload['status'] == 'experimental', payload
assert payload['support_level'] == 'Experimental', payload
assert payload['delivery_decision'] == 'experimental', payload
assert payload['experimental_dynamic_enabled'] is True, payload
assert payload['expected_profile'] == 'ecom_min', payload
assert payload['delivery_contract']['surface'] == 'experimental_dynamic_storefront', payload
assert 'product detail pages' in payload['delivery_contract']['supported_capabilities'], payload
assert 'cart views' in payload['delivery_contract']['supported_capabilities'], payload
assert 'checkout handoff pages' in payload['delivery_contract']['supported_capabilities'], payload
assert 'account login or registration' in payload['delivery_contract']['unsupported_capabilities'], payload
assert 'real payment capture' in payload['delivery_contract']['unsupported_capabilities'], payload
assert 'experimental storefront prototype' in payload['delivery_contract']['operator_positioning'], payload
assert payload['trial_result']['status'] == 'ok', payload
assert payload['trial_result']['detected_profile'] == 'ecom_min', payload
PY
ok_website_check_experimental_dynamic_json=true

writing_packs_json="$TMP_ROOT/writing_packs.json"
PYTHONPATH="$ROOT" python3 -m cli writing packs --json > "$writing_packs_json"
python3 - "$writing_packs_json" <<'PY'
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'writing-packs', payload
assert payload['available_pack_count'] == 3, payload
pack_ids = [item['pack_id'] for item in payload['packs']]
assert pack_ids == ['copy_min', 'story_min', 'book_min'], payload
PY
ok_writing_packs_json=true

writing_check_copy_json="$TMP_ROOT/writing_check_copy.json"
PYTHONPATH="$ROOT" python3 -m cli writing check '写一个企业产品宣传文案，包含首页主标题、卖点和 CTA。' --json > "$writing_check_copy_json"
python3 - "$writing_check_copy_json" <<'PY'
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'writing-check', payload
assert payload['writing_pack'] == 'Copy / Messaging Pack', payload
assert payload['support_level'] == 'Supported', payload
assert payload['expected_profile'] == 'copy_min', payload
assert payload['writing_contract']['surface'] == 'structured_copy_scaffold', payload
assert 'landing-page copy blocks' in payload['writing_contract']['supported_capabilities'], payload
PY
ok_writing_check_copy_json=true

writing_check_story_json="$TMP_ROOT/writing_check_story.json"
PYTHONPATH="$ROOT" python3 -m cli writing check '写一个长篇奇幻小说提纲和角色设定，包含主要冲突和章节结构。' --json > "$writing_check_story_json"
python3 - "$writing_check_story_json" <<'PY'
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['writing_pack'] == 'Story / Fiction Outline Pack', payload
assert payload['expected_profile'] == 'story_min', payload
assert payload['writing_contract']['surface'] == 'story_outline_scaffold', payload
assert 'chapter or scene skeletons' in payload['writing_contract']['supported_capabilities'], payload
PY
ok_writing_check_story_json=true

writing_check_book_json="$TMP_ROOT/writing_check_book.json"
PYTHONPATH="$ROOT" python3 -m cli writing check '写一本非虚构商业书目录和章节目标，帮助创业者搭建销售系统。' --json > "$writing_check_book_json"
python3 - "$writing_check_book_json" <<'PY'
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['writing_pack'] == 'Book / Nonfiction Blueprint Pack', payload
assert payload['expected_profile'] == 'book_min', payload
assert payload['writing_contract']['surface'] == 'book_blueprint_scaffold', payload
assert 'table of contents design' in payload['writing_contract']['supported_capabilities'], payload
PY
ok_writing_check_book_json=true

writing_scaffold_copy_json="$TMP_ROOT/writing_scaffold_copy.json"
PYTHONPATH="$ROOT" python3 -m cli writing scaffold '写一个企业产品宣传文案，包含首页主标题、卖点和 CTA。' --json > "$writing_scaffold_copy_json"
python3 - "$writing_scaffold_copy_json" <<'PY'
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'writing-scaffold', payload
assert payload['scaffold_surface'] == 'copy_message_hierarchy', payload
assert payload['scaffold']['headline'], payload
assert payload['scaffold']['message_architecture']['cta_direction'], payload
assert len(payload['scaffold']['sections']) >= 4, payload
PY
ok_writing_scaffold_copy_json=true

writing_scaffold_story_json="$TMP_ROOT/writing_scaffold_story.json"
PYTHONPATH="$ROOT" python3 -m cli writing scaffold '写一个长篇奇幻小说提纲和角色设定，包含主要冲突和章节结构。' --json > "$writing_scaffold_story_json"
python3 - "$writing_scaffold_story_json" <<'PY'
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'writing-scaffold', payload
assert payload['scaffold_surface'] == 'story_outline_architecture', payload
assert payload['scaffold']['working_title'], payload
assert len(payload['scaffold']['character_cards']) == 3, payload
assert len(payload['scaffold']['chapter_tree']) == 5, payload
PY
ok_writing_scaffold_story_json=true

writing_scaffold_book_json="$TMP_ROOT/writing_scaffold_book.json"
PYTHONPATH="$ROOT" python3 -m cli writing scaffold '写一本非虚构商业书目录和章节目标，帮助创业者搭建销售系统。' --json > "$writing_scaffold_book_json"
python3 - "$writing_scaffold_book_json" <<'PY'
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'writing-scaffold', payload
assert payload['scaffold_surface'] == 'book_blueprint_architecture', payload
assert payload['scaffold']['book_title'], payload
assert len(payload['scaffold']['table_of_contents']) == 5, payload
assert len(payload['scaffold']['chapter_cards']) == 5, payload
PY
ok_writing_scaffold_book_json=true

writing_intent_write_json="$TMP_ROOT/writing_intent_write.json"
PYTHONPATH="$ROOT" python3 -m cli writing intent \
  --audience "indie founders" \
  --format-mode "story" \
  --genre "science fantasy" \
  --style-direction "clear cinematic" \
  --localization-mode "english_only" \
  --target-length "chapter_outline" \
  --style-keyword "visual" \
  --style-keyword "structured" \
  --tone-keyword "calm" \
  --tone-keyword "tense" \
  --narrative-constraint "limited point of view" \
  --narrative-constraint "no time travel" \
  --notes "Keep scene objectives obvious." \
  --json > "$writing_intent_write_json"
python3 - "$writing_intent_write_json" <<'PY'
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'writing-intent', payload
assert payload['action'] == 'write', payload
intent = payload['writing_intent']
assert intent['audience'] == 'indie founders', payload
assert intent['format_mode'] == 'story', payload
assert intent['genre'] == 'science fantasy', payload
assert intent['style_direction'] == 'clear cinematic', payload
assert intent['localization_mode'] == 'english_only', payload
assert intent['target_length'] == 'chapter_outline', payload
assert intent['style_keywords'] == ['visual', 'structured'], payload
assert intent['tone_keywords'] == ['calm', 'tense'], payload
assert intent['narrative_constraints'] == ['limited point of view', 'no time travel'], payload
assert intent['notes'] == 'Keep scene objectives obvious.', payload
PY
ok_writing_intent_write_json=true

writing_intent_read_json="$TMP_ROOT/writing_intent_read.json"
PYTHONPATH="$ROOT" python3 -m cli writing intent --json > "$writing_intent_read_json"
python3 - "$writing_intent_read_json" <<'PY'
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'writing-intent', payload
assert payload['action'] == 'read', payload
assert payload['writing_intent']['genre'] == 'science fantasy', payload
assert payload['writing_intent']['style_keywords'] == ['visual', 'structured'], payload
PY
ok_writing_intent_read_json=true

writing_brief_json="$TMP_ROOT/writing_brief.json"
PYTHONPATH="$ROOT" python3 -m cli writing brief '写一个长篇奇幻小说提纲和角色设定，包含主要冲突和章节结构。' --json > "$writing_brief_json"
python3 - "$writing_brief_json" <<'PY'
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'writing-brief', payload
assert payload['brief_mode'] == 'architecture_first_writing_handoff', payload
assert payload['writing_pack'] == 'Story / Fiction Outline Pack', payload
assert payload['scaffold_summary']['scaffold_surface'] == 'story_outline_architecture', payload
assert payload['source_commands']['writing_intent'].endswith('python3 -m cli writing intent --json'), payload
assert payload['source_commands']['writing_check'].endswith("python3 -m cli writing check '写一个长篇奇幻小说提纲和角色设定，包含主要冲突和章节结构。' --json"), payload
assert payload['source_commands']['writing_scaffold'].endswith("python3 -m cli writing scaffold '写一个长篇奇幻小说提纲和角色设定，包含主要冲突和章节结构。' --json"), payload
assert 'You are continuing a writing task from an AIL Builder low-token scaffold.' in payload['model_prompt'], payload
assert 'science fantasy' in payload['model_prompt'], payload
assert 'chapter_tree' in payload['model_prompt'], payload
PY
ok_writing_brief_json=true

writing_brief_emit_prompt_txt="$TMP_ROOT/writing_brief_emit_prompt.txt"
PYTHONPATH="$ROOT" python3 -m cli writing brief '写一个长篇奇幻小说提纲和角色设定，包含主要冲突和章节结构。' --emit-prompt > "$writing_brief_emit_prompt_txt"
grep -q "^You are continuing a writing task from an AIL Builder low-token scaffold\\.$" "$writing_brief_emit_prompt_txt"
grep -q "^Current writing intent:$" "$writing_brief_emit_prompt_txt"
grep -q "science fantasy" "$writing_brief_emit_prompt_txt"
grep -q "^Scaffold summary:$" "$writing_brief_emit_prompt_txt"
ok_writing_brief_emit_prompt_txt=true

writing_expand_copy_json="$TMP_ROOT/writing_expand_copy.json"
PYTHONPATH="$ROOT" python3 -m cli writing expand '写一个企业产品宣传文案，包含首页主标题、卖点和 CTA。' --json > "$writing_expand_copy_json"
python3 - "$writing_expand_copy_json" <<'PY'
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'writing-expand', payload
assert payload['expand_mode'] == 'first_draft_pass', payload
assert payload['writing_pack'] == 'Copy / Messaging Pack', payload
assert payload['expanded_unit_count'] == 3, payload
assert 'Help' in payload['expanded_text'], payload
assert payload['expanded_units'][0]['label'] == 'hero_draft', payload
PY
ok_writing_expand_copy_json=true

writing_expand_story_json="$TMP_ROOT/writing_expand_story.json"
PYTHONPATH="$ROOT" python3 -m cli writing expand '写一个长篇奇幻小说提纲和角色设定，包含主要冲突和章节结构。' --json > "$writing_expand_story_json"
python3 - "$writing_expand_story_json" <<'PY'
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'writing-expand', payload
assert payload['expand_mode'] == 'first_draft_pass', payload
assert payload['writing_pack'] == 'Story / Fiction Outline Pack', payload
assert payload['expanded_unit_count'] == 3, payload
assert 'Opening scene' in payload['expanded_text'], payload
assert payload['expanded_units'][0]['label'] == 'opening_scene_draft', payload
PY
ok_writing_expand_story_json=true

writing_expand_book_json="$TMP_ROOT/writing_expand_book.json"
PYTHONPATH="$ROOT" python3 -m cli writing expand '写一本非虚构商业书目录和章节目标，帮助创业者搭建销售系统。' --json > "$writing_expand_book_json"
python3 - "$writing_expand_book_json" <<'PY'
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'writing-expand', payload
assert payload['expand_mode'] == 'first_draft_pass', payload
assert payload['writing_pack'] == 'Book / Nonfiction Blueprint Pack', payload
assert payload['expanded_unit_count'] == 3, payload
assert 'Book introduction:' in payload['expanded_text'], payload
assert payload['expanded_units'][0]['label'] == 'intro_draft', payload
PY
ok_writing_expand_book_json=true

writing_expand_emit_text_txt="$TMP_ROOT/writing_expand_emit_text.txt"
PYTHONPATH="$ROOT" python3 -m cli writing expand '写一个长篇奇幻小说提纲和角色设定，包含主要冲突和章节结构。' --emit-text > "$writing_expand_emit_text_txt"
grep -q "^Opening scene, disruption:$" "$writing_expand_emit_text_txt"
grep -q "^Character motion:$" "$writing_expand_emit_text_txt"
ok_writing_expand_emit_text_txt=true

website_assets_json="$TMP_ROOT/website_assets.json"
python3 -m cli website assets --json > "$website_assets_json"
python3 - "$website_assets_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'website-assets', payload
assert payload['asset_scope'] == 'summary', payload
assert 'company_product' in payload['available_pack_ids'], payload
assert 'personal_independent' in payload['available_pack_ids'], payload
assert 'blog_style_partial' in payload['available_pack_ids'], payload
assert 'ecom_storefront' not in payload['available_pack_ids'], payload
assert 'after_sales' not in payload['available_pack_ids'], payload
assert 'Only static presentation-style website packs' in payload['public_surface_note'], payload
assert payload['summary']['status'] == 'ok', payload
PY
ok_website_assets_json=true

website_assets_experimental_dynamic_json="$TMP_ROOT/website_assets_experimental_dynamic.json"
python3 -m cli website assets --experimental-dynamic --json > "$website_assets_experimental_dynamic_json"
python3 - "$website_assets_experimental_dynamic_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['experimental_dynamic_enabled'] is True, payload
assert 'company_product' in payload['available_pack_ids'], payload
assert 'personal_independent' in payload['available_pack_ids'], payload
assert 'blog_style_partial' in payload['available_pack_ids'], payload
assert 'ecom_storefront' in payload['available_pack_ids'], payload
assert 'after_sales' in payload['available_pack_ids'], payload
assert 'Experimental ecommerce and after-sales packs are included' in payload['public_surface_note'], payload
PY
ok_website_assets_experimental_dynamic_json=true

website_assets_pack_json="$TMP_ROOT/website_assets_pack.json"
python3 -m cli website assets company_product --json > "$website_assets_pack_json"
python3 - "$website_assets_pack_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'website-assets', payload
assert payload['asset_scope'] == 'pack', payload
assert payload['requested_pack_id'] == 'company_product', payload
assert payload['selected_pack']['pack'] == 'Company / Product Website Pack', payload
assert payload['selected_payload']['expected_profile'] == 'landing', payload
assert payload['selected_payload']['validated_behavior']['project_go_route'] == 'project_continue_diagnose_compile_sync', payload
PY
ok_website_assets_pack_json=true

website_open_asset_json="$TMP_ROOT/website_open_asset.json"
python3 -m cli website open-asset --json > "$website_open_asset_json"
python3 - "$website_open_asset_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'website-open-asset', payload
assert payload['asset_scope'] == 'summary', payload
assert payload['resolved_label'] == 'website_assets_summary_md', payload
assert payload['target']['kind'] == 'file', payload
PY
ok_website_open_asset_json=true

website_open_asset_pack_json="$TMP_ROOT/website_open_asset_pack.json"
python3 -m cli website open-asset company_product --json > "$website_open_asset_pack_json"
python3 - "$website_open_asset_pack_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'website-open-asset', payload
assert payload['asset_scope'] == 'pack', payload
assert payload['requested_pack_id'] == 'company_product', payload
assert payload['target']['kind'] == 'file', payload
assert payload['target']['path'].endswith('company_product.json'), payload
PY
ok_website_open_asset_pack_json=true

website_inspect_asset_json="$TMP_ROOT/website_inspect_asset.json"
python3 -m cli website inspect-asset --json > "$website_inspect_asset_json"
python3 - "$website_inspect_asset_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'website-inspect-asset', payload
assert payload['asset_scope'] == 'summary', payload
assert payload['resolved_label'] == 'website_assets_summary_md', payload
assert payload['inspection']['kind'] == 'file', payload
assert payload['inspection']['exists'] is True, payload
PY
ok_website_inspect_asset_json=true

website_inspect_asset_pack_json="$TMP_ROOT/website_inspect_asset_pack.json"
python3 -m cli website inspect-asset company_product --json > "$website_inspect_asset_pack_json"
python3 - "$website_inspect_asset_pack_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'website-inspect-asset', payload
assert payload['asset_scope'] == 'pack', payload
assert payload['requested_pack_id'] == 'company_product', payload
assert payload['resolved_label'] == 'company_product_json_asset', payload
assert payload['inspection']['kind'] == 'file', payload
assert payload['inspection']['exists'] is True, payload
PY
ok_website_inspect_asset_pack_json=true

website_preview_json="$TMP_ROOT/website_preview.json"
python3 -m cli website preview --json > "$website_preview_json"
python3 - "$website_preview_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'website-preview', payload
assert payload['asset_scope'] == 'summary', payload
assert payload['preview_handoff']['status'] == 'ok', payload
assert payload['preview_handoff']['consumption_kind'] == 'website', payload
assert payload['primary_target_label'] == 'website_assets_summary_md', payload
assert payload['website_preview_summary']['surface_kind'] == 'website_frontier', payload
PY
ok_website_preview_json=true

website_preview_pack_json="$TMP_ROOT/website_preview_pack.json"
python3 -m cli website preview company_product --json > "$website_preview_pack_json"
python3 - "$website_preview_pack_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'website-preview', payload
assert payload['asset_scope'] == 'pack', payload
assert payload['requested_pack_id'] == 'company_product', payload
assert payload['preview_handoff']['status'] == 'ok', payload
assert payload['primary_target_label'] == 'company_product_json_asset', payload
assert payload['website_preview_summary']['surface_kind'] == 'website_pack', payload
PY
ok_website_preview_pack_json=true

website_run_inspect_command_json="$TMP_ROOT/website_run_inspect_command.json"
python3 -m cli website run-inspect-command --json > "$website_run_inspect_command_json"
python3 - "$website_run_inspect_command_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'website-run-inspect-command', payload
assert payload['route_taken'] == 'website_inspect_asset', payload
assert payload['asset_scope'] == 'summary', payload
assert payload['resolved_label'] == 'website_assets_summary_md', payload
assert payload['inspection']['kind'] == 'file', payload
PY
ok_website_run_inspect_command_json=true

website_run_inspect_command_pack_json="$TMP_ROOT/website_run_inspect_command_pack.json"
python3 -m cli website run-inspect-command company_product --json > "$website_run_inspect_command_pack_json"
python3 - "$website_run_inspect_command_pack_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'website-run-inspect-command', payload
assert payload['route_taken'] == 'website_inspect_asset', payload
assert payload['asset_scope'] == 'pack', payload
assert payload['requested_pack_id'] == 'company_product', payload
assert payload['resolved_label'] == 'company_product_json_asset', payload
assert payload['inspection']['kind'] == 'file', payload
PY
ok_website_run_inspect_command_pack_json=true

website_export_handoff_json="$TMP_ROOT/website_export_handoff.json"
python3 -m cli website export-handoff --json > "$website_export_handoff_json"
python3 - "$website_export_handoff_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'website-export-handoff', payload
assert payload['asset_scope'] == 'summary', payload
assert payload['primary_target_label'] == 'website_assets_summary_md', payload
assert payload['primary_inspection']['kind'] == 'file', payload
assert payload['website_summary']['entrypoint'] == 'website-summary', payload
PY
ok_website_export_handoff_json=true

website_export_handoff_pack_json="$TMP_ROOT/website_export_handoff_pack.json"
python3 -m cli website export-handoff company_product --json > "$website_export_handoff_pack_json"
python3 - "$website_export_handoff_pack_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'website-export-handoff', payload
assert payload['asset_scope'] == 'pack', payload
assert payload['requested_pack_id'] == 'company_product', payload
assert payload['primary_target_label'] == 'company_product_json_asset', payload
assert payload['selected_pack']['pack'] == 'Company / Product Website Pack', payload
assert payload['primary_inspection']['kind'] == 'file', payload
PY
ok_website_export_handoff_pack_json=true

website_summary_json="$TMP_ROOT/website_summary.json"
python3 -m cli website summary --json > "$website_summary_json"
python3 - "$website_summary_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'website-summary', payload
assert payload['supported_pack_count'] == 2, payload
assert payload['partial_pack_count'] == 1, payload
assert payload['assets']['status'] == 'ok', payload
assert 'Only static presentation-style website packs' in payload['assets']['public_surface_note'], payload
assert payload['delivery_validation']['status'] == 'ok', payload
assert payload['demo_pack_run']['status'] == 'ok', payload
assert payload['recommended_website_action'] == 'website_assets', payload
PY
ok_website_summary_json=true

website_go_json="$TMP_ROOT/website_go.json"
python3 -m cli website go --json > "$website_go_json"
python3 - "$website_go_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'website-go', payload
assert payload['route_taken'] == 'website_assets', payload
assert payload['executed_website_action'] == 'website_assets', payload
assert payload['result']['entrypoint'] == 'website-assets', payload
assert payload['result']['asset_scope'] == 'summary', payload
PY
ok_website_go_json=true

sync_json="$TMP_ROOT/sync_ok.json"
python3 -m cli sync --json > "$sync_json"
python3 - "$sync_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['written'] >= 1, payload
assert 'manifest_path' in payload, payload
PY
ok_sync_json=true

project_check_json="$TMP_ROOT/project_check_ok.json"
AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project check --json > "$project_check_json"
python3 - "$project_check_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
checks = payload['checks']
assert checks['source_exists'] is True, payload
assert checks['manifest_exists'] is True, payload
assert checks['last_build_exists'] is True, payload
assert checks['cloud_status_available'] is True, payload
assert checks['ready_for_sync'] is True, payload
assert payload['cloud_status']['status'] == 'ok', payload
PY
ok_project_check_json=true

project_summary_json="$TMP_ROOT/project_summary_ok.json"
AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project summary --json > "$project_summary_json"
python3 - "$project_summary_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['recommended_primary_action'] in {
    'project_continue_diagnose_compile_sync',
    'project_doctor_apply_safe_fixes_and_continue',
    'project_doctor',
    'project_doctor_apply_safe_fixes',
}, payload
assert payload['recommended_primary_command'].startswith('PYTHONPATH='), payload
assert payload['recommended_primary_reason'], payload
assert payload['project_check']['status'] == 'ok', payload
assert payload['cloud_status']['status'] == 'ok', payload
assert payload['preview_handoff']['status'] == 'ok', payload
assert payload['preview_handoff']['primary_target']['label'] == 'artifact_root', payload
assert payload['preview_handoff']['consumption_kind'] == 'website', payload
assert payload['preview_handoff']['open_targets'][0]['label'] == 'artifact_root', payload
assert payload['preview_handoff']['open_targets'][0]['display_name'] == 'Website Output Root', payload
assert payload['preview_handoff']['open_targets'][1]['label'] == 'generated_views_dir', payload
PY
ok_project_summary_json=true

project_hooks_json="$TMP_ROOT/project_hooks_ok.json"
(
  cd "$single_page_project_dir"
  PYTHONPATH="$ROOT" AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project hooks --json > "$project_hooks_json"
)
python3 - "$project_hooks_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'warning', payload
assert payload['entrypoint'] == 'project-hooks', payload
assert payload['hook_catalog']['exists'] is False, payload
assert payload['hook_catalog']['page_count'] == 0, payload
assert payload['message'], payload
assert any(step.startswith('inspect ') for step in payload['next_steps']), payload
PY
ok_project_hooks_json=true

project_hooks_home_json="$TMP_ROOT/project_hooks_home_ok.json"
(
  cd "$single_page_project_dir"
  PYTHONPATH="$ROOT" AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project hooks home --json > "$project_hooks_home_json"
)
python3 - "$project_hooks_home_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'warning', payload
assert payload['requested_page_key'] == 'home', payload
assert payload['hook_catalog']['exists'] is False, payload
assert payload['message'], payload
PY
ok_project_hooks_home_json=true

hook_example_project_dir="$(mktemp -d /tmp/ail_cli_smoke_hook_example.XXXXXX)"
cp -R "$ROOT"/output_projects/HookExampleGenerated/. "$hook_example_project_dir"/
rm -f "$hook_example_project_dir/frontend/src/ail-overrides/components/page.home.before.vue"
rm -f "$hook_example_project_dir/frontend/src/ail-overrides/components/page.home.section.hero.after.html"

project_hook_guide_repo_json="$TMP_ROOT/project_hook_guide_repo.json"
(
  cd "$hook_example_project_dir"
  PYTHONPATH="$ROOT" AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project hook-guide --json > "$project_hook_guide_repo_json"
)
python3 - "$project_hook_guide_repo_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'project-hook-guide', payload
assert payload['recommended_page_key'] == 'home', payload
assert payload['recommended_hook_name'] == 'home.before', payload
assert payload['recommended_suggest_command'].endswith('python3 -m cli project hook-init home --suggest --page-key home --json'), payload
assert payload['recommended_dry_run_command'].endswith('python3 -m cli project hook-init home.before --dry-run --json'), payload
assert payload['recommended_explain_command'].endswith('python3 -m cli project hook-init home.before --dry-run --explain'), payload
assert payload['cheat_sheet_path'].endswith('CUSTOMIZATION_UX_OPERATOR_CHEAT_SHEET_20260406.md'), payload
assert len(payload['guide_sections']) >= 4, payload
PY
ok_project_hook_guide_repo_json=true

project_hook_guide_emit_shell_repo_txt="$TMP_ROOT/project_hook_guide_emit_shell_repo.txt"
(
  cd "$hook_example_project_dir"
  PYTHONPATH="$ROOT" AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project hook-guide --emit-shell > "$project_hook_guide_emit_shell_repo_txt"
)
grep -q "^PYTHONPATH=${ROOT} python3 -m cli project hook-init home.before --dry-run --explain$" "$project_hook_guide_emit_shell_repo_txt"
ok_project_hook_guide_emit_shell_repo=true

project_hook_guide_copy_command_repo_txt="$TMP_ROOT/project_hook_guide_copy_command_repo.txt"
(
  cd "$hook_example_project_dir"
  PYTHONPATH="$ROOT" AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project hook-guide --copy-command > "$project_hook_guide_copy_command_repo_txt"
  copied_project_hook_guide_command="$(pbpaste)"
  printf '%s\n' "$copied_project_hook_guide_command" > "$TMP_ROOT/project_hook_guide_copy_command_repo_pbpaste.txt"
)
grep -q "^Project hook-guide command copied$" "$project_hook_guide_copy_command_repo_txt"
grep -q "^- copied_command: PYTHONPATH=${ROOT} python3 -m cli project hook-init home.before --dry-run --explain$" "$project_hook_guide_copy_command_repo_txt"
grep -q "^PYTHONPATH=${ROOT} python3 -m cli project hook-init home.before --dry-run --explain$" "$TMP_ROOT/project_hook_guide_copy_command_repo_pbpaste.txt"
ok_project_hook_guide_copy_command_repo=true

project_hook_guide_run_command_repo_json="$TMP_ROOT/project_hook_guide_run_command_repo.json"
(
  cd "$hook_example_project_dir"
  PYTHONPATH="$ROOT" AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project hook-guide --run-command --json > "$project_hook_guide_run_command_repo_json"
)
python3 - "$project_hook_guide_run_command_repo_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['entrypoint'] == 'project-hook-guide', payload
assert payload['run_command'] == f'PYTHONPATH={ROOT} python3 -m cli project hook-init home --suggest --page-key home --json', payload
assert payload['run_command_requires_confirmation'] is True, payload
assert payload['run_command_confirmed'] is False, payload
assert payload['run_command_confirm_command'] == f'PYTHONPATH={ROOT} python3 -m cli project hook-guide --run-command --yes --json', payload
PY
ok_project_hook_guide_run_command_repo=true

project_hook_guide_run_command_yes_repo_json="$TMP_ROOT/project_hook_guide_run_command_yes_repo.json"
(
  cd "$hook_example_project_dir"
  PYTHONPATH="$ROOT" AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project hook-guide --run-command --yes --json > "$project_hook_guide_run_command_yes_repo_json"
)
python3 - "$project_hook_guide_run_command_yes_repo_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['entrypoint'] == 'project-hook-guide', payload
assert payload['run_command_confirmed'] is True, payload
assert payload['ran_command'] is True, payload
assert payload['run_command_exit_code'] == 0, payload
assert payload['run_result']['entrypoint'] == 'project-hook-suggest', payload
assert payload['run_result']['requested_hook_name'] == 'home', payload
PY
ok_project_hook_guide_run_command_yes_repo=true

project_hook_init_text_compact_repo_txt="$TMP_ROOT/project_hook_init_text_compact_repo.txt"
(
  cd "$hook_example_project_dir"
  PYTHONPATH="$ROOT" AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project hook-init home.before --dry-run --text-compact > "$project_hook_init_text_compact_repo_txt" || true
)
grep -q "^Project hook-init compact$" "$project_hook_init_text_compact_repo_txt"
grep -q "^- hook_name: page.home.before$" "$project_hook_init_text_compact_repo_txt"
grep -q "^- target_relative_path: frontend/src/ail-overrides/components/page.home.before.vue$" "$project_hook_init_text_compact_repo_txt"
grep -q "^- target_reason: " "$project_hook_init_text_compact_repo_txt"
grep -q "^- runnable_next_command: PYTHONPATH=${ROOT} python3 -m cli project hook-init page.home.before --json$" "$project_hook_init_text_compact_repo_txt"
ok_project_hook_init_text_compact_repo=true

project_hook_init_explain_repo_txt="$TMP_ROOT/project_hook_init_explain_repo.txt"
(
  cd "$hook_example_project_dir"
  PYTHONPATH="$ROOT" AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project hook-init home.before --dry-run --explain > "$project_hook_init_explain_repo_txt" || true
)
grep -q "^Project hook-init explain$" "$project_hook_init_explain_repo_txt"
grep -q "^- runnable_next_command: PYTHONPATH=${ROOT} python3 -m cli project hook-init page.home.before --json$" "$project_hook_init_explain_repo_txt"
grep -q "^- message: Dry run only. No hook file was written.$" "$project_hook_init_explain_repo_txt"
grep -q "^- selection: " "$project_hook_init_explain_repo_txt"
grep -q "^- template: " "$project_hook_init_explain_repo_txt"
grep -q "^- target: " "$project_hook_init_explain_repo_txt"
grep -q "^- followup: " "$project_hook_init_explain_repo_txt"
ok_project_hook_init_explain_repo=true

project_hook_init_emit_shell_repo_txt="$TMP_ROOT/project_hook_init_emit_shell_repo.txt"
(
  cd "$hook_example_project_dir"
  PYTHONPATH="$ROOT" AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project hook-init home.before --dry-run --emit-shell > "$project_hook_init_emit_shell_repo_txt"
)
grep -q "^PYTHONPATH=${ROOT} python3 -m cli project hook-init page.home.before --json$" "$project_hook_init_emit_shell_repo_txt"
ok_project_hook_init_emit_shell_repo=true

project_hook_init_copy_command_repo_txt="$TMP_ROOT/project_hook_init_copy_command_repo.txt"
(
  cd "$hook_example_project_dir"
  PYTHONPATH="$ROOT" AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project hook-init home.before --dry-run --copy-command > "$project_hook_init_copy_command_repo_txt"
  copied_project_hook_init_command="$(pbpaste)"
  printf '%s\n' "$copied_project_hook_init_command" > "$TMP_ROOT/project_hook_init_copy_command_repo_pbpaste.txt"
)
grep -q "^Project hook-init next command copied$" "$project_hook_init_copy_command_repo_txt"
grep -q "^- copied_command: PYTHONPATH=${ROOT} python3 -m cli project hook-init page.home.before --json$" "$project_hook_init_copy_command_repo_txt"
grep -q "^PYTHONPATH=${ROOT} python3 -m cli project hook-init page.home.before --json$" "$TMP_ROOT/project_hook_init_copy_command_repo_pbpaste.txt"
ok_project_hook_init_copy_command_repo=true

project_hook_init_emit_confirm_shell_repo_txt="$TMP_ROOT/project_hook_init_emit_confirm_shell_repo.txt"
(
  cd "$hook_example_project_dir"
  PYTHONPATH="$ROOT" AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project hook-init home.before --dry-run --emit-confirm-shell > "$project_hook_init_emit_confirm_shell_repo_txt"
)
grep -q "^PYTHONPATH=${ROOT} python3 -m cli project hook-init page.home.before --json$" "$project_hook_init_emit_confirm_shell_repo_txt"
ok_project_hook_init_emit_confirm_shell_repo=true

project_hook_init_copy_confirm_command_repo_txt="$TMP_ROOT/project_hook_init_copy_confirm_command_repo.txt"
(
  cd "$hook_example_project_dir"
  PYTHONPATH="$ROOT" AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project hook-init home.before --dry-run --copy-confirm-command > "$project_hook_init_copy_confirm_command_repo_txt"
  copied_project_hook_init_confirm="$(pbpaste)"
  printf '%s\n' "$copied_project_hook_init_confirm" > "$TMP_ROOT/project_hook_init_copy_confirm_command_repo_pbpaste.txt"
)
grep -q "^Project hook-init confirm command copied$" "$project_hook_init_copy_confirm_command_repo_txt"
grep -q "^- copied_confirm_command: PYTHONPATH=${ROOT} python3 -m cli project hook-init page.home.before --json$" "$project_hook_init_copy_confirm_command_repo_txt"
grep -q "^PYTHONPATH=${ROOT} python3 -m cli project hook-init page.home.before --json$" "$TMP_ROOT/project_hook_init_copy_confirm_command_repo_pbpaste.txt"
ok_project_hook_init_copy_confirm_command_repo=true

project_hook_init_emit_target_path_repo_txt="$TMP_ROOT/project_hook_init_emit_target_path_repo.txt"
(
  cd "$hook_example_project_dir"
  PYTHONPATH="$ROOT" AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project hook-init home.before --dry-run --emit-target-path > "$project_hook_init_emit_target_path_repo_txt"
)
grep -q "/frontend/src/ail-overrides/components/page.home.before.vue$" "$project_hook_init_emit_target_path_repo_txt"
ok_project_hook_init_emit_target_path_repo=true

project_hook_init_copy_target_path_repo_txt="$TMP_ROOT/project_hook_init_copy_target_path_repo.txt"
(
  cd "$hook_example_project_dir"
  PYTHONPATH="$ROOT" AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project hook-init home.before --dry-run --copy-target-path > "$project_hook_init_copy_target_path_repo_txt"
  copied_project_hook_init_target="$(pbpaste)"
  printf '%s\n' "$copied_project_hook_init_target" > "$TMP_ROOT/project_hook_init_copy_target_path_repo_pbpaste.txt"
)
grep -q "^Project hook-init target path copied$" "$project_hook_init_copy_target_path_repo_txt"
grep -q "/frontend/src/ail-overrides/components/page.home.before.vue$" "$project_hook_init_copy_target_path_repo_txt"
grep -q "/frontend/src/ail-overrides/components/page.home.before.vue$" "$TMP_ROOT/project_hook_init_copy_target_path_repo_pbpaste.txt"
ok_project_hook_init_copy_target_path_repo=true

project_hook_init_emit_target_dir_repo_txt="$TMP_ROOT/project_hook_init_emit_target_dir_repo.txt"
(
  cd "$hook_example_project_dir"
  PYTHONPATH="$ROOT" AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project hook-init home.before --dry-run --emit-target-dir > "$project_hook_init_emit_target_dir_repo_txt"
)
grep -q "/frontend/src/ail-overrides/components$" "$project_hook_init_emit_target_dir_repo_txt"
ok_project_hook_init_emit_target_dir_repo=true

project_hook_init_copy_target_dir_repo_txt="$TMP_ROOT/project_hook_init_copy_target_dir_repo.txt"
(
  cd "$hook_example_project_dir"
  PYTHONPATH="$ROOT" AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project hook-init home.before --dry-run --copy-target-dir > "$project_hook_init_copy_target_dir_repo_txt"
  copied_project_hook_init_target_dir="$(pbpaste)"
  printf '%s\n' "$copied_project_hook_init_target_dir" > "$TMP_ROOT/project_hook_init_copy_target_dir_repo_pbpaste.txt"
)
grep -q "^Project hook-init target directory copied$" "$project_hook_init_copy_target_dir_repo_txt"
grep -q "/frontend/src/ail-overrides/components$" "$project_hook_init_copy_target_dir_repo_txt"
grep -q "/frontend/src/ail-overrides/components$" "$TMP_ROOT/project_hook_init_copy_target_dir_repo_pbpaste.txt"
ok_project_hook_init_copy_target_dir_repo=true

project_hook_init_emit_target_project_root_repo_txt="$TMP_ROOT/project_hook_init_emit_target_project_root_repo.txt"
(
  cd "$hook_example_project_dir"
  PYTHONPATH="$ROOT" AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project hook-init home.before --dry-run --emit-target-project-root > "$project_hook_init_emit_target_project_root_repo_txt"
)
python3 - "$project_hook_init_emit_target_project_root_repo_txt" <<'PY'
import sys
from pathlib import Path
value = Path(open(sys.argv[1], 'r', encoding='utf-8').read().strip()).resolve()
assert value.name.startswith('ail_cli_smoke_hook_example.'), value
PY
ok_project_hook_init_emit_target_project_root_repo=true

project_hook_init_copy_target_project_root_repo_txt="$TMP_ROOT/project_hook_init_copy_target_project_root_repo.txt"
(
  cd "$hook_example_project_dir"
  PYTHONPATH="$ROOT" AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project hook-init home.before --dry-run --copy-target-project-root > "$project_hook_init_copy_target_project_root_repo_txt"
  copied_project_hook_init_target_project_root="$(pbpaste)"
  printf '%s\n' "$copied_project_hook_init_target_project_root" > "$TMP_ROOT/project_hook_init_copy_target_project_root_repo_pbpaste.txt"
)
grep -q "^Project hook-init target project root copied$" "$project_hook_init_copy_target_project_root_repo_txt"
python3 - "$TMP_ROOT/project_hook_init_copy_target_project_root_repo_pbpaste.txt" <<'PY'
import sys
from pathlib import Path
value = Path(open(sys.argv[1], 'r', encoding='utf-8').read().strip()).resolve()
assert value.name.startswith('ail_cli_smoke_hook_example.'), value
PY
ok_project_hook_init_copy_target_project_root_repo=true

project_hook_init_emit_target_project_name_repo_txt="$TMP_ROOT/project_hook_init_emit_target_project_name_repo.txt"
(
  cd "$hook_example_project_dir"
  PYTHONPATH="$ROOT" AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project hook-init home.before --dry-run --emit-target-project-name > "$project_hook_init_emit_target_project_name_repo_txt"
)
python3 - "$project_hook_init_emit_target_project_name_repo_txt" <<'PY'
import sys
value = open(sys.argv[1], 'r', encoding='utf-8').read().strip()
assert value.startswith('ail_cli_smoke_hook_example.'), value
assert '/' not in value, value
PY
ok_project_hook_init_emit_target_project_name_repo=true

project_hook_init_copy_target_project_name_repo_txt="$TMP_ROOT/project_hook_init_copy_target_project_name_repo.txt"
(
  cd "$hook_example_project_dir"
  PYTHONPATH="$ROOT" AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project hook-init home.before --dry-run --copy-target-project-name > "$project_hook_init_copy_target_project_name_repo_txt"
  copied_project_hook_init_target_project_name="$(pbpaste)"
  printf '%s\n' "$copied_project_hook_init_target_project_name" > "$TMP_ROOT/project_hook_init_copy_target_project_name_repo_pbpaste.txt"
)
grep -q "^Project hook-init target project name copied$" "$project_hook_init_copy_target_project_name_repo_txt"
python3 - "$TMP_ROOT/project_hook_init_copy_target_project_name_repo_pbpaste.txt" <<'PY'
import sys
value = open(sys.argv[1], 'r', encoding='utf-8').read().strip()
assert value.startswith('ail_cli_smoke_hook_example.'), value
assert '/' not in value, value
PY
ok_project_hook_init_copy_target_project_name_repo=true

project_hook_init_emit_target_relative_path_repo_txt="$TMP_ROOT/project_hook_init_emit_target_relative_path_repo.txt"
(
  cd "$hook_example_project_dir"
  PYTHONPATH="$ROOT" AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project hook-init home.before --dry-run --emit-target-relative-path > "$project_hook_init_emit_target_relative_path_repo_txt"
)
grep -q "^frontend/src/ail-overrides/components/page.home.before.vue$" "$project_hook_init_emit_target_relative_path_repo_txt"
ok_project_hook_init_emit_target_relative_path_repo=true

project_hook_init_copy_target_relative_path_repo_txt="$TMP_ROOT/project_hook_init_copy_target_relative_path_repo.txt"
(
  cd "$hook_example_project_dir"
  PYTHONPATH="$ROOT" AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project hook-init home.before --dry-run --copy-target-relative-path > "$project_hook_init_copy_target_relative_path_repo_txt"
  copied_project_hook_init_target_relative="$(pbpaste)"
  printf '%s\n' "$copied_project_hook_init_target_relative" > "$TMP_ROOT/project_hook_init_copy_target_relative_path_repo_pbpaste.txt"
)
grep -q "^Project hook-init target relative path copied$" "$project_hook_init_copy_target_relative_path_repo_txt"
grep -q "^- copied_target_relative_path: frontend/src/ail-overrides/components/page.home.before.vue$" "$project_hook_init_copy_target_relative_path_repo_txt"
grep -q "^frontend/src/ail-overrides/components/page.home.before.vue$" "$TMP_ROOT/project_hook_init_copy_target_relative_path_repo_pbpaste.txt"
ok_project_hook_init_copy_target_relative_path_repo=true

project_hook_init_emit_target_bundle_repo_txt="$TMP_ROOT/project_hook_init_emit_target_bundle_repo.txt"
(
  cd "$hook_example_project_dir"
  PYTHONPATH="$ROOT" AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project hook-init home.before --dry-run --emit-target-bundle > "$project_hook_init_emit_target_bundle_repo_txt"
)
python3 - "$project_hook_init_emit_target_bundle_repo_txt" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
from pathlib import Path
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['target_path'].endswith('/frontend/src/ail-overrides/components/page.home.before.vue'), payload
assert payload['target_dir'].endswith('/frontend/src/ail-overrides/components'), payload
assert payload['target_project_root'].startswith('/tmp/ail_cli_smoke_hook_example.') or payload['target_project_root'].startswith('/private/tmp/ail_cli_smoke_hook_example.'), payload
assert str(payload['target_project_name']) == Path(payload['target_project_root']).name, payload
assert payload['target_relative_path'] == 'frontend/src/ail-overrides/components/page.home.before.vue', payload
assert payload['open_command'].startswith('inspect '), payload
assert payload['confirm_command'] == f'PYTHONPATH={ROOT} python3 -m cli project hook-init page.home.before --json', payload
PY
ok_project_hook_init_emit_target_bundle_repo=true

project_hook_init_copy_target_bundle_repo_txt="$TMP_ROOT/project_hook_init_copy_target_bundle_repo.txt"
(
  cd "$hook_example_project_dir"
  PYTHONPATH="$ROOT" AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project hook-init home.before --dry-run --copy-target-bundle > "$project_hook_init_copy_target_bundle_repo_txt"
)
grep -q "^Project hook-init target bundle copied$" "$project_hook_init_copy_target_bundle_repo_txt"
grep -q "^- copied_target_bundle: {" "$project_hook_init_copy_target_bundle_repo_txt"
copied_project_hook_init_target_bundle="$(pbpaste)"
PROJECT_HOOK_INIT_COPIED_TARGET_BUNDLE="$copied_project_hook_init_target_bundle" python3 - <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, os
from pathlib import Path
payload = json.loads(os.environ['PROJECT_HOOK_INIT_COPIED_TARGET_BUNDLE'])
assert payload['target_path'].endswith('/frontend/src/ail-overrides/components/page.home.before.vue'), payload
assert payload['target_dir'].endswith('/frontend/src/ail-overrides/components'), payload
assert str(payload['target_project_name']) == Path(payload['target_project_root']).name, payload
assert payload['target_relative_path'] == 'frontend/src/ail-overrides/components/page.home.before.vue', payload
assert payload['confirm_command'] == f'PYTHONPATH={ROOT} python3 -m cli project hook-init page.home.before --json', payload
PY
ok_project_hook_init_copy_target_bundle_repo=true

project_hook_init_emit_open_shell_repo_txt="$TMP_ROOT/project_hook_init_emit_open_shell_repo.txt"
(
  cd "$hook_example_project_dir"
  PYTHONPATH="$ROOT" AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project hook-init home.before --dry-run --emit-open-shell > "$project_hook_init_emit_open_shell_repo_txt"
)
grep -q "^inspect .*/frontend/src/ail-overrides/components/page.home.before.vue$" "$project_hook_init_emit_open_shell_repo_txt"
ok_project_hook_init_emit_open_shell_repo=true

project_hook_init_copy_open_command_repo_txt="$TMP_ROOT/project_hook_init_copy_open_command_repo.txt"
(
  cd "$hook_example_project_dir"
  PYTHONPATH="$ROOT" AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project hook-init home.before --dry-run --copy-open-command > "$project_hook_init_copy_open_command_repo_txt"
  copied_project_hook_init_open_command="$(pbpaste)"
  printf '%s\n' "$copied_project_hook_init_open_command" > "$TMP_ROOT/project_hook_init_copy_open_command_repo_pbpaste.txt"
)
grep -q "^Project hook-init open command copied$" "$project_hook_init_copy_open_command_repo_txt"
grep -q "^- copied_open_command: inspect .*/frontend/src/ail-overrides/components/page.home.before.vue$" "$project_hook_init_copy_open_command_repo_txt"
grep -q "^inspect .*/frontend/src/ail-overrides/components/page.home.before.vue$" "$TMP_ROOT/project_hook_init_copy_open_command_repo_pbpaste.txt"
ok_project_hook_init_copy_open_command_repo=true

project_hook_init_run_command_repo_json="$TMP_ROOT/project_hook_init_run_command_repo.json"
(
  cd "$hook_example_project_dir"
  PYTHONPATH="$ROOT" AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project hook-init home.before --dry-run --run-command --json > "$project_hook_init_run_command_repo_json"
)
python3 - "$project_hook_init_run_command_repo_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['run_command'], payload
assert payload['run_command'] == f'PYTHONPATH={ROOT} python3 -m cli project hook-init page.home.before --json', payload
assert payload['run_command_requires_confirmation'] is True, payload
assert payload['run_command_confirmed'] is False, payload
assert payload['ran_command'] is False, payload
assert payload['run_command_exit_code'] == 0, payload
assert payload['run_command_warning'], payload
assert payload['run_command_confirm_command'], payload
assert '--run-command' in payload['run_command_confirm_command'], payload
assert '--yes' in payload['run_command_confirm_command'], payload
PY
ok_project_hook_init_run_command_repo=true

project_hook_init_run_command_yes_repo_json="$TMP_ROOT/project_hook_init_run_command_yes_repo.json"
(
  cd "$hook_example_project_dir"
  PYTHONPATH="$ROOT" AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project hook-init home.before --dry-run --run-command --yes --json > "$project_hook_init_run_command_yes_repo_json"
)
python3 - "$project_hook_init_run_command_yes_repo_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, pathlib, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['run_command_confirmed'] is True, payload
assert payload['ran_command'] is True, payload
assert payload['run_command_exit_code'] == 0, payload
result = payload['run_result']
assert result['entrypoint'] == 'project-hook-init', payload
target_path = pathlib.Path(result['target_path'])
assert target_path.name == 'page.home.before.vue', payload
assert result['hook_name'] == 'page.home.before', payload
assert result['wrote'] is True, payload
assert target_path.exists(), payload
PY
ok_project_hook_init_run_command_yes_repo=true
rm -f "$hook_example_project_dir/frontend/src/ail-overrides/components/page.home.before.vue"

project_hook_init_run_open_command_repo_json="$TMP_ROOT/project_hook_init_run_open_command_repo.json"
(
  cd "$hook_example_project_dir"
  PYTHONPATH="$ROOT" AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project hook-init home.before --dry-run --run-open-command --json > "$project_hook_init_run_open_command_repo_json"
)
python3 - "$project_hook_init_run_open_command_repo_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['run_open_command'], payload
assert payload['run_open_command'].startswith('inspect '), payload
assert payload['run_open_command_requires_confirmation'] is True, payload
assert payload['run_open_command_confirmed'] is False, payload
assert payload['ran_open_command'] is False, payload
assert payload['run_open_command_exit_code'] == 0, payload
assert payload['run_open_command_warning'], payload
assert payload['run_open_command_confirm_command'], payload
assert '--yes' in payload['run_open_command_confirm_command'], payload
PY
ok_project_hook_init_run_open_command_repo=true

project_hook_init_run_open_command_yes_repo_json="$TMP_ROOT/project_hook_init_run_open_command_yes_repo.json"
(
  cd "$hook_example_project_dir"
  PYTHONPATH="$ROOT" AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project hook-init home.before --dry-run --run-open-command --yes --json > "$project_hook_init_run_open_command_yes_repo_json"
)
python3 - "$project_hook_init_run_open_command_yes_repo_json" "$hook_example_project_dir" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, pathlib, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
project_root = pathlib.Path(sys.argv[2]).resolve()
assert payload['run_open_command'], payload
assert payload['run_open_command_confirmed'] is True, payload
assert payload['ran_open_command'] is True, payload
assert payload['run_open_command_exit_code'] == 0, payload
result = payload['run_open_result']
assert result['path'].startswith(str(project_root)), payload
assert result['exists'] is False, payload
assert result['line_count'] == 0, payload
PY
ok_project_hook_init_run_open_command_yes_repo=true

project_hook_init_inspect_target_repo_json="$TMP_ROOT/project_hook_init_inspect_target_repo.json"
(
  cd "$hook_example_project_dir"
  PYTHONPATH="$ROOT" AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project hook-init home.before --dry-run --inspect-target --json > "$project_hook_init_inspect_target_repo_json"
)
python3 - "$project_hook_init_inspect_target_repo_json" "$hook_example_project_dir" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, pathlib, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
project_root = pathlib.Path(sys.argv[2]).resolve()
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'project-hook-init', payload
assert payload['dry_run'] is True, payload
assert payload['inspect_target_summary'], payload
target_inspection = payload['target_inspection']
parent_inspection = payload['target_parent_inspection']
assert target_inspection['kind'] == 'file', payload
assert target_inspection['exists'] is False, payload
target_path = pathlib.Path(target_inspection['path']).resolve()
assert target_path.parent == (project_root / 'frontend/src/ail-overrides/components').resolve(), payload
assert parent_inspection['kind'] == 'directory', payload
assert parent_inspection['exists'] is True, payload
assert pathlib.Path(parent_inspection['path']).resolve() == target_path.parent, payload
assert parent_inspection['entry_count'] >= 1, payload
PY
ok_project_hook_init_inspect_target_repo=true

project_hook_init_inspect_target_text_compact_repo_txt="$TMP_ROOT/project_hook_init_inspect_target_text_compact_repo.txt"
(
  cd "$hook_example_project_dir"
  PYTHONPATH="$ROOT" AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project hook-init home.before --dry-run --inspect-target --text-compact > "$project_hook_init_inspect_target_text_compact_repo_txt" || true
)
grep -q "^Project hook-init compact$" "$project_hook_init_inspect_target_text_compact_repo_txt"
grep -q "^- inspect_target_summary: " "$project_hook_init_inspect_target_text_compact_repo_txt"
grep -q "^- inspect_target_parent_summary: " "$project_hook_init_inspect_target_text_compact_repo_txt"
grep -q "^- inspected_target_path: " "$project_hook_init_inspect_target_text_compact_repo_txt"
grep -q "^- inspected_target_exists: " "$project_hook_init_inspect_target_text_compact_repo_txt"
grep -q "^- nearby_entries: " "$project_hook_init_inspect_target_text_compact_repo_txt"
ok_project_hook_init_inspect_target_text_compact_repo=true

project_hook_init_open_target_repo_json="$TMP_ROOT/project_hook_init_open_target_repo.json"
(
  cd "$hook_example_project_dir"
  PYTHONPATH="$ROOT" AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project hook-init home.before --dry-run --open-target --json > "$project_hook_init_open_target_repo_json"
)
python3 - "$project_hook_init_open_target_repo_json" "$hook_example_project_dir" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, pathlib, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
project_root = pathlib.Path(sys.argv[2]).resolve()
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'project-hook-init', payload
assert payload['dry_run'] is True, payload
assert payload['open_target_summary'], payload
assert payload['open_target_reason'], payload
assert payload['open_target_command'].startswith('inspect '), payload
open_target = payload['open_target']
assert open_target['label'] == 'hook_target', payload
assert open_target['kind'] == 'file', payload
target_path = pathlib.Path(open_target['path']).resolve()
assert target_path.parent == (project_root / 'frontend/src/ail-overrides/components').resolve(), payload
assert open_target['exists'] is False, payload
assert payload['open_target_command'].endswith(str(target_path)), payload
PY
ok_project_hook_init_open_target_repo=true

project_hook_init_open_now_repo_json="$TMP_ROOT/project_hook_init_open_now_repo.json"
(
  cd "$hook_example_project_dir"
  PYTHONPATH="$ROOT" AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project hook-init home.before --dry-run --open-now --json > "$project_hook_init_open_now_repo_json"
)
python3 - "$project_hook_init_open_now_repo_json" "$hook_example_project_dir" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, pathlib, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
project_root = pathlib.Path(sys.argv[2]).resolve()
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'project-hook-init', payload
assert payload['dry_run'] is True, payload
assert payload['open_now'] is True, payload
assert payload['open_now_summary'], payload
assert payload['open_now_reason'], payload
open_now_result = payload['open_now_result']
assert open_now_result['kind'] == 'file', payload
assert open_now_result['exists'] is False, payload
target_path = pathlib.Path(open_now_result['path']).resolve()
assert target_path.parent == (project_root / 'frontend/src/ail-overrides/components').resolve(), payload
assert open_now_result['line_count'] == 0, payload
PY
ok_project_hook_init_open_now_repo=true

project_hook_init_open_now_text_compact_repo_txt="$TMP_ROOT/project_hook_init_open_now_text_compact_repo.txt"
(
  cd "$hook_example_project_dir"
  PYTHONPATH="$ROOT" AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project hook-init home.before --dry-run --open-now --text-compact > "$project_hook_init_open_now_text_compact_repo_txt" || true
)
grep -q "^Project hook-init compact$" "$project_hook_init_open_now_text_compact_repo_txt"
grep -q "^- open_now_summary: " "$project_hook_init_open_now_text_compact_repo_txt"
grep -q "^- open_now_path: " "$project_hook_init_open_now_text_compact_repo_txt"
grep -q "^- open_now_exists: " "$project_hook_init_open_now_text_compact_repo_txt"
grep -q "^- open_now_line_count: " "$project_hook_init_open_now_text_compact_repo_txt"
ok_project_hook_init_open_now_text_compact_repo=true

project_hook_init_json="$TMP_ROOT/project_hook_init_ok.json"
(
  cd "$hook_example_project_dir"
  PYTHONPATH="$ROOT" AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project hook-init home.before --json > "$project_hook_init_json"
)
python3 - "$project_hook_init_json" "$hook_example_project_dir" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
from pathlib import Path
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
project_dir = Path(sys.argv[2]).resolve()
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'project-hook-init', payload
assert payload['requested_hook_name'] == 'home.before', payload
assert payload['hook_name'] == 'page.home.before', payload
assert payload['requested_template'] == 'auto', payload
assert payload['template'] == 'vue', payload
assert payload['hook_catalog_verified'] is True, payload
target = Path(payload['target_path']).resolve()
assert target.exists(), payload
assert target == project_dir / 'frontend/src/ail-overrides/components/page.home.before.vue', payload
PY
ok_project_hook_init_json=true

project_hook_init_force_json="$TMP_ROOT/project_hook_init_force_ok.json"
(
  cd "$hook_example_project_dir"
  PYTHONPATH="$ROOT" AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project hook-init home.before --force --json > "$project_hook_init_force_json"
)
python3 - "$project_hook_init_force_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['hook_name'] == 'page.home.before', payload
assert payload['template'] == 'vue', payload
assert payload['overwritten'] is True, payload
PY
ok_project_hook_init_force_json=true

project_hook_init_suggest_json="$TMP_ROOT/project_hook_init_suggest_ok.json"
(
  cd "$hook_example_project_dir"
  PYTHONPATH="$ROOT" AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project hook-init home --suggest --json > "$project_hook_init_suggest_json"
)
python3 - "$project_hook_init_suggest_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'project-hook-suggest', payload
assert payload['requested_hook_name'] == 'home', payload
assert payload['hook_catalog']['exists'] is True, payload
assert payload['suggestions'], payload
assert payload['suggestions'][0]['suggestion_index'] == 1, payload
assert payload['suggestions'][0]['pick_index_command'], payload
assert '--pick-index 1' in payload['suggestions'][0]['pick_index_command'], payload
assert payload['suggestion_pick_examples'], payload
assert payload['recommended_pick_index_command'], payload
assert payload['recommended_next_command'], payload
assert '--pick-recommended' in payload['recommended_next_command'], payload
assert '--pick-index 1' in payload['recommended_pick_index_command'], payload
assert payload['recent_suggestion_memory_path'].endswith('/.ail/last_hook_suggestions.json'), payload
assert any(item['hook_name'] == 'page.home.before' for item in payload['suggestions']), payload
PY
ok_project_hook_init_suggest_json=true

project_hook_init_open_catalog_json="$TMP_ROOT/project_hook_init_open_catalog_ok.json"
(
  cd "$hook_example_project_dir"
  PYTHONPATH="$ROOT" AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project hook-init --open-catalog --json > "$project_hook_init_open_catalog_json"
)
python3 - "$project_hook_init_open_catalog_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'project-hook-open-catalog', payload
assert payload['hook_catalog']['exists'] is True, payload
assert payload['hook_catalog']['json_path'].endswith('/.ail/hook_catalog.json'), payload
assert any(step.startswith('inspect ') for step in payload['next_steps']), payload
PY
ok_project_hook_init_open_catalog_json=true

project_hook_init_suggest_filtered_json="$TMP_ROOT/project_hook_init_suggest_filtered_ok.json"
(
  cd "$hook_example_project_dir"
  PYTHONPATH="$ROOT" AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project hook-init home --suggest --page-key home --section-key hero --json > "$project_hook_init_suggest_filtered_json"
)
python3 - "$project_hook_init_suggest_filtered_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'project-hook-suggest', payload
assert payload['page_key_filter'] == 'home', payload
assert payload['section_key_filter'] == 'hero', payload
assert payload['suggestions'], payload
assert all(item['page_key'] == 'home' for item in payload['suggestions']), payload
assert all(item['section_key'] == 'hero' for item in payload['suggestions']), payload
PY
ok_project_hook_init_suggest_filtered_json=true

project_hook_init_suggest_slot_filtered_json="$TMP_ROOT/project_hook_init_suggest_slot_filtered_ok.json"
(
  cd "$hook_example_project_dir"
  PYTHONPATH="$ROOT" AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project hook-init home --suggest --page-key home --section-key hero --slot-key hero-actions --json > "$project_hook_init_suggest_slot_filtered_json"
)
python3 - "$project_hook_init_suggest_slot_filtered_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'project-hook-suggest', payload
assert payload['page_key_filter'] == 'home', payload
assert payload['section_key_filter'] == 'hero', payload
assert payload['slot_key_filter'] == 'hero-actions', payload
assert payload['suggestions'], payload
assert all(item['page_key'] == 'home' for item in payload['suggestions']), payload
assert all(item['section_key'] == 'hero' for item in payload['suggestions']), payload
assert all(item['slot_key'] == 'hero-actions' for item in payload['suggestions']), payload
PY
ok_project_hook_init_suggest_slot_filtered_json=true

project_hook_init_suggest_slot_only_json="$TMP_ROOT/project_hook_init_suggest_slot_only_ok.json"
(
  cd "$hook_example_project_dir"
  PYTHONPATH="$ROOT" AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project hook-init home --suggest --slot-key hero-actions --json > "$project_hook_init_suggest_slot_only_json"
)
python3 - "$project_hook_init_suggest_slot_only_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'project-hook-suggest', payload
assert payload['slot_key_filter'] == 'hero-actions', payload
assert payload['suggestions'], payload
assert payload['suggestions'][0]['suggestion_index'] == 1, payload
assert all(item['slot_key'] == 'hero-actions' for item in payload['suggestions']), payload
PY
ok_project_hook_init_suggest_slot_only_json=true

project_hook_init_pick_json="$TMP_ROOT/project_hook_init_pick_ok.json"
rm -f "$hook_example_project_dir/frontend/src/ail-overrides/components/page.home.before.vue"
(
  cd "$hook_example_project_dir"
  PYTHONPATH="$ROOT" AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project hook-init home.before --suggest --pick --json > "$project_hook_init_pick_json"
)
python3 - "$project_hook_init_pick_json" "$hook_example_project_dir" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, pathlib, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
project_root = pathlib.Path(sys.argv[2]).resolve()
expected = (project_root / 'frontend/src/ail-overrides/components/page.home.before.vue').resolve()
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'project-hook-init', payload
assert payload['requested_hook_name'] == 'home.before', payload
assert payload['hook_name'] == 'page.home.before', payload
assert payload['selected_from_suggestions'] is True, payload
assert payload['wrote'] is True, payload
assert pathlib.Path(payload['target_path']).resolve() == expected, payload
assert expected.exists(), payload
PY
ok_project_hook_init_pick_json=true

project_hook_init_pick_index_json="$TMP_ROOT/project_hook_init_pick_index_ok.json"
rm -f "$hook_example_project_dir/frontend/src/ail-overrides/components/page.home.section.hero.slot.hero-actions.before.vue"
(
  cd "$hook_example_project_dir"
  PYTHONPATH="$ROOT" AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project hook-init home --suggest --page-key home --section-key hero --slot-key hero-actions --pick-index 2 --json > "$project_hook_init_pick_index_json"
)
python3 - "$project_hook_init_pick_index_json" "$hook_example_project_dir" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, pathlib, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
project_root = pathlib.Path(sys.argv[2]).resolve()
expected = (project_root / 'frontend/src/ail-overrides/components/page.home.section.hero.slot.hero-actions.before.vue').resolve()
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'project-hook-init', payload
assert payload['requested_hook_name'] == 'home', payload
assert payload['hook_name'] == 'page.home.section.hero.slot.hero-actions.before', payload
assert payload['selected_from_suggestions'] is True, payload
assert payload['template'] == 'vue', payload
assert pathlib.Path(payload['target_path']).resolve() == expected, payload
assert expected.exists(), payload
PY
ok_project_hook_init_pick_index_json=true

project_hook_init_pick_recommended_json="$TMP_ROOT/project_hook_init_pick_recommended_ok.json"
rm -f "$hook_example_project_dir/frontend/src/ail-overrides/components/page.home.section.hero.slot.hero-actions.after.html"
(
  cd "$hook_example_project_dir"
  PYTHONPATH="$ROOT" AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project hook-init home --suggest --page-key home --section-key hero --slot-key hero-actions --pick-recommended --json > "$project_hook_init_pick_recommended_json"
)
python3 - "$project_hook_init_pick_recommended_json" "$hook_example_project_dir" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, pathlib, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
project_root = pathlib.Path(sys.argv[2]).resolve()
expected = (project_root / 'frontend/src/ail-overrides/components/page.home.section.hero.slot.hero-actions.after.html').resolve()
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'project-hook-init', payload
assert payload['requested_hook_name'] == 'home', payload
assert payload['hook_name'] == 'page.home.section.hero.slot.hero-actions.after', payload
assert payload['selected_from_suggestions'] is True, payload
assert payload['template'] == 'html', payload
assert pathlib.Path(payload['target_path']).resolve() == expected, payload
assert expected.exists(), payload
PY
ok_project_hook_init_pick_recommended_json=true

project_hook_init_recent_memory_seed_json="$TMP_ROOT/project_hook_init_recent_memory_seed_ok.json"
(
  cd "$hook_example_project_dir"
  PYTHONPATH="$ROOT" AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project hook-init home --suggest --page-key home --section-key hero --slot-key hero-actions --json > "$project_hook_init_recent_memory_seed_json"
)
project_hook_init_recent_memory_pick_json="$TMP_ROOT/project_hook_init_recent_memory_pick_ok.json"
rm -f "$hook_example_project_dir/frontend/src/ail-overrides/components/page.home.section.hero.slot.hero-actions.after.html"
(
  cd "$hook_example_project_dir"
  PYTHONPATH="$ROOT" AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project hook-init --pick-index 1 --json > "$project_hook_init_recent_memory_pick_json"
)
python3 - "$project_hook_init_recent_memory_pick_json" "$hook_example_project_dir" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, pathlib, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
project_root = pathlib.Path(sys.argv[2]).resolve()
expected = (project_root / 'frontend/src/ail-overrides/components/page.home.section.hero.slot.hero-actions.after.html').resolve()
memory_file = (project_root / '.ail/last_hook_suggestions.json').resolve()
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'project-hook-init', payload
assert payload['requested_hook_name'] == 'home', payload
assert payload['hook_name'] == 'page.home.section.hero.slot.hero-actions.after', payload
assert payload['selected_from_suggestions'] is True, payload
assert payload['used_recent_suggestion_memory'] is True, payload
assert payload['template'] == 'html', payload
assert pathlib.Path(payload['target_path']).resolve() == expected, payload
assert expected.exists(), payload
assert memory_file.exists(), payload
PY
ok_project_hook_init_recent_memory_pick_json=true

project_hook_init_reuse_last_suggest_json="$TMP_ROOT/project_hook_init_reuse_last_suggest_ok.json"
rm -f "$hook_example_project_dir/frontend/src/ail-overrides/components/page.home.section.hero.slot.hero-actions.after.html"
(
  cd "$hook_example_project_dir"
  PYTHONPATH="$ROOT" AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project hook-init --reuse-last-suggest --pick-index 1 --json > "$project_hook_init_reuse_last_suggest_json"
)
python3 - "$project_hook_init_reuse_last_suggest_json" "$hook_example_project_dir" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, pathlib, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
project_root = pathlib.Path(sys.argv[2]).resolve()
expected = (project_root / 'frontend/src/ail-overrides/components/page.home.section.hero.slot.hero-actions.after.html').resolve()
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'project-hook-init', payload
assert payload['reuse_last_suggest'] is True, payload
assert payload['used_recent_suggestion_memory'] is True, payload
assert payload['hook_name'] == 'page.home.section.hero.slot.hero-actions.after', payload
assert pathlib.Path(payload['target_path']).resolve() == expected, payload
assert expected.exists(), payload
PY
ok_project_hook_init_reuse_last_suggest_json=true

project_hook_init_last_suggest_json="$TMP_ROOT/project_hook_init_last_suggest_ok.json"
(
  cd "$hook_example_project_dir"
  PYTHONPATH="$ROOT" AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project hook-init --last-suggest --json > "$project_hook_init_last_suggest_json"
)
python3 - "$project_hook_init_last_suggest_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'project-hook-last-suggest', payload
assert payload['recent_suggestion_memory_path'].endswith('/.ail/last_hook_suggestions.json'), payload
assert payload['last_suggest']['requested_hook_name'] == 'home', payload
assert payload['last_suggest']['page_key_filter'] == 'home', payload
assert payload['last_suggest']['section_key_filter'] == 'hero', payload
assert payload['last_suggest']['slot_key_filter'] == 'hero-actions', payload
assert payload['last_suggest']['suggestion_count'] == 2, payload
assert payload['recommended_next_command'], payload
assert '--reuse-last-suggest --pick-recommended' in payload['recommended_next_command'], payload
PY
ok_project_hook_init_last_suggest_json=true

project_preview_json="$TMP_ROOT/project_preview_ok.json"
AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project preview --json > "$project_preview_json"
python3 - "$project_preview_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'project-preview', payload
assert payload['recommended_primary_action'] in {
    'project_continue_diagnose_compile_sync',
    'project_doctor_apply_safe_fixes_and_continue',
    'project_doctor',
    'project_doctor_apply_safe_fixes',
}, payload
assert payload['preview_handoff']['status'] == 'ok', payload
assert payload['preview_handoff']['primary_target']['label'] == 'artifact_root', payload
assert payload['website_preview_summary']['surface_kind'] == 'website', payload
assert payload['website_preview_summary']['generated_pages_target']['label'] == 'generated_views_dir', payload
assert payload['website_preview_summary']['generated_routes_target']['label'] == 'generated_router_dir', payload
assert payload['latest_build_id'], payload
assert payload['latest_artifact_id'], payload
assert any(step.startswith('run PYTHONPATH=') for step in payload['next_steps']), payload
PY
ok_project_preview_json=true

project_serve_dry_run_json="$TMP_ROOT/project_serve_dry_run_ok.json"
PYTHONPATH="$ROOT" python3 -m cli project serve --dry-run --json > "$project_serve_dry_run_json"
python3 - "$project_serve_dry_run_json" <<'PY'
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'project-serve', payload
assert payload['dry_run'] is True, payload
assert payload['started'] is False, payload
assert payload['frontend_root'].endswith('/frontend'), payload
assert payload['package_json'].endswith('/frontend/package.json'), payload
assert payload['local_url'] == 'http://127.0.0.1:5173', payload
assert payload['command'] == 'npm run dev -- --host 127.0.0.1 --port 5173', payload
assert any('npm run dev' in step or step == 'npm install' for step in payload['next_steps']), payload
PY
ok_project_serve_dry_run_json=true

project_open_target_json="$TMP_ROOT/project_open_target.json"
AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project open-target source_of_truth --json > "$project_open_target_json"
python3 - "$project_open_target_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'project-open-target', payload
assert payload['resolved_label'] == 'source_of_truth', payload
assert payload['target']['label'] == 'source_of_truth', payload
assert payload['target']['kind'] == 'file', payload
assert payload['target']['exists'] is True, payload
assert payload['inspect_command'].startswith('inspect '), payload
PY
ok_project_open_target_json=true

project_open_target_default_json="$TMP_ROOT/project_open_target_default.json"
AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project open-target --json > "$project_open_target_default_json"
python3 - "$project_open_target_default_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'project-open-target', payload
assert payload['resolved_label'] == payload['preview_handoff']['primary_target']['label'], payload
assert payload['target']['label'] == 'artifact_root', payload
assert payload['target']['kind'] == 'directory', payload
PY
ok_project_open_target_default_json=true

project_inspect_target_json="$TMP_ROOT/project_inspect_target.json"
AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project inspect-target source_of_truth --json > "$project_inspect_target_json"
python3 - "$project_inspect_target_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'project-inspect-target', payload
assert payload['resolved_label'] == 'source_of_truth', payload
assert payload['inspection']['kind'] == 'file', payload
assert payload['inspection']['exists'] is True, payload
assert payload['inspection']['line_count'] >= 1, payload
assert isinstance(payload['inspection']['content_preview'], str), payload
PY
ok_project_inspect_target_json=true

project_inspect_target_default_json="$TMP_ROOT/project_inspect_target_default.json"
AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project inspect-target --json > "$project_inspect_target_default_json"
python3 - "$project_inspect_target_default_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'project-inspect-target', payload
assert payload['resolved_label'] == 'artifact_root', payload
assert payload['inspection']['kind'] == 'directory', payload
assert payload['inspection']['exists'] is True, payload
assert payload['inspection']['entry_count'] >= 1, payload
PY
ok_project_inspect_target_default_json=true

project_run_inspect_command_json="$TMP_ROOT/project_run_inspect_command.json"
AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project run-inspect-command source_of_truth --json > "$project_run_inspect_command_json"
python3 - "$project_run_inspect_command_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'project-run-inspect-command', payload
assert payload['route_taken'] == 'project_inspect_target', payload
assert payload['resolved_label'] == 'source_of_truth', payload
assert payload['executed_inspect_command'].startswith('inspect '), payload
assert payload['inspection']['kind'] == 'file', payload
assert payload['result']['entrypoint'] == 'project-inspect-target', payload
PY
ok_project_run_inspect_command_json=true

project_run_inspect_command_default_json="$TMP_ROOT/project_run_inspect_command_default.json"
AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project run-inspect-command --json > "$project_run_inspect_command_default_json"
python3 - "$project_run_inspect_command_default_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'project-run-inspect-command', payload
assert payload['route_taken'] == 'project_inspect_target', payload
assert payload['resolved_label'] == 'artifact_root', payload
assert payload['inspection']['kind'] == 'directory', payload
assert payload['result']['entrypoint'] == 'project-inspect-target', payload
PY
ok_project_run_inspect_command_default_json=true

project_export_handoff_json="$TMP_ROOT/project_export_handoff.json"
AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project export-handoff --json > "$project_export_handoff_json"
python3 - "$project_export_handoff_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'project-export-handoff', payload
assert payload['primary_target_label'] == 'artifact_root', payload
assert payload['primary_target']['kind'] == 'directory', payload
assert payload['primary_inspection']['kind'] == 'directory', payload
assert payload['website_preview_summary']['surface_kind'] == 'website', payload
assert payload['website_preview_summary']['primary_target_label'] == 'artifact_root', payload
assert payload['website_delivery_summary']['surface_kind'] == 'website_delivery', payload
assert payload['website_delivery_summary']['primary_preview_target_label'] == 'artifact_root', payload
assert isinstance(payload['website_delivery_summary']['generated_pages_entries'], list), payload
assert payload['recommended_primary_action'], payload
assert payload['project_summary']['project_id'] == payload['project_id'], payload
assert payload['project_preview']['entrypoint'] == 'project-preview', payload
PY
ok_project_export_handoff_json=true

project_style_brief_json="$TMP_ROOT/project_style_brief.json"
AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project style-brief --json > "$project_style_brief_json"
python3 - "$project_style_brief_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'project-style-brief', payload
assert payload['style_mode'] == 'architecture_first_model_styling', payload
assert payload['write_contract']['allowed_write_roots'], payload
assert any(path.endswith('/frontend/src/ail-overrides') for path in payload['write_contract']['allowed_write_roots']), payload
assert any(path.endswith('/frontend/public/ail-overrides') for path in payload['write_contract']['allowed_write_roots']), payload
assert any(path.endswith('/frontend/src/ail-managed') for path in payload['write_contract']['forbidden_write_roots']), payload
assert payload['override_surface']['theme_tokens_path'].endswith('/frontend/src/ail-overrides/theme.tokens.css'), payload
assert payload['override_surface']['custom_css_path'].endswith('/frontend/src/ail-overrides/custom.css'), payload
assert payload['hook_surface']['entrypoint'] == 'project-hook-guide', payload
assert payload['source_commands']['project_style_intent'].endswith('python3 -m cli project style-intent --json'), payload
assert payload['source_commands']['project_export_handoff'].endswith('python3 -m cli project export-handoff --base-url embedded://local --json'), payload
assert payload['source_commands']['project_hook_guide'].endswith('python3 -m cli project hook-guide --json'), payload
assert payload['source_commands']['project_serve'].endswith('python3 -m cli project serve --install-if-needed --json'), payload
assert payload['architecture_contract']['primary_target_label'] == 'artifact_root', payload
assert 'generated_pages_entries' in payload['architecture_contract'], payload
assert 'You are styling an AIL Builder project.' in payload['model_prompt'], payload
PY
ok_project_style_brief_json=true

style_intent_project_dir="$(mktemp -d /tmp/ail_cli_smoke_style_intent.XXXXXX)"
cp -R "$ROOT"/output_projects/CompanyProductSiteBrandPostureReview/. "$style_intent_project_dir"/

project_style_intent_write_json="$TMP_ROOT/project_style_intent_write.json"
(
  cd "$style_intent_project_dir"
  PYTHONPATH="$ROOT" AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project style-intent \
    --audience "founder-led SaaS buyers" \
    --style-direction "editorial clarity" \
    --localization-mode "english_only" \
    --brand-keyword "credible" \
    --brand-keyword "focused" \
    --tone-keyword "calm" \
    --tone-keyword "precise" \
    --visual-constraint "avoid purple" \
    --visual-constraint "mobile first readability" \
    --notes "Prefer strong hierarchy over decorative noise." \
    --json > "$project_style_intent_write_json"
)
python3 - "$project_style_intent_write_json" <<'PY'
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'project-style-intent', payload
assert payload['action'] == 'write', payload
intent = payload['style_intent']
assert intent['audience'] == 'founder-led SaaS buyers', payload
assert intent['style_direction'] == 'editorial clarity', payload
assert intent['localization_mode'] == 'english_only', payload
assert intent['brand_keywords'] == ['credible', 'focused'], payload
assert intent['tone_keywords'] == ['calm', 'precise'], payload
assert intent['visual_constraints'] == ['avoid purple', 'mobile first readability'], payload
assert intent['notes'] == 'Prefer strong hierarchy over decorative noise.', payload
PY
ok_project_style_intent_write_json=true

project_style_intent_read_json="$TMP_ROOT/project_style_intent_read.json"
(
  cd "$style_intent_project_dir"
  PYTHONPATH="$ROOT" AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project style-intent --json > "$project_style_intent_read_json"
)
python3 - "$project_style_intent_read_json" <<'PY'
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['action'] == 'read', payload
assert payload['style_intent']['brand_keywords'] == ['credible', 'focused'], payload
assert payload['style_intent']['tone_keywords'] == ['calm', 'precise'], payload
PY
ok_project_style_intent_read_json=true

project_style_brief_intent_json="$TMP_ROOT/project_style_brief_intent.json"
(
  cd "$style_intent_project_dir"
  PYTHONPATH="$ROOT" AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project style-brief --base-url embedded://local --json > "$project_style_brief_intent_json"
)
python3 - "$project_style_brief_intent_json" <<'PY'
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
intent = payload['design_intent']
assert intent['audience'] == 'founder-led SaaS buyers', payload
assert intent['style_direction'] == 'editorial clarity', payload
assert intent['localization_mode'] == 'english_only', payload
assert intent['brand_keywords'] == ['credible', 'focused'], payload
assert intent['tone_keywords'] == ['calm', 'precise'], payload
assert intent['visual_constraints'] == ['avoid purple', 'mobile first readability'], payload
assert payload['source_commands']['project_style_intent'].endswith('python3 -m cli project style-intent --json'), payload
assert 'founder-led SaaS buyers' in payload['model_prompt'], payload
PY
ok_project_style_brief_intent_json=true

project_style_brief_emit_prompt_txt="$TMP_ROOT/project_style_brief_emit_prompt.txt"
(
  cd "$style_intent_project_dir"
  PYTHONPATH="$ROOT" AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project style-brief --base-url embedded://local --emit-prompt > "$project_style_brief_emit_prompt_txt"
)
grep -q "^You are styling an AIL Builder project\\.$" "$project_style_brief_emit_prompt_txt"
grep -q "^Current project intent:$" "$project_style_brief_emit_prompt_txt"
grep -q "founder-led SaaS buyers" "$project_style_brief_emit_prompt_txt"
grep -q "^Safe write scope:$" "$project_style_brief_emit_prompt_txt"
grep -q "^Do not edit these managed roots directly for durable styling work:$" "$project_style_brief_emit_prompt_txt"
ok_project_style_brief_emit_prompt_txt=true

project_style_apply_check_json="$TMP_ROOT/project_style_apply_check.json"
(
  cd "$ROOT/output_projects/CompanyProductSiteBrandPostureReview"
  PYTHONPATH="$ROOT" AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project style-apply-check --base-url embedded://local --json > "$project_style_apply_check_json"
)
python3 - "$project_style_apply_check_json" <<'PY'
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'project-style-apply-check', payload
assert payload['verification_mode'] == 'local_boundary_and_runtime_continuity', payload
assert payload['managed_boundary']['managed_root_exists'] is True, payload
assert payload['managed_boundary']['verified_count'] >= 4, payload
assert payload['managed_boundary']['violation_count'] == 0, payload
assert payload['route_contract']['route_contract_ok'] is True, payload
assert payload['runtime_entry_contract']['runtime_entry_ok'] is True, payload
assert payload['serve_dry_run']['entrypoint'] == 'project-serve', payload
assert payload['style_brief']['entrypoint'] == 'project-style-brief', payload
assert payload['style_brief']['local_mode'] is True, payload
assert 'status: ok' in payload['summary_text'], payload
PY
ok_project_style_apply_check_json=true

project_style_apply_check_emit_summary_txt="$TMP_ROOT/project_style_apply_check_emit_summary.txt"
(
  cd "$ROOT/output_projects/CompanyProductSiteBrandPostureReview"
  PYTHONPATH="$ROOT" AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project style-apply-check --base-url embedded://local --emit-summary > "$project_style_apply_check_emit_summary_txt"
)
grep -q "^status: ok$" "$project_style_apply_check_emit_summary_txt"
grep -q "^managed_violations: 0$" "$project_style_apply_check_emit_summary_txt"
grep -q "^route_contract_ok: true$" "$project_style_apply_check_emit_summary_txt"
grep -q "^serve_dry_run_status: ok$" "$project_style_apply_check_emit_summary_txt"
ok_project_style_apply_check_emit_summary_txt=true

cloud_status_preview_json="$TMP_ROOT/cloud_status_preview.json"
AIL_CLOUD_BASE_URL=embedded://local python3 -m cli cloud status --json > "$cloud_status_preview_json"
python3 - "$cloud_status_preview_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['preview_handoff']['status'] == 'ok', payload
assert payload['preview_handoff']['primary_target']['label'] == 'artifact_root', payload
assert payload['website_preview_summary']['surface_kind'] == 'website', payload
labels = {item['label'] for item in payload['preview_handoff']['open_targets']}
assert 'source_of_truth' in labels, payload
assert 'generated_views_dir' in labels, payload
assert payload['preview_handoff']['open_targets'][1]['label'] == 'generated_views_dir', payload
assert payload['preview_hint'], payload
PY
ok_cloud_status_preview_json=true

build_id="$(python3 - <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json
from pathlib import Path
payload = json.loads(Path('.ail/last_build.json').read_text(encoding='utf-8'))
print(payload['build_id'])
PY
)"
build_artifact_preview_json="$TMP_ROOT/build_artifact_preview.json"
AIL_CLOUD_BASE_URL=embedded://local python3 -m cli build artifact "$build_id" --json > "$build_artifact_preview_json"
python3 - "$build_artifact_preview_json" "$build_id" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
build_id = sys.argv[2]
assert payload['status'] == 'ok', payload
assert payload['data']['build_id'] == build_id, payload
assert payload['preview_handoff']['status'] == 'ok', payload
assert payload['preview_handoff']['primary_target']['label'] == 'artifact_root', payload
assert payload['website_preview_summary']['surface_kind'] == 'website', payload
assert payload['preview_handoff']['primary_target']['path'] == payload['data']['local_path'], payload
assert payload['next_steps'][1].endswith(f"build show {build_id} --base-url embedded://local --json"), payload
PY
ok_build_artifact_preview_json=true

project_go_json="$TMP_ROOT/project_go_ok.json"
AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project go --json > "$project_go_json"
python3 - "$project_go_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'project-go', payload
assert payload['route_taken'] == 'project_continue_diagnose_compile_sync', payload
assert payload['route_reason'], payload
assert payload['executed_primary_action'] == 'project_continue_diagnose_compile_sync', payload
assert payload['result']['status'] == 'ok', payload
assert payload['result']['action'] == 'diagnose_compile_sync', payload
assert payload['result']['managed_files_written'] >= 1, payload
PY
ok_project_go_json=true

workspace_status_repo_json="$TMP_ROOT/workspace_status_repo.json"
AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace status --json > "$workspace_status_repo_json"
python3 - "$workspace_status_repo_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'workspace-status', payload
assert payload['inside_ail_project'] is True, payload
assert payload['current_project']['status'] == 'ok', payload
assert payload['recommended_workspace_action'] == 'project_go', payload
assert payload['recommended_workspace_command'].startswith('PYTHONPATH='), payload
assert payload['latest_trial_batch']['status'] == 'ok', payload
PY
ok_workspace_status_project_json=true

workspace_hooks_project_json="$TMP_ROOT/workspace_hooks_project.json"
AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hooks --json > "$workspace_hooks_project_json"
python3 - "$workspace_hooks_project_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'workspace-hooks', payload
assert payload['repo_root'].endswith('/ai-cl'), payload
assert payload['scanned_project_count'] >= payload['catalog_project_count'] >= 0, payload
assert payload['page_count'] >= 0, payload
assert payload['section_hook_count'] >= 0, payload
assert payload['slot_hook_count'] >= 0, payload
if payload['catalog_project_count'] > 0:
    assert payload['recommended_hook_project'], payload
    assert payload['recommended_hook_project_root'], payload
    assert payload['recommended_hook_suggest_command'], payload
    assert payload['recommended_workspace_hook_suggest_command'], payload
    assert payload['recommended_workspace_hook_pick_command'], payload
assert payload['next_steps'], payload
if payload['projects']:
    first = payload['projects'][0]
    assert first['project_name'], payload
    assert first['project_root'], payload
    assert first['hook_catalog']['json_path'], payload
    assert first['recommended_hook_suggest_command'], payload
    assert first['recommended_workspace_hook_suggest_command'], payload
    assert first['recommended_workspace_hook_pick_command'], payload
PY
ok_workspace_hooks_project_json=true

workspace_hook_init_project_json="$TMP_ROOT/workspace_hook_init_project.json"
rm -f "$hook_example_project_dir/frontend/src/ail-overrides/components/page.home.before.vue"
(
  cd "$hook_example_project_dir"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-init home.before --json > "$workspace_hook_init_project_json"
)
python3 - "$workspace_hook_init_project_json" "$hook_example_project_dir" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, pathlib, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
project_root = pathlib.Path(sys.argv[2]).resolve()
expected = (project_root / 'frontend/src/ail-overrides/components/page.home.before.vue').resolve()
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'workspace-hook-init', payload
assert payload['route_taken'] == 'current_project', payload
assert payload['selected_project_name'] == project_root.name, payload
assert pathlib.Path(payload['selected_project_root']).resolve() == project_root, payload
result = payload['result']
assert result['entrypoint'] == 'project-hook-init', payload
assert result['hook_name'] == 'page.home.before', payload
assert pathlib.Path(result['target_path']).resolve() == expected, payload
assert expected.exists(), payload
PY
ok_workspace_hook_init_project_json=true

workspace_summary_project_json="$TMP_ROOT/workspace_summary_project.json"
AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace summary --json > "$workspace_summary_project_json"
python3 - "$workspace_summary_project_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'workspace-summary', payload
assert payload['inside_ail_project'] is True, payload
assert payload['current_project']['project_id'], payload
assert payload['current_project']['recommended_primary_action'], payload
assert payload['hook_catalogs']['catalog_project_count'] >= 0, payload
if payload['hook_catalogs']['catalog_project_count'] > 0:
    assert payload['hook_catalogs']['recommended_hook_suggest_command'], payload
    assert payload['hook_catalogs']['recommended_workspace_hook_suggest_command'], payload
assert payload['recommended_workspace_action'] == 'project_go', payload
PY
ok_workspace_summary_project_json=true

workspace_preview_project_json="$TMP_ROOT/workspace_preview_project.json"
AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace preview --json > "$workspace_preview_project_json"
python3 - "$workspace_preview_project_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'workspace-preview', payload
assert payload['route_taken'] == 'project_preview', payload
assert payload['result']['entrypoint'] == 'project-preview', payload
assert payload['preview_handoff']['status'] == 'ok', payload
assert payload['preview_handoff']['primary_target']['label'] == 'artifact_root', payload
assert payload['website_preview_summary']['surface_kind'] == 'website', payload
PY
ok_workspace_preview_project_json=true

workspace_open_target_project_json="$TMP_ROOT/workspace_open_target_project.json"
AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace open-target source_of_truth --json > "$workspace_open_target_project_json"
python3 - "$workspace_open_target_project_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'workspace-open-target', payload
assert payload['route_taken'] == 'project_open_target', payload
assert payload['resolved_label'] == 'source_of_truth', payload
assert payload['target']['kind'] == 'file', payload
assert payload['target']['exists'] is True, payload
assert payload['result']['entrypoint'] == 'project-open-target', payload
PY
ok_workspace_open_target_project_json=true

workspace_inspect_target_project_json="$TMP_ROOT/workspace_inspect_target_project.json"
AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace inspect-target source_of_truth --json > "$workspace_inspect_target_project_json"
python3 - "$workspace_inspect_target_project_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'workspace-inspect-target', payload
assert payload['route_taken'] == 'project_inspect_target', payload
assert payload['resolved_label'] == 'source_of_truth', payload
assert payload['inspection']['kind'] == 'file', payload
assert payload['inspection']['exists'] is True, payload
assert payload['result']['entrypoint'] == 'project-inspect-target', payload
PY
ok_workspace_inspect_target_project_json=true

workspace_run_inspect_command_project_json="$TMP_ROOT/workspace_run_inspect_command_project.json"
AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace run-inspect-command source_of_truth --json > "$workspace_run_inspect_command_project_json"
python3 - "$workspace_run_inspect_command_project_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'workspace-run-inspect-command', payload
assert payload['route_taken'] == 'project_run_inspect_command', payload
assert payload['resolved_label'] == 'source_of_truth', payload
assert payload['inspection']['kind'] == 'file', payload
assert payload['result']['entrypoint'] == 'project-run-inspect-command', payload
PY
ok_workspace_run_inspect_command_project_json=true

workspace_export_handoff_project_json="$TMP_ROOT/workspace_export_handoff_project.json"
AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace export-handoff --json > "$workspace_export_handoff_project_json"
python3 - "$workspace_export_handoff_project_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'workspace-export-handoff', payload
assert payload['route_taken'] == 'project_export_handoff', payload
assert payload['result']['entrypoint'] == 'project-export-handoff', payload
assert payload['primary_target_label'] == 'artifact_root', payload
assert payload['primary_target']['kind'] == 'directory', payload
assert payload['primary_inspection']['kind'] == 'directory', payload
assert payload['website_preview_summary']['surface_kind'] == 'website', payload
assert payload['website_delivery_summary']['surface_kind'] == 'website_delivery', payload
PY
ok_workspace_export_handoff_project_json=true

workspace_go_project_json="$TMP_ROOT/workspace_go_project.json"
AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace go --json > "$workspace_go_project_json"
python3 - "$workspace_go_project_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'workspace-go', payload
assert payload['route_taken'] == 'project_go', payload
assert payload['executed_workspace_action'] == 'project_go', payload
assert payload['result']['entrypoint'] == 'project-go', payload
assert payload['workspace_status']['inside_ail_project'] is True, payload
assert payload['recommended_workspace_action'] == 'project_go', payload
PY
ok_workspace_go_project_json=true

workspace_doctor_project_json="$TMP_ROOT/workspace_doctor_project.json"
AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace doctor --json > "$workspace_doctor_project_json"
python3 - "$workspace_doctor_project_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'workspace-doctor', payload
assert payload['inside_ail_project'] is True, payload
assert payload['route_taken'] == 'project_doctor', payload
assert payload['recommended_workspace_action'] == 'project_doctor', payload
assert payload['result']['status'] == 'ok', payload
assert payload['result']['recommended_action'] == 'continue_iteration', payload
assert payload['result']['fix_plan']['mode'] == 'guided_recovery', payload
PY
ok_workspace_doctor_project_json=true

workspace_continue_project_json="$TMP_ROOT/workspace_continue_project.json"
AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace continue --json > "$workspace_continue_project_json"
python3 - "$workspace_continue_project_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'workspace-continue', payload
assert payload['route_taken'] == 'project_continue_diagnose_compile_sync', payload
assert payload['executed_workspace_action'] == 'project_continue_diagnose_compile_sync', payload
assert payload['result']['status'] == 'ok', payload
assert payload['result']['action'] == 'diagnose_compile_sync', payload
assert payload['result']['managed_files_written'] >= 1, payload
PY
ok_workspace_continue_project_json=true

workspace_status_root_json="$TMP_ROOT/workspace_status_root.json"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace status --json > "$workspace_status_root_json"
)
python3 - "$workspace_status_root_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'workspace-status', payload
assert payload['inside_ail_project'] is False, payload
assert payload['recommended_workspace_action'] in {'trial_run_landing', 'run_readiness_snapshot'}, payload
assert payload['readiness_snapshot']['status'] in {'ok', 'attention'}, payload
assert payload['rc_checks']['status'] in {'ok', 'error', 'attention'}, payload
PY
ok_workspace_status_repo_json=true

workspace_hooks_root_json="$TMP_ROOT/workspace_hooks_root.json"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hooks --json > "$workspace_hooks_root_json"
)
python3 - "$workspace_hooks_root_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'workspace-hooks', payload
assert payload['repo_root'] == ROOT, payload
assert payload['output_projects_root'] == f'{OUTPUT_PROJECTS_ROOT}', payload
assert payload['scanned_project_count'] >= payload['catalog_project_count'] >= 0, payload
assert isinstance(payload['available_projects'], list), payload
if payload['catalog_project_count'] > 0:
    assert payload['recommended_hook_project'], payload
    assert payload['recommended_hook_project_root'], payload
    assert payload['recommended_hook_suggest_command'], payload
    assert payload['recommended_workspace_hook_suggest_command'], payload
    assert payload['recommended_workspace_hook_pick_command'], payload
    assert '--follow-recommended' in payload['recommended_workspace_hook_pick_command'], payload
    assert payload['preferred_workspace_hook_command'], payload
    assert payload['preferred_workspace_hook_reason'], payload
    if payload['recent_hook_project']:
        assert payload['recent_workspace_hook_suggest_command'], payload
        assert '--use-last-project' in payload['recent_workspace_hook_suggest_command'], payload
        assert payload['recent_workspace_hook_pick_command'], payload
        assert '--use-last-project' in payload['recent_workspace_hook_pick_command'], payload
        assert '--use-last-project' in payload['preferred_workspace_hook_command'], payload
    else:
        assert '--follow-recommended' in payload['preferred_workspace_hook_command'], payload
assert payload['next_steps'], payload
PY
ok_workspace_hooks_repo_json=true

workspace_hook_project_dir="$ROOT/output_projects/WorkspaceHookInitSmoke"
rm -rf "$workspace_hook_project_dir"
cp -R "$ROOT"/output_projects/HookExampleGenerated/. "$workspace_hook_project_dir"/
rm -f "$workspace_hook_project_dir/frontend/src/ail-overrides/components/page.home.before.vue"

workspace_hook_guide_repo_json="$TMP_ROOT/workspace_hook_guide_repo.json"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-guide --json > "$workspace_hook_guide_repo_json"
)
python3 - "$workspace_hook_guide_repo_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'workspace-hook-guide', payload
assert payload['recommended_project_name'], payload
assert payload['recommended_workspace_hook_suggest_command'], payload
assert payload['cheat_sheet_path'].endswith('CUSTOMIZATION_UX_OPERATOR_CHEAT_SHEET_20260406.md'), payload
labels = [item.get('label') for item in payload.get('guide_sections', [])]
assert labels[:4] == ['workspace_hooks', 'suggest', 'continue', 'explain'], payload
assert any('workspace hooks --json' in step for step in payload.get('next_steps', [])), payload
PY
ok_workspace_hook_guide_repo_json=true

workspace_hook_guide_emit_shell_repo_txt="$TMP_ROOT/workspace_hook_guide_emit_shell_repo.txt"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-guide --emit-shell > "$workspace_hook_guide_emit_shell_repo_txt"
)
python3 - "$workspace_hook_guide_emit_shell_repo_txt" <<'PY'
import sys
text = open(sys.argv[1], 'r', encoding='utf-8').read().strip()
assert text.startswith("PYTHONPATH=${ROOT} python3 -m cli workspace hook-init "), text
assert ("--use-last-project --pick-recommended --json" in text) or ("--follow-recommended --json" in text), text
PY
ok_workspace_hook_guide_emit_shell_repo=true

workspace_hook_guide_copy_command_repo_txt="$TMP_ROOT/workspace_hook_guide_copy_command_repo.txt"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-guide --copy-command > "$workspace_hook_guide_copy_command_repo_txt"
  copied_workspace_hook_guide_command="$(pbpaste)"
  printf '%s\n' "$copied_workspace_hook_guide_command" > "$TMP_ROOT/workspace_hook_guide_copy_command_repo_pbpaste.txt"
)
grep -q "^Workspace hook-guide command copied$" "$workspace_hook_guide_copy_command_repo_txt"
python3 - "$workspace_hook_guide_copy_command_repo_txt" "$TMP_ROOT/workspace_hook_guide_copy_command_repo_pbpaste.txt" <<'PY'
import sys
stdout = open(sys.argv[1], 'r', encoding='utf-8').read()
pb = open(sys.argv[2], 'r', encoding='utf-8').read().strip()
assert "copied_command: " in stdout, stdout
assert pb.startswith("PYTHONPATH=${ROOT} python3 -m cli workspace hook-init "), pb
assert ("--use-last-project --pick-recommended --json" in pb) or ("--follow-recommended --json" in pb), pb
PY
ok_workspace_hook_guide_copy_command_repo=true

workspace_hook_guide_run_command_repo_json="$TMP_ROOT/workspace_hook_guide_run_command_repo.json"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-guide --run-command --json > "$workspace_hook_guide_run_command_repo_json"
)
python3 - "$workspace_hook_guide_run_command_repo_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['entrypoint'] == 'workspace-hook-guide', payload
assert payload['run_command_requires_confirmation'] is True, payload
assert payload['run_command_confirmed'] is False, payload
assert payload['run_command_confirm_command'] == f'PYTHONPATH={ROOT} python3 -m cli workspace hook-guide --run-command --yes --json', payload
assert payload['run_command'].startswith(f'PYTHONPATH={ROOT} python3 -m cli workspace hook-init '), payload
PY
ok_workspace_hook_guide_run_command_repo=true

workspace_hook_guide_run_command_yes_repo_json="$TMP_ROOT/workspace_hook_guide_run_command_yes_repo.json"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-guide --run-command --yes --json > "$workspace_hook_guide_run_command_yes_repo_json"
)
python3 - "$workspace_hook_guide_run_command_yes_repo_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['entrypoint'] == 'workspace-hook-guide', payload
assert payload['run_command_confirmed'] is True, payload
assert payload['ran_command'] is True, payload
assert payload['run_command_exit_code'] == 0, payload
result = payload['run_result']
assert result['entrypoint'] == 'workspace-hook-init', payload
assert result['status'] == 'ok', payload
PY
ok_workspace_hook_guide_run_command_yes_repo=true

workspace_hook_init_text_compact_repo_txt="$TMP_ROOT/workspace_hook_init_text_compact_repo.txt"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-init home.before --project-name WorkspaceHookInitSmoke --dry-run --text-compact > "$workspace_hook_init_text_compact_repo_txt" || true
)
grep -q "^Workspace hook-init compact$" "$workspace_hook_init_text_compact_repo_txt"
grep -q "^- route_taken: named_workspace_project$" "$workspace_hook_init_text_compact_repo_txt"
grep -q "^- selected_project_name: WorkspaceHookInitSmoke$" "$workspace_hook_init_text_compact_repo_txt"
grep -q "^- hook_name: page.home.before$" "$workspace_hook_init_text_compact_repo_txt"
grep -q "^- target_relative_path: frontend/src/ail-overrides/components/page.home.before.vue$" "$workspace_hook_init_text_compact_repo_txt"
grep -q "^- runnable_next_command: PYTHONPATH=${ROOT} python3 -m cli workspace hook-init --project-name WorkspaceHookInitSmoke page.home.before --json$" "$workspace_hook_init_text_compact_repo_txt"
ok_workspace_hook_init_text_compact_repo=true

workspace_hook_init_explain_repo_txt="$TMP_ROOT/workspace_hook_init_explain_repo.txt"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-init home.before --project-name WorkspaceHookInitSmoke --dry-run --explain > "$workspace_hook_init_explain_repo_txt" || true
)
grep -q "^Workspace hook-init explain$" "$workspace_hook_init_explain_repo_txt"
grep -q "^- route_taken: named_workspace_project$" "$workspace_hook_init_explain_repo_txt"
grep -q "^- runnable_next_command: PYTHONPATH=${ROOT} python3 -m cli workspace hook-init --project-name WorkspaceHookInitSmoke page.home.before --json$" "$workspace_hook_init_explain_repo_txt"
grep -q "^- message: Dry run only. No hook file was written.$" "$workspace_hook_init_explain_repo_txt"
grep -q "^- route: " "$workspace_hook_init_explain_repo_txt"
grep -q "^- selection: " "$workspace_hook_init_explain_repo_txt"
grep -q "^- target: " "$workspace_hook_init_explain_repo_txt"
grep -q "^- followup: " "$workspace_hook_init_explain_repo_txt"
ok_workspace_hook_init_explain_repo=true

workspace_hook_init_emit_shell_repo_txt="$TMP_ROOT/workspace_hook_init_emit_shell_repo.txt"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-init home.before --project-name WorkspaceHookInitSmoke --dry-run --emit-shell > "$workspace_hook_init_emit_shell_repo_txt"
)
grep -q "^PYTHONPATH=${ROOT} python3 -m cli workspace hook-init --project-name WorkspaceHookInitSmoke page.home.before --json$" "$workspace_hook_init_emit_shell_repo_txt"
ok_workspace_hook_init_emit_shell_repo=true

workspace_hook_init_copy_command_repo_txt="$TMP_ROOT/workspace_hook_init_copy_command_repo.txt"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-init home.before --project-name WorkspaceHookInitSmoke --dry-run --copy-command > "$workspace_hook_init_copy_command_repo_txt"
  copied_workspace_hook_init_command="$(pbpaste)"
  printf '%s\n' "$copied_workspace_hook_init_command" > "$TMP_ROOT/workspace_hook_init_copy_command_repo_pbpaste.txt"
)
grep -q "^Workspace hook-init next command copied$" "$workspace_hook_init_copy_command_repo_txt"
grep -q "^- copied_command: PYTHONPATH=${ROOT} python3 -m cli workspace hook-init --project-name WorkspaceHookInitSmoke page.home.before --json$" "$workspace_hook_init_copy_command_repo_txt"
grep -q "^PYTHONPATH=${ROOT} python3 -m cli workspace hook-init --project-name WorkspaceHookInitSmoke page.home.before --json$" "$TMP_ROOT/workspace_hook_init_copy_command_repo_pbpaste.txt"
ok_workspace_hook_init_copy_command_repo=true

workspace_hook_init_emit_confirm_shell_repo_txt="$TMP_ROOT/workspace_hook_init_emit_confirm_shell_repo.txt"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-init home.before --project-name WorkspaceHookInitSmoke --dry-run --emit-confirm-shell > "$workspace_hook_init_emit_confirm_shell_repo_txt"
)
grep -q "^PYTHONPATH=${ROOT} python3 -m cli workspace hook-init --project-name WorkspaceHookInitSmoke page.home.before --json$" "$workspace_hook_init_emit_confirm_shell_repo_txt"
ok_workspace_hook_init_emit_confirm_shell_repo=true

workspace_hook_init_copy_confirm_command_repo_txt="$TMP_ROOT/workspace_hook_init_copy_confirm_command_repo.txt"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-init home.before --project-name WorkspaceHookInitSmoke --dry-run --copy-confirm-command > "$workspace_hook_init_copy_confirm_command_repo_txt"
  copied_workspace_hook_init_confirm="$(pbpaste)"
  printf '%s\n' "$copied_workspace_hook_init_confirm" > "$TMP_ROOT/workspace_hook_init_copy_confirm_command_repo_pbpaste.txt"
)
grep -q "^Workspace hook-init confirm command copied$" "$workspace_hook_init_copy_confirm_command_repo_txt"
grep -q "^- copied_confirm_command: PYTHONPATH=${ROOT} python3 -m cli workspace hook-init --project-name WorkspaceHookInitSmoke page.home.before --json$" "$workspace_hook_init_copy_confirm_command_repo_txt"
grep -q "^PYTHONPATH=${ROOT} python3 -m cli workspace hook-init --project-name WorkspaceHookInitSmoke page.home.before --json$" "$TMP_ROOT/workspace_hook_init_copy_confirm_command_repo_pbpaste.txt"
ok_workspace_hook_init_copy_confirm_command_repo=true

workspace_hook_init_emit_target_path_repo_txt="$TMP_ROOT/workspace_hook_init_emit_target_path_repo.txt"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-init home.before --project-name WorkspaceHookInitSmoke --dry-run --emit-target-path > "$workspace_hook_init_emit_target_path_repo_txt"
)
grep -q "/frontend/src/ail-overrides/components/page.home.before.vue$" "$workspace_hook_init_emit_target_path_repo_txt"
ok_workspace_hook_init_emit_target_path_repo=true

workspace_hook_init_copy_target_path_repo_txt="$TMP_ROOT/workspace_hook_init_copy_target_path_repo.txt"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-init home.before --project-name WorkspaceHookInitSmoke --dry-run --copy-target-path > "$workspace_hook_init_copy_target_path_repo_txt"
  copied_workspace_hook_init_target="$(pbpaste)"
  printf '%s\n' "$copied_workspace_hook_init_target" > "$TMP_ROOT/workspace_hook_init_copy_target_path_repo_pbpaste.txt"
)
grep -q "^Workspace hook-init target path copied$" "$workspace_hook_init_copy_target_path_repo_txt"
grep -q "/frontend/src/ail-overrides/components/page.home.before.vue$" "$workspace_hook_init_copy_target_path_repo_txt"
grep -q "/frontend/src/ail-overrides/components/page.home.before.vue$" "$TMP_ROOT/workspace_hook_init_copy_target_path_repo_pbpaste.txt"
ok_workspace_hook_init_copy_target_path_repo=true

workspace_hook_init_emit_target_dir_repo_txt="$TMP_ROOT/workspace_hook_init_emit_target_dir_repo.txt"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-init home.before --project-name WorkspaceHookInitSmoke --dry-run --emit-target-dir > "$workspace_hook_init_emit_target_dir_repo_txt"
)
grep -q "/frontend/src/ail-overrides/components$" "$workspace_hook_init_emit_target_dir_repo_txt"
ok_workspace_hook_init_emit_target_dir_repo=true

workspace_hook_init_copy_target_dir_repo_txt="$TMP_ROOT/workspace_hook_init_copy_target_dir_repo.txt"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-init home.before --project-name WorkspaceHookInitSmoke --dry-run --copy-target-dir > "$workspace_hook_init_copy_target_dir_repo_txt"
  copied_workspace_hook_init_target_dir="$(pbpaste)"
  printf '%s\n' "$copied_workspace_hook_init_target_dir" > "$TMP_ROOT/workspace_hook_init_copy_target_dir_repo_pbpaste.txt"
)
grep -q "^Workspace hook-init target directory copied$" "$workspace_hook_init_copy_target_dir_repo_txt"
grep -q "/frontend/src/ail-overrides/components$" "$workspace_hook_init_copy_target_dir_repo_txt"
grep -q "/frontend/src/ail-overrides/components$" "$TMP_ROOT/workspace_hook_init_copy_target_dir_repo_pbpaste.txt"
ok_workspace_hook_init_copy_target_dir_repo=true

workspace_hook_init_emit_target_project_root_repo_txt="$TMP_ROOT/workspace_hook_init_emit_target_project_root_repo.txt"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-init home.before --project-name WorkspaceHookInitSmoke --dry-run --emit-target-project-root > "$workspace_hook_init_emit_target_project_root_repo_txt"
)
grep -q "^${ROOT}/output_projects/WorkspaceHookInitSmoke$" "$workspace_hook_init_emit_target_project_root_repo_txt"
ok_workspace_hook_init_emit_target_project_root_repo=true

workspace_hook_init_copy_target_project_root_repo_txt="$TMP_ROOT/workspace_hook_init_copy_target_project_root_repo.txt"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-init home.before --project-name WorkspaceHookInitSmoke --dry-run --copy-target-project-root > "$workspace_hook_init_copy_target_project_root_repo_txt"
  copied_workspace_hook_init_target_project_root="$(pbpaste)"
  printf '%s\n' "$copied_workspace_hook_init_target_project_root" > "$TMP_ROOT/workspace_hook_init_copy_target_project_root_repo_pbpaste.txt"
)
grep -q "^Workspace hook-init target project root copied$" "$workspace_hook_init_copy_target_project_root_repo_txt"
grep -q "^${ROOT}/output_projects/WorkspaceHookInitSmoke$" "$TMP_ROOT/workspace_hook_init_copy_target_project_root_repo_pbpaste.txt"
ok_workspace_hook_init_copy_target_project_root_repo=true

workspace_hook_init_emit_target_project_name_repo_txt="$TMP_ROOT/workspace_hook_init_emit_target_project_name_repo.txt"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-init home.before --project-name WorkspaceHookInitSmoke --dry-run --emit-target-project-name > "$workspace_hook_init_emit_target_project_name_repo_txt"
)
grep -q "^WorkspaceHookInitSmoke$" "$workspace_hook_init_emit_target_project_name_repo_txt"
ok_workspace_hook_init_emit_target_project_name_repo=true

workspace_hook_init_copy_target_project_name_repo_txt="$TMP_ROOT/workspace_hook_init_copy_target_project_name_repo.txt"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-init home.before --project-name WorkspaceHookInitSmoke --dry-run --copy-target-project-name > "$workspace_hook_init_copy_target_project_name_repo_txt"
  copied_workspace_hook_init_target_project_name="$(pbpaste)"
  printf '%s\n' "$copied_workspace_hook_init_target_project_name" > "$TMP_ROOT/workspace_hook_init_copy_target_project_name_repo_pbpaste.txt"
)
grep -q "^Workspace hook-init target project name copied$" "$workspace_hook_init_copy_target_project_name_repo_txt"
grep -q "^WorkspaceHookInitSmoke$" "$TMP_ROOT/workspace_hook_init_copy_target_project_name_repo_pbpaste.txt"
ok_workspace_hook_init_copy_target_project_name_repo=true

workspace_hook_init_emit_target_relative_path_repo_txt="$TMP_ROOT/workspace_hook_init_emit_target_relative_path_repo.txt"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-init home.before --project-name WorkspaceHookInitSmoke --dry-run --emit-target-relative-path > "$workspace_hook_init_emit_target_relative_path_repo_txt"
)
grep -q "^frontend/src/ail-overrides/components/page.home.before.vue$" "$workspace_hook_init_emit_target_relative_path_repo_txt"
ok_workspace_hook_init_emit_target_relative_path_repo=true

workspace_hook_init_copy_target_relative_path_repo_txt="$TMP_ROOT/workspace_hook_init_copy_target_relative_path_repo.txt"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-init home.before --project-name WorkspaceHookInitSmoke --dry-run --copy-target-relative-path > "$workspace_hook_init_copy_target_relative_path_repo_txt"
  copied_workspace_hook_init_target_relative="$(pbpaste)"
  printf '%s\n' "$copied_workspace_hook_init_target_relative" > "$TMP_ROOT/workspace_hook_init_copy_target_relative_path_repo_pbpaste.txt"
)
grep -q "^Workspace hook-init target relative path copied$" "$workspace_hook_init_copy_target_relative_path_repo_txt"
grep -q "^- copied_target_relative_path: frontend/src/ail-overrides/components/page.home.before.vue$" "$workspace_hook_init_copy_target_relative_path_repo_txt"
grep -q "^frontend/src/ail-overrides/components/page.home.before.vue$" "$TMP_ROOT/workspace_hook_init_copy_target_relative_path_repo_pbpaste.txt"
ok_workspace_hook_init_copy_target_relative_path_repo=true

workspace_hook_init_emit_target_bundle_repo_txt="$TMP_ROOT/workspace_hook_init_emit_target_bundle_repo.txt"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-init home.before --project-name WorkspaceHookInitSmoke --dry-run --emit-target-bundle > "$workspace_hook_init_emit_target_bundle_repo_txt"
)
python3 - "$workspace_hook_init_emit_target_bundle_repo_txt" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
from pathlib import Path
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['target_path'].startswith(f'{OUTPUT_PROJECTS_ROOT}/WorkspaceHookInitSmoke/'), payload
assert payload['target_dir'].endswith('/frontend/src/ail-overrides/components'), payload
assert payload['target_project_root'] == f'{OUTPUT_PROJECTS_ROOT}/WorkspaceHookInitSmoke', payload
assert str(payload['target_project_name']) == Path(payload['target_project_root']).name, payload
assert payload['target_relative_path'] == 'frontend/src/ail-overrides/components/page.home.before.vue', payload
assert payload['open_command'].startswith(f'inspect {OUTPUT_PROJECTS_ROOT}/WorkspaceHookInitSmoke/'), payload
assert payload['confirm_command'] == f'PYTHONPATH={ROOT} python3 -m cli workspace hook-init --project-name WorkspaceHookInitSmoke page.home.before --json', payload
PY
ok_workspace_hook_init_emit_target_bundle_repo=true

workspace_hook_init_copy_target_bundle_repo_txt="$TMP_ROOT/workspace_hook_init_copy_target_bundle_repo.txt"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-init home.before --project-name WorkspaceHookInitSmoke --dry-run --copy-target-bundle > "$workspace_hook_init_copy_target_bundle_repo_txt"
)
grep -q "^Workspace hook-init target bundle copied$" "$workspace_hook_init_copy_target_bundle_repo_txt"
grep -q "^- copied_target_bundle: {" "$workspace_hook_init_copy_target_bundle_repo_txt"
copied_workspace_hook_init_target_bundle="$(pbpaste)"
WORKSPACE_HOOK_INIT_COPIED_TARGET_BUNDLE="$copied_workspace_hook_init_target_bundle" python3 - <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, os
from pathlib import Path
payload = json.loads(os.environ['WORKSPACE_HOOK_INIT_COPIED_TARGET_BUNDLE'])
assert payload['target_path'].startswith(f'{OUTPUT_PROJECTS_ROOT}/WorkspaceHookInitSmoke/'), payload
assert payload['target_dir'].endswith('/frontend/src/ail-overrides/components'), payload
assert str(payload['target_project_name']) == Path(payload['target_project_root']).name, payload
assert payload['target_relative_path'] == 'frontend/src/ail-overrides/components/page.home.before.vue', payload
assert payload['confirm_command'] == f'PYTHONPATH={ROOT} python3 -m cli workspace hook-init --project-name WorkspaceHookInitSmoke page.home.before --json', payload
PY
ok_workspace_hook_init_copy_target_bundle_repo=true

workspace_hook_init_emit_open_shell_repo_txt="$TMP_ROOT/workspace_hook_init_emit_open_shell_repo.txt"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-init home.before --project-name WorkspaceHookInitSmoke --dry-run --emit-open-shell > "$workspace_hook_init_emit_open_shell_repo_txt"
)
grep -q "^inspect ${ROOT}/output_projects/WorkspaceHookInitSmoke/frontend/src/ail-overrides/components/page.home.before.vue$" "$workspace_hook_init_emit_open_shell_repo_txt"
ok_workspace_hook_init_emit_open_shell_repo=true

workspace_hook_init_copy_open_command_repo_txt="$TMP_ROOT/workspace_hook_init_copy_open_command_repo.txt"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-init home.before --project-name WorkspaceHookInitSmoke --dry-run --copy-open-command > "$workspace_hook_init_copy_open_command_repo_txt"
  copied_workspace_hook_init_open_command="$(pbpaste)"
  printf '%s\n' "$copied_workspace_hook_init_open_command" > "$TMP_ROOT/workspace_hook_init_copy_open_command_repo_pbpaste.txt"
)
grep -q "^Workspace hook-init open command copied$" "$workspace_hook_init_copy_open_command_repo_txt"
grep -q "^- copied_open_command: inspect ${ROOT}/output_projects/WorkspaceHookInitSmoke/frontend/src/ail-overrides/components/page.home.before.vue$" "$workspace_hook_init_copy_open_command_repo_txt"
grep -q "^inspect ${ROOT}/output_projects/WorkspaceHookInitSmoke/frontend/src/ail-overrides/components/page.home.before.vue$" "$TMP_ROOT/workspace_hook_init_copy_open_command_repo_pbpaste.txt"
ok_workspace_hook_init_copy_open_command_repo=true

workspace_hook_init_run_command_repo_json="$TMP_ROOT/workspace_hook_init_run_command_repo.json"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-init home.before --project-name WorkspaceHookInitSmoke --dry-run --run-command --json > "$workspace_hook_init_run_command_repo_json"
)
python3 - "$workspace_hook_init_run_command_repo_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['run_command'], payload
assert payload['run_command'] == f'PYTHONPATH={ROOT} python3 -m cli workspace hook-init --project-name WorkspaceHookInitSmoke page.home.before --json', payload
assert payload['run_command_requires_confirmation'] is True, payload
assert payload['run_command_confirmed'] is False, payload
assert payload['ran_command'] is False, payload
assert payload['run_command_exit_code'] == 0, payload
assert payload['run_command_warning'], payload
assert payload['run_command_confirm_command'], payload
assert '--run-command' in payload['run_command_confirm_command'], payload
assert '--yes' in payload['run_command_confirm_command'], payload
PY
ok_workspace_hook_init_run_command_repo=true

workspace_hook_init_run_command_yes_repo_json="$TMP_ROOT/workspace_hook_init_run_command_yes_repo.json"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-init home.before --project-name WorkspaceHookInitSmoke --dry-run --run-command --yes --json > "$workspace_hook_init_run_command_yes_repo_json"
)
python3 - "$workspace_hook_init_run_command_yes_repo_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, pathlib, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['run_command_confirmed'] is True, payload
assert payload['ran_command'] is True, payload
assert payload['run_command_exit_code'] == 0, payload
result = payload['run_result']
assert result['entrypoint'] == 'workspace-hook-init', payload
assert result['route_taken'] == 'named_workspace_project', payload
assert result['selected_project_name'] == 'WorkspaceHookInitSmoke', payload
assert result['selected_project_root'] == f'{OUTPUT_PROJECTS_ROOT}/WorkspaceHookInitSmoke', payload
inner = result['result']
assert inner['entrypoint'] == 'project-hook-init', payload
target_path = pathlib.Path(inner['target_path'])
assert target_path == pathlib.Path(f'{OUTPUT_PROJECTS_ROOT}/WorkspaceHookInitSmoke/frontend/src/ail-overrides/components/page.home.before.vue'), payload
assert inner['hook_name'] == 'page.home.before', payload
assert inner['wrote'] is True, payload
assert target_path.exists(), payload
PY
ok_workspace_hook_init_run_command_yes_repo=true
rm -f "$workspace_hook_project_dir/frontend/src/ail-overrides/components/page.home.before.vue"

workspace_hook_init_run_open_command_repo_json="$TMP_ROOT/workspace_hook_init_run_open_command_repo.json"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-init home.before --project-name WorkspaceHookInitSmoke --dry-run --run-open-command --json > "$workspace_hook_init_run_open_command_repo_json"
)
python3 - "$workspace_hook_init_run_open_command_repo_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['run_open_command'], payload
assert payload['run_open_command'].startswith(f'inspect {OUTPUT_PROJECTS_ROOT}/WorkspaceHookInitSmoke/'), payload
assert payload['run_open_command_requires_confirmation'] is True, payload
assert payload['run_open_command_confirmed'] is False, payload
assert payload['ran_open_command'] is False, payload
assert payload['run_open_command_exit_code'] == 0, payload
assert payload['run_open_command_warning'], payload
assert payload['run_open_command_confirm_command'], payload
assert '--yes' in payload['run_open_command_confirm_command'], payload
PY
ok_workspace_hook_init_run_open_command_repo=true

workspace_hook_init_run_open_command_yes_repo_json="$TMP_ROOT/workspace_hook_init_run_open_command_yes_repo.json"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-init home.before --project-name WorkspaceHookInitSmoke --dry-run --run-open-command --yes --json > "$workspace_hook_init_run_open_command_yes_repo_json"
)
python3 - "$workspace_hook_init_run_open_command_yes_repo_json" "$workspace_hook_project_dir" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, pathlib, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
project_root = pathlib.Path(sys.argv[2]).resolve()
assert payload['run_open_command'], payload
assert payload['run_open_command_confirmed'] is True, payload
assert payload['ran_open_command'] is True, payload
assert payload['run_open_command_exit_code'] == 0, payload
result = payload['run_open_result']
assert pathlib.Path(result['path']).resolve().is_relative_to(project_root), payload
assert result['exists'] is False, payload
assert result['line_count'] == 0, payload
PY
ok_workspace_hook_init_run_open_command_yes_repo=true

workspace_hook_init_inspect_target_repo_json="$TMP_ROOT/workspace_hook_init_inspect_target_repo.json"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-init home.before --project-name WorkspaceHookInitSmoke --dry-run --inspect-target --json > "$workspace_hook_init_inspect_target_repo_json"
)
python3 - "$workspace_hook_init_inspect_target_repo_json" "$workspace_hook_project_dir" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, pathlib, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
project_root = pathlib.Path(sys.argv[2]).resolve()
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'workspace-hook-init', payload
assert payload['dry_run'] is True, payload
assert payload['inspect_target_summary'], payload
target_inspection = payload['target_inspection']
parent_inspection = payload['target_parent_inspection']
assert target_inspection['kind'] == 'file', payload
assert target_inspection['exists'] is False, payload
target_path = pathlib.Path(target_inspection['path']).resolve()
assert target_path.parent == (project_root / 'frontend/src/ail-overrides/components').resolve(), payload
assert parent_inspection['kind'] == 'directory', payload
assert parent_inspection['exists'] is True, payload
assert pathlib.Path(parent_inspection['path']).resolve() == target_path.parent, payload
assert parent_inspection['entry_count'] >= 1, payload
PY
ok_workspace_hook_init_inspect_target_repo=true

workspace_hook_init_inspect_target_text_compact_repo_txt="$TMP_ROOT/workspace_hook_init_inspect_target_text_compact_repo.txt"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-init home.before --project-name WorkspaceHookInitSmoke --dry-run --inspect-target --text-compact > "$workspace_hook_init_inspect_target_text_compact_repo_txt" || true
)
grep -q "^Workspace hook-init compact$" "$workspace_hook_init_inspect_target_text_compact_repo_txt"
grep -q "^- inspect_target_summary: " "$workspace_hook_init_inspect_target_text_compact_repo_txt"
grep -q "^- inspect_target_parent_summary: " "$workspace_hook_init_inspect_target_text_compact_repo_txt"
grep -q "^- inspected_target_path: " "$workspace_hook_init_inspect_target_text_compact_repo_txt"
grep -q "^- inspected_target_exists: " "$workspace_hook_init_inspect_target_text_compact_repo_txt"
grep -q "^- nearby_entries: " "$workspace_hook_init_inspect_target_text_compact_repo_txt"
ok_workspace_hook_init_inspect_target_text_compact_repo=true

workspace_hook_init_open_target_repo_json="$TMP_ROOT/workspace_hook_init_open_target_repo.json"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-init home.before --project-name WorkspaceHookInitSmoke --dry-run --open-target --json > "$workspace_hook_init_open_target_repo_json"
)
python3 - "$workspace_hook_init_open_target_repo_json" "$workspace_hook_project_dir" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, pathlib, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
project_root = pathlib.Path(sys.argv[2]).resolve()
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'workspace-hook-init', payload
assert payload['dry_run'] is True, payload
assert payload['open_target_summary'], payload
assert payload['open_target_reason'], payload
assert payload['open_target_command'].startswith('inspect '), payload
open_target = payload['open_target']
assert open_target['label'] == 'hook_target', payload
assert open_target['kind'] == 'file', payload
target_path = pathlib.Path(open_target['path']).resolve()
assert target_path.parent == (project_root / 'frontend/src/ail-overrides/components').resolve(), payload
assert open_target['exists'] is False, payload
assert payload['open_target_command'].endswith(str(target_path)), payload
PY
ok_workspace_hook_init_open_target_repo=true

workspace_hook_init_open_now_repo_json="$TMP_ROOT/workspace_hook_init_open_now_repo.json"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-init home.before --project-name WorkspaceHookInitSmoke --dry-run --open-now --json > "$workspace_hook_init_open_now_repo_json"
)
python3 - "$workspace_hook_init_open_now_repo_json" "$workspace_hook_project_dir" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, pathlib, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
project_root = pathlib.Path(sys.argv[2]).resolve()
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'workspace-hook-init', payload
assert payload['dry_run'] is True, payload
assert payload['open_now'] is True, payload
assert payload['open_now_summary'], payload
assert payload['open_now_reason'], payload
open_now_result = payload['open_now_result']
assert open_now_result['kind'] == 'file', payload
assert open_now_result['exists'] is False, payload
target_path = pathlib.Path(open_now_result['path']).resolve()
assert target_path.parent == (project_root / 'frontend/src/ail-overrides/components').resolve(), payload
assert open_now_result['line_count'] == 0, payload
PY
ok_workspace_hook_init_open_now_repo=true

workspace_hook_init_open_now_text_compact_repo_txt="$TMP_ROOT/workspace_hook_init_open_now_text_compact_repo.txt"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-init home.before --project-name WorkspaceHookInitSmoke --dry-run --open-now --text-compact > "$workspace_hook_init_open_now_text_compact_repo_txt" || true
)
grep -q "^Workspace hook-init compact$" "$workspace_hook_init_open_now_text_compact_repo_txt"
grep -q "^- open_now_summary: " "$workspace_hook_init_open_now_text_compact_repo_txt"
grep -q "^- open_now_path: " "$workspace_hook_init_open_now_text_compact_repo_txt"
grep -q "^- open_now_exists: " "$workspace_hook_init_open_now_text_compact_repo_txt"
grep -q "^- open_now_line_count: " "$workspace_hook_init_open_now_text_compact_repo_txt"
ok_workspace_hook_init_open_now_text_compact_repo=true

workspace_hook_init_repo_json="$TMP_ROOT/workspace_hook_init_repo.json"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-init home.before --project-name WorkspaceHookInitSmoke --json > "$workspace_hook_init_repo_json"
)
python3 - "$workspace_hook_init_repo_json" "$workspace_hook_project_dir" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, pathlib, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
project_root = pathlib.Path(sys.argv[2]).resolve()
expected = (project_root / 'frontend/src/ail-overrides/components/page.home.before.vue').resolve()
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'workspace-hook-init', payload
assert payload['route_taken'] == 'named_workspace_project', payload
assert payload['requested_project_name'] == 'WorkspaceHookInitSmoke', payload
assert payload['selected_project_name'] == 'WorkspaceHookInitSmoke', payload
assert pathlib.Path(payload['selected_project_root']).resolve() == project_root, payload
result = payload['result']
assert result['entrypoint'] == 'project-hook-init', payload
assert result['hook_name'] == 'page.home.before', payload
assert pathlib.Path(result['target_path']).resolve() == expected, payload
assert expected.exists(), payload
PY
ok_workspace_hook_init_repo_json=true

workspace_hook_init_recommended_repo_json="$TMP_ROOT/workspace_hook_init_recommended_repo.json"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-init --use-recommended-project --open-catalog --json > "$workspace_hook_init_recommended_repo_json"
)
python3 - "$workspace_hook_init_recommended_repo_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'workspace-hook-init', payload
assert payload['route_taken'] == 'recommended_workspace_project_explicit', payload
assert payload['use_recommended_project'] is True, payload
assert payload['selected_project_name'], payload
assert payload['selected_project_root'], payload
result = payload['result']
assert result['entrypoint'] == 'project-hook-open-catalog', payload
assert result['hook_catalog']['exists'] is True, payload
PY
ok_workspace_hook_init_recommended_repo_json=true

workspace_recommended_project_dir="$(python3 - "$workspace_hook_init_recommended_repo_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
print(payload['selected_project_root'])
PY
)"
rm -f "$workspace_recommended_project_dir/.ail/last_hook_suggestions.json"

workspace_hook_init_recommended_suggest_repo_json="$TMP_ROOT/workspace_hook_init_recommended_suggest_repo.json"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-init --use-recommended-project --suggest --json > "$workspace_hook_init_recommended_suggest_repo_json"
)
python3 - "$workspace_hook_init_recommended_suggest_repo_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'workspace-hook-init', payload
assert payload['route_taken'] == 'recommended_workspace_project_explicit', payload
assert payload['auto_seeded_recommended_query'] is True, payload
assert payload['auto_seeded_requested_hook_name'], payload
assert payload['auto_seeded_page_key_filter'], payload
assert payload['recommended_next_command'], payload
assert 'python3 -m cli workspace hook-init' in payload['recommended_next_command'], payload
assert '--follow-recommended' in payload['recommended_next_command'], payload
assert payload['workspace_hooks']['recent_hook_project'], payload
result = payload['result']
assert result['entrypoint'] == 'project-hook-suggest', payload
assert result['requested_hook_name'] == payload['auto_seeded_requested_hook_name'], payload
assert result['page_key_filter'] == payload['auto_seeded_page_key_filter'], payload
assert result['suggestions'], payload
assert result['recommended_next_command'], payload
PY
ok_workspace_hook_init_recommended_suggest_repo_json=true

workspace_hook_init_recommended_pick_repo_json="$TMP_ROOT/workspace_hook_init_recommended_pick_repo.json"
workspace_pick_project_dir="$workspace_recommended_project_dir"
workspace_pick_seed_page_key="$(python3 - "$workspace_hook_init_recommended_suggest_repo_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
print(payload['auto_seeded_page_key_filter'])
PY
)"
rm -f \
  "$workspace_pick_project_dir/frontend/src/ail-overrides/components/page.$workspace_pick_seed_page_key.before.vue" \
  "$workspace_pick_project_dir/frontend/src/ail-overrides/components/page.$workspace_pick_seed_page_key.after.vue" \
  "$workspace_pick_project_dir/frontend/src/ail-overrides/components/page.$workspace_pick_seed_page_key.before.html" \
  "$workspace_pick_project_dir/frontend/src/ail-overrides/components/page.$workspace_pick_seed_page_key.after.html"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-init --use-recommended-project --pick-recommended --json > "$workspace_hook_init_recommended_pick_repo_json"
)
python3 - "$workspace_hook_init_recommended_pick_repo_json" "$workspace_pick_project_dir" "$workspace_pick_seed_page_key" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, pathlib, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
project_root = pathlib.Path(sys.argv[2]).resolve()
seed_page_key = sys.argv[3]
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'workspace-hook-init', payload
assert payload['route_taken'] == 'recommended_workspace_project_explicit', payload
assert payload['auto_seeded_recommended_query'] is True, payload
result = payload['result']
assert result['entrypoint'] == 'project-hook-init', payload
assert result['selected_from_suggestions'] is True, payload
assert result['hook_name'].startswith(f'page.{seed_page_key}.'), payload
target_path = pathlib.Path(result['target_path']).resolve()
assert target_path.parent == (project_root / 'frontend/src/ail-overrides/components').resolve(), payload
assert target_path.exists(), payload
PY
ok_workspace_hook_init_recommended_pick_repo_json=true

workspace_summary_root_json="$TMP_ROOT/workspace_summary_root.json"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace summary --json > "$workspace_summary_root_json"
)
python3 - "$workspace_summary_root_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'workspace-summary', payload
assert payload['inside_ail_project'] is False, payload
assert payload['readiness']['status'] in {'ok', 'attention'}, payload
assert payload['rc']['status'] in {'ok', 'error', 'attention'}, payload
assert payload['hook_catalogs']['catalog_project_count'] >= 0, payload
if payload['hook_catalogs']['catalog_project_count'] > 0:
    assert payload['hook_catalogs']['recommended_hook_suggest_command'], payload
    assert payload['hook_catalogs']['recommended_workspace_hook_suggest_command'], payload
    assert payload['hook_catalogs']['recommended_workspace_hook_pick_command'], payload
    assert '--follow-recommended' in payload['hook_catalogs']['recommended_workspace_hook_pick_command'], payload
    assert payload['hook_catalogs']['preferred_workspace_hook_command'], payload
    assert payload['hook_catalogs']['preferred_workspace_hook_reason'], payload
    if payload['hook_catalogs']['recent_hook_project']:
        assert payload['hook_catalogs']['recent_workspace_hook_suggest_command'], payload
        assert payload['hook_catalogs']['recent_workspace_hook_pick_command'], payload
        assert '--use-last-project' in payload['hook_catalogs']['preferred_workspace_hook_command'], payload
    else:
        assert '--follow-recommended' in payload['hook_catalogs']['preferred_workspace_hook_command'], payload
assert payload['recommended_workspace_action'] in {'trial_run_landing', 'run_readiness_snapshot'}, payload
PY
ok_workspace_summary_repo_json=true

workspace_hook_init_follow_recommended_repo_json="$TMP_ROOT/workspace_hook_init_follow_recommended_repo.json"
workspace_follow_pick_project_dir="$(python3 - "$workspace_hook_init_recommended_repo_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
print(payload['selected_project_root'])
PY
)"
rm -f \
  "$workspace_follow_pick_project_dir/frontend/src/ail-overrides/components/page.home.before.vue" \
  "$workspace_follow_pick_project_dir/frontend/src/ail-overrides/components/page.home.after.vue" \
  "$workspace_follow_pick_project_dir/frontend/src/ail-overrides/components/page.home.before.html" \
  "$workspace_follow_pick_project_dir/frontend/src/ail-overrides/components/page.home.after.html"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-init --follow-recommended --json > "$workspace_hook_init_follow_recommended_repo_json"
)
python3 - "$workspace_hook_init_follow_recommended_repo_json" "$workspace_follow_pick_project_dir" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, pathlib, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
project_root = pathlib.Path(sys.argv[2]).resolve()
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'workspace-hook-init', payload
assert payload['route_taken'] == 'recommended_workspace_project_explicit', payload
assert payload['use_recommended_project'] is True, payload
assert payload['follow_recommended'] is True, payload
assert payload['auto_seeded_recommended_query'] is True, payload
result = payload['result']
assert result['entrypoint'] == 'project-hook-init', payload
assert result['selected_from_suggestions'] is True, payload
target_path = pathlib.Path(result['target_path']).resolve()
assert target_path.parent == (project_root / 'frontend/src/ail-overrides/components').resolve(), payload
assert target_path.exists(), payload
PY
ok_workspace_hook_init_follow_recommended_repo_json=true

workspace_hook_init_use_last_project_seed_json="$TMP_ROOT/workspace_hook_init_use_last_project_seed.json"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-init home --project-name WorkspaceHookInitSmoke --suggest --page-key home --section-key hero --slot-key hero-actions --json > "$workspace_hook_init_use_last_project_seed_json"
)
workspace_hook_init_use_last_project_repo_json="$TMP_ROOT/workspace_hook_init_use_last_project_repo.json"
rm -f \
  "$workspace_hook_project_dir/frontend/src/ail-overrides/components/page.home.section.hero.slot.hero-actions.before.vue" \
  "$workspace_hook_project_dir/frontend/src/ail-overrides/components/page.home.section.hero.slot.hero-actions.after.vue" \
  "$workspace_hook_project_dir/frontend/src/ail-overrides/components/page.home.section.hero.slot.hero-actions.before.html" \
  "$workspace_hook_project_dir/frontend/src/ail-overrides/components/page.home.section.hero.slot.hero-actions.after.html"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-init --use-last-project --pick-recommended --json > "$workspace_hook_init_use_last_project_repo_json"
)
python3 - "$workspace_hook_init_use_last_project_repo_json" "$workspace_hook_project_dir" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, pathlib, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
project_root = pathlib.Path(sys.argv[2]).resolve()
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'workspace-hook-init', payload
assert payload['route_taken'] == 'recent_workspace_project_explicit', payload
assert payload['use_last_project'] is True, payload
assert payload['auto_seeded_recommended_query'] is True, payload
assert payload['auto_seeded_from_recent_project_memory'] is True, payload
assert payload['auto_seeded_page_key_filter'] == 'home', payload
assert payload['auto_seeded_section_key_filter'] == 'hero', payload
assert payload['auto_seeded_slot_key_filter'] == 'hero-actions', payload
assert payload['selected_project_name'] == project_root.name, payload
result = payload['result']
assert result['entrypoint'] == 'project-hook-init', payload
assert result['selected_from_suggestions'] is True, payload
target_path = pathlib.Path(result['target_path']).resolve()
assert target_path.parent == (project_root / 'frontend/src/ail-overrides/components').resolve(), payload
assert target_path.exists(), payload
PY
ok_workspace_hook_init_use_last_project_repo_json=true

workspace_hook_continue_dry_run_repo_json="$TMP_ROOT/workspace_hook_continue_dry_run_repo.json"
rm -f \
  "$workspace_hook_project_dir/frontend/src/ail-overrides/components/page.home.section.hero.slot.hero-actions.before.vue" \
  "$workspace_hook_project_dir/frontend/src/ail-overrides/components/page.home.section.hero.slot.hero-actions.after.vue" \
  "$workspace_hook_project_dir/frontend/src/ail-overrides/components/page.home.section.hero.slot.hero-actions.before.html" \
  "$workspace_hook_project_dir/frontend/src/ail-overrides/components/page.home.section.hero.slot.hero-actions.after.html"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-continue --dry-run --json > "$workspace_hook_continue_dry_run_repo_json"
)
python3 - "$workspace_hook_continue_dry_run_repo_json" "$workspace_hook_project_dir" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, pathlib, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
project_root = pathlib.Path(sys.argv[2]).resolve()
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'workspace-hook-continue', payload
assert payload['dry_run'] is True, payload
assert payload['dry_run_summary'], payload
assert payload['dry_run_target_reason'], payload
assert payload['dry_run_confirm_command'], payload
assert payload['continue_strategy'] in {'recent_workspace_project', 'recommended_workspace_project'}, payload
assert payload['selected_strategy_command'] and '--dry-run' in payload['selected_strategy_command'], payload
assert payload['resume_exact_command'] and '--dry-run' in payload['resume_exact_command'], payload
assert payload['preferred_followup_command'] and '--dry-run' in payload['preferred_followup_command'], payload
assert payload['rerun_without_dry_run_command'], payload
assert '--dry-run' not in payload['rerun_without_dry_run_command'], payload
assert payload['dry_run_confirm_command'] == payload['rerun_without_dry_run_command'], payload
result = payload['result']
assert result['entrypoint'] == 'project-hook-init', payload
assert result['dry_run'] is True, payload
assert result['wrote'] is False, payload
assert result['would_write'] is True, payload
target_path = pathlib.Path(result['target_path']).resolve()
assert target_path.parent == (project_root / 'frontend/src/ail-overrides/components').resolve(), payload
assert not target_path.exists(), payload
PY
ok_workspace_hook_continue_dry_run_repo_json=true

workspace_hook_continue_text_compact_repo_txt="$TMP_ROOT/workspace_hook_continue_text_compact_repo.txt"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-continue --dry-run --text-compact > "$workspace_hook_continue_text_compact_repo_txt"
)
grep -q "Workspace hook-continue (compact)" "$workspace_hook_continue_text_compact_repo_txt"
grep -q "^- dry_run: true$" "$workspace_hook_continue_text_compact_repo_txt"
grep -q "^- target_summary: " "$workspace_hook_continue_text_compact_repo_txt"
grep -q "^- target_reason: " "$workspace_hook_continue_text_compact_repo_txt"
grep -q "^- target_path: " "$workspace_hook_continue_text_compact_repo_txt"
grep -q "^- human_next_command: " "$workspace_hook_continue_text_compact_repo_txt"
grep -q "^- runnable_next_command: " "$workspace_hook_continue_text_compact_repo_txt"
grep -q "^- force_next_command: " "$workspace_hook_continue_text_compact_repo_txt"
ok_workspace_hook_continue_text_compact_repo=true

workspace_hook_continue_inspect_target_text_compact_repo_txt="$TMP_ROOT/workspace_hook_continue_inspect_target_text_compact_repo.txt"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-continue --dry-run --inspect-target --text-compact > "$workspace_hook_continue_inspect_target_text_compact_repo_txt"
)
grep -q "Workspace hook-continue (compact)" "$workspace_hook_continue_inspect_target_text_compact_repo_txt"
grep -q "^- inspect_target_summary: " "$workspace_hook_continue_inspect_target_text_compact_repo_txt"
grep -q "^- inspect_target_parent_summary: " "$workspace_hook_continue_inspect_target_text_compact_repo_txt"
grep -q "^- inspected_target_path: " "$workspace_hook_continue_inspect_target_text_compact_repo_txt"
grep -q "^- inspected_target_exists: " "$workspace_hook_continue_inspect_target_text_compact_repo_txt"
grep -q "^- nearby_entries: " "$workspace_hook_continue_inspect_target_text_compact_repo_txt"
ok_workspace_hook_continue_inspect_target_text_compact_repo=true

workspace_hook_continue_explain_repo_txt="$TMP_ROOT/workspace_hook_continue_explain_repo.txt"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-continue --dry-run --explain > "$workspace_hook_continue_explain_repo_txt"
)
grep -q "^Explain:$" "$workspace_hook_continue_explain_repo_txt"
grep -q "^- strategy: " "$workspace_hook_continue_explain_repo_txt"
grep -q "^- memory: " "$workspace_hook_continue_explain_repo_txt"
grep -q "^- resolution: " "$workspace_hook_continue_explain_repo_txt"
grep -q "^- target: " "$workspace_hook_continue_explain_repo_txt"
grep -q "^- followup: " "$workspace_hook_continue_explain_repo_txt"
ok_workspace_hook_continue_explain_repo=true

workspace_hook_continue_emit_shell_repo_txt="$TMP_ROOT/workspace_hook_continue_emit_shell_repo.txt"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-continue --dry-run --emit-shell > "$workspace_hook_continue_emit_shell_repo_txt"
)
grep -q "^PYTHONPATH=${ROOT} python3 -m cli workspace hook-continue " "$workspace_hook_continue_emit_shell_repo_txt"
grep -vq -- "--dry-run" "$workspace_hook_continue_emit_shell_repo_txt"
ok_workspace_hook_continue_emit_shell_repo=true

workspace_hook_continue_emit_confirm_shell_repo_txt="$TMP_ROOT/workspace_hook_continue_emit_confirm_shell_repo.txt"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-continue --dry-run --emit-confirm-shell > "$workspace_hook_continue_emit_confirm_shell_repo_txt"
)
grep -q "^PYTHONPATH=${ROOT} python3 -m cli workspace hook-continue --json$" "$workspace_hook_continue_emit_confirm_shell_repo_txt"
ok_workspace_hook_continue_emit_confirm_shell_repo=true

workspace_hook_continue_emit_target_path_repo_txt="$TMP_ROOT/workspace_hook_continue_emit_target_path_repo.txt"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-continue --dry-run --emit-target-path > "$workspace_hook_continue_emit_target_path_repo_txt"
)
grep -q "^${ROOT}/output_projects/.*/frontend/src/ail-overrides/components/.*$" "$workspace_hook_continue_emit_target_path_repo_txt"
ok_workspace_hook_continue_emit_target_path_repo=true

workspace_hook_continue_emit_target_dir_repo_txt="$TMP_ROOT/workspace_hook_continue_emit_target_dir_repo.txt"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-continue --dry-run --emit-target-dir > "$workspace_hook_continue_emit_target_dir_repo_txt"
)
grep -q "^${ROOT}/output_projects/.*/frontend/src/ail-overrides/components$" "$workspace_hook_continue_emit_target_dir_repo_txt"
ok_workspace_hook_continue_emit_target_dir_repo=true

workspace_hook_continue_emit_target_project_root_repo_txt="$TMP_ROOT/workspace_hook_continue_emit_target_project_root_repo.txt"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-continue --dry-run --emit-target-project-root > "$workspace_hook_continue_emit_target_project_root_repo_txt"
)
grep -q "^${ROOT}/output_projects/.*$" "$workspace_hook_continue_emit_target_project_root_repo_txt"
ok_workspace_hook_continue_emit_target_project_root_repo=true

workspace_hook_continue_emit_target_project_name_repo_txt="$TMP_ROOT/workspace_hook_continue_emit_target_project_name_repo.txt"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-continue --dry-run --emit-target-project-name > "$workspace_hook_continue_emit_target_project_name_repo_txt"
)
grep -Eq "^[A-Za-z0-9._-]+$" "$workspace_hook_continue_emit_target_project_name_repo_txt"
ok_workspace_hook_continue_emit_target_project_name_repo=true

workspace_hook_continue_emit_target_relative_path_repo_txt="$TMP_ROOT/workspace_hook_continue_emit_target_relative_path_repo.txt"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-continue --dry-run --emit-target-relative-path > "$workspace_hook_continue_emit_target_relative_path_repo_txt"
)
grep -q "^frontend/src/ail-overrides/components/.*$" "$workspace_hook_continue_emit_target_relative_path_repo_txt"
ok_workspace_hook_continue_emit_target_relative_path_repo=true

workspace_hook_continue_emit_target_bundle_repo_txt="$TMP_ROOT/workspace_hook_continue_emit_target_bundle_repo.txt"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-continue --dry-run --emit-target-bundle > "$workspace_hook_continue_emit_target_bundle_repo_txt"
)
python3 - "$workspace_hook_continue_emit_target_bundle_repo_txt" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
from pathlib import Path
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['target_path'].startswith(f'{OUTPUT_PROJECTS_ROOT}/'), payload
assert payload['target_dir'].endswith('/frontend/src/ail-overrides/components'), payload
assert payload['target_project_root'].startswith(f'{OUTPUT_PROJECTS_ROOT}/'), payload
assert str(payload['target_project_name']) == Path(payload['target_project_root']).name, payload
assert payload['target_relative_path'].startswith('frontend/src/ail-overrides/components/'), payload
assert payload['open_command'].startswith(f'inspect {OUTPUT_PROJECTS_ROOT}/'), payload
assert payload['confirm_command'] == f'PYTHONPATH={ROOT} python3 -m cli workspace hook-continue --json', payload
PY
ok_workspace_hook_continue_emit_target_bundle_repo=true

workspace_hook_continue_emit_open_shell_repo_txt="$TMP_ROOT/workspace_hook_continue_emit_open_shell_repo.txt"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-continue --dry-run --emit-open-shell > "$workspace_hook_continue_emit_open_shell_repo_txt"
)
grep -q "^inspect ${ROOT}/output_projects/.*/frontend/src/ail-overrides/components/.*$" "$workspace_hook_continue_emit_open_shell_repo_txt"
ok_workspace_hook_continue_emit_open_shell_repo=true

workspace_hook_continue_copy_open_command_repo_txt="$TMP_ROOT/workspace_hook_continue_copy_open_command_repo.txt"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-continue --dry-run --copy-open-command > "$workspace_hook_continue_copy_open_command_repo_txt"
)
grep -q "^Workspace hook-continue open command copied$" "$workspace_hook_continue_copy_open_command_repo_txt"
grep -q "^- copied_open_command: inspect ${ROOT}/output_projects/.*/frontend/src/ail-overrides/components/.*$" "$workspace_hook_continue_copy_open_command_repo_txt"
workspace_hook_continue_copied_open_command="$(pbpaste)"
case "$workspace_hook_continue_copied_open_command" in
  "inspect ${ROOT}/output_projects/"*)
    ;;
  *)
    echo "workspace hook-continue --copy-open-command did not copy an inspect command"
    exit 1
    ;;
esac
ok_workspace_hook_continue_copy_open_command_repo=true

workspace_hook_continue_copy_confirm_command_repo_txt="$TMP_ROOT/workspace_hook_continue_copy_confirm_command_repo.txt"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-continue --dry-run --copy-confirm-command > "$workspace_hook_continue_copy_confirm_command_repo_txt"
)
grep -q "^Workspace hook-continue confirm command copied$" "$workspace_hook_continue_copy_confirm_command_repo_txt"
grep -q "^- copied_confirm_command: PYTHONPATH=${ROOT} python3 -m cli workspace hook-continue --json$" "$workspace_hook_continue_copy_confirm_command_repo_txt"
workspace_hook_continue_copied_confirm_command="$(pbpaste)"
case "$workspace_hook_continue_copied_confirm_command" in
  "PYTHONPATH=${ROOT} python3 -m cli workspace hook-continue --json")
    ;;
  *)
    echo "workspace hook-continue --copy-confirm-command did not copy the expected confirm command"
    exit 1
    ;;
esac
ok_workspace_hook_continue_copy_confirm_command_repo=true

workspace_hook_continue_copy_target_path_repo_txt="$TMP_ROOT/workspace_hook_continue_copy_target_path_repo.txt"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-continue --dry-run --copy-target-path > "$workspace_hook_continue_copy_target_path_repo_txt"
)
grep -q "^Workspace hook-continue target path copied$" "$workspace_hook_continue_copy_target_path_repo_txt"
grep -q "^- copied_target_path: ${ROOT}/output_projects/.*/frontend/src/ail-overrides/components/.*$" "$workspace_hook_continue_copy_target_path_repo_txt"
workspace_hook_continue_copied_target_path="$(pbpaste)"
case "$workspace_hook_continue_copied_target_path" in
  "${ROOT}/output_projects/"*)
    ;;
  *)
    echo "workspace hook-continue --copy-target-path did not copy the resolved hook target path"
    exit 1
    ;;
esac
ok_workspace_hook_continue_copy_target_path_repo=true

workspace_hook_continue_copy_target_dir_repo_txt="$TMP_ROOT/workspace_hook_continue_copy_target_dir_repo.txt"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-continue --dry-run --copy-target-dir > "$workspace_hook_continue_copy_target_dir_repo_txt"
)
grep -q "^Workspace hook-continue target directory copied$" "$workspace_hook_continue_copy_target_dir_repo_txt"
grep -q "^- copied_target_dir: ${ROOT}/output_projects/.*/frontend/src/ail-overrides/components$" "$workspace_hook_continue_copy_target_dir_repo_txt"
workspace_hook_continue_copied_target_dir="$(pbpaste)"
case "$workspace_hook_continue_copied_target_dir" in
  "${ROOT}/output_projects/"*)
    ;;
  *)
    echo "workspace hook-continue --copy-target-dir did not copy the resolved hook target directory"
    exit 1
    ;;
esac
ok_workspace_hook_continue_copy_target_dir_repo=true

workspace_hook_continue_copy_target_project_root_repo_txt="$TMP_ROOT/workspace_hook_continue_copy_target_project_root_repo.txt"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-continue --dry-run --copy-target-project-root > "$workspace_hook_continue_copy_target_project_root_repo_txt"
)
grep -q "^Workspace hook-continue target project root copied$" "$workspace_hook_continue_copy_target_project_root_repo_txt"
grep -q "^- copied_target_project_root: ${ROOT}/output_projects/.*$" "$workspace_hook_continue_copy_target_project_root_repo_txt"
workspace_hook_continue_copied_target_project_root="$(pbpaste)"
case "$workspace_hook_continue_copied_target_project_root" in
  "${ROOT}/output_projects/"*)
    ;;
  *)
    echo "workspace hook-continue --copy-target-project-root did not copy the resolved target project root"
    exit 1
    ;;
esac
ok_workspace_hook_continue_copy_target_project_root_repo=true

workspace_hook_continue_copy_target_project_name_repo_txt="$TMP_ROOT/workspace_hook_continue_copy_target_project_name_repo.txt"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-continue --dry-run --copy-target-project-name > "$workspace_hook_continue_copy_target_project_name_repo_txt"
)
grep -q "^Workspace hook-continue target project name copied$" "$workspace_hook_continue_copy_target_project_name_repo_txt"
grep -Eq "^- copied_target_project_name: [A-Za-z0-9._-]+$" "$workspace_hook_continue_copy_target_project_name_repo_txt"
workspace_hook_continue_copied_target_project_name="$(pbpaste)"
case "$workspace_hook_continue_copied_target_project_name" in
  *"/"*)
    echo "workspace hook-continue --copy-target-project-name copied a path instead of a project name"
    exit 1
    ;;
  "")
    echo "workspace hook-continue --copy-target-project-name copied an empty project name"
    exit 1
    ;;
  *)
    ;;
esac
ok_workspace_hook_continue_copy_target_project_name_repo=true

workspace_hook_continue_copy_target_relative_path_repo_txt="$TMP_ROOT/workspace_hook_continue_copy_target_relative_path_repo.txt"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-continue --dry-run --copy-target-relative-path > "$workspace_hook_continue_copy_target_relative_path_repo_txt"
)
grep -q "^Workspace hook-continue target relative path copied$" "$workspace_hook_continue_copy_target_relative_path_repo_txt"
grep -q "^- copied_target_relative_path: frontend/src/ail-overrides/components/.*$" "$workspace_hook_continue_copy_target_relative_path_repo_txt"
workspace_hook_continue_copied_target_relative_path="$(pbpaste)"
case "$workspace_hook_continue_copied_target_relative_path" in
  "frontend/src/ail-overrides/components/"*)
    ;;
  *)
    echo "workspace hook-continue --copy-target-relative-path did not copy the resolved target relative path"
    exit 1
    ;;
esac
ok_workspace_hook_continue_copy_target_relative_path_repo=true

workspace_hook_continue_copy_target_bundle_repo_txt="$TMP_ROOT/workspace_hook_continue_copy_target_bundle_repo.txt"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-continue --dry-run --copy-target-bundle > "$workspace_hook_continue_copy_target_bundle_repo_txt"
)
grep -q "^Workspace hook-continue target bundle copied$" "$workspace_hook_continue_copy_target_bundle_repo_txt"
grep -q "^- copied_target_bundle: {" "$workspace_hook_continue_copy_target_bundle_repo_txt"
workspace_hook_continue_copied_target_bundle="$(pbpaste)"
WORKSPACE_HOOK_CONTINUE_COPIED_TARGET_BUNDLE="$workspace_hook_continue_copied_target_bundle" python3 - <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, os
from pathlib import Path
payload = json.loads(os.environ['WORKSPACE_HOOK_CONTINUE_COPIED_TARGET_BUNDLE'])
assert payload['target_path'].startswith(f'{OUTPUT_PROJECTS_ROOT}/'), payload
assert payload['target_dir'].endswith('/frontend/src/ail-overrides/components'), payload
assert payload['target_project_root'].startswith(f'{OUTPUT_PROJECTS_ROOT}/'), payload
assert str(payload['target_project_name']) == Path(payload['target_project_root']).name, payload
assert payload['target_relative_path'].startswith('frontend/src/ail-overrides/components/'), payload
assert payload['open_command'].startswith(f'inspect {OUTPUT_PROJECTS_ROOT}/'), payload
assert payload['confirm_command'] == f'PYTHONPATH={ROOT} python3 -m cli workspace hook-continue --json', payload
PY
ok_workspace_hook_continue_copy_target_bundle_repo=true

workspace_hook_continue_copy_command_repo_txt="$TMP_ROOT/workspace_hook_continue_copy_command_repo.txt"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-continue --dry-run --copy-command > "$workspace_hook_continue_copy_command_repo_txt"
)
grep -q "^Workspace hook-continue command copied$" "$workspace_hook_continue_copy_command_repo_txt"
grep -q "^- copied_command: " "$workspace_hook_continue_copy_command_repo_txt"
workspace_hook_continue_copied_command="$(pbpaste)"
case "$workspace_hook_continue_copied_command" in
  "PYTHONPATH=${ROOT} python3 -m cli workspace hook-continue "*)
    ;;
  *)
    echo "unexpected clipboard command: $workspace_hook_continue_copied_command" >&2
    exit 1
    ;;
esac
case "$workspace_hook_continue_copied_command" in
  *"--dry-run"*)
    echo "clipboard command unexpectedly kept --dry-run: $workspace_hook_continue_copied_command" >&2
    exit 1
    ;;
  *)
    ;;
esac
ok_workspace_hook_continue_copy_command_repo=true

workspace_hook_continue_run_open_command_repo_json="$TMP_ROOT/workspace_hook_continue_run_open_command_repo.json"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-continue --dry-run --run-open-command --json > "$workspace_hook_continue_run_open_command_repo_json"
)
python3 - "$workspace_hook_continue_run_open_command_repo_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'workspace-hook-continue', payload
assert payload['dry_run'] is True, payload
assert payload['run_open_command'], payload
assert payload['run_open_command'].startswith('inspect '), payload
assert payload['run_open_command_requires_confirmation'] is True, payload
assert payload['run_open_command_confirmed'] is False, payload
assert payload['ran_open_command'] is False, payload
assert payload['run_open_command_exit_code'] == 0, payload
assert payload['run_open_result'] is None, payload
assert payload['run_open_command_warning'], payload
assert payload['run_open_command_confirm_command'], payload
assert '--yes' in payload['run_open_command_confirm_command'], payload
PY
ok_workspace_hook_continue_run_open_command_repo=true

workspace_hook_continue_run_open_command_yes_repo_json="$TMP_ROOT/workspace_hook_continue_run_open_command_yes_repo.json"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-continue --dry-run --run-open-command --yes --json > "$workspace_hook_continue_run_open_command_yes_repo_json"
)
python3 - "$workspace_hook_continue_run_open_command_yes_repo_json" "$workspace_hook_project_dir" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, pathlib, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
project_root = pathlib.Path(sys.argv[2]).resolve()
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'workspace-hook-continue', payload
assert payload['run_open_command'], payload
assert payload['run_open_command_confirmed'] is True, payload
assert payload['ran_open_command'] is True, payload
assert payload['run_open_command_exit_code'] == 0, payload
assert isinstance(payload['run_open_result'], dict), payload
run_open_result = payload['run_open_result']
target_path = pathlib.Path(run_open_result['path']).resolve()
assert target_path.parent == (project_root / 'frontend/src/ail-overrides/components').resolve(), payload
assert run_open_result['exists'] is False, payload
assert run_open_result['line_count'] == 0, payload
PY
ok_workspace_hook_continue_run_open_command_yes_repo=true

workspace_hook_continue_run_command_repo_json="$TMP_ROOT/workspace_hook_continue_run_command_repo.json"
rm -f \
  "$workspace_hook_project_dir/frontend/src/ail-overrides/components/page.home.section.hero.slot.hero-actions.before.vue" \
  "$workspace_hook_project_dir/frontend/src/ail-overrides/components/page.home.section.hero.slot.hero-actions.after.vue" \
  "$workspace_hook_project_dir/frontend/src/ail-overrides/components/page.home.section.hero.slot.hero-actions.before.html" \
  "$workspace_hook_project_dir/frontend/src/ail-overrides/components/page.home.section.hero.slot.hero-actions.after.html"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-continue --dry-run --run-command --json > "$workspace_hook_continue_run_command_repo_json"
)
python3 - "$workspace_hook_continue_run_command_repo_json" "$workspace_hook_project_dir" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, pathlib, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
project_root = pathlib.Path(sys.argv[2]).resolve()
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'workspace-hook-continue', payload
assert payload['dry_run'] is True, payload
assert payload['run_command'], payload
assert '--dry-run' not in payload['run_command'], payload
assert payload['run_command_requires_confirmation'] is True, payload
assert payload['run_command_confirmed'] is False, payload
assert payload['ran_command'] is False, payload
assert payload['run_command_exit_code'] == 0, payload
assert payload['run_result'] is None, payload
assert payload['run_command_warning'], payload
assert payload['run_command_confirm_command'], payload
assert '--yes' in payload['run_command_confirm_command'], payload
target_path = pathlib.Path((payload['result'])['target_path']).resolve()
assert target_path.parent == (project_root / 'frontend/src/ail-overrides/components').resolve(), payload
assert not target_path.exists(), payload
PY
ok_workspace_hook_continue_run_command_repo=true

workspace_hook_continue_run_command_yes_repo_json="$TMP_ROOT/workspace_hook_continue_run_command_yes_repo.json"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-continue --dry-run --run-command --yes --json > "$workspace_hook_continue_run_command_yes_repo_json"
)
python3 - "$workspace_hook_continue_run_command_yes_repo_json" "$workspace_hook_project_dir" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, pathlib, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
project_root = pathlib.Path(sys.argv[2]).resolve()
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'workspace-hook-continue', payload
assert payload['run_command'], payload
assert payload['run_command_confirmed'] is True, payload
assert payload['ran_command'] is True, payload
assert payload['run_command_exit_code'] == 0, payload
assert isinstance(payload['run_result'], dict), payload
run_result = payload['run_result']
assert run_result['entrypoint'] == 'workspace-hook-continue', payload
inner = run_result['result']
assert inner['entrypoint'] == 'project-hook-init', payload
target_path = pathlib.Path(inner['target_path']).resolve()
assert target_path.parent == (project_root / 'frontend/src/ail-overrides/components').resolve(), payload
assert target_path.exists(), payload
PY
ok_workspace_hook_continue_run_command_yes_repo=true

workspace_hook_continue_inspect_target_repo_json="$TMP_ROOT/workspace_hook_continue_inspect_target_repo.json"
rm -f \
  "$workspace_hook_project_dir/frontend/src/ail-overrides/components/page.home.section.hero.slot.hero-actions.before.vue" \
  "$workspace_hook_project_dir/frontend/src/ail-overrides/components/page.home.section.hero.slot.hero-actions.after.vue" \
  "$workspace_hook_project_dir/frontend/src/ail-overrides/components/page.home.section.hero.slot.hero-actions.before.html" \
  "$workspace_hook_project_dir/frontend/src/ail-overrides/components/page.home.section.hero.slot.hero-actions.after.html"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-continue --dry-run --inspect-target --json > "$workspace_hook_continue_inspect_target_repo_json"
)
python3 - "$workspace_hook_continue_inspect_target_repo_json" "$workspace_hook_project_dir" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, pathlib, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
project_root = pathlib.Path(sys.argv[2]).resolve()
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'workspace-hook-continue', payload
assert payload['dry_run'] is True, payload
assert payload['inspect_target_summary'], payload
target_inspection = payload['target_inspection']
parent_inspection = payload['target_parent_inspection']
assert target_inspection['kind'] == 'file', payload
assert target_inspection['exists'] is False, payload
target_path = pathlib.Path(target_inspection['path']).resolve()
assert target_path.parent == (project_root / 'frontend/src/ail-overrides/components').resolve(), payload
assert parent_inspection['kind'] == 'directory', payload
assert parent_inspection['exists'] is True, payload
assert pathlib.Path(parent_inspection['path']).resolve() == target_path.parent, payload
assert parent_inspection['entry_count'] >= 1, payload
PY
ok_workspace_hook_continue_inspect_target_repo=true

workspace_hook_continue_open_target_repo_json="$TMP_ROOT/workspace_hook_continue_open_target_repo.json"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-continue --dry-run --open-target --json > "$workspace_hook_continue_open_target_repo_json"
)
python3 - "$workspace_hook_continue_open_target_repo_json" "$workspace_hook_project_dir" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, pathlib, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
project_root = pathlib.Path(sys.argv[2]).resolve()
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'workspace-hook-continue', payload
assert payload['dry_run'] is True, payload
assert payload['open_target_summary'], payload
assert payload['open_target_reason'], payload
assert payload['open_target_command'].startswith('inspect '), payload
open_target = payload['open_target']
assert open_target['label'] == 'hook_target', payload
assert open_target['kind'] == 'file', payload
target_path = pathlib.Path(open_target['path']).resolve()
assert target_path.parent == (project_root / 'frontend/src/ail-overrides/components').resolve(), payload
assert open_target['exists'] is False, payload
assert payload['open_target_command'].endswith(str(target_path)), payload
PY
ok_workspace_hook_continue_open_target_repo=true

workspace_hook_continue_open_now_repo_json="$TMP_ROOT/workspace_hook_continue_open_now_repo.json"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-continue --dry-run --open-now --json > "$workspace_hook_continue_open_now_repo_json"
)
python3 - "$workspace_hook_continue_open_now_repo_json" "$workspace_hook_project_dir" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, pathlib, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
project_root = pathlib.Path(sys.argv[2]).resolve()
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'workspace-hook-continue', payload
assert payload['dry_run'] is True, payload
assert payload['open_now'] is True, payload
assert payload['open_now_summary'], payload
assert payload['open_now_reason'], payload
open_now_result = payload['open_now_result']
assert open_now_result['kind'] == 'file', payload
assert open_now_result['exists'] is False, payload
target_path = pathlib.Path(open_now_result['path']).resolve()
assert target_path.parent == (project_root / 'frontend/src/ail-overrides/components').resolve(), payload
assert open_now_result['line_count'] == 0, payload
PY
ok_workspace_hook_continue_open_now_repo=true

workspace_hook_continue_open_now_text_compact_repo_txt="$TMP_ROOT/workspace_hook_continue_open_now_text_compact_repo.txt"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-continue --dry-run --open-now --text-compact > "$workspace_hook_continue_open_now_text_compact_repo_txt"
)
grep -q "Workspace hook-continue (compact)" "$workspace_hook_continue_open_now_text_compact_repo_txt"
grep -q "^- open_now_summary: " "$workspace_hook_continue_open_now_text_compact_repo_txt"
grep -q "^- open_now_path: " "$workspace_hook_continue_open_now_text_compact_repo_txt"
grep -q "^- open_now_exists: " "$workspace_hook_continue_open_now_text_compact_repo_txt"
grep -q "^- open_now_line_count: " "$workspace_hook_continue_open_now_text_compact_repo_txt"
ok_workspace_hook_continue_open_now_text_compact_repo=true

grep -q "^- target_reason: " "$workspace_hook_continue_open_now_text_compact_repo_txt"
ok_workspace_hook_continue_open_now_text_compact_has_reason_repo=true

workspace_hook_continue_repo_json="$TMP_ROOT/workspace_hook_continue_repo.json"
rm -f \
  "$workspace_hook_project_dir/frontend/src/ail-overrides/components/page.home.section.hero.slot.hero-actions.before.vue" \
  "$workspace_hook_project_dir/frontend/src/ail-overrides/components/page.home.section.hero.slot.hero-actions.after.vue" \
  "$workspace_hook_project_dir/frontend/src/ail-overrides/components/page.home.section.hero.slot.hero-actions.before.html" \
  "$workspace_hook_project_dir/frontend/src/ail-overrides/components/page.home.section.hero.slot.hero-actions.after.html"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-continue --json > "$workspace_hook_continue_repo_json"
)
python3 - "$workspace_hook_continue_repo_json" "$workspace_hook_project_dir" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, pathlib, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
project_root = pathlib.Path(sys.argv[2]).resolve()
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'workspace-hook-continue', payload
assert payload['continue_strategy'] in {'recent_workspace_project', 'recommended_workspace_project'}, payload
assert payload['continue_summary'], payload
assert payload['continue_reason'], payload
assert payload['selected_project_name'], payload
assert payload['selected_strategy_command'], payload
assert payload['resume_exact_command'], payload
assert payload['broaden_to_section_command'], payload
assert payload['broaden_to_page_command'], payload
assert payload['auto_broaden_command'], payload
assert payload['preferred_followup_command'], payload
assert payload['preferred_followup_reason'], payload
assert payload['rerun_with_force_command'], payload
assert payload['recommended_next_command'], payload
if payload['continue_strategy'] == 'recent_workspace_project':
    assert payload['used_workspace_recent_query_memory'] is True, payload
    assert payload['continued_page_key_filter'] == 'home', payload
    assert payload['continued_section_key_filter'] == 'hero', payload
    assert payload['continued_slot_key_filter'] == 'hero-actions', payload
result = payload['result']
assert result['entrypoint'] == 'project-hook-init', payload
target_path = pathlib.Path(result['target_path']).resolve()
assert target_path.parent == (project_root / 'frontend/src/ail-overrides/components').resolve(), payload
assert target_path.exists(), payload
PY
ok_workspace_hook_continue_repo_json=true

workspace_hook_continue_open_now_preview_repo_txt="$TMP_ROOT/workspace_hook_continue_open_now_preview_repo.txt"
(
  cd "$ROOT"
  set +e
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-continue --dry-run --open-now --text-compact > "$workspace_hook_continue_open_now_preview_repo_txt"
  exit_code=$?
  set -e
  if [ "$exit_code" -ne 0 ] && [ "$exit_code" -ne 3 ]; then
    exit "$exit_code"
  fi
)
grep -q "^- open_now_exists: True$" "$workspace_hook_continue_open_now_preview_repo_txt"
grep -q "^- open_now_line_count: " "$workspace_hook_continue_open_now_preview_repo_txt"
grep -q "^- open_now_preview: " "$workspace_hook_continue_open_now_preview_repo_txt"
ok_workspace_hook_continue_open_now_preview_repo=true

workspace_hook_continue_broaden_repo_json="$TMP_ROOT/workspace_hook_continue_broaden_repo.json"
rm -f \
  "$workspace_hook_project_dir/frontend/src/ail-overrides/components/page.home.before.vue" \
  "$workspace_hook_project_dir/frontend/src/ail-overrides/components/page.home.after.vue" \
  "$workspace_hook_project_dir/frontend/src/ail-overrides/components/page.home.before.html" \
  "$workspace_hook_project_dir/frontend/src/ail-overrides/components/page.home.after.html"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-continue --broaden-to page --json > "$workspace_hook_continue_broaden_repo_json"
)
python3 - "$workspace_hook_continue_broaden_repo_json" "$workspace_hook_project_dir" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, pathlib, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
project_root = pathlib.Path(sys.argv[2]).resolve()
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'workspace-hook-continue', payload
assert payload['broaden_to'] == 'page', payload
assert payload['continue_strategy'] == 'recent_workspace_project', payload
assert payload['broadened_recent_query'] is True, payload
assert payload['used_workspace_recent_query_memory'] is True, payload
assert payload['resume_exact_command'], payload
assert '--broaden-to section' in payload['broaden_to_section_command'], payload
assert '--broaden-to page' in payload['broaden_to_page_command'], payload
assert payload['preferred_followup_command'] == payload['broaden_to_page_command'], payload
assert payload['continued_page_key_filter'] == 'home', payload
assert payload['continued_section_key_filter'] is None, payload
assert payload['continued_slot_key_filter'] is None, payload
result = payload['result']
assert result['entrypoint'] == 'project-hook-init', payload
target_path = pathlib.Path(result['target_path']).resolve()
assert target_path.parent == (project_root / 'frontend/src/ail-overrides/components').resolve(), payload
assert target_path.exists(), payload
PY
ok_workspace_hook_continue_broaden_repo_json=true

workspace_hook_continue_auto_repo_json="$TMP_ROOT/workspace_hook_continue_auto_repo.json"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-init home --project-name WorkspaceHookInitSmoke --suggest --page-key home --section-key hero --slot-key hero-actions --json > /dev/null
)
cat > "$workspace_hook_project_dir/frontend/src/ail-overrides/components/page.home.section.hero.slot.hero-actions.before.vue" <<'EOF'
<template>
  <div>existing exact slot override</div>
</template>
EOF
rm -f \
  "$workspace_hook_project_dir/frontend/src/ail-overrides/components/page.home.section.hero.before.vue" \
  "$workspace_hook_project_dir/frontend/src/ail-overrides/components/page.home.section.hero.after.vue" \
  "$workspace_hook_project_dir/frontend/src/ail-overrides/components/page.home.before.vue" \
  "$workspace_hook_project_dir/frontend/src/ail-overrides/components/page.home.after.vue"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace hook-continue --broaden-to auto --json > "$workspace_hook_continue_auto_repo_json"
)
python3 - "$workspace_hook_continue_auto_repo_json" "$workspace_hook_project_dir" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, pathlib, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
project_root = pathlib.Path(sys.argv[2]).resolve()
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'workspace-hook-continue', payload
assert payload['broaden_to'] == 'auto', payload
assert payload['continue_strategy'] == 'recent_workspace_project', payload
assert payload['auto_broaden_attempted'] is True, payload
assert payload['auto_broaden_resolved_to'] in {'section', 'page'}, payload
assert payload['auto_broaden_attempts'][0] == 'exact', payload
assert payload['used_workspace_recent_query_memory'] is True, payload
assert '--broaden-to auto' in payload['auto_broaden_command'], payload
assert payload['preferred_followup_command'] == payload['auto_broaden_command'], payload
assert payload['continued_page_key_filter'] == 'home', payload
assert payload['continued_slot_key_filter'] != 'hero-actions', payload
result = payload['result']
assert result['entrypoint'] == 'project-hook-init', payload
target_path = pathlib.Path(result['target_path']).resolve()
assert target_path.parent == (project_root / 'frontend/src/ail-overrides/components').resolve(), payload
assert target_path.exists(), payload
assert target_path.name != 'page.home.section.hero.slot.hero-actions.before.vue', payload
PY
ok_workspace_hook_continue_auto_repo_json=true

workspace_preview_root_json="$TMP_ROOT/workspace_preview_root.json"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace preview --json > "$workspace_preview_root_json"
)
python3 - "$workspace_preview_root_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'workspace-preview', payload
assert payload['route_taken'] == 'workspace_preview_root', payload
assert payload['preview_handoff']['status'] == 'ok', payload
assert payload['preview_handoff']['primary_target']['label'] in {'latest_trial_batch_report', 'readiness_report'}, payload
assert payload['recommended_workspace_action'] in {'trial_run_landing', 'run_readiness_snapshot'}, payload
PY
ok_workspace_preview_repo_json=true

workspace_open_target_root_json="$TMP_ROOT/workspace_open_target_root.json"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace open-target project_context --json > "$workspace_open_target_root_json"
)
python3 - "$workspace_open_target_root_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'workspace-open-target', payload
assert payload['route_taken'] == 'workspace_preview_root', payload
assert payload['resolved_label'] == 'project_context', payload
assert payload['target']['kind'] == 'file', payload
assert payload['target']['exists'] is True, payload
assert payload['inspect_command'].startswith('inspect '), payload
PY
ok_workspace_open_target_repo_json=true

workspace_inspect_target_root_json="$TMP_ROOT/workspace_inspect_target_root.json"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace inspect-target project_context --json > "$workspace_inspect_target_root_json"
)
python3 - "$workspace_inspect_target_root_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'workspace-inspect-target', payload
assert payload['route_taken'] == 'workspace_preview_root', payload
assert payload['resolved_label'] == 'project_context', payload
assert payload['inspection']['kind'] == 'file', payload
assert payload['inspection']['exists'] is True, payload
assert payload['inspection']['line_count'] >= 1, payload
PY
ok_workspace_inspect_target_repo_json=true

workspace_run_inspect_command_root_json="$TMP_ROOT/workspace_run_inspect_command_root.json"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace run-inspect-command project_context --json > "$workspace_run_inspect_command_root_json"
)
python3 - "$workspace_run_inspect_command_root_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'workspace-run-inspect-command', payload
assert payload['route_taken'] == 'workspace_inspect_target', payload
assert payload['resolved_label'] == 'project_context', payload
assert payload['inspection']['kind'] == 'file', payload
assert payload['result']['entrypoint'] == 'workspace-inspect-target', payload
PY
ok_workspace_run_inspect_command_repo_json=true

workspace_export_handoff_root_json="$TMP_ROOT/workspace_export_handoff_root.json"
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace export-handoff --json > "$workspace_export_handoff_root_json"
)
python3 - "$workspace_export_handoff_root_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'workspace-export-handoff', payload
assert payload['route_taken'] == 'workspace_export_root', payload
assert payload['primary_target_label'] in {'latest_trial_batch_report', 'readiness_report'}, payload
assert payload['primary_target']['kind'] == 'file', payload
assert payload['primary_inspection']['kind'] == 'file', payload
assert payload['workspace_summary']['entrypoint'] == 'workspace-summary', payload
assert payload['workspace_preview']['entrypoint'] == 'workspace-preview', payload
assert payload['preview_handoff']['consumption_kind'] == 'website_workspace', payload
assert payload['website_surface_summary']['surface_kind'] == 'website_frontier', payload
assert 'Company / Product Website Pack' in payload['website_surface_summary']['supported_packs'], payload
PY
ok_workspace_export_handoff_repo_json=true

workspace_go_root_json="$TMP_ROOT/workspace_go_root.json"
set +e
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace go --json > "$workspace_go_root_json"
)
workspace_go_root_exit=$?
set -e
python3 - "$workspace_go_root_json" "$workspace_go_root_exit" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
exit_code = int(sys.argv[2])
assert payload['status'] in {'ok', 'attention', 'warning'}, payload
assert payload['entrypoint'] == 'workspace-go', payload
assert payload['route_taken'] in {'trial_run_landing', 'run_readiness_snapshot'}, payload
assert payload['executed_workspace_action'] in {'trial_run_landing', 'run_readiness_snapshot'}, payload
if payload['route_taken'] == 'trial_run_landing':
    assert exit_code == 0, exit_code
    assert payload['result']['entrypoint'] == 'trial-run', payload
    assert payload['result']['scenario'] == 'landing', payload
    assert payload['result']['detected_profile'] == 'landing', payload
    assert payload['result']['repair_used'] is False, payload
else:
    assert exit_code == 3, exit_code
    assert payload['result']['reason'] == 'workspace_not_ready_for_execution', payload
PY
ok_workspace_go_repo_json=true

workspace_doctor_root_json="$TMP_ROOT/workspace_doctor_root.json"
set +e
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace doctor --json > "$workspace_doctor_root_json"
)
workspace_doctor_root_exit=$?
set -e
python3 - "$workspace_doctor_root_json" "$workspace_doctor_root_exit" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
exit_code = int(sys.argv[2])
assert payload['entrypoint'] == 'workspace-doctor', payload
assert payload['inside_ail_project'] is False, payload
assert payload['route_taken'] in {'workspace_healthy', 'workspace_rc_recovery'}, payload
assert payload['recommended_workspace_action'] in {'trial_run_landing', 'rc_check_refresh'}, payload
if payload['status'] == 'ok':
    assert exit_code == 0, exit_code
    assert payload['route_taken'] == 'workspace_healthy', payload
else:
    assert exit_code == 3, exit_code
    assert payload['status'] == 'attention', payload
    assert payload['route_taken'] == 'workspace_rc_recovery', payload
PY
ok_workspace_doctor_repo_json=true

workspace_continue_root_json="$TMP_ROOT/workspace_continue_root.json"
set +e
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli workspace continue --json > "$workspace_continue_root_json"
)
workspace_continue_root_exit=$?
set -e
python3 - "$workspace_continue_root_json" "$workspace_continue_root_exit" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
exit_code = int(sys.argv[2])
assert payload['entrypoint'] == 'workspace-continue', payload
assert payload['route_taken'] in {'workspace_go', 'workspace_doctor'}, payload
assert payload['executed_workspace_action'] in {'workspace_go', 'workspace_doctor'}, payload
if payload['route_taken'] == 'workspace_go':
    assert exit_code == 0, exit_code
    assert payload['result']['entrypoint'] == 'workspace-go', payload
else:
    assert exit_code == 3, exit_code
    assert payload['result']['entrypoint'] == 'workspace-doctor', payload
    assert payload['result']['status'] == 'attention', payload
PY
ok_workspace_continue_repo_json=true

rc_check_json="$TMP_ROOT/rc_check.json"
set +e
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli rc-check --json > "$rc_check_json"
)
rc_check_exit=$?
set -e
python3 - "$rc_check_json" "$rc_check_exit" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
exit_code = int(sys.argv[2])
assert payload['entrypoint'] == 'rc-check', payload
assert payload['status'] in {'ok', 'attention'}, payload
assert payload['rc']['status'] in {'ok', 'error', 'attention'}, payload
assert payload['readiness']['status'] in {'ok', 'attention'}, payload
assert payload['recommended_release_action'] in {'workspace_go', 'run_rc_checks'}, payload
assert payload['workspace_summary']['entrypoint'] == 'workspace-summary', payload
if payload['status'] == 'ok':
    assert exit_code == 0, exit_code
else:
    assert exit_code == 3, exit_code
PY
ok_rc_check_json=true

rc_check_refresh_json="$TMP_ROOT/rc_check_refresh.json"
set +e
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli rc-check --refresh --json > "$rc_check_refresh_json"
)
rc_check_refresh_exit=$?
set -e
python3 - "$rc_check_refresh_json" "$rc_check_refresh_exit" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
exit_code = int(sys.argv[2])
assert payload['entrypoint'] == 'rc-check', payload
assert payload['refresh']['status'] in {'ok', 'warning'}, payload
assert payload['refresh']['command'] == f'bash {ROOT}/testing/run_readiness_snapshot.sh', payload
assert payload['readiness']['status'] in {'ok', 'attention'}, payload
if payload['status'] == 'ok':
    assert exit_code == 0, exit_code
else:
    assert exit_code == 3, exit_code
PY
ok_rc_check_refresh_json=true

rc_go_json="$TMP_ROOT/rc_go.json"
set +e
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli rc-go --json > "$rc_go_json"
)
rc_go_exit=$?
set -e
python3 - "$rc_go_json" "$rc_go_exit" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
exit_code = int(sys.argv[2])
assert payload['entrypoint'] == 'rc-go', payload
assert payload['status'] in {'ok', 'attention', 'warning'}, payload
assert payload['route_taken'] in {'workspace_go', 'run_rc_checks'}, payload
assert payload['executed_release_action'] in {'workspace_go', 'run_rc_checks'}, payload
if payload['route_taken'] == 'workspace_go':
    assert exit_code == 0, exit_code
    assert payload['result']['entrypoint'] == 'workspace-go', payload
else:
    assert exit_code == 3, exit_code
    assert payload['result']['reason'] == 'rc_not_ready_for_execution', payload
PY
ok_rc_go_json=true

rc_go_refresh_json="$TMP_ROOT/rc_go_refresh.json"
set +e
(
  cd "$ROOT"
  AIL_CLOUD_BASE_URL=embedded://local python3 -m cli rc-go --refresh --json > "$rc_go_refresh_json"
)
rc_go_refresh_exit=$?
set -e
python3 - "$rc_go_refresh_json" "$rc_go_refresh_exit" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
exit_code = int(sys.argv[2])
assert payload['entrypoint'] == 'rc-go', payload
assert payload['refresh']['status'] in {'ok', 'warning'}, payload
assert payload['route_taken'] in {'workspace_go', 'run_rc_checks'}, payload
if payload['route_taken'] == 'workspace_go':
    assert exit_code == 0, exit_code
    assert payload['result']['entrypoint'] == 'workspace-go', payload
else:
    assert exit_code == 3, exit_code
    assert payload['result']['reason'] == 'rc_not_ready_for_execution', payload
PY
ok_rc_go_refresh_json=true

project_doctor_json="$TMP_ROOT/project_doctor_ok.json"
AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project doctor --fix-plan --json > "$project_doctor_json"
python3 - "$project_doctor_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['recommended_action'] == 'continue_iteration', payload
assert payload['project_check']['status'] == 'ok', payload
assert payload['source_diagnosis']['diagnosis']['compile_recommended'] == 'yes', payload
assert payload['fix_plan']['mode'] == 'guided_recovery', payload
assert len(payload['fix_plan']['steps']) >= 2, payload
PY
ok_project_doctor_json=true

project_doctor_apply_safe_noop_json="$TMP_ROOT/project_doctor_apply_safe_noop.json"
AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project doctor --apply-safe-fixes --json > "$project_doctor_apply_safe_noop_json"
python3 - "$project_doctor_apply_safe_noop_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['recommended_action'] == 'continue_iteration', payload
assert payload['safe_fix_result']['status'] == 'noop', payload
assert payload['source_diagnosis']['diagnosis']['compile_recommended'] == 'yes', payload
PY
ok_project_doctor_apply_safe_noop_json=true

project_doctor_apply_safe_continue_noop_json="$TMP_ROOT/project_doctor_apply_safe_continue_noop.json"
AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project doctor --apply-safe-fixes --and-continue --json > "$project_doctor_apply_safe_continue_noop_json"
python3 - "$project_doctor_apply_safe_continue_noop_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['safe_fix_result']['status'] == 'noop', payload
assert payload['continue_result']['build_id'], payload
assert payload['continue_result']['managed_files_written'] >= 1, payload
PY
ok_project_doctor_apply_safe_continue_noop_json=true

project_continue_auto_no_repair_json="$TMP_ROOT/project_continue_auto_no_repair.json"
AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project continue --auto-repair-compile-sync --json > "$project_continue_auto_no_repair_json"
python3 - "$project_continue_auto_no_repair_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['action'] == 'auto_repair_compile_sync', payload
assert payload['auto_repair_used'] is False, payload
assert payload['diagnosis_before']['compile_recommended'] == 'yes', payload
assert payload['diagnosis_after']['compile_recommended'] == 'yes', payload
assert payload['managed_files_written'] >= 1, payload
PY
ok_project_continue_auto_no_repair_json=true

cat > "$TMP_ROOT/.ail/source.ail" <<'EOF'
#PROFILE[landing]
@PAGE[Home,/]
#UI[landing:Header]
#UI[landing:Hero]
#UI[landing:Testimonials]
#UI[landing:FAQ]
#UI[landing:Contact]
#UI[landing:Footer]
EOF

project_continue_auto_repair_json="$TMP_ROOT/project_continue_auto_repair.json"
AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project continue --auto-repair-compile-sync --json > "$project_continue_auto_repair_json"
python3 - "$project_continue_auto_repair_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['action'] == 'auto_repair_compile_sync', payload
assert payload['auto_repair_used'] is True, payload
assert payload['diagnosis_before']['compile_recommended'] == 'no', payload
assert payload['diagnosis_after']['compile_recommended'] == 'yes', payload
assert payload['managed_files_written'] >= 1, payload
PY
ok_project_continue_auto_repair_json=true

compile_err_json="$TMP_ROOT/compile_error.json"
set +e
python3 -m cli compile --cloud --json > "$compile_err_json"
compile_exit=$?
set -e
python3 - "$compile_err_json" "$compile_exit" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
exit_code = int(sys.argv[2])
assert exit_code == 5, exit_code
assert payload['status'] == 'error', payload
assert payload['error']['code'] == 'cloud_api_error', payload
assert payload['error']['exit_code'] == 5, payload
PY
ok_compile_error_json=true

printf '\n// local drift\n' >> src/views/generated/Home.vue

sync_conflict_json="$TMP_ROOT/sync_conflict.json"
set +e
python3 -m cli sync --json > "$sync_conflict_json"
sync_exit=$?
set -e
python3 - "$sync_conflict_json" "$sync_exit" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
exit_code = int(sys.argv[2])
assert exit_code == 4, exit_code
assert payload['status'] == 'error', payload
assert payload['error']['code'] == 'sync_conflict', payload
assert payload['error']['exit_code'] == 4, payload
assert payload['error']['details']['blocks_safe_sync'] is True, payload
assert payload['error']['details']['blocks_existing_output_review'] is False, payload
assert 'not necessarily a website generation failure' in payload['error']['details']['message'], payload
PY
ok_sync_conflict_json=true

project_check_conflict_json="$TMP_ROOT/project_check_conflict.json"
set +e
AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project check --json > "$project_check_conflict_json"
project_check_exit=$?
set -e
python3 - "$project_check_conflict_json" "$project_check_exit" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
exit_code = int(sys.argv[2])
assert exit_code == 4, exit_code
assert payload['status'] == 'conflict', payload
assert payload['checks']['sync_conflicts_detected'] is True, payload
assert payload['checks']['ready_for_sync'] is False, payload
assert len(payload['sync_conflicts']) >= 1, payload
assert payload['sync_conflict_summary']['blocks_safe_sync'] is True, payload
assert payload['sync_conflict_summary']['blocks_existing_output_review'] is False, payload
assert 'not necessarily a website generation failure' in payload['sync_conflict_summary']['message'], payload
assert payload['sync_conflicts'][0]['category'] == 'managed_file_drift', payload
assert payload['sync_conflicts'][0]['user_message'], payload
PY
ok_project_check_conflict_json=true

project_summary_conflict_json="$TMP_ROOT/project_summary_conflict.json"
AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project summary --json > "$project_summary_conflict_json"
python3 - "$project_summary_conflict_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['doctor_status'] == 'conflict', payload
assert payload['recommended_primary_action'] == 'project_doctor', payload
assert 'conflict-resolution decision' in payload['recommended_primary_reason'], payload
PY
ok_project_summary_conflict_json=true

project_preview_conflict_json="$TMP_ROOT/project_preview_conflict.json"
AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project preview --json > "$project_preview_conflict_json"
python3 - "$project_preview_conflict_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'project-preview', payload
assert payload['doctor_status'] == 'conflict', payload
assert payload['recommended_primary_action'] == 'project_doctor', payload
assert payload['preview_handoff']['status'] == 'ok', payload
assert payload['preview_hint'], payload
PY
ok_project_preview_conflict_json=true

project_export_handoff_conflict_json="$TMP_ROOT/project_export_handoff_conflict.json"
AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project export-handoff --json > "$project_export_handoff_conflict_json"
python3 - "$project_export_handoff_conflict_json" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
assert payload['status'] == 'ok', payload
assert payload['entrypoint'] == 'project-export-handoff', payload
assert payload['primary_target_label'] == 'artifact_root', payload
assert payload['primary_target']['kind'] == 'directory', payload
assert payload['primary_inspection']['kind'] == 'directory', payload
assert payload['project_summary']['doctor_status'] == 'conflict', payload
assert payload['recommended_primary_action'] == 'project_doctor', payload
PY
ok_project_export_handoff_conflict_json=true

project_go_conflict_json="$TMP_ROOT/project_go_conflict.json"
set +e
AIL_CLOUD_BASE_URL=embedded://local python3 -m cli project go --json > "$project_go_conflict_json"
project_go_exit=$?
set -e
python3 - "$project_go_conflict_json" "$project_go_exit" <<'PY'
import os
ROOT = os.environ['AIL_REPO_ROOT']
OUTPUT_PROJECTS_ROOT = f"{ROOT}/output_projects"
import json, sys
payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
exit_code = int(sys.argv[2])
assert exit_code == 4, exit_code
assert payload['status'] == 'conflict', payload
assert payload['entrypoint'] == 'project-go', payload
assert payload['route_taken'] == 'project_doctor', payload
assert payload['route_reason'], payload
assert payload['executed_primary_action'] == 'project_doctor', payload
assert payload['result']['status'] == 'conflict', payload
assert payload['result']['recommended_action'] == 'resolve_sync_conflicts', payload
PY
ok_project_go_conflict_json=true

export CLI_SMOKE_OK_COMPILE_JSON="$ok_compile_json"
export CLI_SMOKE_OK_SINGLE_PAGE_LANDING_NAV_JSON="$ok_single_page_landing_nav_json"
export CLI_SMOKE_OK_ECOM_CHECKOUT_FLOW_JSON="$ok_ecom_checkout_flow_json"
export CLI_SMOKE_OK_ECOM_CART_FLOW_JSON="$ok_ecom_cart_flow_json"
export CLI_SMOKE_OK_ECOM_PRODUCT_FEEDBACK_JSON="$ok_ecom_product_feedback_json"
export CLI_SMOKE_OK_WEBSITE_CHECK_JSON="$ok_website_check_json"
export CLI_SMOKE_OK_WEBSITE_CHECK_OUT_OF_SCOPE_JSON="$ok_website_check_out_of_scope_json"
export CLI_SMOKE_OK_WEBSITE_CHECK_EXPERIMENTAL_DYNAMIC_JSON="$ok_website_check_experimental_dynamic_json"
export CLI_SMOKE_OK_WEBSITE_ASSETS_JSON="$ok_website_assets_json"
export CLI_SMOKE_OK_WEBSITE_ASSETS_EXPERIMENTAL_DYNAMIC_JSON="$ok_website_assets_experimental_dynamic_json"
export CLI_SMOKE_OK_WEBSITE_ASSETS_PACK_JSON="$ok_website_assets_pack_json"
export CLI_SMOKE_OK_WEBSITE_OPEN_ASSET_JSON="$ok_website_open_asset_json"
export CLI_SMOKE_OK_WEBSITE_OPEN_ASSET_PACK_JSON="$ok_website_open_asset_pack_json"
export CLI_SMOKE_OK_WEBSITE_INSPECT_ASSET_JSON="$ok_website_inspect_asset_json"
export CLI_SMOKE_OK_WEBSITE_INSPECT_ASSET_PACK_JSON="$ok_website_inspect_asset_pack_json"
export CLI_SMOKE_OK_WEBSITE_PREVIEW_JSON="$ok_website_preview_json"
export CLI_SMOKE_OK_WEBSITE_PREVIEW_PACK_JSON="$ok_website_preview_pack_json"
export CLI_SMOKE_OK_WEBSITE_RUN_INSPECT_COMMAND_JSON="$ok_website_run_inspect_command_json"
export CLI_SMOKE_OK_WEBSITE_RUN_INSPECT_COMMAND_PACK_JSON="$ok_website_run_inspect_command_pack_json"
export CLI_SMOKE_OK_WEBSITE_EXPORT_HANDOFF_JSON="$ok_website_export_handoff_json"
export CLI_SMOKE_OK_WEBSITE_EXPORT_HANDOFF_PACK_JSON="$ok_website_export_handoff_pack_json"
export CLI_SMOKE_OK_WEBSITE_SUMMARY_JSON="$ok_website_summary_json"
export CLI_SMOKE_OK_WEBSITE_GO_JSON="$ok_website_go_json"
export CLI_SMOKE_OK_SYNC_JSON="$ok_sync_json"
export CLI_SMOKE_OK_COMPILE_ERROR_JSON="$ok_compile_error_json"
export CLI_SMOKE_OK_SYNC_CONFLICT_JSON="$ok_sync_conflict_json"
export CLI_SMOKE_OK_DIAGNOSE_JSON="$ok_diagnose_json"
export CLI_SMOKE_OK_REPAIR_JSON="$ok_repair_json"
export CLI_SMOKE_OK_POST_REPAIR_DIAGNOSE_JSON="$ok_post_repair_diagnose_json"
export CLI_SMOKE_OK_PROJECT_CHECK_JSON="$ok_project_check_json"
export CLI_SMOKE_OK_PROJECT_CHECK_CONFLICT_JSON="$ok_project_check_conflict_json"
export CLI_SMOKE_OK_PROJECT_DOCTOR_JSON="$ok_project_doctor_json"
export CLI_SMOKE_OK_PROJECT_DOCTOR_VALIDATION_JSON="$ok_project_doctor_validation_json"
export CLI_SMOKE_OK_PROJECT_DOCTOR_APPLY_SAFE_NOOP_JSON="$ok_project_doctor_apply_safe_noop_json"
export CLI_SMOKE_OK_PROJECT_DOCTOR_APPLY_SAFE_REPAIR_JSON="$ok_project_doctor_apply_safe_repair_json"
export CLI_SMOKE_OK_PROJECT_DOCTOR_APPLY_SAFE_CONTINUE_NOOP_JSON="$ok_project_doctor_apply_safe_continue_noop_json"
export CLI_SMOKE_OK_PROJECT_DOCTOR_APPLY_SAFE_CONTINUE_REPAIR_JSON="$ok_project_doctor_apply_safe_continue_repair_json"
export CLI_SMOKE_OK_PROJECT_CONTINUE_AUTO_REPAIR_JSON="$ok_project_continue_auto_repair_json"
export CLI_SMOKE_OK_PROJECT_CONTINUE_AUTO_NO_REPAIR_JSON="$ok_project_continue_auto_no_repair_json"
export CLI_SMOKE_OK_PROJECT_SUMMARY_JSON="$ok_project_summary_json"
export CLI_SMOKE_OK_PROJECT_HOOKS_JSON="$ok_project_hooks_json"
export CLI_SMOKE_OK_PROJECT_HOOKS_HOME_JSON="$ok_project_hooks_home_json"
export CLI_SMOKE_OK_PROJECT_HOOK_INIT_JSON="$ok_project_hook_init_json"
export CLI_SMOKE_OK_PROJECT_HOOK_GUIDE_REPO_JSON="$ok_project_hook_guide_repo_json"
export CLI_SMOKE_OK_PROJECT_HOOK_GUIDE_EMIT_SHELL_REPO="$ok_project_hook_guide_emit_shell_repo"
export CLI_SMOKE_OK_PROJECT_HOOK_GUIDE_COPY_COMMAND_REPO="$ok_project_hook_guide_copy_command_repo"
export CLI_SMOKE_OK_PROJECT_HOOK_GUIDE_RUN_COMMAND_REPO="$ok_project_hook_guide_run_command_repo"
export CLI_SMOKE_OK_PROJECT_HOOK_GUIDE_RUN_COMMAND_YES_REPO="$ok_project_hook_guide_run_command_yes_repo"
export CLI_SMOKE_OK_PROJECT_HOOK_INIT_TEXT_COMPACT_REPO="$ok_project_hook_init_text_compact_repo"
export CLI_SMOKE_OK_PROJECT_HOOK_INIT_EXPLAIN_REPO="$ok_project_hook_init_explain_repo"
export CLI_SMOKE_OK_PROJECT_HOOK_INIT_EMIT_SHELL_REPO="$ok_project_hook_init_emit_shell_repo"
export CLI_SMOKE_OK_PROJECT_HOOK_INIT_COPY_COMMAND_REPO="$ok_project_hook_init_copy_command_repo"
export CLI_SMOKE_OK_PROJECT_HOOK_INIT_EMIT_CONFIRM_SHELL_REPO="$ok_project_hook_init_emit_confirm_shell_repo"
export CLI_SMOKE_OK_PROJECT_HOOK_INIT_COPY_CONFIRM_COMMAND_REPO="$ok_project_hook_init_copy_confirm_command_repo"
export CLI_SMOKE_OK_PROJECT_HOOK_INIT_EMIT_TARGET_PATH_REPO="$ok_project_hook_init_emit_target_path_repo"
export CLI_SMOKE_OK_PROJECT_HOOK_INIT_COPY_TARGET_PATH_REPO="$ok_project_hook_init_copy_target_path_repo"
export CLI_SMOKE_OK_PROJECT_HOOK_INIT_EMIT_TARGET_DIR_REPO="$ok_project_hook_init_emit_target_dir_repo"
export CLI_SMOKE_OK_PROJECT_HOOK_INIT_COPY_TARGET_DIR_REPO="$ok_project_hook_init_copy_target_dir_repo"
export CLI_SMOKE_OK_PROJECT_HOOK_INIT_EMIT_TARGET_PROJECT_ROOT_REPO="$ok_project_hook_init_emit_target_project_root_repo"
export CLI_SMOKE_OK_PROJECT_HOOK_INIT_COPY_TARGET_PROJECT_ROOT_REPO="$ok_project_hook_init_copy_target_project_root_repo"
export CLI_SMOKE_OK_PROJECT_HOOK_INIT_EMIT_TARGET_PROJECT_NAME_REPO="$ok_project_hook_init_emit_target_project_name_repo"
export CLI_SMOKE_OK_PROJECT_HOOK_INIT_COPY_TARGET_PROJECT_NAME_REPO="$ok_project_hook_init_copy_target_project_name_repo"
export CLI_SMOKE_OK_PROJECT_HOOK_INIT_EMIT_TARGET_RELATIVE_PATH_REPO="$ok_project_hook_init_emit_target_relative_path_repo"
export CLI_SMOKE_OK_PROJECT_HOOK_INIT_COPY_TARGET_RELATIVE_PATH_REPO="$ok_project_hook_init_copy_target_relative_path_repo"
export CLI_SMOKE_OK_PROJECT_HOOK_INIT_EMIT_TARGET_BUNDLE_REPO="$ok_project_hook_init_emit_target_bundle_repo"
export CLI_SMOKE_OK_PROJECT_HOOK_INIT_COPY_TARGET_BUNDLE_REPO="$ok_project_hook_init_copy_target_bundle_repo"
export CLI_SMOKE_OK_PROJECT_HOOK_INIT_EMIT_OPEN_SHELL_REPO="$ok_project_hook_init_emit_open_shell_repo"
export CLI_SMOKE_OK_PROJECT_HOOK_INIT_COPY_OPEN_COMMAND_REPO="$ok_project_hook_init_copy_open_command_repo"
export CLI_SMOKE_OK_PROJECT_HOOK_INIT_RUN_COMMAND_REPO="$ok_project_hook_init_run_command_repo"
export CLI_SMOKE_OK_PROJECT_HOOK_INIT_RUN_COMMAND_YES_REPO="$ok_project_hook_init_run_command_yes_repo"
export CLI_SMOKE_OK_PROJECT_HOOK_INIT_RUN_OPEN_COMMAND_REPO="$ok_project_hook_init_run_open_command_repo"
export CLI_SMOKE_OK_PROJECT_HOOK_INIT_RUN_OPEN_COMMAND_YES_REPO="$ok_project_hook_init_run_open_command_yes_repo"
export CLI_SMOKE_OK_PROJECT_HOOK_INIT_INSPECT_TARGET_REPO="$ok_project_hook_init_inspect_target_repo"
export CLI_SMOKE_OK_PROJECT_HOOK_INIT_INSPECT_TARGET_TEXT_COMPACT_REPO="$ok_project_hook_init_inspect_target_text_compact_repo"
export CLI_SMOKE_OK_PROJECT_HOOK_INIT_OPEN_TARGET_REPO="$ok_project_hook_init_open_target_repo"
export CLI_SMOKE_OK_PROJECT_HOOK_INIT_OPEN_NOW_REPO="$ok_project_hook_init_open_now_repo"
export CLI_SMOKE_OK_PROJECT_HOOK_INIT_OPEN_NOW_TEXT_COMPACT_REPO="$ok_project_hook_init_open_now_text_compact_repo"
export CLI_SMOKE_OK_PROJECT_HOOK_INIT_FORCE_JSON="$ok_project_hook_init_force_json"
export CLI_SMOKE_OK_PROJECT_HOOK_INIT_SUGGEST_JSON="$ok_project_hook_init_suggest_json"
export CLI_SMOKE_OK_PROJECT_HOOK_INIT_OPEN_CATALOG_JSON="$ok_project_hook_init_open_catalog_json"
export CLI_SMOKE_OK_PROJECT_HOOK_INIT_SUGGEST_FILTERED_JSON="$ok_project_hook_init_suggest_filtered_json"
export CLI_SMOKE_OK_PROJECT_HOOK_INIT_SUGGEST_SLOT_FILTERED_JSON="$ok_project_hook_init_suggest_slot_filtered_json"
export CLI_SMOKE_OK_PROJECT_HOOK_INIT_SUGGEST_SLOT_ONLY_JSON="$ok_project_hook_init_suggest_slot_only_json"
export CLI_SMOKE_OK_PROJECT_HOOK_INIT_PICK_JSON="$ok_project_hook_init_pick_json"
export CLI_SMOKE_OK_PROJECT_HOOK_INIT_PICK_INDEX_JSON="$ok_project_hook_init_pick_index_json"
export CLI_SMOKE_OK_PROJECT_HOOK_INIT_PICK_RECOMMENDED_JSON="$ok_project_hook_init_pick_recommended_json"
export CLI_SMOKE_OK_PROJECT_HOOK_INIT_RECENT_MEMORY_PICK_JSON="$ok_project_hook_init_recent_memory_pick_json"
export CLI_SMOKE_OK_PROJECT_HOOK_INIT_REUSE_LAST_SUGGEST_JSON="$ok_project_hook_init_reuse_last_suggest_json"
export CLI_SMOKE_OK_PROJECT_HOOK_INIT_LAST_SUGGEST_JSON="$ok_project_hook_init_last_suggest_json"
export CLI_SMOKE_OK_PROJECT_SUMMARY_CONFLICT_JSON="$ok_project_summary_conflict_json"
export CLI_SMOKE_OK_PROJECT_PREVIEW_JSON="$ok_project_preview_json"
export CLI_SMOKE_OK_PROJECT_SERVE_DRY_RUN_JSON="$ok_project_serve_dry_run_json"
export CLI_SMOKE_OK_PROJECT_PREVIEW_CONFLICT_JSON="$ok_project_preview_conflict_json"
export CLI_SMOKE_OK_PROJECT_OPEN_TARGET_JSON="$ok_project_open_target_json"
export CLI_SMOKE_OK_PROJECT_OPEN_TARGET_DEFAULT_JSON="$ok_project_open_target_default_json"
export CLI_SMOKE_OK_PROJECT_INSPECT_TARGET_JSON="$ok_project_inspect_target_json"
export CLI_SMOKE_OK_PROJECT_INSPECT_TARGET_DEFAULT_JSON="$ok_project_inspect_target_default_json"
export CLI_SMOKE_OK_PROJECT_RUN_INSPECT_COMMAND_JSON="$ok_project_run_inspect_command_json"
export CLI_SMOKE_OK_PROJECT_RUN_INSPECT_COMMAND_DEFAULT_JSON="$ok_project_run_inspect_command_default_json"
export CLI_SMOKE_OK_PROJECT_EXPORT_HANDOFF_JSON="$ok_project_export_handoff_json"
export CLI_SMOKE_OK_PROJECT_EXPORT_HANDOFF_CONFLICT_JSON="$ok_project_export_handoff_conflict_json"
export CLI_SMOKE_OK_PROJECT_GO_JSON="$ok_project_go_json"
export CLI_SMOKE_OK_PROJECT_GO_REPAIR_JSON="$ok_project_go_repair_json"
export CLI_SMOKE_OK_PROJECT_GO_CONFLICT_JSON="$ok_project_go_conflict_json"
export CLI_SMOKE_OK_WORKSPACE_STATUS_REPO_JSON="$ok_workspace_status_repo_json"
export CLI_SMOKE_OK_WORKSPACE_STATUS_PROJECT_JSON="$ok_workspace_status_project_json"
export CLI_SMOKE_OK_WORKSPACE_HOOKS_REPO_JSON="$ok_workspace_hooks_repo_json"
export CLI_SMOKE_OK_WORKSPACE_HOOKS_PROJECT_JSON="$ok_workspace_hooks_project_json"
export CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_REPO_JSON="$ok_workspace_hook_init_repo_json"
export CLI_SMOKE_OK_WORKSPACE_HOOK_GUIDE_REPO_JSON="$ok_workspace_hook_guide_repo_json"
export CLI_SMOKE_OK_WORKSPACE_HOOK_GUIDE_EMIT_SHELL_REPO="$ok_workspace_hook_guide_emit_shell_repo"
export CLI_SMOKE_OK_WORKSPACE_HOOK_GUIDE_COPY_COMMAND_REPO="$ok_workspace_hook_guide_copy_command_repo"
export CLI_SMOKE_OK_WORKSPACE_HOOK_GUIDE_RUN_COMMAND_REPO="$ok_workspace_hook_guide_run_command_repo"
export CLI_SMOKE_OK_WORKSPACE_HOOK_GUIDE_RUN_COMMAND_YES_REPO="$ok_workspace_hook_guide_run_command_yes_repo"
export CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_TEXT_COMPACT_REPO="$ok_workspace_hook_init_text_compact_repo"
export CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_EXPLAIN_REPO="$ok_workspace_hook_init_explain_repo"
export CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_EMIT_SHELL_REPO="$ok_workspace_hook_init_emit_shell_repo"
export CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_COPY_COMMAND_REPO="$ok_workspace_hook_init_copy_command_repo"
export CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_EMIT_CONFIRM_SHELL_REPO="$ok_workspace_hook_init_emit_confirm_shell_repo"
export CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_COPY_CONFIRM_COMMAND_REPO="$ok_workspace_hook_init_copy_confirm_command_repo"
export CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_EMIT_TARGET_PATH_REPO="$ok_workspace_hook_init_emit_target_path_repo"
export CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_COPY_TARGET_PATH_REPO="$ok_workspace_hook_init_copy_target_path_repo"
export CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_EMIT_TARGET_DIR_REPO="$ok_workspace_hook_init_emit_target_dir_repo"
export CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_COPY_TARGET_DIR_REPO="$ok_workspace_hook_init_copy_target_dir_repo"
export CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_EMIT_TARGET_PROJECT_ROOT_REPO="$ok_workspace_hook_init_emit_target_project_root_repo"
export CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_COPY_TARGET_PROJECT_ROOT_REPO="$ok_workspace_hook_init_copy_target_project_root_repo"
export CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_EMIT_TARGET_PROJECT_NAME_REPO="$ok_workspace_hook_init_emit_target_project_name_repo"
export CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_COPY_TARGET_PROJECT_NAME_REPO="$ok_workspace_hook_init_copy_target_project_name_repo"
export CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_EMIT_TARGET_RELATIVE_PATH_REPO="$ok_workspace_hook_init_emit_target_relative_path_repo"
export CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_COPY_TARGET_RELATIVE_PATH_REPO="$ok_workspace_hook_init_copy_target_relative_path_repo"
export CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_EMIT_TARGET_BUNDLE_REPO="$ok_workspace_hook_init_emit_target_bundle_repo"
export CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_COPY_TARGET_BUNDLE_REPO="$ok_workspace_hook_init_copy_target_bundle_repo"
export CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_EMIT_OPEN_SHELL_REPO="$ok_workspace_hook_init_emit_open_shell_repo"
export CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_COPY_OPEN_COMMAND_REPO="$ok_workspace_hook_init_copy_open_command_repo"
export CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_RUN_COMMAND_REPO="$ok_workspace_hook_init_run_command_repo"
export CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_RUN_COMMAND_YES_REPO="$ok_workspace_hook_init_run_command_yes_repo"
export CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_RUN_OPEN_COMMAND_REPO="$ok_workspace_hook_init_run_open_command_repo"
export CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_RUN_OPEN_COMMAND_YES_REPO="$ok_workspace_hook_init_run_open_command_yes_repo"
export CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_INSPECT_TARGET_REPO="$ok_workspace_hook_init_inspect_target_repo"
export CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_INSPECT_TARGET_TEXT_COMPACT_REPO="$ok_workspace_hook_init_inspect_target_text_compact_repo"
export CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_OPEN_TARGET_REPO="$ok_workspace_hook_init_open_target_repo"
export CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_OPEN_NOW_REPO="$ok_workspace_hook_init_open_now_repo"
export CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_OPEN_NOW_TEXT_COMPACT_REPO="$ok_workspace_hook_init_open_now_text_compact_repo"
export CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_PROJECT_JSON="$ok_workspace_hook_init_project_json"
export CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_RECOMMENDED_REPO_JSON="$ok_workspace_hook_init_recommended_repo_json"
export CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_RECOMMENDED_SUGGEST_REPO_JSON="$ok_workspace_hook_init_recommended_suggest_repo_json"
export CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_RECOMMENDED_PICK_REPO_JSON="$ok_workspace_hook_init_recommended_pick_repo_json"
export CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_FOLLOW_RECOMMENDED_REPO_JSON="$ok_workspace_hook_init_follow_recommended_repo_json"
export CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_USE_LAST_PROJECT_REPO_JSON="$ok_workspace_hook_init_use_last_project_repo_json"
export CLI_SMOKE_OK_WORKSPACE_HOOK_CONTINUE_REPO_JSON="$ok_workspace_hook_continue_repo_json"
export CLI_SMOKE_OK_WORKSPACE_HOOK_CONTINUE_BROADEN_REPO_JSON="$ok_workspace_hook_continue_broaden_repo_json"
export CLI_SMOKE_OK_WORKSPACE_HOOK_CONTINUE_AUTO_REPO_JSON="$ok_workspace_hook_continue_auto_repo_json"
export CLI_SMOKE_OK_WORKSPACE_HOOK_CONTINUE_DRY_RUN_REPO_JSON="$ok_workspace_hook_continue_dry_run_repo_json"
export CLI_SMOKE_OK_WORKSPACE_HOOK_CONTINUE_TEXT_COMPACT_REPO="$ok_workspace_hook_continue_text_compact_repo"
export CLI_SMOKE_OK_WORKSPACE_HOOK_CONTINUE_INSPECT_TARGET_TEXT_COMPACT_REPO="$ok_workspace_hook_continue_inspect_target_text_compact_repo"
export CLI_SMOKE_OK_WORKSPACE_HOOK_CONTINUE_OPEN_TARGET_REPO="$ok_workspace_hook_continue_open_target_repo"
export CLI_SMOKE_OK_WORKSPACE_HOOK_CONTINUE_OPEN_NOW_REPO="$ok_workspace_hook_continue_open_now_repo"
export CLI_SMOKE_OK_WORKSPACE_HOOK_CONTINUE_OPEN_NOW_TEXT_COMPACT_REPO="$ok_workspace_hook_continue_open_now_text_compact_repo"
export CLI_SMOKE_OK_WORKSPACE_HOOK_CONTINUE_OPEN_NOW_TEXT_COMPACT_HAS_REASON_REPO="$ok_workspace_hook_continue_open_now_text_compact_has_reason_repo"
export CLI_SMOKE_OK_WORKSPACE_HOOK_CONTINUE_OPEN_NOW_PREVIEW_REPO="$ok_workspace_hook_continue_open_now_preview_repo"
export CLI_SMOKE_OK_WORKSPACE_HOOK_CONTINUE_EXPLAIN_REPO="$ok_workspace_hook_continue_explain_repo"
export CLI_SMOKE_OK_WORKSPACE_HOOK_CONTINUE_EMIT_SHELL_REPO="$ok_workspace_hook_continue_emit_shell_repo"
export CLI_SMOKE_OK_WORKSPACE_HOOK_CONTINUE_EMIT_CONFIRM_SHELL_REPO="$ok_workspace_hook_continue_emit_confirm_shell_repo"
export CLI_SMOKE_OK_WORKSPACE_HOOK_CONTINUE_EMIT_TARGET_PATH_REPO="$ok_workspace_hook_continue_emit_target_path_repo"
export CLI_SMOKE_OK_WORKSPACE_HOOK_CONTINUE_EMIT_TARGET_DIR_REPO="$ok_workspace_hook_continue_emit_target_dir_repo"
export CLI_SMOKE_OK_WORKSPACE_HOOK_CONTINUE_EMIT_TARGET_PROJECT_ROOT_REPO="$ok_workspace_hook_continue_emit_target_project_root_repo"
export CLI_SMOKE_OK_WORKSPACE_HOOK_CONTINUE_EMIT_TARGET_PROJECT_NAME_REPO="$ok_workspace_hook_continue_emit_target_project_name_repo"
export CLI_SMOKE_OK_WORKSPACE_HOOK_CONTINUE_EMIT_TARGET_RELATIVE_PATH_REPO="$ok_workspace_hook_continue_emit_target_relative_path_repo"
export CLI_SMOKE_OK_WORKSPACE_HOOK_CONTINUE_EMIT_TARGET_BUNDLE_REPO="$ok_workspace_hook_continue_emit_target_bundle_repo"
export CLI_SMOKE_OK_WORKSPACE_HOOK_CONTINUE_EMIT_OPEN_SHELL_REPO="$ok_workspace_hook_continue_emit_open_shell_repo"
export CLI_SMOKE_OK_WORKSPACE_HOOK_CONTINUE_COPY_OPEN_COMMAND_REPO="$ok_workspace_hook_continue_copy_open_command_repo"
export CLI_SMOKE_OK_WORKSPACE_HOOK_CONTINUE_COPY_CONFIRM_COMMAND_REPO="$ok_workspace_hook_continue_copy_confirm_command_repo"
export CLI_SMOKE_OK_WORKSPACE_HOOK_CONTINUE_COPY_TARGET_PATH_REPO="$ok_workspace_hook_continue_copy_target_path_repo"
export CLI_SMOKE_OK_WORKSPACE_HOOK_CONTINUE_COPY_TARGET_DIR_REPO="$ok_workspace_hook_continue_copy_target_dir_repo"
export CLI_SMOKE_OK_WORKSPACE_HOOK_CONTINUE_COPY_TARGET_PROJECT_ROOT_REPO="$ok_workspace_hook_continue_copy_target_project_root_repo"
export CLI_SMOKE_OK_WORKSPACE_HOOK_CONTINUE_COPY_TARGET_PROJECT_NAME_REPO="$ok_workspace_hook_continue_copy_target_project_name_repo"
export CLI_SMOKE_OK_WORKSPACE_HOOK_CONTINUE_COPY_TARGET_RELATIVE_PATH_REPO="$ok_workspace_hook_continue_copy_target_relative_path_repo"
export CLI_SMOKE_OK_WORKSPACE_HOOK_CONTINUE_COPY_TARGET_BUNDLE_REPO="$ok_workspace_hook_continue_copy_target_bundle_repo"
export CLI_SMOKE_OK_WORKSPACE_HOOK_CONTINUE_COPY_COMMAND_REPO="$ok_workspace_hook_continue_copy_command_repo"
export CLI_SMOKE_OK_WORKSPACE_HOOK_CONTINUE_RUN_OPEN_COMMAND_REPO="$ok_workspace_hook_continue_run_open_command_repo"
export CLI_SMOKE_OK_WORKSPACE_HOOK_CONTINUE_RUN_OPEN_COMMAND_YES_REPO="$ok_workspace_hook_continue_run_open_command_yes_repo"
export CLI_SMOKE_OK_WORKSPACE_HOOK_CONTINUE_RUN_COMMAND_REPO="$ok_workspace_hook_continue_run_command_repo"
export CLI_SMOKE_OK_WORKSPACE_HOOK_CONTINUE_RUN_COMMAND_YES_REPO="$ok_workspace_hook_continue_run_command_yes_repo"
export CLI_SMOKE_OK_WORKSPACE_HOOK_CONTINUE_INSPECT_TARGET_REPO="$ok_workspace_hook_continue_inspect_target_repo"
export CLI_SMOKE_OK_WORKSPACE_GO_REPO_JSON="$ok_workspace_go_repo_json"
export CLI_SMOKE_OK_WORKSPACE_GO_PROJECT_JSON="$ok_workspace_go_project_json"
export CLI_SMOKE_OK_WORKSPACE_SUMMARY_REPO_JSON="$ok_workspace_summary_repo_json"
export CLI_SMOKE_OK_WORKSPACE_SUMMARY_PROJECT_JSON="$ok_workspace_summary_project_json"
export CLI_SMOKE_OK_WORKSPACE_PREVIEW_REPO_JSON="$ok_workspace_preview_repo_json"
export CLI_SMOKE_OK_WORKSPACE_PREVIEW_PROJECT_JSON="$ok_workspace_preview_project_json"
export CLI_SMOKE_OK_WORKSPACE_OPEN_TARGET_REPO_JSON="$ok_workspace_open_target_repo_json"
export CLI_SMOKE_OK_WORKSPACE_OPEN_TARGET_PROJECT_JSON="$ok_workspace_open_target_project_json"
export CLI_SMOKE_OK_WORKSPACE_INSPECT_TARGET_REPO_JSON="$ok_workspace_inspect_target_repo_json"
export CLI_SMOKE_OK_WORKSPACE_INSPECT_TARGET_PROJECT_JSON="$ok_workspace_inspect_target_project_json"
export CLI_SMOKE_OK_WORKSPACE_RUN_INSPECT_COMMAND_REPO_JSON="$ok_workspace_run_inspect_command_repo_json"
export CLI_SMOKE_OK_WORKSPACE_RUN_INSPECT_COMMAND_PROJECT_JSON="$ok_workspace_run_inspect_command_project_json"
export CLI_SMOKE_OK_WORKSPACE_EXPORT_HANDOFF_REPO_JSON="$ok_workspace_export_handoff_repo_json"
export CLI_SMOKE_OK_WORKSPACE_EXPORT_HANDOFF_PROJECT_JSON="$ok_workspace_export_handoff_project_json"
export CLI_SMOKE_OK_WORKSPACE_DOCTOR_REPO_JSON="$ok_workspace_doctor_repo_json"
export CLI_SMOKE_OK_WORKSPACE_DOCTOR_PROJECT_JSON="$ok_workspace_doctor_project_json"
export CLI_SMOKE_OK_WORKSPACE_CONTINUE_REPO_JSON="$ok_workspace_continue_repo_json"
export CLI_SMOKE_OK_WORKSPACE_CONTINUE_PROJECT_JSON="$ok_workspace_continue_project_json"
export CLI_SMOKE_OK_RC_CHECK_JSON="$ok_rc_check_json"
export CLI_SMOKE_OK_RC_CHECK_REFRESH_JSON="$ok_rc_check_refresh_json"
export CLI_SMOKE_OK_RC_GO_JSON="$ok_rc_go_json"
export CLI_SMOKE_OK_RC_GO_REFRESH_JSON="$ok_rc_go_refresh_json"
export CLI_SMOKE_OK_CLOUD_STATUS_PREVIEW_JSON="$ok_cloud_status_preview_json"
export CLI_SMOKE_OK_BUILD_ARTIFACT_PREVIEW_JSON="$ok_build_artifact_preview_json"
export CLI_SMOKE_OK_AFTER_SALES_FLOW_JSON="$ok_after_sales_flow_json"
export CLI_SMOKE_OK_ECOM_HOME_SURFACE_JSON="$ok_ecom_home_surface_json"

python3 - <<PY
import json
import os
from pathlib import Path
payload = {
    'status': 'ok',
    'tmp_root': '$TMP_ROOT',
    'checks': {
        'compile_json_ok': os.environ['CLI_SMOKE_OK_COMPILE_JSON'] == 'true',
        'single_page_landing_nav_json_ok': os.environ['CLI_SMOKE_OK_SINGLE_PAGE_LANDING_NAV_JSON'] == 'true',
        'after_sales_flow_json_ok': os.environ['CLI_SMOKE_OK_AFTER_SALES_FLOW_JSON'] == 'true',
        'ecom_home_surface_json_ok': os.environ['CLI_SMOKE_OK_ECOM_HOME_SURFACE_JSON'] == 'true',
        'ecom_checkout_flow_json_ok': os.environ['CLI_SMOKE_OK_ECOM_CHECKOUT_FLOW_JSON'] == 'true',
        'ecom_cart_flow_json_ok': os.environ['CLI_SMOKE_OK_ECOM_CART_FLOW_JSON'] == 'true',
        'ecom_product_feedback_json_ok': os.environ['CLI_SMOKE_OK_ECOM_PRODUCT_FEEDBACK_JSON'] == 'true',
        'website_check_json_ok': os.environ['CLI_SMOKE_OK_WEBSITE_CHECK_JSON'] == 'true',
        'website_check_out_of_scope_json_ok': os.environ['CLI_SMOKE_OK_WEBSITE_CHECK_OUT_OF_SCOPE_JSON'] == 'true',
        'website_check_experimental_dynamic_json_ok': os.environ['CLI_SMOKE_OK_WEBSITE_CHECK_EXPERIMENTAL_DYNAMIC_JSON'] == 'true',
        'website_assets_json_ok': os.environ['CLI_SMOKE_OK_WEBSITE_ASSETS_JSON'] == 'true',
        'website_assets_experimental_dynamic_json_ok': os.environ['CLI_SMOKE_OK_WEBSITE_ASSETS_EXPERIMENTAL_DYNAMIC_JSON'] == 'true',
        'website_assets_pack_json_ok': os.environ['CLI_SMOKE_OK_WEBSITE_ASSETS_PACK_JSON'] == 'true',
        'website_open_asset_json_ok': os.environ['CLI_SMOKE_OK_WEBSITE_OPEN_ASSET_JSON'] == 'true',
        'website_open_asset_pack_json_ok': os.environ['CLI_SMOKE_OK_WEBSITE_OPEN_ASSET_PACK_JSON'] == 'true',
        'website_inspect_asset_json_ok': os.environ['CLI_SMOKE_OK_WEBSITE_INSPECT_ASSET_JSON'] == 'true',
        'website_inspect_asset_pack_json_ok': os.environ['CLI_SMOKE_OK_WEBSITE_INSPECT_ASSET_PACK_JSON'] == 'true',
        'website_preview_json_ok': os.environ['CLI_SMOKE_OK_WEBSITE_PREVIEW_JSON'] == 'true',
        'website_preview_pack_json_ok': os.environ['CLI_SMOKE_OK_WEBSITE_PREVIEW_PACK_JSON'] == 'true',
        'website_run_inspect_command_json_ok': os.environ['CLI_SMOKE_OK_WEBSITE_RUN_INSPECT_COMMAND_JSON'] == 'true',
        'website_run_inspect_command_pack_json_ok': os.environ['CLI_SMOKE_OK_WEBSITE_RUN_INSPECT_COMMAND_PACK_JSON'] == 'true',
        'website_export_handoff_json_ok': os.environ['CLI_SMOKE_OK_WEBSITE_EXPORT_HANDOFF_JSON'] == 'true',
        'website_export_handoff_pack_json_ok': os.environ['CLI_SMOKE_OK_WEBSITE_EXPORT_HANDOFF_PACK_JSON'] == 'true',
        'website_summary_json_ok': os.environ['CLI_SMOKE_OK_WEBSITE_SUMMARY_JSON'] == 'true',
        'website_go_json_ok': os.environ['CLI_SMOKE_OK_WEBSITE_GO_JSON'] == 'true',
        'sync_json_ok': os.environ['CLI_SMOKE_OK_SYNC_JSON'] == 'true',
        'compile_error_json_ok': os.environ['CLI_SMOKE_OK_COMPILE_ERROR_JSON'] == 'true',
        'sync_conflict_json_ok': os.environ['CLI_SMOKE_OK_SYNC_CONFLICT_JSON'] == 'true',
        'diagnose_json_ok': os.environ['CLI_SMOKE_OK_DIAGNOSE_JSON'] == 'true',
        'repair_json_ok': os.environ['CLI_SMOKE_OK_REPAIR_JSON'] == 'true',
        'post_repair_diagnose_json_ok': os.environ['CLI_SMOKE_OK_POST_REPAIR_DIAGNOSE_JSON'] == 'true',
        'project_check_json_ok': os.environ['CLI_SMOKE_OK_PROJECT_CHECK_JSON'] == 'true',
        'project_check_conflict_json_ok': os.environ['CLI_SMOKE_OK_PROJECT_CHECK_CONFLICT_JSON'] == 'true',
        'project_doctor_json_ok': os.environ['CLI_SMOKE_OK_PROJECT_DOCTOR_JSON'] == 'true',
        'project_doctor_validation_json_ok': os.environ['CLI_SMOKE_OK_PROJECT_DOCTOR_VALIDATION_JSON'] == 'true',
        'project_doctor_apply_safe_noop_json_ok': os.environ['CLI_SMOKE_OK_PROJECT_DOCTOR_APPLY_SAFE_NOOP_JSON'] == 'true',
        'project_doctor_apply_safe_repair_json_ok': os.environ['CLI_SMOKE_OK_PROJECT_DOCTOR_APPLY_SAFE_REPAIR_JSON'] == 'true',
        'project_doctor_apply_safe_continue_noop_json_ok': os.environ['CLI_SMOKE_OK_PROJECT_DOCTOR_APPLY_SAFE_CONTINUE_NOOP_JSON'] == 'true',
        'project_doctor_apply_safe_continue_repair_json_ok': os.environ['CLI_SMOKE_OK_PROJECT_DOCTOR_APPLY_SAFE_CONTINUE_REPAIR_JSON'] == 'true',
        'project_continue_auto_repair_json_ok': os.environ['CLI_SMOKE_OK_PROJECT_CONTINUE_AUTO_REPAIR_JSON'] == 'true',
        'project_continue_auto_no_repair_json_ok': os.environ['CLI_SMOKE_OK_PROJECT_CONTINUE_AUTO_NO_REPAIR_JSON'] == 'true',
        'project_summary_json_ok': os.environ['CLI_SMOKE_OK_PROJECT_SUMMARY_JSON'] == 'true',
        'project_hooks_json_ok': os.environ['CLI_SMOKE_OK_PROJECT_HOOKS_JSON'] == 'true',
        'project_hooks_home_json_ok': os.environ['CLI_SMOKE_OK_PROJECT_HOOKS_HOME_JSON'] == 'true',
        'project_hook_init_json_ok': os.environ['CLI_SMOKE_OK_PROJECT_HOOK_INIT_JSON'] == 'true',
        'project_hook_guide_repo_json_ok': os.environ['CLI_SMOKE_OK_PROJECT_HOOK_GUIDE_REPO_JSON'] == 'true',
        'project_hook_guide_emit_shell_repo_ok': os.environ['CLI_SMOKE_OK_PROJECT_HOOK_GUIDE_EMIT_SHELL_REPO'] == 'true',
        'project_hook_guide_copy_command_repo_ok': os.environ['CLI_SMOKE_OK_PROJECT_HOOK_GUIDE_COPY_COMMAND_REPO'] == 'true',
        'project_hook_guide_run_command_repo_ok': os.environ['CLI_SMOKE_OK_PROJECT_HOOK_GUIDE_RUN_COMMAND_REPO'] == 'true',
        'project_hook_guide_run_command_yes_repo_ok': os.environ['CLI_SMOKE_OK_PROJECT_HOOK_GUIDE_RUN_COMMAND_YES_REPO'] == 'true',
        'project_hook_init_text_compact_repo_ok': os.environ['CLI_SMOKE_OK_PROJECT_HOOK_INIT_TEXT_COMPACT_REPO'] == 'true',
        'project_hook_init_explain_repo_ok': os.environ['CLI_SMOKE_OK_PROJECT_HOOK_INIT_EXPLAIN_REPO'] == 'true',
        'project_hook_init_emit_shell_repo_ok': os.environ['CLI_SMOKE_OK_PROJECT_HOOK_INIT_EMIT_SHELL_REPO'] == 'true',
        'project_hook_init_copy_command_repo_ok': os.environ['CLI_SMOKE_OK_PROJECT_HOOK_INIT_COPY_COMMAND_REPO'] == 'true',
        'project_hook_init_emit_confirm_shell_repo_ok': os.environ['CLI_SMOKE_OK_PROJECT_HOOK_INIT_EMIT_CONFIRM_SHELL_REPO'] == 'true',
        'project_hook_init_copy_confirm_command_repo_ok': os.environ['CLI_SMOKE_OK_PROJECT_HOOK_INIT_COPY_CONFIRM_COMMAND_REPO'] == 'true',
        'project_hook_init_emit_target_path_repo_ok': os.environ['CLI_SMOKE_OK_PROJECT_HOOK_INIT_EMIT_TARGET_PATH_REPO'] == 'true',
        'project_hook_init_copy_target_path_repo_ok': os.environ['CLI_SMOKE_OK_PROJECT_HOOK_INIT_COPY_TARGET_PATH_REPO'] == 'true',
        'project_hook_init_emit_target_dir_repo_ok': os.environ['CLI_SMOKE_OK_PROJECT_HOOK_INIT_EMIT_TARGET_DIR_REPO'] == 'true',
        'project_hook_init_copy_target_dir_repo_ok': os.environ['CLI_SMOKE_OK_PROJECT_HOOK_INIT_COPY_TARGET_DIR_REPO'] == 'true',
        'project_hook_init_emit_target_project_root_repo_ok': os.environ['CLI_SMOKE_OK_PROJECT_HOOK_INIT_EMIT_TARGET_PROJECT_ROOT_REPO'] == 'true',
        'project_hook_init_copy_target_project_root_repo_ok': os.environ['CLI_SMOKE_OK_PROJECT_HOOK_INIT_COPY_TARGET_PROJECT_ROOT_REPO'] == 'true',
        'project_hook_init_emit_target_project_name_repo_ok': os.environ['CLI_SMOKE_OK_PROJECT_HOOK_INIT_EMIT_TARGET_PROJECT_NAME_REPO'] == 'true',
        'project_hook_init_copy_target_project_name_repo_ok': os.environ['CLI_SMOKE_OK_PROJECT_HOOK_INIT_COPY_TARGET_PROJECT_NAME_REPO'] == 'true',
        'project_hook_init_emit_target_relative_path_repo_ok': os.environ['CLI_SMOKE_OK_PROJECT_HOOK_INIT_EMIT_TARGET_RELATIVE_PATH_REPO'] == 'true',
        'project_hook_init_copy_target_relative_path_repo_ok': os.environ['CLI_SMOKE_OK_PROJECT_HOOK_INIT_COPY_TARGET_RELATIVE_PATH_REPO'] == 'true',
        'project_hook_init_emit_target_bundle_repo_ok': os.environ['CLI_SMOKE_OK_PROJECT_HOOK_INIT_EMIT_TARGET_BUNDLE_REPO'] == 'true',
        'project_hook_init_copy_target_bundle_repo_ok': os.environ['CLI_SMOKE_OK_PROJECT_HOOK_INIT_COPY_TARGET_BUNDLE_REPO'] == 'true',
        'project_hook_init_emit_open_shell_repo_ok': os.environ['CLI_SMOKE_OK_PROJECT_HOOK_INIT_EMIT_OPEN_SHELL_REPO'] == 'true',
        'project_hook_init_copy_open_command_repo_ok': os.environ['CLI_SMOKE_OK_PROJECT_HOOK_INIT_COPY_OPEN_COMMAND_REPO'] == 'true',
        'project_hook_init_run_command_repo_ok': os.environ['CLI_SMOKE_OK_PROJECT_HOOK_INIT_RUN_COMMAND_REPO'] == 'true',
        'project_hook_init_run_command_yes_repo_ok': os.environ['CLI_SMOKE_OK_PROJECT_HOOK_INIT_RUN_COMMAND_YES_REPO'] == 'true',
        'project_hook_init_run_open_command_repo_ok': os.environ['CLI_SMOKE_OK_PROJECT_HOOK_INIT_RUN_OPEN_COMMAND_REPO'] == 'true',
        'project_hook_init_run_open_command_yes_repo_ok': os.environ['CLI_SMOKE_OK_PROJECT_HOOK_INIT_RUN_OPEN_COMMAND_YES_REPO'] == 'true',
        'project_hook_init_inspect_target_repo_ok': os.environ['CLI_SMOKE_OK_PROJECT_HOOK_INIT_INSPECT_TARGET_REPO'] == 'true',
        'project_hook_init_inspect_target_text_compact_repo_ok': os.environ['CLI_SMOKE_OK_PROJECT_HOOK_INIT_INSPECT_TARGET_TEXT_COMPACT_REPO'] == 'true',
        'project_hook_init_open_target_repo_ok': os.environ['CLI_SMOKE_OK_PROJECT_HOOK_INIT_OPEN_TARGET_REPO'] == 'true',
        'project_hook_init_open_now_repo_ok': os.environ['CLI_SMOKE_OK_PROJECT_HOOK_INIT_OPEN_NOW_REPO'] == 'true',
        'project_hook_init_open_now_text_compact_repo_ok': os.environ['CLI_SMOKE_OK_PROJECT_HOOK_INIT_OPEN_NOW_TEXT_COMPACT_REPO'] == 'true',
        'project_hook_init_force_json_ok': os.environ['CLI_SMOKE_OK_PROJECT_HOOK_INIT_FORCE_JSON'] == 'true',
        'project_hook_init_suggest_json_ok': os.environ['CLI_SMOKE_OK_PROJECT_HOOK_INIT_SUGGEST_JSON'] == 'true',
        'project_hook_init_open_catalog_json_ok': os.environ['CLI_SMOKE_OK_PROJECT_HOOK_INIT_OPEN_CATALOG_JSON'] == 'true',
        'project_hook_init_suggest_filtered_json_ok': os.environ['CLI_SMOKE_OK_PROJECT_HOOK_INIT_SUGGEST_FILTERED_JSON'] == 'true',
        'project_hook_init_suggest_slot_filtered_json_ok': os.environ['CLI_SMOKE_OK_PROJECT_HOOK_INIT_SUGGEST_SLOT_FILTERED_JSON'] == 'true',
        'project_hook_init_suggest_slot_only_json_ok': os.environ['CLI_SMOKE_OK_PROJECT_HOOK_INIT_SUGGEST_SLOT_ONLY_JSON'] == 'true',
        'project_hook_init_pick_json_ok': os.environ['CLI_SMOKE_OK_PROJECT_HOOK_INIT_PICK_JSON'] == 'true',
        'project_hook_init_pick_index_json_ok': os.environ['CLI_SMOKE_OK_PROJECT_HOOK_INIT_PICK_INDEX_JSON'] == 'true',
        'project_hook_init_pick_recommended_json_ok': os.environ['CLI_SMOKE_OK_PROJECT_HOOK_INIT_PICK_RECOMMENDED_JSON'] == 'true',
        'project_hook_init_recent_memory_pick_json_ok': os.environ['CLI_SMOKE_OK_PROJECT_HOOK_INIT_RECENT_MEMORY_PICK_JSON'] == 'true',
        'project_hook_init_reuse_last_suggest_json_ok': os.environ['CLI_SMOKE_OK_PROJECT_HOOK_INIT_REUSE_LAST_SUGGEST_JSON'] == 'true',
        'project_hook_init_last_suggest_json_ok': os.environ['CLI_SMOKE_OK_PROJECT_HOOK_INIT_LAST_SUGGEST_JSON'] == 'true',
        'project_summary_conflict_json_ok': os.environ['CLI_SMOKE_OK_PROJECT_SUMMARY_CONFLICT_JSON'] == 'true',
        'project_preview_json_ok': os.environ['CLI_SMOKE_OK_PROJECT_PREVIEW_JSON'] == 'true',
        'project_serve_dry_run_json_ok': os.environ['CLI_SMOKE_OK_PROJECT_SERVE_DRY_RUN_JSON'] == 'true',
        'project_preview_conflict_json_ok': os.environ['CLI_SMOKE_OK_PROJECT_PREVIEW_CONFLICT_JSON'] == 'true',
        'project_open_target_json_ok': os.environ['CLI_SMOKE_OK_PROJECT_OPEN_TARGET_JSON'] == 'true',
        'project_open_target_default_json_ok': os.environ['CLI_SMOKE_OK_PROJECT_OPEN_TARGET_DEFAULT_JSON'] == 'true',
        'project_inspect_target_json_ok': os.environ['CLI_SMOKE_OK_PROJECT_INSPECT_TARGET_JSON'] == 'true',
        'project_inspect_target_default_json_ok': os.environ['CLI_SMOKE_OK_PROJECT_INSPECT_TARGET_DEFAULT_JSON'] == 'true',
        'project_run_inspect_command_json_ok': os.environ['CLI_SMOKE_OK_PROJECT_RUN_INSPECT_COMMAND_JSON'] == 'true',
        'project_run_inspect_command_default_json_ok': os.environ['CLI_SMOKE_OK_PROJECT_RUN_INSPECT_COMMAND_DEFAULT_JSON'] == 'true',
        'project_export_handoff_json_ok': os.environ['CLI_SMOKE_OK_PROJECT_EXPORT_HANDOFF_JSON'] == 'true',
        'project_export_handoff_conflict_json_ok': os.environ['CLI_SMOKE_OK_PROJECT_EXPORT_HANDOFF_CONFLICT_JSON'] == 'true',
        'project_go_json_ok': os.environ['CLI_SMOKE_OK_PROJECT_GO_JSON'] == 'true',
        'project_go_repair_json_ok': os.environ['CLI_SMOKE_OK_PROJECT_GO_REPAIR_JSON'] == 'true',
        'project_go_conflict_json_ok': os.environ['CLI_SMOKE_OK_PROJECT_GO_CONFLICT_JSON'] == 'true',
        'workspace_status_repo_json_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_STATUS_REPO_JSON'] == 'true',
        'workspace_status_project_json_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_STATUS_PROJECT_JSON'] == 'true',
        'workspace_hooks_repo_json_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOKS_REPO_JSON'] == 'true',
        'workspace_hooks_project_json_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOKS_PROJECT_JSON'] == 'true',
        'workspace_hook_init_repo_json_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_REPO_JSON'] == 'true',
        'workspace_hook_guide_repo_json_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_GUIDE_REPO_JSON'] == 'true',
        'workspace_hook_guide_emit_shell_repo_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_GUIDE_EMIT_SHELL_REPO'] == 'true',
        'workspace_hook_guide_copy_command_repo_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_GUIDE_COPY_COMMAND_REPO'] == 'true',
        'workspace_hook_guide_run_command_repo_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_GUIDE_RUN_COMMAND_REPO'] == 'true',
        'workspace_hook_guide_run_command_yes_repo_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_GUIDE_RUN_COMMAND_YES_REPO'] == 'true',
        'workspace_hook_init_text_compact_repo_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_TEXT_COMPACT_REPO'] == 'true',
        'workspace_hook_init_explain_repo_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_EXPLAIN_REPO'] == 'true',
        'workspace_hook_init_emit_shell_repo_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_EMIT_SHELL_REPO'] == 'true',
        'workspace_hook_init_copy_command_repo_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_COPY_COMMAND_REPO'] == 'true',
        'workspace_hook_init_emit_confirm_shell_repo_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_EMIT_CONFIRM_SHELL_REPO'] == 'true',
        'workspace_hook_init_copy_confirm_command_repo_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_COPY_CONFIRM_COMMAND_REPO'] == 'true',
        'workspace_hook_init_emit_target_path_repo_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_EMIT_TARGET_PATH_REPO'] == 'true',
        'workspace_hook_init_copy_target_path_repo_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_COPY_TARGET_PATH_REPO'] == 'true',
        'workspace_hook_init_emit_target_dir_repo_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_EMIT_TARGET_DIR_REPO'] == 'true',
        'workspace_hook_init_copy_target_dir_repo_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_COPY_TARGET_DIR_REPO'] == 'true',
        'workspace_hook_init_emit_target_project_root_repo_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_EMIT_TARGET_PROJECT_ROOT_REPO'] == 'true',
        'workspace_hook_init_copy_target_project_root_repo_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_COPY_TARGET_PROJECT_ROOT_REPO'] == 'true',
        'workspace_hook_init_emit_target_project_name_repo_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_EMIT_TARGET_PROJECT_NAME_REPO'] == 'true',
        'workspace_hook_init_copy_target_project_name_repo_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_COPY_TARGET_PROJECT_NAME_REPO'] == 'true',
        'workspace_hook_init_emit_target_relative_path_repo_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_EMIT_TARGET_RELATIVE_PATH_REPO'] == 'true',
        'workspace_hook_init_copy_target_relative_path_repo_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_COPY_TARGET_RELATIVE_PATH_REPO'] == 'true',
        'workspace_hook_init_emit_target_bundle_repo_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_EMIT_TARGET_BUNDLE_REPO'] == 'true',
        'workspace_hook_init_copy_target_bundle_repo_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_COPY_TARGET_BUNDLE_REPO'] == 'true',
        'workspace_hook_init_emit_open_shell_repo_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_EMIT_OPEN_SHELL_REPO'] == 'true',
        'workspace_hook_init_copy_open_command_repo_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_COPY_OPEN_COMMAND_REPO'] == 'true',
        'workspace_hook_init_run_command_repo_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_RUN_COMMAND_REPO'] == 'true',
        'workspace_hook_init_run_command_yes_repo_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_RUN_COMMAND_YES_REPO'] == 'true',
        'workspace_hook_init_run_open_command_repo_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_RUN_OPEN_COMMAND_REPO'] == 'true',
        'workspace_hook_init_run_open_command_yes_repo_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_RUN_OPEN_COMMAND_YES_REPO'] == 'true',
        'workspace_hook_init_inspect_target_repo_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_INSPECT_TARGET_REPO'] == 'true',
        'workspace_hook_init_inspect_target_text_compact_repo_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_INSPECT_TARGET_TEXT_COMPACT_REPO'] == 'true',
        'workspace_hook_init_open_target_repo_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_OPEN_TARGET_REPO'] == 'true',
        'workspace_hook_init_open_now_repo_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_OPEN_NOW_REPO'] == 'true',
        'workspace_hook_init_open_now_text_compact_repo_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_OPEN_NOW_TEXT_COMPACT_REPO'] == 'true',
        'workspace_hook_init_project_json_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_PROJECT_JSON'] == 'true',
        'workspace_hook_init_recommended_repo_json_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_RECOMMENDED_REPO_JSON'] == 'true',
        'workspace_hook_init_recommended_suggest_repo_json_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_RECOMMENDED_SUGGEST_REPO_JSON'] == 'true',
        'workspace_hook_init_recommended_pick_repo_json_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_RECOMMENDED_PICK_REPO_JSON'] == 'true',
        'workspace_hook_init_follow_recommended_repo_json_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_FOLLOW_RECOMMENDED_REPO_JSON'] == 'true',
        'workspace_hook_init_use_last_project_repo_json_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_INIT_USE_LAST_PROJECT_REPO_JSON'] == 'true',
        'workspace_hook_continue_repo_json_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_CONTINUE_REPO_JSON'] == 'true',
        'workspace_hook_continue_broaden_repo_json_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_CONTINUE_BROADEN_REPO_JSON'] == 'true',
        'workspace_hook_continue_auto_repo_json_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_CONTINUE_AUTO_REPO_JSON'] == 'true',
        'workspace_hook_continue_dry_run_repo_json_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_CONTINUE_DRY_RUN_REPO_JSON'] == 'true',
        'workspace_hook_continue_text_compact_repo_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_CONTINUE_TEXT_COMPACT_REPO'] == 'true',
        'workspace_hook_continue_inspect_target_text_compact_repo_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_CONTINUE_INSPECT_TARGET_TEXT_COMPACT_REPO'] == 'true',
        'workspace_hook_continue_open_target_repo_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_CONTINUE_OPEN_TARGET_REPO'] == 'true',
        'workspace_hook_continue_open_now_repo_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_CONTINUE_OPEN_NOW_REPO'] == 'true',
        'workspace_hook_continue_open_now_text_compact_repo_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_CONTINUE_OPEN_NOW_TEXT_COMPACT_REPO'] == 'true',
        'workspace_hook_continue_open_now_text_compact_has_reason_repo_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_CONTINUE_OPEN_NOW_TEXT_COMPACT_HAS_REASON_REPO'] == 'true',
        'workspace_hook_continue_open_now_preview_repo_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_CONTINUE_OPEN_NOW_PREVIEW_REPO'] == 'true',
        'workspace_hook_continue_explain_repo_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_CONTINUE_EXPLAIN_REPO'] == 'true',
        'workspace_hook_continue_emit_shell_repo_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_CONTINUE_EMIT_SHELL_REPO'] == 'true',
        'workspace_hook_continue_emit_confirm_shell_repo_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_CONTINUE_EMIT_CONFIRM_SHELL_REPO'] == 'true',
        'workspace_hook_continue_emit_target_path_repo_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_CONTINUE_EMIT_TARGET_PATH_REPO'] == 'true',
        'workspace_hook_continue_emit_target_dir_repo_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_CONTINUE_EMIT_TARGET_DIR_REPO'] == 'true',
        'workspace_hook_continue_emit_target_project_root_repo_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_CONTINUE_EMIT_TARGET_PROJECT_ROOT_REPO'] == 'true',
        'workspace_hook_continue_emit_target_project_name_repo_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_CONTINUE_EMIT_TARGET_PROJECT_NAME_REPO'] == 'true',
        'workspace_hook_continue_emit_target_relative_path_repo_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_CONTINUE_EMIT_TARGET_RELATIVE_PATH_REPO'] == 'true',
        'workspace_hook_continue_emit_target_bundle_repo_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_CONTINUE_EMIT_TARGET_BUNDLE_REPO'] == 'true',
        'workspace_hook_continue_emit_open_shell_repo_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_CONTINUE_EMIT_OPEN_SHELL_REPO'] == 'true',
        'workspace_hook_continue_copy_open_command_repo_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_CONTINUE_COPY_OPEN_COMMAND_REPO'] == 'true',
        'workspace_hook_continue_copy_confirm_command_repo_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_CONTINUE_COPY_CONFIRM_COMMAND_REPO'] == 'true',
        'workspace_hook_continue_copy_target_path_repo_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_CONTINUE_COPY_TARGET_PATH_REPO'] == 'true',
        'workspace_hook_continue_copy_target_dir_repo_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_CONTINUE_COPY_TARGET_DIR_REPO'] == 'true',
        'workspace_hook_continue_copy_target_project_root_repo_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_CONTINUE_COPY_TARGET_PROJECT_ROOT_REPO'] == 'true',
        'workspace_hook_continue_copy_target_project_name_repo_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_CONTINUE_COPY_TARGET_PROJECT_NAME_REPO'] == 'true',
        'workspace_hook_continue_copy_target_relative_path_repo_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_CONTINUE_COPY_TARGET_RELATIVE_PATH_REPO'] == 'true',
        'workspace_hook_continue_copy_target_bundle_repo_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_CONTINUE_COPY_TARGET_BUNDLE_REPO'] == 'true',
        'workspace_hook_continue_copy_command_repo_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_CONTINUE_COPY_COMMAND_REPO'] == 'true',
        'workspace_hook_continue_run_open_command_repo_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_CONTINUE_RUN_OPEN_COMMAND_REPO'] == 'true',
        'workspace_hook_continue_run_open_command_yes_repo_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_CONTINUE_RUN_OPEN_COMMAND_YES_REPO'] == 'true',
        'workspace_hook_continue_run_command_repo_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_CONTINUE_RUN_COMMAND_REPO'] == 'true',
        'workspace_hook_continue_run_command_yes_repo_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_CONTINUE_RUN_COMMAND_YES_REPO'] == 'true',
        'workspace_hook_continue_inspect_target_repo_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_HOOK_CONTINUE_INSPECT_TARGET_REPO'] == 'true',
        'workspace_go_repo_json_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_GO_REPO_JSON'] == 'true',
        'workspace_go_project_json_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_GO_PROJECT_JSON'] == 'true',
        'workspace_summary_repo_json_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_SUMMARY_REPO_JSON'] == 'true',
        'workspace_summary_project_json_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_SUMMARY_PROJECT_JSON'] == 'true',
        'workspace_preview_repo_json_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_PREVIEW_REPO_JSON'] == 'true',
        'workspace_preview_project_json_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_PREVIEW_PROJECT_JSON'] == 'true',
        'workspace_open_target_repo_json_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_OPEN_TARGET_REPO_JSON'] == 'true',
        'workspace_open_target_project_json_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_OPEN_TARGET_PROJECT_JSON'] == 'true',
        'workspace_inspect_target_repo_json_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_INSPECT_TARGET_REPO_JSON'] == 'true',
        'workspace_inspect_target_project_json_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_INSPECT_TARGET_PROJECT_JSON'] == 'true',
        'workspace_run_inspect_command_repo_json_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_RUN_INSPECT_COMMAND_REPO_JSON'] == 'true',
        'workspace_run_inspect_command_project_json_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_RUN_INSPECT_COMMAND_PROJECT_JSON'] == 'true',
        'workspace_export_handoff_repo_json_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_EXPORT_HANDOFF_REPO_JSON'] == 'true',
        'workspace_export_handoff_project_json_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_EXPORT_HANDOFF_PROJECT_JSON'] == 'true',
        'workspace_doctor_repo_json_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_DOCTOR_REPO_JSON'] == 'true',
        'workspace_doctor_project_json_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_DOCTOR_PROJECT_JSON'] == 'true',
        'workspace_continue_repo_json_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_CONTINUE_REPO_JSON'] == 'true',
        'workspace_continue_project_json_ok': os.environ['CLI_SMOKE_OK_WORKSPACE_CONTINUE_PROJECT_JSON'] == 'true',
        'rc_check_json_ok': os.environ['CLI_SMOKE_OK_RC_CHECK_JSON'] == 'true',
        'rc_check_refresh_json_ok': os.environ['CLI_SMOKE_OK_RC_CHECK_REFRESH_JSON'] == 'true',
        'rc_go_json_ok': os.environ['CLI_SMOKE_OK_RC_GO_JSON'] == 'true',
        'rc_go_refresh_json_ok': os.environ['CLI_SMOKE_OK_RC_GO_REFRESH_JSON'] == 'true',
        'cloud_status_preview_json_ok': os.environ['CLI_SMOKE_OK_CLOUD_STATUS_PREVIEW_JSON'] == 'true',
        'build_artifact_preview_json_ok': os.environ['CLI_SMOKE_OK_BUILD_ARTIFACT_PREVIEW_JSON'] == 'true',
    },
}
Path('$RESULTS_JSON').write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
print(json.dumps(payload, indent=2, ensure_ascii=False))
PY
