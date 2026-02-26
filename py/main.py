import sys
from pathlib import Path

from image_renderer import render_image


def _parse_aspect(argv: list[str]) -> str | None:
    if "--aspect" not in argv:
        return None
    i = argv.index("--aspect")
    if i + 1 >= len(argv):
        return None
    return argv[i + 1]


def main():
    if len(sys.argv) < 3:
        print(
            "Usage: python main.py <input_image> <output_image> "
            "[--aspect 16:9|9:16|4:3|3:4|5:4|4:5|1:1]"
        )
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    aspect = _parse_aspect(sys.argv[3:])

    ok, logs = render_image(input_path, output_path, aspect)
    print(logs)
    print(f"[OK] Output: {output_path}")


if __name__ == "__main__":
    main()
