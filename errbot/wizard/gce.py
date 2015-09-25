import webbrowser
import httplib2
import os
from urllib.parse import parse_qsl
from oauth2client import client
from googleapiclient.discovery import build
from http.server import HTTPServer, BaseHTTPRequestHandler

class AuthHandler(BaseHTTPRequestHandler):
  def do_GET(self):
    self.send_response(200)
    self.send_header("Content-type", "text/html")
    self.end_headers()
    query = self.path.split('?', 1)[-1]
    query = dict(parse_qsl(query))
    if 'error' in query:
      sys.exit('Authentication request was rejected.')
    if 'code' in query:
      global code
      code = query['code']
    self.server.query_params = query
    self.wfile.write(b"<html><head><title>Authentication Status</title></head>")
    self.wfile.write(b"<body><p>The authentication flow has completed.</p>")
    self.wfile.write(b"</body></html>")

  def log_message(self, format, *args):
    """Do not log messages to stdout while running as command line program."""

class API(object):
  def __init__(self, project):
    self.project = project
    self.env = dict(os.environ)

  def auth(self):
    httpd = HTTPServer(('localhost', 8080), AuthHandler)
    flow = client.flow_from_clientsecrets('application_default_credentials.json',
                                          scope='https://www.googleapis.com/auth/compute',
                                          redirect_uri='http://localhost:8080')
    auth_uri = flow.step1_get_authorize_url()
    webbrowser.open_new(auth_uri)
    httpd.handle_request()
    credentials = flow.step2_exchange(code)
    self.compute = build('compute', 'v1', credentials=credentials)

  def get_regions(self):
    regions = self.compute.zones().list(project=self.project).execute()['items']
    return [region['name'] for region in regions]
