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

    def handle_error(self, message: str) -> Any:
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

    def handle_error(self, message: str) -> Any:
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

            print("Overall API Request Limit:")
            print(f"  Used:        {used}")
            print(f"  Usage:       {remaining}/{limit}")
            print(f"  Reset at:    {reset_time}")
            if remaining >= 1 and remaining <= 5:
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
                "Error: API request limit exceeded. Please wait and try again later\nRun --limit or -l to check the time remaining until your request limit resets\n"
            )
        return self.api_endpoint.get_content(endpoint, self.username)

    def handle_event(self, event_type: Optional[str] = None):
        if event_type is None:
            return "NoEvent"

        event_type = event_type.lower()
        event_list = ["push", "pull", "star", "issues"]

        if event_type == event_list[0]:
            return "PushEvent"
        elif event_type == event_list[1]:
            return "PullRequestEvent"
        elif event_type == event_list[2]:
            return "WatchEvent"
        elif event_type == event_list[3]:
            return "IssuesEvent"
        elif event_type not in event_list:
            return "NoEvent"

        return None

    def event_message(self, event: str, commit_count: int, repo_name: str):
        if event == "PushEvent":
            if commit_count == 1:
                return f"- Pushed {commit_count} commit to {repo_name}"
            return f"- Pushed {commit_count} commits to {repo_name}"
        elif event == "PullRequestEvent":
            return f"- Opened a pull request in {repo_name}"
        elif event == "WatchEvent":
            return f"- Starred {repo_name}"
        elif event == "IssuesEvent":
            return f"- Opened a new issue in {repo_name}"
        return ""

    def handle_response(self, parser, event: Optional[str] = None):
        repos = {}
        repo_dates = {}

        responses = self.__response()

        if isinstance(responses, dict) and (
            responses.get("status") == "404" or responses.get("message") == "Not Found"
        ):
            self.api_endpoint.handle_error("Error: Account not found\n")

        for response in responses:
            event_type = response.get("type")
            repo_name = response.get("repo", {}).get("name")
            event_date = response.get("created_at")

            if not repo_name:
                continue

            if repo_name not in repos:
                repos[repo_name] = {
                    "PushEvent": 0,
                    "PullRequestEvent": 0,
                    "IssuesEvent": 0,
                    "WatchEvent": 0,
                }
                repo_dates[repo_name] = event_date

            if event_type in repos[repo_name]:
                repos[repo_name][event_type] += 1

            if event_date > repo_dates[repo_name]:
                repo_dates[repo_name] = event_date

        filtered_event = self.handle_event(event) if event else None

        output_messages = []

        for repo_name, events in repos.items():
            date = datetime.strptime(repo_dates[repo_name], "%Y-%m-%dT%H:%M:%SZ")
            format_date = date.strftime("%B %d, %Y")

            for event_type, count in events.items():
                if filtered_event != "NoEvent":
                    event_msg = self.event_message(event_type, count, repo_name)

                    if (event_type == filtered_event and count > 0) or (
                        filtered_event is None and count > 0
                    ):
                        if event_msg:
                            output_messages.append(f"{event_msg}")
                            output_messages.append(f"  Latest activity: {format_date}")
                            output_messages.append("")

        if filtered_event == "NoEvent":
            print(f"Error: {event} is an invalid event type")
            if parser:
                parser.print_help()
            sys.exit(0)
        return output_messages
