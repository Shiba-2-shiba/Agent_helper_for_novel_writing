---
name: idea-generator
description: Brainstorm new novel concepts, widen rough ideas, and shape them into a usable logline. Use when the user wants to create a new story from scratch or needs broad ideation before formal setting work.
version: 0.2
---

# Purpose

企画の立ち上げ段階で、発想を広げ、物語の核を言語化する。

# Read First

- `agent/HUB.md`
- 必要なら `agent/request_template.md`

# Required Inputs

- ユーザーの初期アイディア、キーワード、ジャンル希望

# Procedure

## 1. 発想を広げる

- 一度に大量質問を投げず、1〜2論点ずつ対話する
- ユーザーの断片情報に対して、必ず複数の具体案を返す
- ロジックの厳密性より、面白さ、差別化、伸びしろを優先する

## 2. 物語の核を定める

- 主人公
- 目的
- 弱点
- 世界観のフック
- 事件の入口

上記が見えたら、1〜2文のログラインを作り、ユーザー合意を取る。

## 3. 次フェーズへ渡す

- ログライン合意後、プロジェクト名を決める
- 案件の箱を作る段階へ進める
- その後は `SKILL_project_bootstrap.md` へ渡す

# Handoff

- ログライン確定後: `SKILL_project_bootstrap.md`

# Outputs

- アイディア候補
- ログライン案
- 次に決めるべき論点

# Do Not

- 6項目をまとめて質問しない
- ユーザーの突飛な案を即否定しない
- この段階で設定テンプレートの詳細記入まで進めない
