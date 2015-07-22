import logging
import os
from jinja2 import Environment, FileSystemLoader
from bottle import TEMPLATE_PATH

log = logging.getLogger(__name__)


def make_templates_path(root):
    return root + os.sep + 'templates'


system_templates_path = make_templates_path(os.path.dirname(__file__))
template_path = [system_templates_path]
TEMPLATE_PATH.insert(0, system_templates_path)  # for views
env = Environment(loader=FileSystemLoader(template_path),
                  trim_blocks=True,
                  keep_trailing_newline=False)


def tenv():
    return env


def make_templates_from_plugin_path(plugin_path):
    return make_templates_path(os.sep.join(plugin_path.split(os.sep)[:-1]))


def add_plugin_templates_path(path):
    global env
    tmpl_path = make_templates_from_plugin_path(path)
    if os.path.exists(tmpl_path):
        log.debug("Templates directory found for this plugin [%s]" % tmpl_path)
        template_path.append(tmpl_path)  # for webhooks
        TEMPLATE_PATH.insert(0, tmpl_path)  # for webviews
        # Ditch and recreate a new templating environment
        env = Environment(loader=FileSystemLoader(template_path))
        return
    log.debug("No templates directory found for this plugin [Looking for %s]" % tmpl_path)


def remove_plugin_templates_path(path):
    global env
    tmpl_path = make_templates_from_plugin_path(path)
    if tmpl_path in template_path:
        template_path.remove(tmpl_path)  # for webhooks
        TEMPLATE_PATH.remove(tmpl_path)  # for webviews
        # Ditch and recreate a new templating environment
        env = Environment(loader=FileSystemLoader(template_path))
