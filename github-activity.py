import argparse
import sys

from github_activity_api import APIEndpoint, RateLimit, UserActivity


def main(argv: list[str]):
    api_endpoint = APIEndpoint()

    parser = argparse.ArgumentParser(
        prog="github-activity",
        usage="%(prog)s [options] [username] [event]",
        description=(
            "A command-line tool to retrieve and display GitHub user activity, "
            "including push events, pull requests, issues, and more. "
            "This tool is based on the Roadmap.sh Backend Project: https://roadmap.sh/projects/github-user-activity"
        ),
        add_help=False,
    )
    parser.add_argument("username", nargs="?", help="Github Username")
    parser.add_argument(
        "event",
        nargs="?",
        help="Event Type: push, pull, star, issues, fork, create, or leave empty for all activities",
    )
    parser.add_argument(
        "-u",
        "--usage",
        action="store_true",
        help="Check remaining requests",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version="%(prog)s 0.1.1",
        help="Print version",
    )
    parser.add_argument("-h", "--help", action="help", help="Print help")

    args = parser.parse_args()

    if len(argv) == 1:
        parser.print_help()
        sys.exit(1)

    rate = RateLimit(api_endpoint)
    if args.usage:
        if args.username:
            parser.print_help()
            sys.exit(1)

        rate.api_limit_message()
        sys.exit(0)

    if not args.username:
        parser.print_help()
        sys.exit(1)

    user = UserActivity(args.username, api_endpoint, rate)
    response = user.handle_response(parser, args.event)
    if not response:
        print(
            f"No activity found for the event {args.event if args.event else 'All'}\n",
        )
        sys.exit(1)
    user.paginate_response(response, event=args.event)

    remaining = rate.handle_api_limit()
    if 1 <= remaining <= 5:
        print(
            f"Warning: You only have {remaining} request{'s' if remaining != 1 else ''} left\n"
        )
    elif remaining < 1:
        print(
            "You have no requests remaining. Run --usage or -u to check the time until your request limit resets\n"
        )


if __name__ == "__main__":
    main(sys.argv)
