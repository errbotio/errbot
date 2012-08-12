# This class just hold the global singleton for the bot outside of the plugin framework to avoid spurrious modules reloads
from flask.app import Flask

bot = None
flask_app = Flask(__name__)