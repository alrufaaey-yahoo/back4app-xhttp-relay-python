import json
import os
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.request import Request, urlopen

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import app


class UpstreamHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        response = json.dumps({
            "path": self.path,
            "body": body.decode(),
            "forwarded": self.headers.get("X-Forwarded-For"),
            "host": self.headers.get("Host"),
        }).encode()
        self.send_response(201)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, *_args):
        pass


class RelayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.upstream = ThreadingHTTPServer(("127.0.0.1", 0), UpstreamHandler)
        threading.Thread(target=cls.upstream.serve_forever, daemon=True).start()
        cls.relay = ThreadingHTTPServer(("127.0.0.1", 0), app.RelayHandler)
        cls.previous_target = os.environ.get("TARGET_DOMAIN")
        os.environ["TARGET_DOMAIN"] = f"http://127.0.0.1:{cls.upstream.server_port}"
        threading.Thread(target=cls.relay.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.relay.shutdown()
        cls.upstream.shutdown()
        if cls.previous_target is None:
            os.environ.pop("TARGET_DOMAIN", None)
        else:
            os.environ["TARGET_DOMAIN"] = cls.previous_target

    def test_health(self):
        with urlopen(f"http://127.0.0.1:{self.relay.server_port}/health") as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(json.loads(response.read()), {"status": "ok"})

    def test_relay_preserves_request_data_and_client_ip(self):
        request = Request(
            f"http://127.0.0.1:{self.relay.server_port}/hello?x=1",
            data=b"payload",
            method="POST",
            headers={"X-Real-IP": "203.0.113.5", "Connection": "close"},
        )
        with urlopen(request) as response:
            self.assertEqual(response.status, 201)
            payload = json.loads(response.read())
        self.assertEqual(payload["path"], "/hello?x=1")
        self.assertEqual(payload["body"], "payload")
        self.assertEqual(payload["forwarded"], "203.0.113.5")


if __name__ == "__main__":
    unittest.main()
