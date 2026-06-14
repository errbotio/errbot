# Project Tool

These are support tools for the project

`./plugin-gen.py`

- Generates `repos.json`, which has a list of available plugins
- It will also update a `blocklist.txt` file of false positive on the initial research to optimize subsequent ones.
- Takes a while with the API rate limit.

`./gen_home.py`

- Generates a Github wiki compatible page named `Home.md` with all the plugins using `repos.json`

`./releases.sh`

- automates the release process for errbot.
- creates a temporary directory, clones the repository, builds the python package, and prepares multi-arch docker images.
- **Requirements:**
    - `git`
    - `pipenv`
    - `python 3.12`
    - `podman` (for docker image builds)
- **Execution (macOS):**
    1. **Pre-requisite:** Open `tools/releases.sh` and update the `RELEASE`, `BRANCH`, and `PYTHON_VERSION` variables to match the target release.
    2. Ensure you have the requirements installed (e.g., `brew install pipenv podman`).
    3. Make the script executable: `chmod +x tools/releases.sh`
    4. Run the script from the project root: `./tools/releases.sh`
    5. Follow the manual steps printed at the end of the script to complete the publication.
