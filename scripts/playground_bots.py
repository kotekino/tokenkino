#!/usr/bin/env python
# --------------------------------------------------------------
# scripts/playground_bots.py — the playground puppeteer (senses C/D live-testing).
#
# Drives the PLAYBOT_* test bots (John, Hellen, …) as PUPPETS: each invocation sends ONE message as
# ONE bot into a playground channel, via the Discord REST API (no gateway session needed to send —
# only tokeniko's own gateway matters for him to PERCEIVE it). Deterministic, polished input by
# design (the inbound preparser is OFF), so every probe is a reproducible specimen for
# doc/ref/test-feedback.md.
#
# The ladder each flag exercises (senses/inbound.grade_directedness):
#   plain message            -> ambient 0.6         ("the polite guest" band)
#   --reply-to <his msg id>  -> reply_to_me 0.9      (adapter resolves the author)
#   --reply-to <other id>    -> someone's thread 0.15
#   --mention                -> mentions_me 0.9      (real <@id> ping; his NAME as a word works too)
#
# Bots are discovered from tokeniko/.env: PLAYBOT_<NAME>_TOKEN. Tokens are secrets — never printed,
# never committed (this script is config-free; the .env is gitignored).
#
# Usage (from the repo root):
#   python scripts/playground_bots.py --list
#   python scripts/playground_bots.py john <channel_id> "a cat is an animal"
#   python scripts/playground_bots.py hellen <channel_id> "do you exist?" --mention
#   python scripts/playground_bots.py john <channel_id> "I disagree" --reply-to <message_id>
# Prints the sent message id — feed it to --reply-to to build threads.
# --------------------------------------------------------------
import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / "tokeniko" / ".env")

_API = "https://discord.com/api/v10"
_PREFIX, _SUFFIX = "PLAYBOT_", "_TOKEN"


def discover_bots() -> dict[str, str]:
    return {
        k[len(_PREFIX):-len(_SUFFIX)].lower(): v.strip().strip("'\"")
        for k, v in os.environ.items()
        if k.startswith(_PREFIX) and k.endswith(_SUFFIX) and v.strip()
    }


def send_message(token: str, channel_id: str, content: str, reply_to: str | None = None) -> dict:
    body: dict = {"content": content}
    if reply_to:
        # fail_if_not_exists=False: still deliver (unthreaded) if the target message vanished
        body["message_reference"] = {"message_id": reply_to, "fail_if_not_exists": False}
    req = urllib.request.Request(
        f"{_API}/channels/{channel_id}/messages",
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bot {token}", "Content-Type": "application/json",
                 # Discord's edge rejects UA-less requests with 403
                 "User-Agent": "DiscordBot (tokeniko-playground, 0.1)"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description="send one message as one playground bot")
    ap.add_argument("bot", nargs="?", help="bot name (see --list)")
    ap.add_argument("channel_id", nargs="?", help="target channel id")
    ap.add_argument("content", nargs="?", help="the message text")
    ap.add_argument("--reply-to", help="message id to thread the message under")
    ap.add_argument("--mention", action="store_true",
                    help="prefix a real @-mention of tokeniko (needs TOKENIKO_DISCORD_USER_ID in .env)")
    ap.add_argument("--list", action="store_true", help="list the available bots and exit")
    args = ap.parse_args()

    bots = discover_bots()
    if args.list:
        for name in sorted(bots):
            print(f"  {name}  (PLAYBOT_{name.upper()}_TOKEN set)")
        return 0
    if not (args.bot and args.channel_id and args.content):
        ap.error("bot, channel_id and content are required (or use --list)")

    token = bots.get(args.bot.lower())
    if token is None:
        print(f"unknown bot {args.bot!r} — available: {', '.join(sorted(bots)) or '(none)'}", file=sys.stderr)
        return 1

    content = args.content
    if args.mention:
        tokeniko_id = os.getenv("TOKENIKO_DISCORD_USER_ID", "").strip()
        if not tokeniko_id:
            print("--mention needs TOKENIKO_DISCORD_USER_ID in tokeniko/.env", file=sys.stderr)
            return 1
        content = f"<@{tokeniko_id}> {content}"

    msg = send_message(token, args.channel_id, content, reply_to=args.reply_to)
    print(f"sent as {args.bot}: message_id={msg['id']} channel_id={msg['channel_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
