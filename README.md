# GitHub User Activity CLI

## Overview

This project is a command-line interface (CLI) tool that fetches and displays recent GitHub user activity. It's designed for backend learning purposes and is based on a project idea from [roadmap.sh](https://roadmap.sh/projects/github-user-activity).

## Features

- Fetch recent activity for a specified GitHub user
- Display activity in a user-friendly format in the terminal
- Summarize different types of events (Push, Pull Request, Watch, Issues)

## Screenshots

<details>
  <summary>Click to see all activities</summary>
  
  ![All Activities](/docs/all_activities.png)
</details>

<details>
  <summary>Click to see push activities</summary>
  
  ![Push Activities](/docs/push_activities.png)
</details>

<details>
  <summary>Click to see pull request activities</summary>
  
  ![Pull Request Activities](/docs/pull_activities.png)
</details>

<details>
  <summary>Click to see issue activities</summary>
  
  ![Issue Activities](/docs/issues_activities.png)
</details>

<details>
  <summary>Click to see fork activities</summary>
  
  ![Fork Activities](/docs/fork_activities.png)
</details>

<details>
  <summary>Click to see create activities</summary>
  
  ![Create Activities](/docs/create_activities.png)
</details>

## Installation

1. Ensure you have Python 3 installed on your system.
2. Clone this repository:
   ```
   git clone https://github.com/TheMasshiro/github-user-activity-cli.git
   ```
3. Navigate to the project directory:
   ```
   cd github-user-activity-cli
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

```
./github-activity octocat pull
```

The pull event will display the recent pull activities of the specified user.

For more information, use help:

```
./github-activity -h
```

## Contributing

This is a learning project, but contributions and suggestions are welcome. Please feel free to fork the repository and submit pull requests.

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## Acknowledgements

- This project idea is inspired by [roadmap.sh](https://roadmap.sh/projects/github-user-activity)
- Uses the GitHub API to fetch user activity data

## TODO

- Better sorting and handling of the github api response
- PRACTICE MORE
