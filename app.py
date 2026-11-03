#!/usr/bin/env python3
"""HTTP relay server for Back4App Containers."""

from __future__ import annotations

import http.client
import json
import logging
import os
import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

DEFAULT_TARGET_DOMAIN = "https://vps.thumbayan.com:443"
HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
    "forwarded",
    "x-forwarded-host",
    "x-forwarded-proto",
    "x-forwarded-port",
}

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper(), format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("xhttp-relay")


def configured_target() -> tuple[str, str, int, str]:
    raw = os.getenv("TARGET_DOMAIN", DEFAULT_TARGET_DOMAIN).rstrip("/")
    parsed = urlsplit(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("TARGET_DOMAIN must be an absolute http:// or https:// URL")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    base_path = parsed.path.rstrip("/")
    return parsed.scheme, parsed.hostname, port, base_path


def make_connection(scheme: str, host: str, port: int) -> http.client.HTTPConnection:
    timeout = float(os.getenv("UPSTREAM_TIMEOUT", "30"))
    connection_class = http.client.HTTPSConnection if scheme == "https" else http.client.HTTPConnection
    return connection_class(host, port, timeout=timeout)


class RelayHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:
        self._handle_relay()

    def do_HEAD(self) -> None:
        self._handle_relay()

    def do_POST(self) -> None:
        self._handle_relay()

    def do_PUT(self) -> None:
        self._handle_relay()

    def do_PATCH(self) -> None:
        self._handle_relay()

    def do_DELETE(self) -> None:
        self._handle_relay()

    def do_OPTIONS(self) -> None:
        self._handle_relay()

    def _send_json(self, status: int, payload: dict[str, str]) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _handle_relay(self) -> None:
        if self.path.split("?", 1)[0] in {"/health", "/healthz"}:
            self._send_json(200, {"status": "ok"})
            return

        try:
            scheme, host, port, base_path = configured_target()
            target_path = f"{base_path}{self.path}"
            body_length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(body_length) if body_length > 0 else None
            headers: dict[str, str] = {}
            client_ip: str | None = None

            for key, value in self.headers.items():
                lower_key = key.lower()
                if lower_key in HOP_BY_HOP_HEADERS or lower_key.startswith("x-vercel-"):
                    continue
                if lower_key == "x-real-ip":
                    client_ip = value
                    continue
                if lower_key == "x-forwarded-for":
                    client_ip = client_ip or value
                    continue
                headers[key] = value

            if client_ip:
                headers["X-Forwarded-For"] = client_ip

            connection = make_connection(scheme, host, port)
            try:
                connection.request(self.command, target_path, body=body, headers=headers)
                upstream = connection.getresponse()
                response_body = upstream.read()
            finally:
                connection.close()

            self.send_response(upstream.status, upstream.reason)
            for key, value in upstream.getheaders():
                if key.lower() not in HOP_BY_HOP_HEADERS and key.lower() != "content-length":
                    self.send_header(key, value)
            self.send_header("Content-Length", str(len(response_body)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(response_body)

        except (ValueError, socket.timeout, OSError, http.client.HTTPException) as error:
            logger.exception("Relay request failed: %s", error)
            self._send_json(502, {"error": "Bad Gateway: Proxy Request Failed"})

    def log_message(self, fmt: str, *args: object) -> None:
        logger.info("%s - %s", self.address_string(), fmt % args)


def main() -> None:
    port = int(os.getenv("PORT", "3000"))
    server = ThreadingHTTPServer(("0.0.0.0", port), RelayHandler)
    logger.info("Server listening on 0.0.0.0:%s; target=%s", port, os.getenv("TARGET_DOMAIN", DEFAULT_TARGET_DOMAIN))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
