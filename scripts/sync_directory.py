"""Autonomous Directory & Personnel Change Sync Script.

Demonstrates how AURA automatically detects who changed, when, and for which position,
and updates data/contacts_override.json with a transparent audit trail.

Usage:
  python scripts/sync_directory.py --list
  python scripts/sync_directory.py --update hostel_boys_manager "Dr. K. Srinivas" --phone "9848011223"
  python scripts/sync_directory.py --audit
"""
import argparse
import datetime
import json
import os
import sys

# Add project root to sys.path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from agent.contacts import load_contacts, update_personnel, OVERRIDE_FILE


def list_contacts():
    contacts = load_contacts()
    print("\n" + "=" * 70)
    print("SR UNIVERSITY ACTIVE PERSONNEL DIRECTORY (LIVE OVERLAY)")
    print("=" * 70)
    for pos_id, c in contacts.items():
        print(f"\n[Position ID]: {pos_id}")
        print(f"  Role:         {c.get('role')}")
        print(f"  Active Name:  {c.get('current_name')}")
        if c.get("previous_name"):
            print(f"  Previous:     {c.get('previous_name')}")
        print(f"  Phone:        {c.get('phone')}")
        print(f"  Email:        {c.get('email')}")
        print(f"  Office:       {c.get('office')}")
        print(f"  Last Updated: {c.get('last_updated')}")
        print(f"  Verified:     {c.get('verified')}")
    print("\n" + "=" * 70 + "\n")


def simulate_diff_check():
    """Simulates checking a new administrative notice / directory feed and detecting changes."""
    print("[SYNC] Checking official SRU Administrative Roster for updates...")
    contacts = load_contacts()

    # Sample incoming live roster from university admin feed
    incoming_feed = {
        "hostel_boys_manager": {
            "name": "Dr. K. Srinivas",
            "phone": "9848011223",
            "email": "stu.boyshostel@sru.edu.in",
            "office": "BH-2 Administrative Office",
            "notice": "Updated as per SRU Administrative Office Order No. SRU/ADM/2026/044."
        }
    }

    detected_changes = []
    for pos_id, fresh in incoming_feed.items():
        current = contacts.get(pos_id, {})
        curr_name = current.get("current_name")
        new_name = fresh.get("name")
        if curr_name != new_name:
            detected_changes.append({
                "pos_id": pos_id,
                "role": current.get("role", pos_id),
                "old_name": curr_name,
                "new_name": new_name,
                "phone": fresh.get("phone"),
                "email": fresh.get("email"),
                "office": fresh.get("office"),
                "notice": fresh.get("notice"),
            })

    if not detected_changes:
        print("[SYNC] ✅ All personnel entries are up-to-date. No changes detected.")
        return

    print(f"\n[ALERT] Detected {len(detected_changes)} personnel change(s):")
    for ch in detected_changes:
        print(f"  ⚠️  Position: {ch['role']} ({ch['pos_id']})")
        print(f"      Preceding Official: {ch['old_name']}")
        print(f"      Newly Appointed:    {ch['new_name']}")
        print(f"      Effective Date:     {datetime.date.today().isoformat()}")

        # Autonomously apply update
        update_personnel(
            position_id=ch["pos_id"],
            name=ch["new_name"],
            phone=ch.get("phone", ""),
            email=ch.get("email", ""),
            office=ch.get("office", ""),
            notice=ch.get("notice", ""),
        )
        print(f"  ✅ [AUTO-APPLIED] Successfully updated '{ch['pos_id']}' in {OVERRIDE_FILE}")


def main():
    parser = argparse.ArgumentParser(description="SRU Personnel Directory Sync Tool")
    parser.add_argument("--list", action="store_true", help="List current active contacts")
    parser.add_argument("--check-feed", action="store_true", help="Simulate checking directory feed for diffs")
    parser.add_argument("--update", metavar="POSITION_ID", help="Position ID to update")
    parser.add_argument("name", nargs="?", help="New personnel name")
    parser.add_argument("--phone", default="", help="Official phone number")
    parser.add_argument("--email", default="", help="Official email address")
    parser.add_argument("--office", default="", help="Office location")
    parser.add_argument("--notice", default="", help="Administrative notice")

    args = parser.parse_args()

    if args.list:
        list_contacts()
    elif args.check_feed:
        simulate_diff_check()
    elif args.update:
        if not args.name:
            print("Error: Name required when using --update. Example: --update hostel_boys_manager 'Dr. New Name'")
            sys.exit(1)
        res = update_personnel(
            position_id=args.update,
            name=args.name,
            phone=args.phone,
            email=args.email,
            office=args.office,
            notice=args.notice,
        )
        print(f"✅ Successfully updated {res['position_id']}:")
        print(f"   New Official:       {res['new_name']}")
        print(f"   Preceding Official: {res['previous_name']}")
        print(f"   Timestamp:          {res['last_updated']}")
    else:
        list_contacts()


if __name__ == "__main__":
    main()

