"""Custom Runtime entrypoint for SoniScope FC web functions.

The existing FC functions are configured with the start command
``python3 app.py``. This file starts a tiny WSGI server and delegates every
HTTP request to the function-local ``handler.handler`` callable.
"""

from __future__ import annotations

import os
from socketserver import ThreadingMixIn
from wsgiref.simple_server import WSGIServer, make_server

from handler import handler as application


class ThreadingWSGIServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True


def _port() -> int:
    raw = os.environ.get("FC_SERVER_PORT") or os.environ.get("PORT") or "9000"
    return int(raw)


def main() -> None:
    host = "0.0.0.0"
    port = _port()
    with make_server(host, port, application, server_class=ThreadingWSGIServer) as server:
        print(f"SoniScope FC custom runtime listening on {host}:{port}", flush=True)
        server.serve_forever()


if __name__ == "__main__":
    main()
