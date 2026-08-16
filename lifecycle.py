import signal


def install_shutdown_handlers(shutdown):
    """Install standard Unix termination handlers for a graceful service stop."""

    def handle_shutdown(signum, frame):
        shutdown()
        raise SystemExit(0)

    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)
    return handle_shutdown
