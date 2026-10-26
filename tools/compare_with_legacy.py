"""Compare the new renderer with the legacy `tldr.py` on every page of a checkout.

Colors are stripped, so only the visible text is compared. Differences are
expected where the legacy client has bugs; review them, don't blindly "fix".

    pip install termcolor shtab
    python tools/compare_with_legacy.py path/to/legacy/tldr.py path/to/tldr [short|long|both]
"""

from __future__ import annotations

import importlib.util
import io
import re
import sys
from contextlib import redirect_stdout
from pathlib import Path

from tldr.render import PLAIN, render_page

ANSI = re.compile(r"\x1b\[[0-9;]*m")


def load_legacy(path: Path):
    spec = importlib.util.spec_from_file_location("legacy_tldr", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def legacy_render(legacy, markdown: bytes, style: str) -> str:
    buffer = io.BytesIO()
    text = io.TextIOWrapper(buffer, encoding="utf-8", write_through=True)
    with redirect_stdout(text):
        legacy.output(markdown.splitlines(), style)
    return ANSI.sub("", buffer.getvalue().decode("utf-8"))


def main() -> int:
    legacy = load_legacy(Path(sys.argv[1]))
    repo = Path(sys.argv[2])
    style = sys.argv[3] if len(sys.argv) > 3 else "long"

    pages = sorted(repo.glob("pages*/*/*.md"))
    differing = 0
    for page in pages:
        markdown = page.read_bytes()
        old = legacy_render(legacy, markdown, style)
        new = render_page(markdown.decode("utf-8"), style, PLAIN)
        if old != new:
            differing += 1
            print(f"== {page.relative_to(repo)}")
            for old_line, new_line in zip(old.splitlines(), new.splitlines()):
                if old_line != new_line:
                    print(f"  old: {old_line}\n  new: {new_line}")
    print(f"{differing} of {len(pages)} pages differ", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
