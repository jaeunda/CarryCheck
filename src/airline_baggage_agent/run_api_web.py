"""Run CarryCheck with strict embedding and Chat API usage."""

from .server.app import main as server_main


def main() -> None:
    server_main(default_runtime="api", runtime_locked=True)


if __name__ == "__main__":
    main()
