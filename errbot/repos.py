import urllib.request
import ast


def get_known_repos():
    """
    Get known repos from registry

    An example entry of the json file is the following
    'errbotio/err-pypi': {
        'avatar_url': None,
        'documentation': 'some commands to query pypi',
        'path': 'https://github.com/errbotio/err-pypi.git',
        'python': None
    }, ...
    """
    registry_url = 'http://bit.ly/1kjdlRX'
    registry = urllib.request.urlopen(registry_url).read()
    return ast.literal_eval(registry.decode('utf-8'))

KNOWN_PUBLIC_REPOS = get_known_repos()
