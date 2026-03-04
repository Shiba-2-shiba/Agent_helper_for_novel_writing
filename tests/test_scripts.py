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
        templates_dir = os.path.join(PROJECT_ROOT, "templates")
        for name in os.listdir(templates_dir):
            if name.endswith(".md"):
                shutil.copy2(os.path.join(templates_dir, name), str(proj / name))
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


class TestRuntimeRefactorScripts:
    """runtime 系スクリプトの動作検証"""

    @pytest.fixture()
    def runtime_project(self, tmp_path):
        proj = tmp_path / "runtime_proj"
        proj.mkdir()

        outline = """# Outline

## 第2章：承・前半（目標：約20,000字）
> 仲間との出会いと小目標の達成。

シーン一覧:
- [ ] シーン1（約1000〜1500字）: 主人公が新しい依頼を受ける
- [ ] シーン2（約1000〜1500字）: 仲間と合流し最初の障害にぶつかる
- [ ] シーン3（約1000〜1500字）: 障害を越えるために決断する
"""
        (proj / "05_chapter_outline_100k.md").write_text(outline, encoding="utf-8")

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
        state_schema = proj / "agent" / "state_schema_novel.yaml"
        state_schema.write_text("narration_tense: 過去形\n", encoding="utf-8")

        (proj / "chapter_2_scene_1.txt").write_text(
            "主人公は市場で奇妙な依頼書を受け取り、胸騒ぎを覚えた。",
            encoding="utf-8",
        )
        (proj / "chapter_2_scene_2.txt").write_text(
            "仲間と合流したが、橋は崩れ、先へ進むには危険な川を渡るしかなかった。",
            encoding="utf-8",
        )
        return str(proj)

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

        runtime_dir = os.path.join(runtime_project, "runtime")
        for name in (
            "style_contract_compact.md",
            "scene_brief_compact.md",
            "continuity_pack.md",
            "request_compact.md",
        ):
            assert os.path.isfile(os.path.join(runtime_dir, name)), f"Missing runtime file: {name}"

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

        runtime_dir = os.path.join(runtime_project, "runtime")
        resume_path = os.path.join(runtime_dir, "resume_brief.md")
        request_path = os.path.join(runtime_dir, "request_compact.md")
        style_path = os.path.join(runtime_dir, "style_contract_compact.md")
        scene_brief_path = os.path.join(runtime_dir, "scene_brief_compact.md")

        assert os.path.isfile(style_path)
        assert os.path.isfile(request_path)
        assert os.path.isfile(resume_path)
        assert not os.path.exists(scene_brief_path)

        resume_text = open(resume_path, "r", encoding="utf-8").read()
        assert "Current Position:" in resume_text
        assert "agent/memory/session_notes.md" in resume_text
        assert "chapter_2_scene_2.txt" in resume_text

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
