import http.client
import json
import socket
import sys
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Optional


class AbstractAPI(ABC):
    @abstractmethod
    def check_internet(self):
        pass

    def handle_error(self, message: str):
        pass

    def get_content(self, endpoint: str, username: Optional[str] = None):
        pass


class APIEndpoint(AbstractAPI):
    def check_internet(self, host="8.8.8.8", port=53) -> bool:
        try:
            socket.setdefaulttimeout(5)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
            return True
        except (socket.timeout, socket.error):
            return False

    def handle_error(self, message: str):
        print(message)
        sys.exit(1)

    def get_content(
        self,
        endpoint: str,
        username: Optional[str] = None,
    ):
        if not self.check_internet():
            self.handle_error(
                "Error: Unable to connect to GitHub\nPlease check your network connection\n"
            )

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
            self.handle_error(
                "Error: Unable to parse GitHub response\nPlease try again\n"
            )

        except http.client.HTTPException:
            self.handle_error(
                "Error: Unable to connect to GitHub\nPlease check your network connection\n"
            )


class RateLimit:
    def __init__(self, api_endpoint: APIEndpoint):
        self.api_endpoint = api_endpoint

    def __response(self, endpoint="/rate_limit"):
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
                self.api_endpoint.handle_error(
                    "Error: API request limit data not found"
                )

            rate_info = rate.get("rate", {})
            remaining = rate_info.get("remaining")
            remaining_limit = int(remaining)

        except KeyError:
            self.api_endpoint.handle_error("Error: Invalid API response structure\n")
        except ValueError:
            self.api_endpoint.handle_error("Error: Failed to process API response\n")

        return remaining_limit

    def api_limit_message(self):
        try:
            rate = self.__response()
            rate_info = rate.get("rate", {})
            if not rate_info:
                self.api_endpoint.handle_error(
                    "Error: API request limit data not found\n"
                )
            used = rate_info.get("used")
            remaining = rate_info.get("remaining")
            limit = rate_info.get("limit")
            reset_timestamp = rate_info.get("reset")

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
            self.api_endpoint.handle_error("Error: Invalid API response structure\n")
        except ValueError:
            self.api_endpoint.handle_error("Error: Failed to process API response\n")


class UserActivity:
    def __init__(self, username, api_endpoint: APIEndpoint, rate: RateLimit):
        self.username = username
        self.api_endpoint = api_endpoint
        self.rate = rate

    def __response(self, endpoint=None):
        endpoint = f"/users/{self.username}/events"
        if self.rate.handle_api_limit() < 1:
            self.api_endpoint.handle_error(
                "Error: API request limit exceeded. Please wait and try again later\nRun --usage or -u to check the time remaining until your request limit resets\n"
            )
        return self.api_endpoint.get_content(endpoint, self.username)

    def handle_event(self, event_type: Optional[str] = None):
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
        ref: Optional[dict] = None,
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

    def handle_response(self, parser, user_event: Optional[str] = None):
        grouped_events = {}
        event_ref: dict[Any, Any] = {}

        responses = self.__response()
        if isinstance(responses, dict) and (
            responses.get("status") == "404" or responses.get("message") == "Not Found"
        ):
            self.api_endpoint.handle_error("Error: Account not found\n")

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
            sys.exit(0)

        output_messages = []
        for date, messages in format_messages.items():
            output_messages.append(date)
            output_messages.extend(messages)
            output_messages.append("")

        return output_messages
