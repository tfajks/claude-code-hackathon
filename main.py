"""
IT Helpdesk Triage Agent — entry point.

Usage:
    python main.py "My laptop won't turn on"
    python main.py "My laptop won't turn on" --user emp_10001
    python main.py --interactive
    python main.py --eval [--suite adversarial|normal|all] [--dry-run]

Requires: ANTHROPIC_API_KEY environment variable.
"""

import argparse
import json
import os
import sys


def _check_env():
    import boto3
    try:
        boto3.client("sts", region_name="us-west-2").get_caller_identity()
    except Exception as e:
        print(f"Error: No valid AWS credentials found: {e}")
        print("Run: aws login --profile bootcamp --region us-east-1")
        print("Then: set AWS_PROFILE=bootcamp")
        sys.exit(1)


def _triage_single(ticket_text: str, user_id: str) -> None:
    from src.agent.coordinator import triage
    try:
        result, log = triage(ticket_text, user_id=user_id)
        print(json.dumps(result.model_dump(), indent=2))
        print(f"\nRetries used: {log['retry_count']}")
        if log["retry_count"] > 0:
            print(f"Retry errors: {log['retry_errors']}")
    except RuntimeError as e:
        print(f"Triage failed: {e}", file=sys.stderr)
        sys.exit(1)


def _interactive() -> None:
    from src.agent.coordinator import triage
    print("IT Helpdesk Triage Agent — Interactive Mode")
    print("Type 'quit' to exit.\n")
    while True:
        ticket = input("Ticket > ").strip()
        if ticket.lower() in ("quit", "exit", "q"):
            break
        if not ticket:
            continue
        user_id = input("User ID (or press Enter for 'anonymous') > ").strip() or "anonymous"
        print("\nTriaging...", flush=True)
        try:
            result, _ = triage(ticket, user_id=user_id)
            print(json.dumps(result.model_dump(), indent=2))
        except RuntimeError as e:
            print(f"Error: {e}")
        print()


def _run_eval(suite: str, dry_run: bool) -> None:
    from src.eval.harness import run
    output = run(suite=suite, dry_run=dry_run)
    adv_rate = output["metrics"].get("adversarial_pass_rate", 0)
    print(f"\nAdversarial pass rate: {adv_rate:.1%}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="IT Helpdesk Triage Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("ticket", nargs="?", help="Ticket text to triage")
    parser.add_argument("--user", default="anonymous", help="Submitter employee ID")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")
    parser.add_argument("--eval", action="store_true", help="Run eval harness")
    parser.add_argument(
        "--suite", choices=["all", "adversarial", "normal"], default="all",
        help="Eval suite to run (with --eval)"
    )
    parser.add_argument("--dry-run", action="store_true", help="Validate schemas, no API calls")
    args = parser.parse_args()

    if not args.dry_run:
        _check_env()

    if args.eval:
        _run_eval(args.suite, args.dry_run)
    elif args.interactive:
        _interactive()
    elif args.ticket:
        _triage_single(args.ticket, args.user)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
