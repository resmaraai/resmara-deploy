#!/usr/bin/env python3
"""Create the three Stripe objects Resmara needs, in whatever mode the key belongs to.

    STRIPE_SECRET_KEY=sk_live_... ./scripts/stripe_setup.py
    ./scripts/stripe_setup.py --key-file ~/.resmara-stripe-live.env

What it makes (idempotent — re-running finds what exists and creates nothing twice):

  1. Product  "Resmara campaign"     the catalogue item the owner sees in Stripe
  2. Price    4900 usd, one-off      the $49 the app charges (app also sends inline price_data)
  3. Webhook  https://www.resmara.com/api/billing/webhook  subscribed to checkout.session.completed

The webhook's signing secret is returned by Stripe **only at creation**, so it is written to the
--out file (mode 600) rather than printed. Values are never echoed: only a prefix and length.

Exit codes: 0 done, 2 no key, 3 Stripe refused (message on stderr).
"""
from __future__ import annotations

import argparse
import json
import os
import stat
import subprocess
import sys
import urllib.parse

API = "https://api.stripe.com/v1"
WEBHOOK_URL = os.getenv("RESMARA_WEBHOOK_URL", "https://www.resmara.com/api/billing/webhook")
PRODUCT_NAME = "Resmara campaign"
PRODUCT_DESC = "One property campaign - 14 days of social posts for one listing."
PRICE_CENTS = 4900
CURRENCY = "usd"
EVENTS = ["checkout.session.completed"]


def call(key: str, method: str, path: str, pairs: list | None = None) -> dict:
    cmd = ["curl", "-s", "-X", method, f"{API}/{path}", "-H", f"Authorization: Bearer {key}"]
    if pairs:
        cmd += ["-H", "Content-Type: application/x-www-form-urlencoded",
                "--data-binary", urllib.parse.urlencode(pairs)]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=60).stdout
    data = json.loads(out or "{}")
    if isinstance(data, dict) and data.get("error"):
        sys.stderr.write("Stripe refused: %s\n" % data["error"].get("message"))
        sys.exit(3)
    return data


def find_key(path: str, name: str) -> str:
    for line in open(path):
        if line.strip().startswith(name + "="):
            return line.split("=", 1)[1].strip()
    return ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--key-file", help="file with STRIPE_SECRET_KEY=... (0600)")
    ap.add_argument("--out", default=os.path.expanduser("~/.resmara-stripe-live.env"))
    args = ap.parse_args()

    key = os.getenv("STRIPE_SECRET_KEY", "").strip()
    if not key and args.key_file:
        key = find_key(args.key_file, "STRIPE_SECRET_KEY")
    if not key.startswith(("sk_", "rk_")):
        sys.stderr.write("No usable STRIPE_SECRET_KEY (need sk_/rk_)\n")
        return 2

    acct = call(key, "GET", "account")
    live = bool(acct.get("charges_enabled")) and not key.startswith("sk_test")
    mode = "test" if key.startswith(("sk_test", "rk_test")) else "live"
    print("account      %s  %s" % (acct.get("id"), (acct.get("business_profile") or {}).get("name")))
    print("mode         %s   charges_enabled=%s  payouts_enabled=%s"
          % (mode, acct.get("charges_enabled"), acct.get("payouts_enabled")))
    if acct.get("requirements", {}).get("currently_due"):
        print("still due    %s" % ", ".join(acct["requirements"]["currently_due"]))

    products = call(key, "GET", "products?limit=100").get("data", [])
    prod = next((p for p in products if p["name"] == PRODUCT_NAME), None)
    if prod:
        print("product      %s (exists)" % prod["id"])
    else:
        prod = call(key, "POST", "products", [("name", PRODUCT_NAME), ("description", PRODUCT_DESC)])
        print("product      %s (created)" % prod["id"])

    prices = call(key, "GET", "prices?limit=100&product=" + prod["id"]).get("data", [])
    price = next((p for p in prices
                  if p["unit_amount"] == PRICE_CENTS and p["currency"] == CURRENCY
                  and p.get("type") == "one_time"), None)
    if price:
        print("price        %s (exists) %s %s" % (price["id"], PRICE_CENTS, CURRENCY))
    else:
        price = call(key, "POST", "prices", [("product", prod["id"]),
                                             ("unit_amount", str(PRICE_CENTS)),
                                             ("currency", CURRENCY)])
        print("price        %s (created) %s %s" % (price["id"], PRICE_CENTS, CURRENCY))

    hooks = call(key, "GET", "webhook_endpoints?limit=100").get("data", [])
    hook = next((h for h in hooks if h["url"] == WEBHOOK_URL), None)
    secret = ""
    if hook:
        print("webhook      %s (exists) %s  events=%s"
              % (hook["id"], hook["url"], ",".join(hook.get("enabled_events") or [])))
    else:
        hook = call(key, "POST", "webhook_endpoints",
                    [("url", WEBHOOK_URL), ("description", "Resmara campaign paid")] +
                    [("enabled_events[]", e) for e in EVENTS])
        secret = hook.get("secret", "")
        print("webhook      %s (created) %s  events=%s"
              % (hook["id"], WEBHOOK_URL, ",".join(EVENTS)))

    lines = ["# Resmara Stripe - %s mode, account %s (created by scripts/stripe_setup.py)"
             % (mode, acct.get("id")),
             "STRIPE_SECRET_KEY=" + key,
             "STRIPE_PRODUCT_ID=" + prod["id"],
             "STRIPE_PRICE_ID=" + price["id"],
             "STRIPE_WEBHOOK_SECRET=" + (secret or "<existing endpoint - copy from the dashboard>")]
    if args.out:
        with open(args.out, "w") as f:
            f.write("\n".join(lines) + "\n")
        os.chmod(args.out, stat.S_IRUSR | stat.S_IWUSR)
        print("wrote        %s (0600)" % args.out)
    if secret:
        print("webhook secret stored: prefix %s len %d" % (secret[:8], len(secret)))
    else:
        print("webhook secret NOT shown: endpoint already existed, copy it from the dashboard")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
