"""The resume the site links to: the newest resume_dd_mm_yyyy.pdf in the knowledge resume folder."""

import re
from datetime import date
from pathlib import Path

_PDF_NAME = re.compile(r"resume_(\d{2})_(\d{2})_(\d{4})\.pdf")


def latest_resume_pdf(folder: Path) -> Path | None:
    """The PDF with the newest date in its name, or None.

    Only files named resume_dd_mm_yyyy.pdf with a real date count; other formats (the resume folder
    also holds .docx, .md and .txt versions) and misnamed files are ignored.
    """
    newest: tuple[date, Path] | None = None
    for path in folder.iterdir() if folder.is_dir() else []:
        match = _PDF_NAME.fullmatch(path.name)
        if match is None or not path.is_file():
            continue
        day, month, year = (int(part) for part in match.group(1, 2, 3))
        try:
            when = date(year, month, day)
        except ValueError:  # for example 31_02_2026
            continue
        if newest is None or when > newest[0]:
            newest = (when, path)
    return newest[1] if newest else None
