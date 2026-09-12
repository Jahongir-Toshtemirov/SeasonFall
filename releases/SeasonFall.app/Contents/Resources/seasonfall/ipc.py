"""Single-instance IPC: a tiny local-socket server living in the overlay process.

Lets the CLI and the settings GUI talk to a running overlay:
reload / pause / resume / quit / status.
"""
from __future__ import annotations

import getpass
import json
import os

from PySide6.QtCore import QObject
from PySide6.QtNetwork import QLocalServer, QLocalSocket


def socket_name() -> str:
    """Per-user socket name; SEASONFALL_IPC_NAME overrides it so that test
    instances never clash with (or disconnect) a real running overlay."""
    user = getpass.getuser() or "user"
    return os.environ.get("SEASONFALL_IPC_NAME") or f"seasonfall-{user}"



def send_command(cmd: str, wait_reply: bool = False):
    """Send a command to a running overlay. Returns reply dict / True / None."""
    sock = QLocalSocket()
    sock.connectToServer(socket_name())
    if not sock.waitForConnected(500):
        sock.abort()
        return None
    payload = (json.dumps({"cmd": cmd}) + "\n").encode()
    sock.write(payload)
    sock.flush()
    if sock.state() == QLocalSocket.LocalSocketState.ConnectedState:
        sock.waitForBytesWritten(500)
    if wait_reply:
        if sock.waitForReadyRead(900):
            data = bytes(sock.readAll()).decode(errors="replace").strip()
            try:
                reply = json.loads(data.splitlines()[0])
                sock.disconnectFromServer()
                return reply
            except Exception:
                pass
        sock.disconnectFromServer()
        return None
    sock.disconnectFromServer()
    return True


def probe_status() -> dict | None:
    return send_command("status", wait_reply=True)


class IpcServer(QObject):
    """Listens for commands inside the overlay process."""

    def __init__(self, manager):
        super().__init__(manager)
        self.manager = manager
        name = socket_name()
        QLocalServer.removeServer(name)  # clear stale socket from a crash
        self.server = QLocalServer(self)
        self.server.newConnection.connect(self._on_connection)
        if not self.server.listen(name):
            from .util import dbg
            dbg("IPC listen failed:", self.server.errorString())

    def _on_connection(self) -> None:
        sock = self.server.nextPendingConnection()
        if sock is None:
            return
        sock.readyRead.connect(lambda: self._handle(sock))

    def _handle(self, sock) -> None:
        data = bytes(sock.readAll()).decode(errors="replace").strip()
        if not data:
            return
        try:
            msg = json.loads(data.splitlines()[0])
        except Exception:
            return
        cmd = msg.get("cmd")
        reply = {"ok": True}
        if cmd == "reload":
            from .config import Config
            self.manager.apply_config(Config.load())
        elif cmd == "pause":
            self.manager.pause()
        elif cmd == "resume":
            self.manager.resume()
        elif cmd == "status":
            reply.update({
                "running": self.manager.running,
                "paused": self.manager.paused,
                "season": "+".join(s.key for s in self.manager.specs),
                "season_name": self.manager.season_label(),
                "particles": sum(len(w.field.particles)
                                 for w in self.manager.windows),
                "fps": round(self.manager.fps, 1),
            })
        elif cmd == "quit":
            self._write(sock, reply)
            from PySide6.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                app.quit()
            return
        else:
            reply = {"ok": False, "error": f"unknown cmd {cmd!r}"}
        self._write(sock, reply)

    @staticmethod
    def _write(sock, obj) -> None:
        try:
            if sock.state() != QLocalSocket.LocalSocketState.ConnectedState:
                return
            sock.write((json.dumps(obj) + "\n").encode())
            sock.flush()
            sock.waitForBytesWritten(300)
        except Exception:
            pass
