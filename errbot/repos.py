import requests

API_ENDPOINT = 'http://api.fizz-buzz-314.appspot.com/api/v1/plugins'
# API_ENDPOINT = 'http://localhost:8081/api/v1/plugins' # use that for
# local test


def get_public_repos():
  """ This will fetch the list of repos from our public list. """
  return requests.get(API_ENDPOINT).json()
