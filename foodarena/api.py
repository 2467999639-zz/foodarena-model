"""Local demo HTTP API. Put authentication and a production server in front before deployment."""

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .ranker import load_model, recommend

MAX_BODY = 256 * 1024


def create_server(host="127.0.0.1", port=8000):
    model = load_model()

    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(10)

        def log_message(self, format, *args):
            # Do not persist request paths or user preference data.
            pass

        def reply(self, code, payload):
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == "/health":
                self.reply(200, {"status": "ok", "model_version": model["version"]})
            else:
                self.reply(404, {"error": "not_found"})

        def do_POST(self):
            if self.path != "/recommend":
                self.reply(404, {"error": "not_found"})
                return
            if self.headers.get_content_type() != "application/json":
                self.reply(415, {"error": "use application/json"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= MAX_BODY:
                    self.reply(413, {"error": "body must be between 1 and 262144 bytes"})
                    return
                request = json.loads(self.rfile.read(length).decode("utf-8"))
                self.reply(200, recommend(request, model))
            except (ValueError, UnicodeError) as error:
                self.reply(400, {"error": "invalid_request", "message": str(error)})
            except (TimeoutError, OSError):
                self.close_connection = True

    return ThreadingHTTPServer((host, port), Handler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8000, type=int)
    args = parser.parse_args()
    server = create_server(args.host, args.port)
    print("FoodArena model API: http://{}:{}/health".format(*server.server_address), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
