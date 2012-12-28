# This class just hold the global singletons for the bot outside of the plugin framework to avoid spurrious modules reloads

#if PY2:
#    from flask.app import Flask
#    flask_app = Flask(__name__)
bot = None
