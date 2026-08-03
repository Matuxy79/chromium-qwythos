"""Generate Windows and browser icon bundles from the Qwythos master mark."""

from pathlib import Path

from PIL import Image


REPO_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = REPO_ROOT / "static" / "static"
BACKEND_STATIC_DIR = REPO_ROOT / "backend" / "qwythos" / "static"
SOURCE = STATIC_DIR / "favicon.png"
ICON_SIZES = (16, 20, 24, 32, 40, 48, 64, 128, 256)


def main() -> None:
    with Image.open(SOURCE) as source:
        mark = source.convert("RGBA")
        outputs = (
            REPO_ROOT / "static" / "favicon.ico",
            STATIC_DIR / "favicon.ico",
            STATIC_DIR / "qwythos.ico",
            BACKEND_STATIC_DIR / "favicon.ico",
        )
        for output in outputs:
            mark.save(output, format="ICO", sizes=[(size, size) for size in ICON_SIZES])

    generated = ", ".join(path.relative_to(REPO_ROOT).as_posix() for path in outputs)
    print(f"Generated {generated} from {SOURCE.relative_to(REPO_ROOT).as_posix()}")


if __name__ == "__main__":
    main()
