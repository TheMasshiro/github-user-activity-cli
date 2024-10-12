# GitHub Activity CLI

## Overview

This project is a command-line interface (CLI) tool that fetches and displays recent GitHub user activity. It's designed for backend learning purposes and is based on a project idea from [roadmap.sh](https://roadmap.sh/projects/github-user-activity).

## Features

- Fetch recent activity for a specified GitHub user
- Display activity in a user-friendly format in the terminal
- Summarize different types of events (Push, Pull Request, Watch, Issues)

## Installation

1. Ensure you have Python 3 installed on your system.
2. Clone this repository:
   ```
   git clone https://github.com/TheMasshiro/github-activity-cli.git
   ```
3. Navigate to the project directory:
   ```
   cd github-activity-cli
   ```

## Usage

Run the script from the command line, providing a GitHub username as an argument:

```
./github-activity <username>
```

For example:

```
./github-activity octocat
```

The script will display the recent activities of the specified user.

## Technologies Used

- Python 3
- Standard Library modules:
  - `argparse` for parsing command-line arguments
  - `http.client` for making HTTP requests
  - `json` for parsing JSON responses
  - `socket` for network communication and checking internet connection
  - `sys` for interacting with the Python interpreter and handling command-line arguments
  - `datetime` for working with dates and times (e.g., timestamps)
  - `typing.List` for type hinting, specifically when working with lists

## Contributing

This is a learning project, but contributions and suggestions are welcome. Please feel free to fork the repository and submit pull requests.

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## Acknowledgements

- This project idea is inspired by [roadmap.sh](https://roadmap.sh/projects/github-user-activity)
- Uses the GitHub API to fetch user activity data

## TODO

- Pagination for when the output is long
- Better sorting and handling of the github api response
- PRACTICE MORE
