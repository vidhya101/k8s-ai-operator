#!/usr/bin/env python3
"""
Serve our Munder-Difflin hire manifests as a local gallery.

WHY THIS EXISTS. Munder's hire-import flow accepts a URL to a manifest:
    munderdifflin://hire?src=<https-url>
For public galleries the URL must be HTTPS; loopback (http://127.0.0.1:*) is
allowed for local development (see src/main/hire.ts). This script serves the
generated manifests from .claude/munder/hires/ at http://127.0.0.1:<port>/ so
you can import each one by opening a deep link (or by File → Import a hire).

USAGE:
    python3 .claude/scripts/serve-munder-hires.py [--port 9977]

Then in Munder: File → Import a hire → paste one of:
    http://127.0.0.1:9977/cloud-manager.json
    http://127.0.0.1:9977/terraform-manager.json
    ...

Or open the printed deep links in your browser (macOS: `open <link>`); Munder
registers the `munderdifflin://` scheme and the OS routes back to the app.

BINDING TO LOOPBACK ONLY. We bind 127.0.0.1 explicitly (never 0.0.0.0). No
service should ever be exposed to the LAN from a script that lives in a repo,
and Munder's hire validator only trusts loopback origins for non-HTTPS anyway.
"""
from __future__ import annotations

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HIRE_DIR = Path(__file__).resolve().parents[2] / ".claude" / "munder" / "hires"


class HireHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802  (BaseHTTPRequestHandler API)
        # Serve JSON files verbatim; deny anything else (no directory listing
        # or path traversal — this is a tiny, single-purpose server).
        rel = self.path.lstrip("/").split("?", 1)[0]

        # Landing page — human-readable index of the gallery + the deep links.
        if rel in ("", "index", "index.html"):
            self._serve_index()
            return

        # Only JSON files, no traversal, no dotfiles, no subdirs.
        if (
            not rel.endswith(".json")
            or "/" in rel
            or "\\" in rel
            or rel.startswith(".")
        ):
            self._plain(404, "not found")
            return

        target = HIRE_DIR / rel
        if not target.is_file() or target.parent.resolve() != HIRE_DIR.resolve():
            self._plain(404, "not found")
            return

        body = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        # Munder is the only intended consumer; no CORS needed.
        self.end_headers()
        self.wfile.write(body)

    def _serve_index(self) -> None:
        try:
            index = json.loads((HIRE_DIR / "gallery-index.json").read_text())
        except FileNotFoundError:
            self._plain(500, "run generate-munder-hires.py first")
            return

        port = self.server.server_port  # type: ignore[attr-defined]
        rows = []
        for a in index.get("agents", []):
            name = a["name"]
            deep = f"munderdifflin://hire?src=http://127.0.0.1:{port}/{name}.json"
            direct = f"http://127.0.0.1:{port}/{name}.json"
            rows.append(f"""
              <tr>
                <td><code>{name}</code></td>
                <td>{a['character']}</td>
                <td>{a['goal']}</td>
                <td>
                  <a href="{deep}">import →</a><br>
                  <small><a href="{direct}">json</a></small>
                </td>
              </tr>""")

        html = f"""<!doctype html>
<html><head><meta charset=utf-8>
<title>.claude/ · Munder hire gallery</title>
<style>
  body {{ font: 14px/1.5 -apple-system, sans-serif; max-width: 980px; margin: 2em auto; padding: 0 1em; }}
  table {{ border-collapse: collapse; width: 100%; }}
  th, td {{ text-align: left; padding: 8px 12px; border-bottom: 1px solid #ddd; vertical-align: top; }}
  th {{ background: #f5f5f5; }}
  code {{ background: #f0f0f0; padding: 1px 4px; border-radius: 3px; }}
  h1 {{ margin-bottom: 0; }} p.sub {{ color: #666; margin-top: 4px; }}
</style></head>
<body>
  <h1>Your DevOps team · Munder hire gallery</h1>
  <p class="sub">{index.get('description','')}</p>
  <p>Click <em>import</em> next to each manager to open the pre-filled Add-Agent
     modal in Munder-Difflin. Review it, then click <strong>Spawn</strong>.</p>
  <p><strong>Cost warning:</strong> each spawned agent burns tokens continuously.
     Start with <code>orchestrator</code> (Michael, auto-provisioned by Munder) plus
     one or two managers; spawn the rest only when you actually delegate to them.</p>
  <table>
    <thead><tr><th>agent</th><th>character</th><th>goal</th><th>action</th></tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table>
</body></html>"""
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _plain(self, code: int, msg: str) -> None:
        body = msg.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args) -> None:  # noqa: A003 (BaseHTTPRequestHandler override)
        # Compact one-line log to stderr instead of the default noisy Apache-style.
        sys.stderr.write(f"[{self.address_string()}] {fmt % args}\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=9977,
                        help="port to bind on 127.0.0.1 (default: 9977)")
    args = parser.parse_args()

    if not HIRE_DIR.is_dir() or not any(HIRE_DIR.glob("*.json")):
        sys.stderr.write(
            f"no manifests in {HIRE_DIR} — run generate-munder-hires.py first\n"
        )
        return 2

    server = ThreadingHTTPServer(("127.0.0.1", args.port), HireHandler)
    print(f"gallery serving on http://127.0.0.1:{args.port}/")
    print(f"open it in your browser to see per-agent import links.")
    print(f"stop with ctrl-c.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
