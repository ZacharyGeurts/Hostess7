#!/usr/bin/env python3
"""Deploy Hostess7 GitHub Pages edge proxy on Cloudflare Workers."""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

ORIGIN = "https://zacharygeurts.github.io/Hostess7"
WORKER_SCRIPT = f"""
addEventListener('fetch', event => {{ event.respondWith(handle(event.request)); }});
async function handle(request) {{
  const url = new URL(request.url);
  let path = url.pathname;
  if (path === '/' || path.endsWith('/')) path = (path.replace(/\\/$/, '') || '') + '/index.html';
  const target = '{ORIGIN}' + path + url.search;
  const resp = await fetch(target, {{ headers: {{ 'User-Agent': 'Hostess7-Cloudflare-Edge/1.0' }} }});
  const out = new Response(resp.body, resp);
  out.headers.set('X-Hostess7-Edge', 'cloudflare');
  out.headers.set('Cache-Control', 'public, max-age=300');
  return out;
}}
""".strip()


def _api(method: str, path: str, body: dict | None = None, token: str = "") -> dict:
    url = f"https://api.cloudflare.com/client/v4{path}"
    data = None
    headers = {"Authorization": f"Bearer {token}"}
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--worker", default="hostess7")
    ap.add_argument("--version", default="1.0.0-beta")
    args = ap.parse_args()

    token = os.environ.get("CLOUDFLARE_API_TOKEN") or os.environ.get("CF_API_TOKEN")
    account = os.environ.get("CLOUDFLARE_ACCOUNT_ID") or "4b10f43cab3c5833c91bb238295b296f"
    if not token:
        print("SKIP: CLOUDFLARE_API_TOKEN not set", file=sys.stderr)
        return 0

    metadata = json.dumps({"body_part": "script", "compatibility_date": "2026-06-30"})
    boundary = f"----Hostess7{os.getpid()}"
    parts = [
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"metadata\"\r\nContent-Type: application/json\r\n\r\n{metadata}\r\n",
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"script\"; filename=\"script\"\r\nContent-Type: application/javascript\r\n\r\n{WORKER_SCRIPT}\r\n",
        f"--{boundary}--\r\n",
    ]
    payload = "".join(parts).encode()

    url = f"https://api.cloudflare.com/client/v4/accounts/{account}/workers/scripts/{args.worker}"
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="PUT",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            doc = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        print(f"FAIL worker upload: {exc.read().decode()[:500]}", file=sys.stderr)
        return 1

    if not doc.get("success"):
        print(json.dumps(doc, indent=2), file=sys.stderr)
        return 1

    try:
        _api(
            "POST",
            f"/accounts/{account}/workers/scripts/{args.worker}/subdomain",
            {"enabled": True},
            token,
        )
    except Exception as exc:
        print(f"WARN subdomain: {exc}", file=sys.stderr)

    print(json.dumps({
        "ok": True,
        "worker": args.worker,
        "origin": ORIGIN,
        "edge_url": f"https://{args.worker}.gzac5314.workers.dev/",
        "version": args.version,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())