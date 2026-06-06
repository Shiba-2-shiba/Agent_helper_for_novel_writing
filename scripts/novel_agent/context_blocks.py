from dataclasses import asdict, dataclass
import os
import re


@dataclass
class ContextBlock:
    id: str
    role: str
    source_path: str
    start_line: int
    end_line: int
    title: str
    content: str
    summary: str
    tokens_estimate: int

    def to_index_entry(self):
        payload = asdict(self)
        payload.pop("content", None)
        return payload


def count_estimated_tokens(text):
    if not text:
        return 0
    return max(1, len(text) // 2)


def build_excerpt(text, max_chars=220):
    compact = re.sub(r"\s+", " ", text.strip())
    if len(compact) <= max_chars:
        return compact
    return compact[:max_chars].rstrip() + "..."


def relative_source(path, project_dir):
    try:
        return os.path.relpath(path, project_dir)
    except ValueError:
        return os.path.abspath(path)


def make_block(*, block_id, role, source_path, project_dir, start_line, end_line, title, content, summary=""):
    return ContextBlock(
        id=block_id,
        role=role,
        source_path=relative_source(source_path, project_dir),
        start_line=start_line,
        end_line=end_line,
        title=title,
        content=content.rstrip(),
        summary=summary or build_excerpt(content),
        tokens_estimate=count_estimated_tokens(content),
    )
