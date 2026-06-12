from __future__ import annotations

import json
import os
import socket
import struct
import threading
from dataclasses import dataclass
from typing import Any


class BackendError(RuntimeError):
    """Raised when an Unreal TCP backend cannot complete a command."""


@dataclass(frozen=True)
class BackendConfig:
    host: str = "127.0.0.1"
    port: int = 55558
    timeout: float = 30.0
    retries: int = 1
    protocol: str = "length"
    persistent: bool = True


class JsonTcpBackend:
    """Client for Unreal TCP JSON backends.

    Supported protocols:
    - length: 4-byte big-endian length prefix followed by UTF-8 JSON.
    - raw: UTF-8 JSON request; response is read until a complete JSON object or EOF.
    """

    def __init__(self, config: BackendConfig) -> None:
        self.config = config
        self._sock: socket.socket | None = None
        self._lock = threading.RLock()

    def close(self) -> None:
        with self._lock:
            if self._sock is not None:
                try:
                    self._sock.close()
                finally:
                    self._sock = None

    def send(self, command: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        last_error: Exception | None = None
        attempts = max(1, self.config.retries + 1)

        for attempt in range(attempts):
            try:
                with self._lock:
                    self._ensure_socket()
                    assert self._sock is not None
                    payload = json.dumps(
                        {"type": command, "params": params or {}},
                        ensure_ascii=False,
                        separators=(",", ":"),
                    ).encode("utf-8")
                    if self.config.protocol == "length":
                        self._sock.sendall(struct.pack(">I", len(payload)))
                        self._sock.sendall(payload)
                        header = self._recv_exact(4)
                        size = struct.unpack(">I", header)[0]
                        body = self._recv_exact(size)
                    elif self.config.protocol == "raw":
                        self._sock.sendall(payload)
                        try:
                            self._sock.shutdown(socket.SHUT_WR)
                        except OSError:
                            pass
                        body = self._recv_json_bytes()
                    else:
                        raise BackendError(f"Unsupported protocol '{self.config.protocol}'")
                    result = json.loads(body.decode("utf-8"))
                    if not isinstance(result, dict):
                        raise BackendError(f"Backend returned non-object JSON: {type(result).__name__}")
                    if not self.config.persistent:
                        self.close()
                    return result
            except Exception as exc:  # noqa: BLE001 - reset and retry once on transport failures.
                last_error = exc
                self.close()
                if attempt + 1 >= attempts:
                    break

        raise BackendError(
            f"Unreal backend {self.config.host}:{self.config.port} failed for {command}: {last_error}"
        ) from last_error

    def _ensure_socket(self) -> None:
        if self._sock is not None:
            return
        sock = socket.create_connection((self.config.host, self.config.port), timeout=self.config.timeout)
        sock.settimeout(self.config.timeout)
        self._sock = sock

    def _recv_exact(self, size: int) -> bytes:
        assert self._sock is not None
        chunks = bytearray()
        while len(chunks) < size:
            chunk = self._sock.recv(size - len(chunks))
            if not chunk:
                raise BackendError("Socket closed while reading response")
            chunks.extend(chunk)
        return bytes(chunks)

    def _recv_json_bytes(self) -> bytes:
        assert self._sock is not None
        chunks = bytearray()
        while True:
            chunk = self._sock.recv(8192)
            if not chunk:
                if chunks:
                    return bytes(chunks)
                raise BackendError("Socket closed before response")
            chunks.extend(chunk)
            try:
                json.loads(chunks.decode("utf-8"))
                return bytes(chunks)
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue


class BackendPool:
    def __init__(self) -> None:
        self._clients: dict[int, JsonTcpBackend] = {}
        self._lock = threading.RLock()
        self.host = os.getenv("XS_MCP_HOST", "127.0.0.1")
        self.timeout = float(os.getenv("XS_MCP_TIMEOUT", "30"))
        self.retries = int(os.getenv("XS_MCP_RETRIES", "1"))
        self.unreal_port = int(os.getenv("XS_MCP_UNREAL_PORT", "55557"))
        self.blueprint_port = int(os.getenv("XS_MCP_BLUEPRINT_PORT", "55558"))
        self.graph_port = int(os.getenv("XS_MCP_GRAPH_PORT", str(self.unreal_port)))

    def client(self, port: int) -> JsonTcpBackend:
        with self._lock:
            if port not in self._clients:
                protocol = self._protocol_for_port(port)
                self._clients[port] = JsonTcpBackend(
                    BackendConfig(
                        host=self.host,
                        port=port,
                        timeout=self.timeout,
                        retries=self.retries,
                        protocol=protocol,
                        persistent=protocol == "length",
                    )
                )
            return self._clients[port]

    def send(self, port: int, command: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.client(port).send(command, params)

    def close(self) -> None:
        with self._lock:
            for client in self._clients.values():
                client.close()
            self._clients.clear()

    def _protocol_for_port(self, port: int) -> str:
        port_key = f"XS_MCP_PORT_{port}_PROTOCOL"
        if os.getenv(port_key):
            return os.environ[port_key].lower()
        if port == self.graph_port and os.getenv("XS_MCP_GRAPH_PROTOCOL"):
            return os.environ["XS_MCP_GRAPH_PROTOCOL"].lower()
        if port == self.unreal_port:
            return os.getenv("XS_MCP_UNREAL_PROTOCOL", "raw").lower()
        if port == self.blueprint_port:
            return os.getenv("XS_MCP_BLUEPRINT_PROTOCOL", "length").lower()
        return os.getenv("XS_MCP_DEFAULT_PROTOCOL", "length").lower()


pool = BackendPool()
