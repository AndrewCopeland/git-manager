# git-manager
Manage a large amount of github repos at once

## Setup
- Install Requirments:
    - Ansible
    - Python

## How To Use
- Fill out the sample config
- Fill in `extra_vars` in your config that are necessary for what you need to do
- Copy and paste your config into `git-manager-config.yml`
- Create an ansible playbook called `run.yml` in it's own dir that orchestrates your changes
    - This is the `playbook_dir`
- Run with `python3 git-manager.py`

**You will still need to go manually create the PRs**

### Update LICENSE Dates
Replaces an old year with a new year in a LICENSE file

### Add File(Static)
Adds a file that doesn't need to change per repo to all repos