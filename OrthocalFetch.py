#!/usr/bin/env python3
"""Fetch Orthocal reports with bounded memory and JSON item limits."""

from __future__ import annotations

import argparse
import datetime as dt
import ipaddress
import json
import socket
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

USER_AGENT = "Omarchy Orthodox Daily/1.0 (+https://orthocal.info/)"
ORTHOCAL_HOST = "orthocal.info"
MAX_RESPONSE_BYTES = 1024 * 1024
MAX_JSON_ITEMS = 20000
MAX_JSON_DEPTH = 100
MAX_REDIRECTS = 5
CHUNK_SIZE = 64 * 1024


def validate_url(url: str) -> None:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != ORTHOCAL_HOST:
        raise ValueError("Refusing non-Orthocal redirect destination")

    infos = socket.getaddrinfo(parsed.hostname, parsed.port or 443, type=socket.SOCK_STREAM)
    if not infos:
        raise ValueError("Could not resolve Orthocal host")
    for info in infos:
        address = info[4][0]
        ip = ipaddress.ip_address(address)
        if not ip.is_global:
            raise ValueError("Refusing private or loopback Orthocal address")


def redirect_count(request: urllib.request.Request) -> int:
    return int(next(
        (value for key, value in request.headers.items() if key.lower() == "x-omarchy-redirects"),
        "0",
    ))


class SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[override]
        validate_url(newurl)
        redirects = redirect_count(req) + 1
        if redirects > MAX_REDIRECTS:
            raise urllib.error.HTTPError(req.full_url, code, "Too many redirects", headers, fp)
        request = super().redirect_request(req, fp, code, msg, headers, newurl)
        if request is not None:
            request.add_header("X-Omarchy-Redirects", str(redirects))
        return request


OPENER = urllib.request.build_opener(SafeRedirectHandler)


def fetch_bytes(url: str, timeout: int = 12) -> bytes:
    validate_url(url)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "X-Omarchy-Redirects": "0"})
    data = bytearray()
    with OPENER.open(request, timeout=timeout) as response:
        final_url = response.geturl()
        validate_url(final_url)
        while True:
            chunk = response.read(min(CHUNK_SIZE, MAX_RESPONSE_BYTES + 1 - len(data)))
            if not chunk:
                break
            data.extend(chunk)
            if len(data) > MAX_RESPONSE_BYTES:
                raise ValueError("Orthocal response exceeds local byte limit")
    return bytes(data)


def json_item_count(value: Any) -> int:
    count = 0
    stack: list[tuple[Any, int]] = [(value, 0)]
    while stack:
        item, depth = stack.pop()
        if depth > MAX_JSON_DEPTH:
            raise ValueError("Orthocal response exceeds local nesting limit")
        count += 1
        if count > MAX_JSON_ITEMS:
            raise ValueError("Orthocal response exceeds local item limit")
        if isinstance(item, dict):
            count += len(item)
            stack.extend((child, depth + 1) for child in item.values())
        elif isinstance(item, list):
            count += len(item)
            stack.extend((child, depth + 1) for child in item)
        if count > MAX_JSON_ITEMS:
            raise ValueError("Orthocal response exceeds local item limit")
    return count


def checked_json(data: bytes) -> dict[str, Any]:
    try:
        parsed = json.loads(data.decode("utf-8"))
    except RecursionError as error:
        raise ValueError("Orthocal response exceeds local nesting limit") from error
    if not isinstance(parsed, dict):
        raise ValueError("Orthocal response is not an object")
    json_item_count(parsed)
    return parsed


def api_url(tradition: str, calendar: str, day: dt.date, translation: str) -> str:
    return (
        f"https://orthocal.info/api/{urllib.parse.quote(tradition)}/"
        f"{urllib.parse.quote(calendar)}/{day.year}/{day.month}/{day.day}/"
        f"?translation={urllib.parse.quote(translation)}"
    )


def fetch_report(tradition: str, calendar: str, translation: str, day: dt.date) -> dict[str, Any]:
    report = checked_json(fetch_bytes(api_url(tradition, calendar, day, translation)))
    report["tradition"] = tradition
    report["calendar"] = calendar
    report["translation"] = translation
    report["civil_date"] = day.isoformat()
    return report


def read_cached_report(path: Path) -> dict[str, Any] | None:
    try:
        if not path.exists() or path.stat().st_size > MAX_RESPONSE_BYTES:
            return None
        return checked_json(path.read_bytes())
    except (OSError, ValueError, json.JSONDecodeError):
        return None


def command_day(args: argparse.Namespace) -> None:
    report = fetch_report(args.tradition, args.calendar, args.translation, args.date)
    print(json.dumps(report, ensure_ascii=False, separators=(",", ":")))


def command_week(args: argparse.Namespace) -> None:
    base = Path(args.state_dir) / "daily" / "orthocal" / args.tradition / args.calendar / args.translation
    base.mkdir(parents=True, exist_ok=True)
    start = args.date - dt.timedelta(days=(args.date.weekday() + 1) % 7)
    out: dict[str, Any] = {}
    for offset in range(7):
        day = start + dt.timedelta(days=offset)
        key = day.isoformat()
        path = base / f"{key}.json"
        data: dict[str, Any] | None
        try:
            data = fetch_report(args.tradition, args.calendar, args.translation, day)
            path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
        except Exception:
            data = read_cached_report(path)
        if isinstance(data, dict):
            out[key] = data
    print(json.dumps(out, ensure_ascii=False, separators=(",", ":")))


def parse_date(value: str) -> dt.date:
    return dt.date.fromisoformat(value)


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    day = subparsers.add_parser("day")
    day.add_argument("--tradition", required=True)
    day.add_argument("--calendar", required=True)
    day.add_argument("--translation", required=True)
    day.add_argument("--date", required=True, type=parse_date)
    day.set_defaults(func=command_day)

    week = subparsers.add_parser("week")
    week.add_argument("--tradition", required=True)
    week.add_argument("--calendar", required=True)
    week.add_argument("--translation", required=True)
    week.add_argument("--date", required=True, type=parse_date)
    week.add_argument("--state-dir", required=True)
    week.set_defaults(func=command_week)

    args = parser.parse_args()
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
