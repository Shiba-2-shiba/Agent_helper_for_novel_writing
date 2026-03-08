"""
tests/test_scripts.py
小説作成フレームワーク スクリプトの動作テスト

実行方法:
    python -m pytest tests/ -v
"""
import json
import os
import sys
import subprocess
import shutil
import pytest

# プロジェクトルート（tests/ の親）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR  = os.path.join(PROJECT_ROOT, "scripts")
TEMPLATES_DIR = os.path.join(PROJECT_ROOT, "templates")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from eval_skill_trigger_qa import route_prompt
from prompt_utils import (
    count_completed_scene_files,
    compute_gate_threshold,
    compute_target_length_profile,
    load_target_length_profile,
    resolve_outline_path,
    resolve_target_profile_from_state,
    suggest_scene_output_path,
    UserFacingError,
)


RUNTIME_OUTLINE_TEXT = """# Outline

## 第1章 Chapter Card
- 章の役割: 導入
- 想定シーン数: 1
- 想定最小字数: 1000
- 想定目標字数: 1250

### Scene Ledger
| scene_id | scene_type | purpose | turn | payoff_or_seed | min | target | max | depends_on | status |
|---|---|---|---|---|---:|---:|---:|---|---|
| 1-1 | standard | 序盤の導入を置く | 平穏 -> 不穏 | 種まき | 1000 | 1250 | 1500 | - | planned |

## 第2章 Chapter Card
- 章の役割: 障害の提示
- 想定シーン数: 3
- 想定最小字数: 3000
- 想定目標字数: 3750

### Scene Ledger
| scene_id | scene_type | purpose | turn | payoff_or_seed | min | target | max | depends_on | status |
|---|---|---|---|---|---:|---:|---:|---|---|
| 2-1 | standard | 主人公が新しい依頼を受ける | 日常 -> 予感 | 種まき | 1000 | 1250 | 1500 | 1-1 | planned |
| 2-2 | standard | 仲間と合流し最初の障害にぶつかる | 警戒 -> 緊張 | 回収: 合流 / 種: 障害 | 1000 | 1250 | 1500 | 2-1 | planned |
| 2-3 | standard | 障害を越えるために決断する | 逡巡 -> 決断 | 次章への推進力 | 1000 | 1250 | 1500 | 2-2 | planned |
"""


def copy_markdown_templates(project_dir, *, skip_names=None):
    skip = set(skip_names or [])
    for name in os.listdir(TEMPLATES_DIR):
        if name.endswith(".md") and name not in skip:
            shutil.copy2(os.path.join(TEMPLATES_DIR, name), str(project_dir / name))


def write_utf8(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)


def build_state_schema_text(
    *,
    target_total_chars=None,
    target_length_profile="",
    planning_gate_enabled=True,
    planning_gate_min_chars=None,
    planning_target_total_chars=None,
    total_chars=None,
    length_mode="",
    planning_gate_status="ready",
    planned_total_min_chars=4000,
    planned_total_target_chars=5000,
    planned_scene_count=4,
):
    lines = ["targets:"]
    if target_total_chars is not None:
        lines.append(f"  target_total_chars: {target_total_chars}")
    if target_length_profile:
        lines.append(f"  target_length_profile: {target_length_profile}")
    if target_total_chars is not None or target_length_profile:
        lines.append(f"  planning_gate_enabled: {'true' if planning_gate_enabled else 'false'}")
    if planning_gate_min_chars is not None:
        lines.append(f"  planning_gate_min_chars: {planning_gate_min_chars}")
    if planning_target_total_chars is not None:
        lines.append(f"  planning_target_total_chars: {planning_target_total_chars}")
    if total_chars is not None:
        lines.append(f"  total_chars: {total_chars}")
    if length_mode:
        lines.append(f"  length_mode: {length_mode}")
    lines.extend(
        [
            "active_work:",
            f"  planning_gate_status: {planning_gate_status}",
            "progress:",
            f"  planned_total_min_chars: {planned_total_min_chars}",
            f"  planned_total_target_chars: {planned_total_target_chars}",
            f"  planned_scene_count: {planned_scene_count}",
            "narration_tense: 過去形",
        ]
    )
    return "\n".join(lines) + "\n"


def create_runtime_project(
    tmp_path,
    *,
    outline_filename="05_chapter_outline_100k.md",
    outline_text=RUNTIME_OUTLINE_TEXT,
    state_schema_text=None,
):
    proj = tmp_path / "runtime_proj"
    proj.mkdir()

    write_utf8(str(proj / outline_filename), outline_text)
    agent_memory = proj / "agent" / "memory"
    agent_memory.mkdir(parents=True)
    (agent_memory / "global_notes.md").write_text(
        "## 文体契約\n"
        "- 視点: 一人称（主人公）\n"
        "- 地の文時制: 過去形\n"
        "- 口調: 軽口を混ぜる\n"
        "- 禁止: メタ発言\n",
        encoding="utf-8",
    )
    (agent_memory / "session_notes.md").write_text(
        "- 仲間との距離感はまだ固い\n"
        "- 次の選択で信頼が揺れる\n",
        encoding="utf-8",
    )

    if state_schema_text is None:
        state_schema_text = build_state_schema_text(
            length_mode="long_form_100k",
            planning_gate_min_chars=3000,
            planning_target_total_chars=4000,
        )

    write_utf8(str(proj / "agent" / "state_schema_novel.yaml"), state_schema_text)
    (proj / "chapter_2_scene_1.txt").write_text(
        "主人公は市場で奇妙な依頼書を受け取り、胸騒ぎを覚えた。",
        encoding="utf-8",
    )
    (proj / "chapter_2_scene_2.txt").write_text(
        "仲間と合流したが、橋は崩れ、先へ進むには危険な川を渡るしかなかった。",
        encoding="utf-8",
    )
    return str(proj)


def scene_runtime_dir(project_dir, scene_id, mode):
    return os.path.join(project_dir, "runtime", "scenes", scene_id, mode)


# ---------------------------------------------------------------------------
# init_project.py のテスト
# ---------------------------------------------------------------------------

