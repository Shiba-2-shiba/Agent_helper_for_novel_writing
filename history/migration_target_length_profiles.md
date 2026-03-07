# Target Length Profile Migration Note

## New Canonical Sources

- 新規 project は `05_chapter_outline.md` を全体計画の正本として生成します。
- 新規 project は `targets.target_total_chars` と `targets.target_length_profile` を canonical field として書きます。
- planning gate の判定は `planning_gate_enabled` と `planning_gate_status` を主条件に扱います。

## Legacy Fallbacks

- 既存 project の `05_chapter_outline_100k.md` は runtime / prompt scripts の read-path fallback として引き続き読めます。
- 既存 project の `targets.length_mode: long_form_100k` は read-path fallback として引き続き解決されます。
- `Length Mode` と `long_form_100k` は新規 write-path や agent routing の主語ではありません。

## What You Need To Change

- 既存 project を急いで rename する必要はありません。
- ただし、今後の手動更新や agent docs 参照では `05_chapter_outline.md`、`Target Total Chars`、`Target Length Profile` を優先してください。
- planning gate で詰まった場合は、`long_form_100k` かどうかではなく `planning_gate_enabled=true` かつ `planning_gate_status != ready` を見ます。
