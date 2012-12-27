# This class just hold the global singletons for the bot outside of the plugin framework to avoid spurrious modules reloads
import sys

if sys.version_info[0] < 3:
    from flask.app import Flask
    flask_app = Flask(__name__)
bot = None
