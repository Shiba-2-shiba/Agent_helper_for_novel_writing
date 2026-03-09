# Pytest Failure Triage

Status: draft
Date: 2026-03-09
Command: `pytest -q tests/test_scripts.py`
Result: `6 failed, 55 passed`

## 1. Purpose

本メモは、`tests/test_scripts.py` 実行時に発生した 6 件の失敗を、現仕様を前提に以下の 3 区分へ切り分けるための記録である。

1. `テスト修正対象`
2. `実装不整合`
3. `テストバグ`

今回の前提は「現仕様に合わせてテストを直す」であり、旧仕様へコードを戻す判断は行わない。

## 2. Classification Rules

### 2.1 テスト修正対象

以下に該当するもの。

1. 現仕様に対してテスト期待値が古い
2. 既に同ファイル内の別テストが新仕様を前提にしている
3. 実装挙動が現行仕様書や現行コードの意図と整合している

### 2.2 実装不整合

以下に該当するもの。

1. テスト期待値が現仕様と整合している
2. 実装だけが旧挙動または矛盾挙動になっている
3. テスト修正ではなく実装修正が主手段になる

### 2.3 テストバグ

以下に該当するもの。

1. テストコード自体が Python として不正
2. テストの fixture / setup が意図した条件を満たしていない
3. 失敗原因がアプリ本体ではなく、テスト記述の誤りにある

## 3. Triage Table

| No. | Test | Failure Summary | Classification | Reasoning | Recommended Action |
|---|---|---|---|---|---|
| 1 | `TestInitProject.test_creates_correct_folder_structure` | `init_project.py` 呼び出し時に `--target-total-chars` 未指定で exit 2 | テスト修正対象 | 現行実装は `--target-total-chars` 必須であり、同ファイル内にもその仕様を前提にしたテストが存在する | 呼び出しを `--target-total-chars 50000` など付きに更新する |
| 2 | `TestInitProject.test_exits_with_error_on_existing_directory` | 既存ディレクトリ再実行テストが引数不足で exit 2 になっている | テスト修正対象 | このテストが検証したいのは「既存ディレクトリ時の exit 1」であり、現状はその前段の argparse で失敗している | 必須引数を渡したうえで既存ディレクトリ分岐を検証する |
| 3 | `TestInitProject.test_from_ideas_transfers_logline` | `--from_ideas` テストが引数不足で失敗 | テスト修正対象 | `from_ideas` の検証以前に、現仕様の required arg を満たしていない | 必須引数を追加して、`01_concept_sheet.md` への転記を検証する |
| 4 | `TestRuntimeRefactorScripts.test_build_runtime_context_resume_mode_generates_resume_brief` | `resume_brief.md` に `Write Next:` が含まれる | テスト修正対象 | 現行実装は「requested scene is not started yet」の場合に `Write Next` を出す設計で、挙動は一貫している | 期待値を `Write Next` ありへ更新し、`Scene ID: 2-3` と `Reason` を確認する |
| 5 | `TestRuntimeRefactorScripts.test_build_runtime_context_resume_marks_requested_scene_as_stale_when_later_scene_exists` | `stale 候補` ではなく依存欠落ブロック扱いになっている | テストバグ | `runtime_project` fixture では `2-1` の依存先 `1-1` が存在せず、stale 条件より先に blocked dependency 条件へ入る。テストの前提セットアップが目的に合っていない | stale を検証したいなら `1-1` を作成するか、依存欠落しない scene 構成に fixture を調整する |
| 6 | `TestRuntimeRefactorScripts.test_build_runtime_context_resume_redirects_to_missing_dependency_scene` | `handle.write(..., encoding=\"utf-8\")` で `TypeError` | テストバグ | `TextIOWrapper.write()` に `encoding` 引数はない。アプリ実装に到達する前にテストが壊れている | `handle.write(\"終盤シーン本文\")` に修正する |

## 4. Detailed Notes

### 4.1 `init_project.py` 系 3 件

根拠:

1. 現行 `init_project.py` は `--target-total-chars` を `required=True` で要求している
2. 同一テストファイルには、canonical target profile を検証する新仕様テストが既に存在する
3. 同一テストファイルには、「target 未指定では初期化しない」ことを確認するテストも既に存在する

したがって、失敗 1 から 3 は実装不整合ではなく、旧呼び出しの残骸とみなしてよい。

### 4.2 `resume_brief` の `Write Next` 期待値

根拠:

1. `build_resume_brief()` は requested scene 未着手時に `Write Next` を明示する実装である
2. `2-3` は fixture 上まだ本文未作成なので、「次に何を書くか」を返すのは現仕様として自然
3. 期待値 `Write Next がないこと` は、現行 resume 設計と整合しない

したがって、これはテスト期待値の更新で扱う。

### 4.3 stale 判定テスト

根拠:

1. 対象 fixture では `2-1` が `depends_on: 1-1`
2. しかし fixture には `1-1` 本文が存在しない
3. 現行実装は `blocked_dependency` を `stale` より優先して判定する

そのため、`stale 候補` を期待する前提条件が作れていない。これは期待値の古さというより、テスト条件の誤構築である。

### 4.4 `write()` の `encoding` 引数

これは純粋にテストコードの記述ミスであり、分類上もっとも明確な `テストバグ` である。

## 5. Summary by Category

### 5.1 テスト修正対象

1. `TestInitProject.test_creates_correct_folder_structure`
2. `TestInitProject.test_exits_with_error_on_existing_directory`
3. `TestInitProject.test_from_ideas_transfers_logline`
4. `TestRuntimeRefactorScripts.test_build_runtime_context_resume_mode_generates_resume_brief`

### 5.2 実装不整合

今回の 6 件については、現時点では該当なし。

注記:

1. これは「実装に改善余地がない」という意味ではない
2. 少なくとも今回の失敗原因は、現仕様との比較ではテスト側にあると判断した

### 5.3 テストバグ

1. `TestRuntimeRefactorScripts.test_build_runtime_context_resume_marks_requested_scene_as_stale_when_later_scene_exists`
2. `TestRuntimeRefactorScripts.test_build_runtime_context_resume_redirects_to_missing_dependency_scene`

## 6. Recommended Fix Order

1. `write()` の誤記を修正する
2. `init_project.py` 系 3 件に必須引数を追加する
3. `resume_brief` の `Write Next` 期待値を現仕様へ合わせる
4. stale 判定テストの fixture 条件を修正する
5. `pytest -q tests/test_scripts.py` を再実行する

## 7. Proposed Follow-up

次の作業単位では、上記 6 件のうち `テスト修正対象` と `テストバグ` をまとめて修正し、再度 `pytest` を走らせる。
