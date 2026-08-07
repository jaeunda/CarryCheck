"""Run CarryCheck without making any external API calls."""

from .server.app import main as server_main


def main() -> None:
    server_main(default_runtime="local", runtime_locked=True)


if __name__ == "__main__":
    main()
