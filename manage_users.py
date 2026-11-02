#!/usr/bin/env python3
"""
SpinSleeve Multi-Tenant User Management CLI.
Allows easy inspection, approval, and management of invite-only beta users stored in Google Cloud Datastore.
"""

import sys
import argparse
import datetime
from google.cloud import datastore

PROJECT_ID = "secret-compass-181513"


def get_client():
    return datastore.Client(project=PROJECT_ID)


def list_users(args):
    client = get_client()
    query = client.query(kind="User")
    users = list(query.fetch())

    if not users:
        print("No users found in Datastore.")
        return

    print("\n=== SpinSleeve Registered Users ===")
    print(f"{'SPOTIFY ID':<20} | {'NAME':<20} | {'APPROVED?':<10} | {'ROLE':<8} | {'LAST LOGIN'}")
    print("-" * 80)
    for u in users:
        spotify_id = u.key.name or u.get("spotify_id", "Unknown")
        name = u.get("display_name", "Unknown")
        approved = "YES [Approved]" if u.get("is_approved") else "NO [Pending]"
        role = u.get("role", "user")
        last_login = u.get("last_login_at", "Never")
        if isinstance(last_login, datetime.datetime):
            last_login = last_login.strftime("%Y-%m-%d %H:%M UTC")
        print(f"{spotify_id:<20} | {name:<20} | {approved:<10} | {role:<8} | {last_login}")
    print()


def approve_user(args):
    client = get_client()
    key = client.key("User", args.spotify_id)
    user = client.get(key)

    role = getattr(args, "role", "user") or "user"

    if not user:
        # Create a pre-approved placeholder
        user = datastore.Entity(key=key)
        user.update({
            "spotify_id": args.spotify_id,
            "display_name": args.name or args.spotify_id,
            "is_approved": True,
            "role": role,
            "created_at": datetime.datetime.now(datetime.timezone.utc),
            "sync_status": "idle"
        })
        client.put(user)
        print(f"Pre-approved new user '{args.spotify_id}' ({args.name or ''}) with role '{role}' successfully!")
    else:
        user["is_approved"] = True
        if args.name:
            user["display_name"] = args.name
        if role:
            user["role"] = role
        client.put(user)
        print(f"User '{args.spotify_id}' is now APPROVED as '{user.get('role', 'user')}' for SpinSleeve Beta access!")


def revoke_user(args):
    client = get_client()
    key = client.key("User", args.spotify_id)
    user = client.get(key)
    if not user:
        print(f"User '{args.spotify_id}' does not exist.")
        return
    user["is_approved"] = False
    client.put(user)
    print(f"Access revoked for user '{args.spotify_id}'.")


def main():
    parser = argparse.ArgumentParser(description="SpinSleeve Beta User Management")
    subparsers = parser.add_subparsers(dest="command")

    # List
    subparsers.add_parser("list", help="List all registered and pending users")

    # Approve / Whitelist
    approve_parser = subparsers.add_parser("approve", help="Approve or whitelist a user")
    approve_parser.add_argument("spotify_id", help="Spotify User ID or username")
    approve_parser.add_argument("--name", help="Optional display name", default=None)
    approve_parser.add_argument("--role", choices=["admin", "user"], default="user", help="User role (admin or user)")

    # Revoke
    revoke_parser = subparsers.add_parser("revoke", help="Revoke access for a user")
    revoke_parser.add_argument("spotify_id", help="Spotify User ID or username")

    args = parser.parse_args()

    if args.command == "list":
        list_users(args)
    elif args.command == "approve":
        approve_user(args)
    elif args.command == "revoke":
        revoke_user(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
