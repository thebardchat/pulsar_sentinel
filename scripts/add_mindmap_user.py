#!/usr/bin/env python3
"""
add_mindmap_user.py — User management CLI for the ShaneBrain Mindmap.

Lives next to mindmap_server.py and writes to the same NAS-backed users.json.
The mindmap server re-reads the file on every login attempt, so changes here
take effect immediately — no restart needed.

Usage
-----
  # Add a family member
  python3 add_mindmap_user.py add tiffany --role family --display-name "Tiffany"

  # Add an owner (full perms)
  python3 add_mindmap_user.py add shane --role owner --display-name "Shane"

  # Add a viewer (read-only)
  python3 add_mindmap_user.py add ryker --role viewer --display-name "Ryker"

  # Update a password
  python3 add_mindmap_user.py passwd tiffany

  # List all users (no passwords printed)
  python3 add_mindmap_user.py list

  # Remove a user
  python3 add_mindmap_user.py remove old_account

  # Initialize the file with a starter owner (interactive)
  python3 add_mindmap_user.py init

Roles
-----
  owner    — read everything, post deltas, manage users (future)
  family   — read everything, post deltas
  viewer   — read everything, no writes

The file is written atomically. Permissions are set to 0600.

Default users_file: /mnt/nas/shanebrain/users.json (override with --file)
"""
from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from mindmap_auth import _hash_password  # noqa: E402

DEFAULT_USERS_FILE = "/mnt/nas/shanebrain/users.json"
ROLES = ["owner", "family", "viewer"]


def load(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def save(path: Path, users: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(users, indent=2))
    tmp.replace(path)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def prompt_password(confirm: bool = True) -> str:
    while True:
        p1 = getpass.getpass("Password: ")
        if not p1:
            print("  (empty password rejected)")
            continue
        if len(p1) < 6:
            print("  (minimum 6 characters)")
            continue
        if confirm:
            p2 = getpass.getpass("Confirm:  ")
            if p1 != p2:
                print("  (mismatch, try again)")
                continue
        return p1


def cmd_add(args, users):
    if args.username in users:
        print(f"User '{args.username}' already exists. Use 'passwd' or 'remove' first.")
        return 1
    if args.role not in ROLES:
        print(f"Unknown role '{args.role}'. Choose from: {', '.join(ROLES)}")
        return 1
    pw = prompt_password()
    users[args.username] = {
        "username": args.username,
        "display_name": args.display_name or args.username.title(),
        "role": args.role,
        "password_hash": _hash_password(pw),
    }
    save(args.path, users)
    print(f"OK — added {args.username} ({args.role}) to {args.path}")
    return 0


def cmd_passwd(args, users):
    if args.username not in users:
        print(f"No such user: {args.username}")
        return 1
    pw = prompt_password()
    users[args.username]["password_hash"] = _hash_password(pw)
    save(args.path, users)
    print(f"OK — password updated for {args.username}")
    return 0


def cmd_list(args, users):
    if not users:
        print("(no users defined)")
        return 0
    width = max(len(u) for u in users)
    print(f"{'USERNAME':<{width}}  ROLE     DISPLAY NAME")
    print("-" * (width + 30))
    for name, info in sorted(users.items()):
        print(f"{name:<{width}}  {info.get('role', '?'):<8} {info.get('display_name', '')}")
    return 0


def cmd_remove(args, users):
    if args.username not in users:
        print(f"No such user: {args.username}")
        return 1
    del users[args.username]
    save(args.path, users)
    print(f"OK — removed {args.username}")
    return 0


def cmd_init(args, users):
    if users:
        print(f"Users file already exists with {len(users)} user(s). Use 'add' instead.")
        return 1
    print("Initial owner setup — this account can sign in immediately.")
    username = input("Username (default: shane): ").strip() or "shane"
    display = input(f"Display name (default: {username.title()}): ").strip() or username.title()
    pw = prompt_password()
    users[username] = {
        "username": username,
        "display_name": display,
        "role": "owner",
        "password_hash": _hash_password(pw),
    }
    save(args.path, users)
    print(f"OK — initialized {args.path} with owner '{username}'")
    print("\nNow add family members:")
    print(f"  python3 {sys.argv[0]} add <name> --role family --display-name \"<Name>\"")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Manage ShaneBrain Mindmap users.")
    ap.add_argument("--file", default=DEFAULT_USERS_FILE, help="Path to users.json")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_add = sub.add_parser("add", help="Add a new user")
    p_add.add_argument("username")
    p_add.add_argument("--role", default="family", choices=ROLES)
    p_add.add_argument("--display-name", default=None)
    p_add.set_defaults(func=cmd_add)

    p_pw = sub.add_parser("passwd", help="Change a user's password")
    p_pw.add_argument("username")
    p_pw.set_defaults(func=cmd_passwd)

    p_ls = sub.add_parser("list", help="List all users")
    p_ls.set_defaults(func=cmd_list)

    p_rm = sub.add_parser("remove", help="Delete a user")
    p_rm.add_argument("username")
    p_rm.set_defaults(func=cmd_remove)

    p_init = sub.add_parser("init", help="Initialize users.json with an owner")
    p_init.set_defaults(func=cmd_init)

    args = ap.parse_args()
    args.path = Path(args.file)
    users = load(args.path)
    return args.func(args, users)


if __name__ == "__main__":
    sys.exit(main())