class TestInitProject:
    """init_project.py の動作検証"""

    def test_creates_correct_folder_structure(self, tmp_path, monkeypatch):
        """正しいフォルダ構造が作成されること"""
        monkeypatch.chdir(PROJECT_ROOT)
        # tmp_path 内にプロジェクト名を作る
        project_name = str(tmp_path / "test_novel")
        result = subprocess.run(
            [sys.executable, os.path.join(SCRIPTS_DIR, "init_project.py"), project_name],
            capture_output=True, text=True
        )
        assert result.returncode == 0, f"Expected exit 0, got: {result.stderr}"

        # テンプレートがコピーされているか
        for i in range(1, 6):
            md_name = [f for f in os.listdir(project_name) if f.startswith(f"0{i}_")]
            assert len(md_name) >= 1, f"Template 0{i}_*.md not found"

        # 章フォルダが作成されているか
        expected_chapters = [
            "chapter_1_introduction",
            "chapter_2_rising_action",
            "chapter_3_complication",
            "chapter_4_climax",
            "chapter_5_resolution",
        ]
        for ch in expected_chapters:
            ch_path = os.path.join(project_name, ch)
            assert os.path.isdir(ch_path), f"Chapter folder missing: {ch}"
            body_path = os.path.join(ch_path, "body.md")
            assert os.path.isfile(body_path), f"body.md missing in {ch}"

    def test_exits_with_error_on_existing_directory(self, tmp_path, monkeypatch):
        """既存ディレクトリへの再実行は exit code 1 で終了すること（S6修正の検証）"""
        monkeypatch.chdir(PROJECT_ROOT)
        project_name = str(tmp_path / "existing_novel")
        os.makedirs(project_name)

        result = subprocess.run(
            [sys.executable, os.path.join(SCRIPTS_DIR, "init_project.py"), project_name],
            capture_output=True, text=True
        )
        assert result.returncode == 1, f"Expected exit 1 for existing dir, got: {result.returncode}"
        assert "Error" in result.stdout or "Error" in result.stderr

    def test_from_ideas_transfers_logline(self, tmp_path, monkeypatch):
        """--from_ideas フラグで generated_ideas.md が転記されること（S2修正の検証）"""
        # generated_ideas.md をtmp内に偽装して BASE_DIR を差し替えるのは複雑なため、
        # generated_ideas.md をプロジェクトルートに一時配置してテスト
        ideas_path = os.path.join(PROJECT_ROOT, "generated_ideas.md")
        sample_logline = "【テスト世界観】を舞台に、【臆病な主人公】が、【村の滅亡】をきっかけに、【世界を救う】を目指す物語。"
        try:
            with open(ideas_path, "w", encoding="utf-8") as f:
                f.write("# 生成されたアイディアメモ\n\n## ログライン\n")
                f.write(f"> {sample_logline}\n\n## 回答ログ\n- **ジャンル/ターゲット**: テスト用\n")

            project_name = str(tmp_path / "from_ideas_novel")
            result = subprocess.run(
                [sys.executable, os.path.join(SCRIPTS_DIR, "init_project.py"),
                 project_name, "--from_ideas"],
                capture_output=True, text=True
            )
            assert result.returncode == 0, result.stderr

            concept_path = os.path.join(project_name, "01_concept_sheet.md")
            with open(concept_path, "r", encoding="utf-8") as f:
                content = f.read()
            assert sample_logline in content, "Logline was not transferred to 01_concept_sheet.md"
        finally:
            if os.path.exists(ideas_path):
                os.remove(ideas_path)

    @pytest.mark.parametrize(
        ("target_total_chars", "target_length_profile", "planning_gate_min_chars"),
        [
            (30000, "novel_30k", 24000),
            (50000, "novel_50k", 40000),
            (100000, "novel_100k", 80000),
        ],
    )
    def test_canonical_init_project_writes_target_profile(
        self,
        tmp_path,
        monkeypatch,
        target_total_chars,
        target_length_profile,
        planning_gate_min_chars,
    ):
        """新規 project で canonical target fields と outline が生成されること"""
        monkeypatch.chdir(PROJECT_ROOT)
        project_name = str(tmp_path / f"target_{target_total_chars}")
        result = subprocess.run(
            [
                sys.executable,
                os.path.join(SCRIPTS_DIR, "init_project.py"),
                project_name,
                "--target-total-chars",
                str(target_total_chars),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stdout + result.stderr

        state_schema_path = os.path.join(project_name, "agent", "state_schema_novel.yaml")
        outline_path = os.path.join(project_name, "05_chapter_outline.md")
        legacy_outline_path = os.path.join(project_name, "05_chapter_outline_100k.md")
        global_notes_path = os.path.join(project_name, "agent", "memory", "global_notes.md")
        session_notes_path = os.path.join(project_name, "agent", "memory", "session_notes.md")

        assert os.path.isfile(state_schema_path)
        assert os.path.isfile(outline_path)
        assert not os.path.exists(legacy_outline_path)
        assert os.path.isfile(global_notes_path)
        assert os.path.isfile(session_notes_path)

        state_schema_text = open(state_schema_path, "r", encoding="utf-8").read()
        outline_text = open(outline_path, "r", encoding="utf-8").read()

        assert f"target_total_chars: {target_total_chars}" in state_schema_text
        assert f'target_length_profile: "{target_length_profile}"' in state_schema_text
        assert "planning_gate_enabled: true" in state_schema_text
        assert f"planning_gate_min_chars: {planning_gate_min_chars}" in state_schema_text
        assert f"planning_target_total_chars: {target_total_chars}" in state_schema_text
        assert "length_mode:" not in state_schema_text
        assert f"- 全体目標文字数: {target_total_chars}" in outline_text
        assert f"- 計画ゲート下限: {planning_gate_min_chars}" in outline_text

    def test_init_project_requires_target_total_chars(self, tmp_path, monkeypatch):
        """target 未指定では初期化を開始しないこと"""
        monkeypatch.chdir(PROJECT_ROOT)
        project_name = str(tmp_path / "missing_target_novel")
        result = subprocess.run(
            [sys.executable, os.path.join(SCRIPTS_DIR, "init_project.py"), project_name],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "--target-total-chars" in (result.stdout + result.stderr)


# ---------------------------------------------------------------------------
# build_llm_prompt.py のテスト
# ---------------------------------------------------------------------------

class TestBuildLLMPrompt:
    """build_llm_prompt.py の動作検証"""

    @pytest.fixture()
    def sample_project(self, tmp_path):
        """サンプルプロジェクトを tmp_path 内に生成してパスを返す"""
        proj = tmp_path / "sample_proj"
        proj.mkdir()
        copy_markdown_templates(proj)
        return str(proj)

    def test_generates_output_file(self, sample_project):
        """llm_prompt_output.txt が生成されること"""
        result = subprocess.run(
            [sys.executable, os.path.join(SCRIPTS_DIR, "build_llm_prompt.py"),
             "--project", sample_project, "--chapter", "1"],
            capture_output=True, text=True
        )
        assert result.returncode == 0, result.stderr
        out_path = os.path.join(sample_project, "llm_prompt_output.txt")
        assert os.path.isfile(out_path), "llm_prompt_output.txt was not created"

    def test_output_contains_required_sections(self, sample_project):
        """出力ファイルに必要なセクションが含まれること（S4修正の検証）"""
        subprocess.run(
            [sys.executable, os.path.join(SCRIPTS_DIR, "build_llm_prompt.py"),
             "--project", sample_project, "--chapter", "1"],
            capture_output=True, text=True
        )
        out_path = os.path.join(sample_project, "llm_prompt_output.txt")
        with open(out_path, "r", encoding="utf-8") as f:
            content = f.read()

        required_sections = [
            "### 1. 物語のコア設定",
            "### 2. キャラクター情報",
            "### 3. 世界観",
            "### 4. プロット概要",
            "### 5. 現在の章のシーン構成",
        ]
        for section in required_sections:
            assert section in content, f"Required section missing: {section}"

    def test_exits_with_error_on_missing_project(self, tmp_path):
        """存在しないプロジェクトでは exit code 1 で終了すること（S3修正の検証）"""
        result = subprocess.run(
            [sys.executable, os.path.join(SCRIPTS_DIR, "build_llm_prompt.py"),
             "--project", str(tmp_path / "nonexistent"), "--chapter", "1"],
            capture_output=True, text=True
        )
        assert result.returncode == 1, f"Expected exit 1, got: {result.returncode}"

    def test_token_estimate_is_printed(self, sample_project):
        """推定トークン数が標準出力に表示されること（フェーズ3の検証）"""
        result = subprocess.run(
            [sys.executable, os.path.join(SCRIPTS_DIR, "build_llm_prompt.py"),
             "--project", sample_project, "--chapter", "1"],
            capture_output=True, text=True
        )
        assert "推定トークン数" in result.stdout, "Token estimate not shown in output"
        assert "legacy full-context path" in result.stdout, "Legacy warning not shown in output"

    def test_prompt_contains_length_contract(self, sample_project):
        """出力に文字数契約セクションが含まれること"""
        result = subprocess.run(
            [sys.executable, os.path.join(SCRIPTS_DIR, "build_llm_prompt.py"),
             "--project", sample_project, "--chapter", "1", "--mode", "prose"],
            capture_output=True, text=True
        )
        assert result.returncode == 0, result.stderr
        out_path = os.path.join(sample_project, "llm_prompt_output.txt")
        content = open(out_path, "r", encoding="utf-8").read()
        assert "### 6. 文字数契約 (Length Contract)" in content
        assert "scene_min_chars: 1,000" in content
        assert "scene_target_chars: 1,250" in content
        assert "scene_max_chars: 1,500" in content
        assert "scene_min_chars" in content
        assert "scene_target_chars" in content
        assert "scene_max_chars" in content

    def test_prompt_contains_style_contract(self, sample_project):
        """global_notes の文体契約がプロンプトに反映されること"""
        style_dir = os.path.join(sample_project, "agent", "memory")
        os.makedirs(style_dir, exist_ok=True)
        global_notes = os.path.join(style_dir, "global_notes.md")
        with open(global_notes, "w", encoding="utf-8") as f:
            f.write(
                "## 文体契約\n"
                "- 視点: 一人称（ジェイク）\n"
                "- 主人公語尾: 「〜かな」「〜だよね」\n"
            )

        result = subprocess.run(
            [sys.executable, os.path.join(SCRIPTS_DIR, "build_llm_prompt.py"),
             "--project", sample_project, "--chapter", "1"],
            capture_output=True, text=True
        )
        assert result.returncode == 0, result.stderr
        out_path = os.path.join(sample_project, "llm_prompt_output.txt")
        content = open(out_path, "r", encoding="utf-8").read()
        assert "### 7. 文体契約 (Style Contract)" in content
        assert "視点: 一人称（ジェイク）" in content

    def test_auto_load_previous_text_when_missing(self, sample_project):
        """previous_text 未指定時に直近シーンを自動読込すること"""
        chapter_dir = os.path.join(sample_project, "chapter_2_rising_action")
        os.makedirs(chapter_dir, exist_ok=True)
        scene_1 = os.path.join(chapter_dir, "chapter_2_scene_1.txt")
        scene_2 = os.path.join(chapter_dir, "chapter_2_scene_2.txt")
        with open(scene_1, "w", encoding="utf-8") as f:
            f.write("これは第2章シーン1の本文です。")
        with open(scene_2, "w", encoding="utf-8") as f:
            f.write("これは第2章シーン2の本文です。")

        result = subprocess.run(
            [sys.executable, os.path.join(SCRIPTS_DIR, "build_llm_prompt.py"),
             "--project", sample_project, "--chapter", "2"],
            capture_output=True, text=True
        )
        assert result.returncode == 0, result.stderr
        out_path = os.path.join(sample_project, "llm_prompt_output.txt")
        content = open(out_path, "r", encoding="utf-8").read()
        assert "### 8. 連続性要約（直近話）" in content
        assert "Source (auto_hybrid)" in content
        assert "chapter_2_scene_2.txt" in content
        assert "### 10. 直前シーン本文（参照原文）" in content

    def test_mode_prose_forbids_idea_output_instruction(self, sample_project):
        """prose モードではアイデア出力指示が入らないこと"""
        result = subprocess.run(
            [sys.executable, os.path.join(SCRIPTS_DIR, "build_llm_prompt.py"),
             "--project", sample_project, "--chapter", "1", "--mode", "prose"],
            capture_output=True, text=True
        )
        assert result.returncode == 0, result.stderr
        out_path = os.path.join(sample_project, "llm_prompt_output.txt")
        content = open(out_path, "r", encoding="utf-8").read()
        assert "展開アイデアを5案提示" not in content
        assert "本文のみを出力する" in content

    def test_batch_scene_prompt_includes_sequential_rule(self, sample_project):
        """複数話指定時に逐次生成ルールが入ること"""
        result = subprocess.run(
            [sys.executable, os.path.join(SCRIPTS_DIR, "build_llm_prompt.py"),
             "--project", sample_project, "--chapter", "2",
             "--batch_scenes", "2-1,2-2,2-3"],
            capture_output=True, text=True
        )
        assert result.returncode == 0, result.stderr
        out_path = os.path.join(sample_project, "llm_prompt_output.txt")
        content = open(out_path, "r", encoding="utf-8").read()
        assert "逐次生成ルール" in content
        assert "`2-1`" in content

    def test_legacy_build_llm_prompt_works_with_old_outline_only(self, tmp_path):
        """legacy outline のみでも build_llm_prompt が動くこと"""
        proj = tmp_path / "legacy_prompt_proj"
        proj.mkdir()
        copy_markdown_templates(proj, skip_names={"05_chapter_outline.md"})
        result = subprocess.run(
            [
                sys.executable,
                os.path.join(SCRIPTS_DIR, "build_llm_prompt.py"),
                "--project",
                str(proj),
                "--chapter",
                "1",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert os.path.isfile(os.path.join(proj, "llm_prompt_output.txt"))

    def test_canonical_build_llm_prompt_works_with_new_outline_only(self, tmp_path):
        """canonical outline のみでも build_llm_prompt が動くこと"""
        proj = tmp_path / "canonical_prompt_proj"
        proj.mkdir()
        copy_markdown_templates(proj, skip_names={"05_chapter_outline_100k.md"})
        result = subprocess.run(
            [
                sys.executable,
                os.path.join(SCRIPTS_DIR, "build_llm_prompt.py"),
                "--project",
                str(proj),
                "--chapter",
                "1",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert os.path.isfile(os.path.join(proj, "llm_prompt_output.txt"))


class TestTargetProfileResolvers:
    """target profile resolver の互換レイヤ検証"""

    def test_legacy_state_without_new_fields_resolves_to_100k_profile(self, tmp_path):
        project_dir = tmp_path / "legacy_state_project"
        write_utf8(
            str(project_dir / "agent" / "state_schema_novel.yaml"),
            build_state_schema_text(
                length_mode="long_form_100k",
                planning_gate_min_chars=80000,
                planning_target_total_chars=100000,
            ),
        )

        payload = load_target_length_profile(str(project_dir))

        assert payload["target_total_chars"] == 100000
        assert payload["target_length_profile"] == "novel_100k"
        assert payload["planning_gate_enabled"] is True
        assert payload["planning_gate_min_chars"] == 80000
        assert payload["planning_target_total_chars"] == 100000
        assert payload["source"] == "legacy_planning_target"

    def test_legacy_length_mode_long_form_100k_maps_to_novel_100k(self):
        payload = resolve_target_profile_from_state(
            "targets:\n"
            "  length_mode: long_form_100k\n"
        )

        assert payload["target_total_chars"] == 100000
        assert payload["target_length_profile"] == "novel_100k"
        assert payload["source"] == "legacy_length_mode"

    def test_canonical_30k_state_resolves_to_30k_profile(self):
        payload = resolve_target_profile_from_state(
            build_state_schema_text(
                target_total_chars=30000,
                target_length_profile="novel_30k",
                planning_gate_min_chars=24000,
                planning_target_total_chars=30000,
            )
        )

        assert payload["target_total_chars"] == 30000
        assert payload["target_length_profile"] == "novel_30k"
        assert payload["planning_gate_min_chars"] == 24000
        assert payload["planning_target_total_chars"] == 30000
        assert payload["source"] == "canonical_state"

    def test_canonical_50k_state_resolves_to_50k_profile(self):
        payload = resolve_target_profile_from_state(
            build_state_schema_text(
                target_total_chars=50000,
                target_length_profile="novel_50k",
                planning_gate_min_chars=40000,
                planning_target_total_chars=50000,
            )
        )

        assert payload["target_total_chars"] == 50000
        assert payload["target_length_profile"] == "novel_50k"
        assert payload["planning_gate_min_chars"] == 40000
        assert payload["planning_target_total_chars"] == 50000
        assert payload["source"] == "canonical_state"

    def test_mixed_new_profile_with_legacy_fields_present_prefers_new_fields(self):
        payload = resolve_target_profile_from_state(
            build_state_schema_text(
                target_total_chars=50000,
                target_length_profile="novel_50k",
                planning_gate_min_chars=40000,
                planning_target_total_chars=50000,
                total_chars=100000,
                length_mode="long_form_100k",
            )
        )

        assert payload["target_total_chars"] == 50000
        assert payload["target_length_profile"] == "novel_50k"
        assert payload["planning_gate_min_chars"] == 40000
        assert payload["planning_target_total_chars"] == 50000
        assert payload["source"] == "canonical_state"

    def test_legacy_outline_filename_is_discoverable(self, tmp_path):
        project_dir = tmp_path / "legacy_outline_project"
        project_dir.mkdir()
        write_utf8(str(project_dir / "05_chapter_outline_100k.md"), "# legacy outline\n")

        resolved = resolve_outline_path(str(project_dir), require_exists=True)

        assert resolved.endswith("05_chapter_outline_100k.md")

    def test_canonical_outline_filename_is_preferred_when_present(self, tmp_path):
        project_dir = tmp_path / "canonical_outline_project"
        project_dir.mkdir()
        write_utf8(str(project_dir / "05_chapter_outline_100k.md"), "# legacy outline\n")
        write_utf8(str(project_dir / "05_chapter_outline.md"), "# canonical outline\n")

        resolved = resolve_outline_path(str(project_dir), require_exists=True)

        assert resolved.endswith("05_chapter_outline.md")

    @pytest.mark.parametrize(
        ("target_total_chars", "target_length_profile", "planning_gate_min_chars"),
        [
            (30000, "novel_30k", 24000),
            (50000, "novel_50k", 40000),
            (100000, "novel_100k", 80000),
        ],
    )
    def test_compute_gate_threshold_matches_profile(
        self,
        target_total_chars,
        target_length_profile,
        planning_gate_min_chars,
    ):
        assert compute_target_length_profile(target_total_chars) == target_length_profile
        assert compute_gate_threshold(target_total_chars) == planning_gate_min_chars

    def test_invalid_target_total_chars_fails_fast(self):
        with pytest.raises(UserFacingError, match="unsupported target_total_chars: 75000"):
            resolve_target_profile_from_state(
                build_state_schema_text(
                    target_total_chars=75000,
                    planning_gate_min_chars=60000,
                    planning_target_total_chars=75000,
                )
            )

    def test_invalid_target_length_profile_fails_fast(self):
        with pytest.raises(UserFacingError, match="unsupported target_length_profile: novel_70k"):
            resolve_target_profile_from_state(
                build_state_schema_text(
                    target_length_profile="novel_70k",
                )
            )

    def test_count_completed_scene_files_supports_scene_dash_filenames(self, tmp_path):
        project_dir = tmp_path / "dash_scene_names"
        chapter_dir = project_dir / "chapter_1_introduction"
        chapter_dir.mkdir(parents=True)
        (chapter_dir / "scene_1-1.txt").write_text("本文", encoding="utf-8")
        (chapter_dir / "scene_1-3.txt").write_text("本文", encoding="utf-8")
        assert count_completed_scene_files(str(project_dir)) == 2


class TestRuntimeRefactorScripts:
    """runtime 系スクリプトの動作検証"""

    @pytest.fixture()
    def runtime_project(self, tmp_path):
        return create_runtime_project(tmp_path)

    def test_runtime_flow_generates_compact_files_and_expand_prompt(self, runtime_project):
        runtime_result = subprocess.run(
            [
                sys.executable,
                os.path.join(SCRIPTS_DIR, "build_runtime_context.py"),
                "--project",
                runtime_project,
                "--chapter",
                "2",
                "--scene",
                "2-3",
                "--mode",
                "draft",
            ],
            capture_output=True,
            text=True,
        )
        assert runtime_result.returncode == 0, runtime_result.stdout + runtime_result.stderr

        runtime_dir = scene_runtime_dir(runtime_project, "2-3", "draft")
        for name in (
            "style_contract_compact.md",
            "scene_brief_compact.md",
            "continuity_pack.md",
            "request_compact.md",
            "planning_gate_brief.md",
        ):
            assert os.path.isfile(os.path.join(runtime_dir, name)), f"Missing runtime file: {name}"
        assert os.path.isfile(os.path.join(runtime_project, "runtime", "runtime_index.json"))

        planning_gate_brief = open(os.path.join(runtime_dir, "planning_gate_brief.md"), "r", encoding="utf-8").read()
        assert "Planning Gate: ready" in planning_gate_brief
        assert "Planned Total Min Chars: 4000" in planning_gate_brief
        assert "Target Total Chars: 100000" in planning_gate_brief
        assert "Target Length Profile: novel_100k" in planning_gate_brief
        assert "Planning Gate Enabled: true" in planning_gate_brief
        assert "Next Planning Action:" in planning_gate_brief

        request_compact = open(os.path.join(runtime_dir, "request_compact.md"), "r", encoding="utf-8").read()
        assert "- Target Total Chars: 100000" in request_compact
        assert "- Target Length Profile: novel_100k" in request_compact
        assert "- Planning Gate Enabled: true" in request_compact

        scene_brief = open(os.path.join(runtime_dir, "scene_brief_compact.md"), "r", encoding="utf-8").read()
        assert "Target Total Chars: 100000" in scene_brief
        assert "Target Length Profile: novel_100k" in scene_brief
        assert "Planning Gate Enabled: true" in scene_brief

        continuity = open(os.path.join(runtime_dir, "continuity_pack.md"), "r", encoding="utf-8").read()
        assert "chapter_2_scene_2.txt" in continuity
        assert "chapter_2_scene_1.txt" in continuity

        draft_prompt_result = subprocess.run(
            [
                sys.executable,
                os.path.join(SCRIPTS_DIR, "build_draft_prompt.py"),
                "--project",
                runtime_project,
            ],
            capture_output=True,
            text=True,
        )
        assert draft_prompt_result.returncode == 0, draft_prompt_result.stdout + draft_prompt_result.stderr
        assert "estimated_tokens=" in draft_prompt_result.stdout
        draft_prompt = open(os.path.join(runtime_dir, "draft_prompt.txt"), "r", encoding="utf-8").read()
        assert "## Planning Gate Brief" in draft_prompt
        assert draft_prompt.rstrip().endswith("本文のみ出力")

        short_text_path = os.path.join(runtime_project, "draft_short.txt")
        with open(short_text_path, "w", encoding="utf-8") as handle:
            handle.write("「短い」\n\n主人公は息を整えた。")

        check_result = subprocess.run(
            [
                sys.executable,
                os.path.join(SCRIPTS_DIR, "check_scene_output.py"),
                "--project",
                runtime_project,
                "--text",
                short_text_path,
            ],
            capture_output=True,
            text=True,
        )
        assert check_result.returncode == 0, check_result.stdout + check_result.stderr
        report_path = os.path.join(runtime_dir, "check_report.json")
        report = json.load(open(report_path, "r", encoding="utf-8"))
        assert report["min_chars"] == 1000
        assert report["target_chars"] == 1250
        assert report["max_chars"] == 1500
        assert report["needs_expand"] is True
        assert report["within_max"] is True

        expand_result = subprocess.run(
            [
                sys.executable,
                os.path.join(SCRIPTS_DIR, "build_expand_prompt.py"),
                "--project",
                runtime_project,
                "--draft_text",
                short_text_path,
            ],
            capture_output=True,
            text=True,
        )
        assert expand_result.returncode == 0, expand_result.stdout + expand_result.stderr
        assert "estimated_tokens=" in expand_result.stdout
        instruction = open(os.path.join(runtime_dir, "expand_instruction.md"), "r", encoding="utf-8").read()
        expand_prompt = open(os.path.join(runtime_dir, "expand_prompt.txt"), "r", encoding="utf-8").read()
        assert "Missing Chars:" in instruction
        assert "structured_local_insertions" in instruction
        assert "途中への差し込みも可" in instruction
        assert "返答は局所差分ブロックのみ" in expand_prompt
        assert "## Existing Paragraph Map" in expand_prompt
        assert "TARGET: after P2" in expand_prompt
        assert "最初の行は必ず `[EDIT 1]` から始める" in expand_prompt
        assert "`ANCHOR:` は `Existing Paragraph Map` の `- Pn:` の右側をそのままコピペする" in expand_prompt
        assert "## Response Template" in expand_prompt
        assert "## Bad Output Examples" in expand_prompt
        assert os.path.isfile(os.path.join(runtime_dir, "expand_prompt.txt"))

        edits_path = os.path.join(runtime_project, "expand_response.txt")
        with open(edits_path, "w", encoding="utf-8") as handle:
            handle.write(
                "[EDIT 1]\n"
                "TARGET: after P1\n"
                "ANCHOR: 「短い」\n"
                "TEXT:\n"
                "彼は返事の意味を測りかねて、喉の奥の熱を飲み込んだ。\n\n"
                "[EDIT 2]\n"
                "TARGET: end_of_text\n"
                "ANCHOR: END\n"
                "TEXT:\n"
                "それでも足を止める理由にはならないと、彼は壁から背を離した。\n"
            )

        apply_result = subprocess.run(
            [
                sys.executable,
                os.path.join(SCRIPTS_DIR, "apply_expand_edits.py"),
                "--project",
                runtime_project,
                "--text",
                short_text_path,
                "--edits",
                edits_path,
            ],
            capture_output=True,
            text=True,
        )
        assert apply_result.returncode == 0, apply_result.stdout + apply_result.stderr
        updated_text = open(short_text_path, "r", encoding="utf-8").read()
        assert "彼は返事の意味を測りかねて" in updated_text
        assert "それでも足を止める理由にはならない" in updated_text
        assert updated_text.index("彼は返事の意味を測りかねて") < updated_text.index("主人公は息を整えた。")

    def test_legacy_runtime_context_works_with_old_outline_only(self, tmp_path):
        project_dir = create_runtime_project(tmp_path, outline_filename="05_chapter_outline_100k.md")

        result = subprocess.run(
            [
                sys.executable,
                os.path.join(SCRIPTS_DIR, "build_runtime_context.py"),
                "--project",
                project_dir,
                "--chapter",
                "2",
                "--scene",
                "2-3",
                "--mode",
                "draft",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, result.stdout + result.stderr
        assert os.path.isfile(os.path.join(scene_runtime_dir(project_dir, "2-3", "draft"), "scene_brief_compact.md"))

    def test_canonical_runtime_context_works_with_new_outline_only(self, tmp_path):
        project_dir = create_runtime_project(
            tmp_path,
            outline_filename="05_chapter_outline.md",
            state_schema_text=build_state_schema_text(
                target_total_chars=50000,
                target_length_profile="novel_50k",
                planning_gate_min_chars=40000,
                planning_target_total_chars=50000,
            ),
        )

        result = subprocess.run(
            [
                sys.executable,
                os.path.join(SCRIPTS_DIR, "build_runtime_context.py"),
                "--project",
                project_dir,
                "--chapter",
                "2",
                "--scene",
                "2-3",
                "--mode",
                "draft",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, result.stdout + result.stderr
        planning_gate_brief = open(
            os.path.join(scene_runtime_dir(project_dir, "2-3", "draft"), "planning_gate_brief.md"),
            "r",
            encoding="utf-8",
        ).read()
        assert "Target Total Chars: 50000" in planning_gate_brief
        assert "Target Length Profile: novel_50k" in planning_gate_brief

    def test_mixed_new_state_with_legacy_outline_passes(self, tmp_path):
        project_dir = create_runtime_project(
            tmp_path,
            outline_filename="05_chapter_outline_100k.md",
            state_schema_text=build_state_schema_text(
                target_total_chars=30000,
                target_length_profile="novel_30k",
                planning_gate_min_chars=24000,
                planning_target_total_chars=30000,
                total_chars=100000,
                length_mode="long_form_100k",
            ),
        )

        result = subprocess.run(
            [
                sys.executable,
                os.path.join(SCRIPTS_DIR, "build_runtime_context.py"),
                "--project",
                project_dir,
                "--chapter",
                "2",
                "--scene",
                "2-3",
                "--mode",
                "draft",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, result.stdout + result.stderr
        planning_gate_brief = open(
            os.path.join(scene_runtime_dir(project_dir, "2-3", "draft"), "planning_gate_brief.md"),
            "r",
            encoding="utf-8",
        ).read()
        request_compact = open(
            os.path.join(scene_runtime_dir(project_dir, "2-3", "draft"), "request_compact.md"),
            "r",
            encoding="utf-8",
        ).read()
        assert "Target Total Chars: 30000" in planning_gate_brief
        assert "Target Length Profile: novel_30k" in planning_gate_brief
        assert "- Target Total Chars: 30000" in request_compact
        assert "- Target Length Profile: novel_30k" in request_compact
        assert "- Length Mode: long_form_100k" in request_compact

    def test_mixed_legacy_state_with_new_outline_passes(self, tmp_path):
        project_dir = create_runtime_project(
            tmp_path,
            outline_filename="05_chapter_outline.md",
            state_schema_text=build_state_schema_text(
                length_mode="long_form_100k",
                planning_gate_min_chars=80000,
                planning_target_total_chars=100000,
            ),
        )

        result = subprocess.run(
            [
                sys.executable,
                os.path.join(SCRIPTS_DIR, "build_runtime_context.py"),
                "--project",
                project_dir,
                "--chapter",
                "2",
                "--scene",
                "2-3",
                "--mode",
                "draft",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, result.stdout + result.stderr
        planning_gate_brief = open(
            os.path.join(scene_runtime_dir(project_dir, "2-3", "draft"), "planning_gate_brief.md"),
            "r",
            encoding="utf-8",
        ).read()
        assert "Target Total Chars: 100000" in planning_gate_brief
        assert "Target Length Profile: novel_100k" in planning_gate_brief

    def test_build_draft_prompt_fails_when_runtime_inputs_are_missing(self, tmp_path):
        project_dir = tmp_path / "missing_runtime"
        runtime_dir = project_dir / "runtime"
        runtime_dir.mkdir(parents=True)
        (runtime_dir / "style_contract_compact.md").write_text("stub", encoding="utf-8")

        result = subprocess.run(
            [
                sys.executable,
                os.path.join(SCRIPTS_DIR, "build_draft_prompt.py"),
                "--project",
                str(project_dir),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1
        assert "ERROR:" in result.stdout

    def test_build_draft_prompt_fails_when_planning_gate_is_blocked(self, tmp_path):
        project_dir = tmp_path / "planning_blocked"
        runtime_dir = project_dir / "runtime"
        runtime_dir.mkdir(parents=True)
        (runtime_dir / "style_contract_compact.md").write_text("# Style Contract Compact", encoding="utf-8")
        (runtime_dir / "scene_brief_compact.md").write_text(
            "# Scene Brief Compact\n"
            "Scene Type: standard\n"
            "Length Band: 1000 / 1250 / 1500\n"
            "- Planning Gate: blocked\n",
            encoding="utf-8",
        )
        (runtime_dir / "continuity_pack.md").write_text("# Continuity Pack", encoding="utf-8")
        (runtime_dir / "request_compact.md").write_text(
            "# Request Compact\n"
            "- Length Mode: long_form_100k\n"
            "- Planning Gate: blocked\n",
            encoding="utf-8",
        )

        result = subprocess.run(
            [
                sys.executable,
                os.path.join(SCRIPTS_DIR, "build_draft_prompt.py"),
                "--project",
                str(project_dir),
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 1
        assert "planning_gate_status is not ready" in result.stdout
        assert not os.path.exists(os.path.join(runtime_dir, "draft_prompt.txt"))

    @pytest.mark.parametrize(
        ("target_total_chars", "target_length_profile", "planning_gate_min_chars"),
        [
            (30000, "novel_30k", 24000),
            (50000, "novel_50k", 40000),
            (100000, "novel_100k", 80000),
        ],
    )
    def test_canonical_build_draft_prompt_fails_when_planning_gate_is_blocked(
        self,
        tmp_path,
        target_total_chars,
        target_length_profile,
        planning_gate_min_chars,
    ):
        project_dir = tmp_path / f"blocked_{target_total_chars}"
        runtime_dir = project_dir / "runtime"
        runtime_dir.mkdir(parents=True)
        (runtime_dir / "style_contract_compact.md").write_text("# Style Contract Compact", encoding="utf-8")
        (runtime_dir / "scene_brief_compact.md").write_text(
            "# Scene Brief Compact\n"
            f"Target Total Chars: {target_total_chars}\n"
            f"Target Length Profile: {target_length_profile}\n"
            "Planning Gate Enabled: true\n"
            "Scene Type: standard\n"
            "Length Band: 1000 / 1250 / 1500\n"
            "- Planning Gate: blocked\n",
            encoding="utf-8",
        )
        (runtime_dir / "continuity_pack.md").write_text("# Continuity Pack", encoding="utf-8")
        (runtime_dir / "request_compact.md").write_text(
            "# Request Compact\n"
            f"- Target Total Chars: {target_total_chars}\n"
            f"- Target Length Profile: {target_length_profile}\n"
            "- Planning Gate Enabled: true\n"
            "- Planning Gate: blocked\n"
            "- Target Band: 1000 / 1250 / 1500\n",
            encoding="utf-8",
        )
        (runtime_dir / "planning_gate_brief.md").write_text(
            "# Planning Gate Brief\n"
            f"Target Total Chars: {target_total_chars}\n"
            f"Target Length Profile: {target_length_profile}\n"
            "Planning Gate Enabled: true\n"
            f"Planning Gate Min Chars: {planning_gate_min_chars}\n"
            "Planning Gate: blocked\n",
            encoding="utf-8",
        )

        result = subprocess.run(
            [
                sys.executable,
                os.path.join(SCRIPTS_DIR, "build_draft_prompt.py"),
                "--project",
                str(project_dir),
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 1
        assert "planning_gate_status is not ready" in result.stdout
        assert not os.path.exists(os.path.join(runtime_dir, "draft_prompt.txt"))

    def test_build_runtime_context_resume_mode_generates_resume_brief(self, runtime_project):
        result = subprocess.run(
            [
                sys.executable,
                os.path.join(SCRIPTS_DIR, "build_runtime_context.py"),
                "--project",
                runtime_project,
                "--chapter",
                "2",
                "--scene",
                "chapter_2_scene_3",
                "--mode",
                "resume",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stdout + result.stderr

        runtime_dir = scene_runtime_dir(runtime_project, "2-3", "resume")
        resume_path = os.path.join(runtime_dir, "resume_brief.md")
        request_path = os.path.join(runtime_dir, "request_compact.md")
        style_path = os.path.join(runtime_dir, "style_contract_compact.md")
        planning_gate_path = os.path.join(runtime_dir, "planning_gate_brief.md")
        scene_brief_path = os.path.join(runtime_dir, "scene_brief_compact.md")

        assert os.path.isfile(style_path)
        assert os.path.isfile(request_path)
        assert os.path.isfile(planning_gate_path)
        assert os.path.isfile(resume_path)
        assert not os.path.exists(scene_brief_path)

        resume_text = open(resume_path, "r", encoding="utf-8").read()
        assert "Current Position:" in resume_text
        assert "runtime/planning_gate_brief.md" in resume_text
        assert "agent/memory/session_notes.md" in resume_text
        assert "chapter_2_scene_2.txt" in resume_text
        assert "Write Next:" not in resume_text

    def test_build_runtime_context_blocks_draft_when_dependency_scene_is_missing(self, tmp_path):
        project_dir = create_runtime_project(tmp_path, outline_filename="05_chapter_outline.md")
        os.remove(os.path.join(project_dir, "chapter_2_scene_2.txt"))

        result = subprocess.run(
            [
                sys.executable,
                os.path.join(SCRIPTS_DIR, "build_runtime_context.py"),
                "--project",
                project_dir,
                "--chapter",
                "2",
                "--scene",
                "2-3",
                "--mode",
                "draft",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 1
        assert "dependent scene not found: 2-2" in result.stdout

    def test_build_runtime_context_resume_marks_requested_scene_as_stale_when_later_scene_exists(self, runtime_project):
        result = subprocess.run(
            [
                sys.executable,
                os.path.join(SCRIPTS_DIR, "build_runtime_context.py"),
                "--project",
                runtime_project,
                "--chapter",
                "2",
                "--scene",
                "2-1",
                "--mode",
                "resume",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, result.stdout + result.stderr
        resume_path = os.path.join(scene_runtime_dir(runtime_project, "2-1", "resume"), "resume_brief.md")
        resume_text = open(resume_path, "r", encoding="utf-8").read()
        assert "stale 候補" in resume_text

    def test_build_runtime_context_resume_redirects_to_missing_dependency_scene(self, tmp_path):
        project_dir = create_runtime_project(tmp_path, outline_filename="05_chapter_outline.md")
        with open(os.path.join(project_dir, "chapter_2_scene_3.txt"), "w", encoding="utf-8") as handle:
            handle.write("終盤シーン本文", encoding="utf-8")
        os.remove(os.path.join(project_dir, "chapter_2_scene_2.txt"))
        expected_output_path = os.path.join(project_dir, "chapter_2_scene_2.txt")

        result = subprocess.run(
            [
                sys.executable,
                os.path.join(SCRIPTS_DIR, "build_runtime_context.py"),
                "--project",
                project_dir,
                "--chapter",
                "2",
                "--scene",
                "2-3",
                "--mode",
                "resume",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, result.stdout + result.stderr
        resume_path = os.path.join(scene_runtime_dir(project_dir, "2-3", "resume"), "resume_brief.md")
        resume_text = open(resume_path, "r", encoding="utf-8").read()
        state_text = open(os.path.join(project_dir, "agent", "state_schema_novel.yaml"), "r", encoding="utf-8").read()
        assert "依存シーン 2-2 が欠落" in resume_text
        assert "2-2 を先に新規作成する" in resume_text
        assert f"Output Path: {expected_output_path}" in resume_text
        assert "Reason: 2-3 depends_on 2-2" in resume_text
        assert 'recommended_skill: "novel-writer"' in state_text
        assert f'active_scene: "2-2"' in state_text
        assert f'next_action: "2-2 を先に新規作成する -> {expected_output_path}"' in state_text

    def test_suggest_scene_output_path_prefers_dash_scene_filenames_inside_chapter_dir(self, tmp_path):
        project_dir = tmp_path / "dash_output_project"
        chapter_dir = project_dir / "chapter_1_introduction"
        chapter_dir.mkdir(parents=True)
        (chapter_dir / "scene_1-1.txt").write_text("本文", encoding="utf-8")
        (chapter_dir / "scene_1-3.txt").write_text("本文", encoding="utf-8")

        output_path = suggest_scene_output_path(str(project_dir), {"chapter": 1, "scene": 2, "canonical_id": "1-2", "filename": "chapter_1_scene_2.txt"})
        assert output_path == os.path.join(str(chapter_dir), "scene_1-2.txt")

    def test_migrate_project_state_populates_target_metadata_and_runtime_index(self, tmp_path):
        project_dir = create_runtime_project(tmp_path, outline_filename="05_chapter_outline.md")
        runtime_root = os.path.join(project_dir, "runtime")
        os.makedirs(runtime_root, exist_ok=True)
        with open(os.path.join(runtime_root, "scene_brief_compact.md"), "w", encoding="utf-8") as handle:
            handle.write(
                "# Scene Brief Compact\n"
                "Hard Constraints:\n"
                "- Scene ID: 2-3\n"
            )
        with open(os.path.join(runtime_root, "resume_brief.md"), "w", encoding="utf-8") as handle:
            handle.write("# Resume Brief\nCurrent Position: chapter 2 scene 2 の準備段階。\n")

        result = subprocess.run(
            [
                sys.executable,
                os.path.join(SCRIPTS_DIR, "migrate_project_state.py"),
                "--project",
                project_dir,
                "--target-source",
                "late_update",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, result.stdout + result.stderr
        state_text = open(os.path.join(project_dir, "agent", "state_schema_novel.yaml"), "r", encoding="utf-8").read()
        index_payload = json.load(open(os.path.join(runtime_root, "runtime_index.json"), "r", encoding="utf-8"))
        report = json.load(open(os.path.join(runtime_root, "migration_report.json"), "r", encoding="utf-8"))
        assert 'target_confirmation_source: "late_update"' in state_text
        assert "target_confirmed: true" in state_text
        assert index_payload["latest_by_mode"]["draft"]["scene_id"] == "2-3"
        assert index_payload["latest_by_mode"]["resume"]["scene_id"] == "2-2"
        assert report["latest_scene"] == "2-2"
        assert report["regenerated_resume_runtime"]
        assert os.path.isfile(report["regenerated_resume_runtime"])
        assert report["next_write_target"]["scene_id"] == "1-1"
        assert report["next_write_target"]["output_path"].endswith("chapter_1_scene_1.txt")

    def test_route_prompt_prefers_setting_creator_for_blocked_planning_gate(self):
        prompt = "long_form_100k の planning gate が blocked なので scene inventory を増やしたい。"
        assert route_prompt(prompt) == "setting-creator"

    def test_route_prompt_prefers_setting_creator_for_blocked_planning_gate_with_canonical_wording(self):
        prompt = "planning_gate_enabled=true の案件で planning gate が blocked なので scene inventory を増やしたい。"
        assert route_prompt(prompt) == "setting-creator"

    def test_check_scene_output_does_not_flag_plain_ai_word_as_meta(self, tmp_path):
        project_dir = tmp_path / "ai_safe_case"
        runtime_dir = project_dir / "runtime"
        runtime_dir.mkdir(parents=True)
        text_path = project_dir / "scene.txt"
        text_path.write_text(
            "AI研究会の看板が風で揺れた。\n\n主人公はそれを見上げて、少しだけ笑った。",
            encoding="utf-8",
        )

        result = subprocess.run(
            [
                sys.executable,
                os.path.join(SCRIPTS_DIR, "check_scene_output.py"),
                "--project",
                str(project_dir),
                "--text",
                str(text_path),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        report = json.load(open(runtime_dir / "check_report.json", "r", encoding="utf-8"))
        assert "meta_commentary_detected" not in report["format_violations"]

    def test_check_scene_output_writes_detailed_report_fields(self, tmp_path):
        project_dir = tmp_path / "detailed_report"
        runtime_dir = project_dir / "runtime"
        runtime_dir.mkdir(parents=True)
        (runtime_dir / "style_contract_compact.md").write_text(
            "# Style Contract Compact\n"
            "- 禁止表現:\n"
            "  - 作者視点のメタ説明\n"
            "  - 見出しや箇条書きの混入\n",
            encoding="utf-8",
        )
        text_path = project_dir / "scene.txt"
        text_path.write_text(
            "以下に本文を出力します。\n# 見出し\n- 箇条書き\n本文が続く。",
            encoding="utf-8",
        )

        result = subprocess.run(
            [
                sys.executable,
                os.path.join(SCRIPTS_DIR, "check_scene_output.py"),
                "--project",
                str(project_dir),
                "--text",
                str(text_path),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stdout + result.stderr

        report = json.load(open(runtime_dir / "check_report.json", "r", encoding="utf-8"))
        assert "meta_commentary_detected" in report["format_violations"]
        assert "heading_detected" in report["format_violations"]
        assert "bullet_list_detected" in report["format_violations"]
        assert report["format_violations_detail"]
        assert report["forbidden_hits_detail"]
        assert "meta_rule" in report["forbidden_hits"]
        assert "heading_rule" in report["forbidden_hits"]
        assert report["char_delta_to_min"] == report["actual_chars"] - report["min_chars"]
        assert report["char_delta_to_target"] == report["actual_chars"] - report["target_chars"]

    def test_check_scene_output_syncs_scene_ledger_status(self, tmp_path):
        project_dir = create_runtime_project(tmp_path, outline_filename="05_chapter_outline.md")
        subprocess.run(
            [
                sys.executable,
                os.path.join(SCRIPTS_DIR, "build_runtime_context.py"),
                "--project",
                project_dir,
                "--chapter",
                "2",
                "--scene",
                "2-3",
                "--mode",
                "draft",
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        text_path = os.path.join(project_dir, "chapter_2_scene_3.txt")
        with open(text_path, "w", encoding="utf-8") as handle:
            handle.write("あ" * 1300)

        subprocess.run(
            [
                sys.executable,
                os.path.join(SCRIPTS_DIR, "check_scene_output.py"),
                "--project",
                project_dir,
                "--text",
                text_path,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        outline_text = open(os.path.join(project_dir, "05_chapter_outline.md"), "r", encoding="utf-8").read()
        assert "| 2-3 | standard | 障害を越えるために決断する | 逡巡 -> 決断 | 次章への推進力 | 1000 | 1250 | 1500 | 2-2 | completed |" in outline_text

    def test_check_scene_output_detects_unclosed_dialogue_and_duplicate_paragraphs(self, tmp_path):
        project_dir = tmp_path / "structural_warnings"
        runtime_dir = project_dir / "runtime"
        runtime_dir.mkdir(parents=True)
        text_path = project_dir / "scene.txt"
        repeated = "主人公は石畳の上で足を止め、胸のざわめきが消えないことを自覚した。"
        text_path.write_text(
            f"「まだ終わってない\n\n{repeated}\n\n{repeated}",
            encoding="utf-8",
        )

        result = subprocess.run(
            [
                sys.executable,
                os.path.join(SCRIPTS_DIR, "check_scene_output.py"),
                "--project",
                str(project_dir),
                "--text",
                str(text_path),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stdout + result.stderr

        report = json.load(open(runtime_dir / "check_report.json", "r", encoding="utf-8"))
        assert "unclosed_dialogue_detected" in report["format_violations"]
        assert "duplicate_paragraph_detected" in report["format_violations"]
        detail_types = [item["type"] for item in report["format_violations_detail"]]
        assert "unclosed_dialogue_detected" in detail_types
        assert "duplicate_paragraph_detected" in detail_types

    def test_build_expand_prompt_fails_on_invalid_json(self, tmp_path):
        project_dir = tmp_path / "broken_report"
        runtime_dir = project_dir / "runtime"
        runtime_dir.mkdir(parents=True)
        (runtime_dir / "style_contract_compact.md").write_text("style", encoding="utf-8")
        (runtime_dir / "check_report.json").write_text("{broken", encoding="utf-8")
        draft_path = project_dir / "draft.txt"
        draft_path.write_text("本文", encoding="utf-8")

        result = subprocess.run(
            [
                sys.executable,
                os.path.join(SCRIPTS_DIR, "build_expand_prompt.py"),
                "--project",
                str(project_dir),
                "--draft_text",
                str(draft_path),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1
        assert "ERROR: check_report.json is invalid" in result.stdout

    def test_apply_expand_edits_fails_on_anchor_mismatch(self, tmp_path):
        project_dir = tmp_path / "bad_expand_apply"
        project_dir.mkdir()
        text_path = project_dir / "scene.txt"
        edits_path = project_dir / "edits.txt"
        text_path.write_text("最初の段落。\n\n二番目の段落。", encoding="utf-8")
        edits_path.write_text(
            "[EDIT 1]\n"
            "TARGET: after P1\n"
            "ANCHOR: 一致しないアンカー\n"
            "TEXT:\n"
            "追加文。\n",
            encoding="utf-8",
        )

        result = subprocess.run(
            [
                sys.executable,
                os.path.join(SCRIPTS_DIR, "apply_expand_edits.py"),
                "--project",
                str(project_dir),
                "--text",
                str(text_path),
                "--edits",
                str(edits_path),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1
        assert "ERROR: ANCHOR does not match paragraph P1" in result.stdout


# ---------------------------------------------------------------------------
# eval_skill_trigger_qa.py のテスト
# ---------------------------------------------------------------------------

class TestEvalSkillTriggerQA:
    """eval_skill_trigger_qa.py の動作検証"""

    def test_evaluates_dataset_and_writes_reports(self, tmp_path):
        dataset = tmp_path / "trigger.md"
        json_out = tmp_path / "report.json"
        md_out = tmp_path / "report.md"
        dataset.write_text(
            "# Trigger QA\n\n"
            "## idea-generator\n"
            "### should-trigger\n"
            "- 新しい小説のネタ出しをしたい。\n"
            "### should-not-trigger\n"
            "- どこから再開すべき？\n\n"
            "## resume-orchestrator\n"
            "### should-trigger\n"
            "- どこから再開すべき？\n"
            "### should-not-trigger\n"
            "- アイディアを壁打ちしたい。\n",
            encoding="utf-8",
        )

        result = subprocess.run(
            [
                sys.executable,
                os.path.join(SCRIPTS_DIR, "eval_skill_trigger_qa.py"),
                "--input",
                str(dataset),
                "--json_out",
                str(json_out),
                "--md_out",
                str(md_out),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert json_out.exists()
        assert md_out.exists()
        report = json.load(open(json_out, "r", encoding="utf-8"))
        assert report["summary"]["skills_covered"] == 2
        assert report["summary"]["total_should_trigger"] == 2
        assert report["summary"]["total_should_not_trigger"] == 2

    def test_fails_when_input_file_is_missing(self, tmp_path):
        json_out = tmp_path / "report.json"
        result = subprocess.run(
            [
                sys.executable,
                os.path.join(SCRIPTS_DIR, "eval_skill_trigger_qa.py"),
                "--input",
                str(tmp_path / "missing.md"),
                "--json_out",
                str(json_out),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1
        assert "ERROR: input file not found" in result.stdout


class TestEvalSkillRegressionMinimum:
    """eval_skill_regression_minimum.py の動作検証"""

    def test_evaluates_minimum_regression_and_writes_reports(self, tmp_path):
        dataset = tmp_path / "regression.md"
        json_out = tmp_path / "regression.json"
        md_out = tmp_path / "regression.md.out"
        dataset.write_text(
            "# Regression\n\n"
            "## 1. idea-generator\n"
            "- Input: 新しい小説のネタ出しをしたい。\n"
            "- Expected: アイディア提案を返す。\n\n"
            "## 2. resume-orchestrator\n"
            "- Input: どこから再開すべき？\n"
            "- Expected: 次アクションを1つ返す。\n",
            encoding="utf-8",
        )

        result = subprocess.run(
            [
                sys.executable,
                os.path.join(SCRIPTS_DIR, "eval_skill_regression_minimum.py"),
                "--input",
                str(dataset),
                "--json_out",
                str(json_out),
                "--md_out",
                str(md_out),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        report = json.load(open(json_out, "r", encoding="utf-8"))
        assert report["summary"]["total_cases"] == 2
        assert report["summary"]["passed_cases"] == 2
        assert report["summary"]["skills_covered"] == 2
        assert len(report["summary"]["missing_required_skills"]) == 7

    def test_fails_when_regression_input_is_missing(self, tmp_path):
        json_out = tmp_path / "regression.json"
        result = subprocess.run(
            [
                sys.executable,
                os.path.join(SCRIPTS_DIR, "eval_skill_regression_minimum.py"),
                "--input",
                str(tmp_path / "missing.md"),
                "--json_out",
                str(json_out),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1
        assert "ERROR: input file not found" in result.stdout


class TestRunSkillEvalSuite:
    """run_skill_eval_suite.py の動作検証"""

    def test_runs_suite_and_writes_summary(self, tmp_path):
        trigger_input = tmp_path / "trigger.md"
        min_input = tmp_path / "reg_min.md"
        boundary_input = tmp_path / "reg_boundary.md"

        trigger_input.write_text(
            "## idea-generator\n"
            "### should-trigger\n"
            "- 新しい小説のネタ出しをしたい。\n"
            "### should-not-trigger\n"
            "- どこから再開すべき？\n\n"
            "## resume-orchestrator\n"
            "### should-trigger\n"
            "- どこから再開すべき？\n"
            "### should-not-trigger\n"
            "- アイディアを壁打ちしたい。\n",
            encoding="utf-8",
        )
        min_input.write_text(
            "## 1. idea-generator\n"
            "- Input: 新しい小説のネタ出しをしたい。\n"
            "- Expected: 発想を広げる。\n\n"
            "## 2. resume-orchestrator\n"
            "- Input: どこから再開すべき？\n"
            "- Expected: 再開判断を返す。\n",
            encoding="utf-8",
        )
        boundary_input.write_text(min_input.read_text(encoding="utf-8"), encoding="utf-8")

        trigger_json = tmp_path / "trigger.json"
        trigger_md = tmp_path / "trigger.md.out"
        reg_min_json = tmp_path / "reg_min.json"
        reg_min_md = tmp_path / "reg_min.md.out"
        reg_boundary_json = tmp_path / "reg_boundary.json"
        reg_boundary_md = tmp_path / "reg_boundary.md.out"
        suite_json = tmp_path / "suite.json"
        suite_md = tmp_path / "suite.md"

        result = subprocess.run(
            [
                sys.executable,
                os.path.join(SCRIPTS_DIR, "run_skill_eval_suite.py"),
                "--trigger_input",
                str(trigger_input),
                "--regression_min_input",
                str(min_input),
                "--regression_boundary_input",
                str(boundary_input),
                "--trigger_json_out",
                str(trigger_json),
                "--trigger_md_out",
                str(trigger_md),
                "--regression_min_json_out",
                str(reg_min_json),
                "--regression_min_md_out",
                str(reg_min_md),
                "--regression_boundary_json_out",
                str(reg_boundary_json),
                "--regression_boundary_md_out",
                str(reg_boundary_md),
                "--suite_json_out",
                str(suite_json),
                "--suite_md_out",
                str(suite_md),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        summary = json.load(open(suite_json, "r", encoding="utf-8"))
        assert "overall_pass" in summary
        assert "trigger" in summary
        assert "regression_minimum" in summary
        assert "regression_boundary" in summary

    def test_fails_when_suite_inputs_are_missing(self, tmp_path):
        suite_json = tmp_path / "suite.json"
        result = subprocess.run(
            [
                sys.executable,
                os.path.join(SCRIPTS_DIR, "run_skill_eval_suite.py"),
                "--trigger_input",
                str(tmp_path / "missing_trigger.md"),
                "--suite_json_out",
                str(suite_json),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1
        assert "ERROR: trigger QA run failed" in result.stdout
