# This is a list of known public repos for err
# Feel free to make a pull request to add yours !
import urllib.request
import ast


def get_known_repos():
    '''
    Get known repos from registry

    An example entry of the json file is the following
    'errbotio/err-pypi': {
        'avatar_url': None,
        'documentation': 'some commands to query pypi',
        'path': 'https://github.com/errbotio/err-pypi.git',
        'python': None
    }, ...
    '''
    registry = urllib.request.urlopen('https://gist.githubusercontent.com/sijis/95ac411600f085818f22/raw/84ef97b1fbc5c00ebf46c1558d6fd83c07091e6a/repos.json').read()
    return ast.literal_eval(registry.decode('utf-8'))

KNOWN_PUBLIC_REPOS = get_known_repos()
