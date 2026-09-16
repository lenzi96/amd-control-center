"""Application bootstrap and runtime entry point with CLI arguments and single-instance IPC."""

import os
import sys
import json
from PyQt6.QtCore import Qt
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from PyQt6.QtWidgets import QApplication
from .main_window import MainWindow

SERVER_NAME = f"amd_control_center_ipc_{os.getuid()}"


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("amd-control-center")
    app.setApplicationDisplayName("AMD Software: Adrenalin Edition")
    app.setOrganizationName("AMD")
    app.setDesktopFileName("amd-control-center")
    app.setQuitOnLastWindowClosed(False)

    from .icon import get_app_icon
    app_icon = get_app_icon()
    app.setWindowIcon(app_icon)

    # 1. Check if another instance is already running
    socket = QLocalSocket()
    socket.connectToServer(SERVER_NAME)
    if socket.waitForConnected(500):
        # Connected to existing instance! Forward args and exit this instance
        args = sys.argv[1:]
        payload = json.dumps({"args": args}).encode("utf-8")
        socket.write(payload)
        socket.waitForBytesWritten(1000)
        socket.disconnectFromServer()
        sys.exit(0)

    # 2. If not running, clean up any stale socket and start local server
    QLocalServer.removeServer(SERVER_NAME)
    server = QLocalServer()
    if not server.listen(SERVER_NAME):
        QLocalServer.removeServer(SERVER_NAME)
        server.listen(SERVER_NAME)

    window = MainWindow()

    def on_new_connection():
        client = server.nextPendingConnection()
        if not client:
            return
        if client.waitForReadyRead(1000):
            data = bytes(client.readAll()).decode("utf-8")
            try:
                msg = json.loads(data)
                args = msg.get("args", [])
                window.handle_remote_args(args)
            except Exception:
                window.bring_to_front()
        else:
            window.bring_to_front()
        client.disconnectFromServer()

    server.newConnection.connect(on_new_connection)

    def cleanup_server():
        server.close()
        QLocalServer.removeServer(SERVER_NAME)

    app.aboutToQuit.connect(cleanup_server)

    if "--overlay" in sys.argv:
        window.overlay.show()
    elif "--tuning" in sys.argv or "--performance" in sys.argv:
        window._navigate_to(2)
        window.show()
    elif "--gaming" in sys.argv:
        window._navigate_to(1)
        window.show()
    elif "--minimized" in sys.argv or "--tray" in sys.argv:
        pass  # Running in background tray
    else:
        window.show()

    ret = app.exec()
    cleanup_server()
    sys.exit(ret)


if __name__ == "__main__":
    main()

