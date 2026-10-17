from __future__ import annotations

from pathlib import Path
import zipfile


class EpubValidationError(ValueError):
    pass


def validate_epub(path: str | Path) -> None:
    epub_path = Path(path)
    if not epub_path.is_file():
        raise EpubValidationError(f"EPUB not found: {epub_path}")

    with zipfile.ZipFile(epub_path) as z:
        names = z.namelist()
        required = {
            "mimetype",
            "META-INF/container.xml",
            "EPUB/content.opf",
            "EPUB/nav.xhtml",
            "EPUB/toc.ncx",
        }
        missing = required - set(names)
        if missing:
            raise EpubValidationError(
                "Missing required EPUB files: " + ", ".join(sorted(missing))
            )

        if not names or names[0] != "mimetype":
            raise EpubValidationError("EPUB mimetype must be the first ZIP entry")

        info = z.getinfo("mimetype")
        if info.compress_type != zipfile.ZIP_STORED:
            raise EpubValidationError("EPUB mimetype must be uncompressed")

        if z.read("mimetype") != b"application/epub+zip":
            raise EpubValidationError("Invalid EPUB mimetype")

        container = z.read("META-INF/container.xml")
        if b"EPUB/content.opf" not in container:
            raise EpubValidationError("container.xml does not reference EPUB/content.opf")

        opf = z.read("EPUB/content.opf")
        if b"<package" not in opf or b"<manifest" not in opf or b"<spine" not in opf:
            raise EpubValidationError("content.opf is missing package/manifest/spine")

        nav = z.read("EPUB/nav.xhtml")
        if b"<nav" not in nav:
            raise EpubValidationError("nav.xhtml does not contain a nav element")

        for name in names:
            if name.endswith(".xhtml") and name.startswith("EPUB/"):
                z.read(name)


def validate_epub_file(path: str | Path) -> Path:
    validate_epub(path)
    return Path(path)
