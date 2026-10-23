"""
Command line interface for semantic-merge-guard.
"""

import argparse
import sys
import json
from pathlib import Path
from semantic_merge_guard.core import SemanticMergeGuard
from semantic_merge_guard.monetization import LicenseManager

def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="semantic-merge-guard",
        description="Cross-file AST dependency graph analyzer catching silent semantic merge conflicts"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # check command
    check_parser = subparsers.add_parser("check", help="Scan repository for cross-file semantic merge conflicts")
    check_parser.add_argument("--path", default=".", help="Directory to analyze")
    check_parser.add_argument("--fail-on-warning", action="store_true", default=False, help="Fail on HIGH/WARNING severity as well as CRITICAL")
    check_parser.add_argument("--license-key", default=None, help="OrderStream license key")

    # license / donate command
    subparsers.add_parser("license", help="View license tier and 0% fee crypto donation wallets")

    args = parser.parse_args(argv)

    if not args.command or args.command == "license":
        print(LicenseManager.get_banner("semantic-merge-guard"))
        tier = LicenseManager.get_tier(getattr(args, "license_key", None))
        print(f"Active Tier: {tier['name']} ({tier['tier']})")
        print(f"Features: {', '.join(tier['features'])}")
        print(LicenseManager.get_remediation_footer())
        return 0

    if args.command == "check":
        print(LicenseManager.get_banner("semantic-merge-guard"))
        conflicts = SemanticMergeGuard.scan_directory(args.path)
        
        critical_count = sum(1 for c in conflicts if c.severity == "CRITICAL")
        high_count = sum(1 for c in conflicts if c.severity == "HIGH")

        print(f"[SEMANTIC-MERGE-GUARD] Scanned Path: {args.path}")
        print(f"[SEMANTIC-MERGE-GUARD] Total Conflicts Detected: {len(conflicts)} (Critical: {critical_count}, High: {high_count})")

        for c in conflicts:
            print(f"\n  🚨 [{c.severity}] {c.kind}: {c.target_name}")
            print(f"     Location: {c.caller_file}:{c.caller_line}")
            print(f"     Problem:  {c.message}")
            print(f"     Fix:      {c.remediation}")

        print(LicenseManager.get_remediation_footer())

        has_failure = critical_count > 0 or (args.fail_on_warning and high_count > 0)
        if has_failure:
            print(f"\n❌ [SEMANTIC-MERGE-GUARD] FAILED: {len(conflicts)} silent semantic conflict(s) detected! Git clean-merge blocked.")
            return 1
        
        print("\n✅ [SEMANTIC-MERGE-GUARD] PASSED: No cross-file AST semantic conflicts found.")
        return 0

    return 0

if __name__ == "__main__":
    sys.exit(main())
