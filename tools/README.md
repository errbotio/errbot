# Project Tool

These are support tools for the project

`./plugin-gen.py`

- Generates `repos.json`, which has a list of available plugins
- It will also update a `blacklisted.txt` file of false positive on the initial research to optimize subsequent ones.
- Takes a while with the API rate limit.

`./gen_home.py`

- Generates a Github wiki compatible page named `Home.md` with all the plugins using `repos.json`
