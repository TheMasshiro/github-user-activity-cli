import argparse
import http.client
import json
import os
import socket
import sys
import termios
import tty
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any


class AbstractAPI(ABC):
    @abstractmethod
    def check_internet(self, host: str, port: int) -> bool:
        pass

    @abstractmethod
    def get_content(self, endpoint: str, username: str | None = None):
        pass


class APIEndpoint(AbstractAPI):
    def check_internet(self, host: str = "8.8.8.8", port: int = 53) -> bool:
        try:
            socket.setdefaulttimeout(5)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
            return True
        except (socket.timeout, socket.error):
            return False

    def get_content(
        self,
        endpoint: str,
        username: str | None = None,
    ):
        if not self.check_internet():
            print(
                "Error: Unable to connect to GitHub\nPlease check your network connection\n"
            )
            sys.exit(1)

        try:
            host = "api.github.com"
            conn = http.client.HTTPSConnection(host)

            conn.request(
                "GET",
                endpoint,
                headers={
                    "Host": host,
                    "User-Agent": username if username else "github-activity-cli",
                    "Accept": "application/vnd.github.v3+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            )

            response = conn.getresponse()

            data = response.read()
            parsed_data = json.loads(data.decode("utf-8"))

            return parsed_data

        except json.JSONDecodeError:
            print("Error: Unable to parse GitHub response\nPlease try again\n")
            sys.exit(1)

        except http.client.HTTPException:
            print(
                "Error: Unable to connect to GitHub\nPlease check your network connection\n"
            )
            sys.exit(1)


class RateLimit:
    def __init__(self, api_endpoint: APIEndpoint):
        self.api_endpoint = api_endpoint

    def __response(self, endpoint: str = "/rate_limit"):
        return self.api_endpoint.get_content(endpoint)

    def __get_time(self, github_timestamp: int):
        github_dt = datetime.fromtimestamp(github_timestamp, tz=timezone.utc)
        local_tz = datetime.now(timezone.utc).astimezone().tzinfo
        local_dt = github_dt.astimezone(local_tz)

        return local_dt

    def handle_api_limit(self):
        remaining_limit = 0

        try:
            rate = self.__response()
            if not rate:
                print("Error: API request limit data not found")
                sys.exit(1)

            rate_info = rate.get("rate", dict)

            remaining = rate_info.get("remaining")
            remaining_limit = int(remaining)

        except KeyError:
            print("Error: Invalid API response structure\n")
            sys.exit(1)
        except ValueError:
            print("Error: Failed to process API response\n")
            sys.exit(1)

        return remaining_limit

    def api_limit_message(self):
        try:
            rate = self.__response()
            if not rate:
                print("Error: API request limit data not found")
                sys.exit(1)

            rate_info = rate.get("rate", dict)
            if not rate_info:
                print("Error: API request limit data not found\n")
                sys.exit(1)

            used = rate_info.get("used")
            remaining = rate_info.get("remaining")
            limit = rate_info.get("limit")
            reset_timestamp = rate_info.get("reset")

            reset_time = ""
            if reset_timestamp is not None:
                reset_time = "Unknown reset time"

            reset_time = self.__get_time(reset_timestamp).strftime(
                "%I:%M:%S %p | %B %d, %Y"
            )

            print("Overall API Request Usage:")
            print(f"  Used:        {used}")
            print(f"  Usage:       {remaining}/{limit}")
            print(f"  Reset at:    {reset_time}")
            if 1 <= remaining <= 5:
                print(f"Warning: You only have {remaining} requests left\n")

        except KeyError:
            print("Error: Invalid API response structure\n")
            sys.exit(1)
        except ValueError:
            print("Error: Failed to process API response\n")
            sys.exit(1)


class UserActivity:
    def __init__(self, username: str, api_endpoint: APIEndpoint, rate: RateLimit):
        self.username = username
        self.api_endpoint = api_endpoint
        self.rate = rate

    def __response(self, endpoint: str | None = None):
        endpoint = f"/users/{self.username}/events"
        if self.rate.handle_api_limit() < 1:
            print(
                "Error: API request limit exceeded. Please wait and try again later\nRun --usage or -u to check the time remaining until your request limit resets\n"
            )
            sys.exit(1)
        return self.api_endpoint.get_content(endpoint, self.username)

    def handle_event(self, event_type: str | None = None):
        if event_type is None:
            return "NoEvent"

        event_type = event_type.lower()
        github_events = {
            "push": "PushEvent",
            "pull": "PullRequestEvent",
            "star": "WatchEvent",
            "issues": "IssuesEvent",
            "fork": "ForkEvent",
            "delete": "DeleteEvent",
            "comment": "IssueCommentEvent",
            "create": "CreateEvent",
        }

        for key, value in github_events.items():
            if event_type == key:
                return value

        if event_type not in github_events:
            return "NoEvent"

        return None

    def event_message(
        self,
        event_type: str,
        commit_size: int,
        repo_name: str,
        ref: dict[str, dict[str, str]] | None = None,
    ):
        github_messages = {
            "PushEvent": f"- Pushed {commit_size} commit{'' if commit_size == 1 else 's'} to {repo_name}",
            "PullRequestEvent": f"- Opened a pull request in {repo_name}",
            "WatchEvent": f"- Starred {repo_name}",
            "IssuesEvent": f"- Opened a new issue in {repo_name}",
            "ForkEvent": f"- Forked {repo_name}",
            "IssueCommentEvent": f"- Commented on an issue in {repo_name}",
        }

        for event, message in github_messages.items():
            if event_type == event:
                return message

        if ref is None:
            return ""

        for event, ref_info in ref.items():
            if event != event_type:
                continue

            for event, ref_info in ref.items():
                if event != event_type or event not in ["CreateEvent", "DeleteEvent"]:
                    continue

                for ref_name, ref_type in ref_info.items():
                    if ref_type == "repository":
                        return f"- Created a new repository {repo_name}"
                    elif ref_type == "branch":
                        event_action = (
                            "Created a new" if event == "CreateEvent" else "Deleted a"
                        )
                        return f"- {event_action} branch {ref_name}"

        return ""

    def paginate_response(self, user_response: list, items_per_page: int = 20):
        if not user_response:
            sys.exit(1)

        total_items = len(user_response)
        total_pages = (total_items + items_per_page - 1) // items_per_page
        current_page = 1

        def getchar():
            fd = sys.stdin.fileno()
            attr = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                return sys.stdin.read(1)
            finally:
                termios.tcsetattr(fd, termios.TCSANOW, attr)

        while True:
            os.system("clear")
            start = (current_page - 1) * items_per_page
            end = start + items_per_page
            page_items = user_response[start:end]

            print(f"\nPage {current_page} of {total_pages}")
            print("----------------------------------")
            if current_page == 1:
                print()

            for item in page_items:
                print(item)
            print(
                f"\nShowing items {start + 1}-{min(end, total_items)} of {total_items}"
            )
            print("----------------------------------")

            if current_page == 1 and current_page == total_pages:
                print("Only one page. Exiting...")
                sys.exit(1)
            elif current_page == 1:
                print("Enter 'n' for next page or 'q' to quit.")
            elif current_page == total_pages:
                print("Enter 'p' for previous page or 'q' to quit.")
            else:
                print("Enter 'n' for next, 'p' for previous, or 'q' to quit.")

            choice = getchar().lower()
            if choice == "q":
                print("Exiting...")
                break
            elif choice == "n" and current_page < total_pages:
                current_page += 1
            elif choice == "p" and current_page > 1:
                current_page -= 1

    def handle_response(
        self, parser: argparse.ArgumentParser, user_event: str | None = None
    ):
        grouped_events = {}
        event_ref: dict[Any, Any] = {}

        responses = self.__response()
        if not responses:
            print("Error: No data received\n")
            sys.exit(1)

        if isinstance(responses, dict) and (
            responses.get("status") == "404" or responses.get("message") == "Not Found"
        ):
            print("Error: Account not found\n")
            sys.exit(1)

        for response in responses:
            event_type = response.get("type")
            event_date = response.get("created_at")
            repo_name = response.get("repo", {}).get("name")
            payload_size = response.get("payload", {}).get("size")
            payload_ref_type = response.get("payload", {}).get("ref_type")
            payload_ref = response.get("payload", {}).get("ref")
            pull_request = response.get("payload", {}).get("pull_request", {}).get("id")

            if not repo_name or not event_date:
                continue

            github_date = datetime.strptime(event_date, "%Y-%m-%dT%H:%M:%SZ")
            format_date = github_date.strftime("%B %d, %Y")

            if payload_size is None or pull_request is not None:
                payload_size = 1

            key = (format_date, repo_name)
            if key not in grouped_events:
                grouped_events[key] = {
                    "PushEvent": 0,
                    "PullRequestEvent": 0,
                    "IssuesEvent": 0,
                    "WatchEvent": 0,
                    "ForkEvent": 0,
                    "DeleteEvent": 0,
                    "IssueCommentEvent": 0,
                    "CreateEvent": 0,
                }

            grouped_events[key][event_type] += payload_size

            if event_type in ["CreateEvent", "DeleteEvent"]:
                if key not in event_ref:
                    event_ref[key] = {}
                if event_type not in event_ref[key]:
                    event_ref[key][event_type] = {}
                event_ref[key][event_type] = {payload_ref: payload_ref_type}

        filtered_event = self.handle_event(user_event) if user_event else None
        format_messages: dict[Any, Any] = {}

        for (date, repo), events in grouped_events.items():
            for event, commit_size in events.items():
                if filtered_event != "NoEvent":
                    event_ref_key = (date, repo) if (date, repo) in event_ref else None
                    messages = self.event_message(
                        event, commit_size, repo, event_ref.get(event_ref_key)
                    )

                    if (
                        (event == filtered_event) or (filtered_event is None)
                    ) and commit_size > 0:
                        if messages:
                            format_messages.setdefault(date, []).append(f"{messages}")

        if filtered_event == "NoEvent":
            print(f"Error: '{user_event}' is an invalid event type")
            if parser:
                parser.print_help()
            sys.exit(1)

        output_messages = []
        for date, messages in format_messages.items():
            output_messages.append(date)
            output_messages.extend(messages)
            output_messages.append("")

        return output_messages
