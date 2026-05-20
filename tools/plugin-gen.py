#!/usr/bin/env python3
import configparser
import json
import logging
import os
import pathlib
import signal
import sys
import time
from datetime import datetime
from typing import Any, Dict, Optional, Set

import requests
from requests.auth import HTTPBasicAuth

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
log = logging.getLogger(__name__)

DEFAULT_AVATAR = "https://upload.wikimedia.org/wikipedia/commons/5/5f/Err-logo.png"


class CatalogGenerator:
    """
    Generates a plugin catalog by searching GitHub for Errbot plugins.
    Uses Global Code Search and batched processing where supported.
    """

    def __init__(self, tools_dir: pathlib.Path):
        self.tools_dir = tools_dir
        self.repos_json_path = tools_dir / "repos.json"
        self.processed_path = tools_dir / "processed_repos.json"
        self.blocklist_path = tools_dir / "blocklist.txt"
        self.extras_path = tools_dir / "extras.txt"
        self.token_path = tools_dir / "token"

        self.auth = self._get_auth()
        self.session = requests.Session()
        self.session.auth = self.auth

        # State management
        self.plugins = self._load_json(self.repos_json_path, {})
        self.processed_repos = set(self._load_json(self.processed_path, []))
        self.blocklist = self._load_blocklist()

        # Cache for repo metadata to avoid redundant requests
        self.repo_metadata_cache = {}

        log.info(f"Loaded {len(self.plugins)} repositories from {self.repos_json_path}")
        log.info(f"Loaded {len(self.blocklist)} blocklist repositories")

        self.interrupted = False
        signal.signal(signal.SIGINT, self._handle_interrupt)
        signal.signal(signal.SIGTERM, self._handle_interrupt)

    def _handle_interrupt(self, signum, frame):
        log.warning("Interrupt received, saving state and exiting...")
        self.interrupted = True

    def _get_auth(self) -> HTTPBasicAuth:
        """Retrieve GitHub authentication credentials."""
        token_env = os.getenv("ERRBOT_REPOS_TOKEN")
        token_info = None

        if self.token_path.is_file():
            try:
                token_info = self.token_path.read_text().strip()
            except Exception as e:
                log.fatal(f"Token file cannot be read: {e}")
                sys.exit(-1)
        elif token_env:
            token_info = token_env
        else:
            log.fatal(
                "No 'token' file or environment variable 'ERRBOT_REPOS_TOKEN' found."
            )
            sys.exit(-1)

        try:
            user, token = token_info.split(":", 1)
            return HTTPBasicAuth(user, token)
        except ValueError:
            log.fatal("Token should be of the form username:token")
            sys.exit(-1)

    def _load_json(self, path: pathlib.Path, default: Any) -> Any:
        """Load data from a JSON file."""
        if path.exists():
            try:
                with open(path, "r") as f:
                    return json.load(f)
            except Exception as e:
                log.error(f"Failed to load {path}: {e}")
        return default

    def _load_blocklist(self) -> Set[str]:
        """Load blocklist repositories from file."""
        if self.blocklist_path.exists():
            with open(self.blocklist_path, "r") as f:
                return {line.strip() for line in f if line.strip()}
        return set()

    def _save_state(self):
        """Persist the current state to disk."""
        log.info("Saving state...")
        try:
            # Sort plugins by repo name for consistency in file
            sorted_plugins = dict(sorted(self.plugins.items()))
            with open(self.repos_json_path, "w") as f:
                json.dump(sorted_plugins, f, indent=2, separators=(",", ": "))
            with open(self.processed_path, "w") as f:
                json.dump(sorted(list(self.processed_repos)), f, indent=2)
        except Exception as e:
            log.error(f"Failed to save state: {e}")

    def add_to_blocklist(self, repo_name: str):
        """Add a repository to the blocklist and persist it."""
        if repo_name not in self.blocklist:
            self.blocklist.add(repo_name)
            try:
                with open(self.blocklist_path, "a") as f:
                    f.write(repo_name + "\n")
            except Exception as e:
                log.error(f"Failed to update blocklist file: {e}")

    def rate_limit(self, resp: requests.Response):
        """Wait if GitHub API rate limit is reached."""
        if resp.status_code == 403 and "rate limit exceeded" in resp.text.lower():
            log.warning("Rate limit hit. Waiting 60s...")
            time.sleep(60)
            return

        if "X-RateLimit-Remaining" not in resp.headers:
            return

        remain = int(resp.headers["X-RateLimit-Remaining"])
        limit = int(resp.headers["X-RateLimit-Limit"])

        if remain > 1:
            return

        reset = int(resp.headers["X-RateLimit-Reset"])
        ts = datetime.fromtimestamp(reset)
        delay = (ts - datetime.now()).total_seconds()

        log.warning(f"Hit rate limit ({remain}/{limit}). Waiting {delay:.1f} seconds...")
        if delay < 0:
            delay = 2
        time.sleep(delay)

    def get_repo_metadata(self, repo_name: str) -> Optional[Dict[str, Any]]:
        """Fetch repository metadata using Core API."""
        if repo_name in self.repo_metadata_cache:
            return self.repo_metadata_cache[repo_name]

        log.debug(f"Fetching metadata for {repo_name}...")
        resp = self.session.get(f"https://api.github.com/repos/{repo_name}")
        self.rate_limit(resp)

        if resp.status_code == 200:
            metadata = resp.json()
            self.repo_metadata_cache[repo_name] = metadata
            return metadata
        elif resp.status_code == 404:
            log.error(f"Repo {repo_name} not found")
            return None
        else:
            log.error(f"Error fetching metadata for {repo_name}: {resp.status_code}")
            return None

    def _calculate_score(self, repo: Dict[str, Any]) -> float:
        """Calculate a popularity/activity score for a repository."""
        updated_at_str = repo.get("updated_at", "2000-01-01T00:00:00Z")
        updated_at = datetime.strptime(updated_at_str, "%Y-%m-%dT%H:%M:%SZ")
        days_old = (datetime.now() - updated_at).days

        # Formula: Stars + (Watchers * 2) + Forks - (Days Old / 30)
        score = (
            repo.get("stargazers_count", 0)
            + repo.get("watchers_count", 0) * 2
            + repo.get("forks_count", 0)
            - (days_old / 30.0)
        )
        return float(f"{score:.2f}")

    def process_plug_file(self, item: Dict[str, Any], progress_info: str = ""):
        """Process a single .plug file found in search."""
        repo_name = item["repository"]["full_name"]

        if repo_name in self.blocklist:
            return

        log.info(f"{progress_info} Processing {item['path']} in {repo_name}")

        default_branch = item["repository"].get("default_branch")
        if not default_branch:
            # If not in search item, we need to fetch it once per repo
            repo_meta = self.get_repo_metadata(repo_name)
            default_branch = repo_meta.get("default_branch", "master") if repo_meta else "master"

        raw_url = f"https://raw.githubusercontent.com/{repo_name}/{default_branch}/{item['path']}"
        plugfile_resp = self.session.get(raw_url)

        if plugfile_resp.status_code != 200:
            log.error(f"Failed to fetch {raw_url}")
            return

        parser = configparser.ConfigParser()
        try:
            parser.read_string(plugfile_resp.text)
            if "Core" not in parser or "Name" not in parser["Core"]:
                return

            name = parser["Core"]["Name"]
            doc = parser.get("Documentation", "Description", fallback="")
            python = parser.get("Python", "Version", fallback="2")

            # Get repo metadata for scoring
            repo = self.get_repo_metadata(repo_name)
            if not repo:
                return

            avatar_url = repo.get("owner", {}).get("avatar_url", DEFAULT_AVATAR)
            score = self._calculate_score(repo)

            plugin = {
                "path": item["path"],
                "repo": repo["html_url"],
                "documentation": doc,
                "name": name,
                "python": python,
                "avatar_url": avatar_url,
                "score": score,
            }

            repo_entry = self.plugins.get(repo_name, {})
            repo_entry[name] = plugin
            self.plugins[repo_name] = repo_entry
            log.debug(f"Cataloged plugin '{name}' from {repo_name}")

            # Mark repo as processed so Phase 2 skips it
            self.processed_repos.add(repo_name)

        except Exception as e:
            log.error(f"Invalid plug file {item['path']} in {repo_name}: {e}")

    def global_search(self):
        """Find all .plug files globally that mention 'err' or 'errbot'."""
        search_url = "https://api.github.com/search/code"
        # Let requests handle the encoding of spaces and special chars
        params = {"q": "extension:plug err OR errbot"}
        
        processed_count = 0
        total_count = -1

        while search_url and not self.interrupted:
            resp = self.session.get(search_url, params=params)
            self.rate_limit(resp)

            if resp.status_code != 200:
                log.error(f"Phase 1 Search failed: {resp.status_code}")
                log.error(f"Response: {resp.text}")
                break

            data = resp.json()
            if total_count == -1:
                total_count = data.get("total_count", 0)
                log.info(f"Phase 1: Global search found {total_count} potential plugins.")

            items = data.get("items", [])
            for item in items:
                if self.interrupted:
                    break
                processed_count += 1
                progress = f"[Phase 1/2] [File {processed_count}/{total_count}]"
                self.process_plug_file(item, progress)

            if self.interrupted:
                break

            # Save state after each page
            self._save_state()

            search_url = resp.links.get("next", {}).get("url")
            # Clear params for next pages as they are already in the 'next' URL
            params = None
            if search_url:
                time.sleep(2)

    def process_extras(self):
        """Ensure specific repositories from extras.txt are included."""
        if not self.extras_path.exists():
            return

        with open(self.extras_path, "r") as f:
            all_extras = [line.strip() for line in f if line.strip()]

        pending_extras = [r for r in all_extras if r not in self.processed_repos]
        total_extras = len(all_extras)
        log.info(f"Phase 2: Processing {len(pending_extras)} pending repositories from extras.txt.")

        processed_so_far = total_extras - len(pending_extras)

        for repo_name in pending_extras:
            if self.interrupted:
                break

            processed_so_far += 1
            progress = f"[Phase 2/2] [Repo {processed_so_far}/{total_extras}]"
            
            log.info(f"{progress} Searching for plugins in {repo_name}...")
            
            search_url = "https://api.github.com/search/code"
            params = {"q": f"extension:plug repo:{repo_name}"}
            resp = self.session.get(search_url, params=params)
            self.rate_limit(resp)

            if resp.status_code == 200:
                data = resp.json()
                items = data.get("items", [])
                for item in items:
                    self.process_plug_file(item, progress)
                
                self.processed_repos.add(repo_name)
                # Save state frequently to ensure progress isn't lost
                if processed_so_far % 5 == 0:
                    self._save_state()
            elif resp.status_code == 422:
                # Often means repo is empty or issues searching it
                log.warning(f"{progress} Repo {repo_name} search returned 422, skipping.")
                log.debug(f"Response: {resp.text}")
                self.processed_repos.add(repo_name)
            else:
                log.error(f"{progress} Search failed for {repo_name}: {resp.status_code}")
                log.debug(f"Response: {resp.text}")
            
            # Mandatory 2s sleep to avoid hitting the 30 searches/minute limit
            time.sleep(2)

    def run(self):
        """Start the generation process."""
        log.info("Starting optimized plugin catalog generation...")

        # 1. Global search for .plug files
        self.global_search()

        # 2. Process extras
        if not self.interrupted:
            self.process_extras()

        self._save_state()
        if self.interrupted:
            log.info("Interrupted. State saved.")
        else:
            log.info("Finished successfully!")


if __name__ == "__main__":
    tools_dir = pathlib.Path(__file__).parent.resolve()
    generator = CatalogGenerator(tools_dir)
    generator.run()
