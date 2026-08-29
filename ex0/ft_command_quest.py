"""Command Quest: discover the command-line parameters list (sys.argv)."""

import sys


def main() -> None:
    """Display every command-line parameter received by the program."""
    print("=== Command Quest ===")
    print(f"Program name: {sys.argv[0]}")

    arguments: list[str] = sys.argv[1:]
    received: int = len(arguments)

    if received == 0:
        print("No arguments provided!")
    else:
        print(f"Arguments received: {received}")
        position: int = 1
        for argument in arguments:
            print(f"Argument {position}: {argument}")
            position += 1

    print(f"Total arguments: {len(sys.argv)}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"Command Quest failed: {error}")
