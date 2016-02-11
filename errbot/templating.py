import logging
import os
from jinja2 import Environment, FileSystemLoader
from bottle import TEMPLATE_PATH

log = logging.getLogger(__name__)


def make_templates_path(root):
    return os.path.join(root, 'templates')


system_templates_path = make_templates_path(os.path.dirname(__file__))
TEMPLATE_PATH.insert(0, system_templates_path)  # for webviews


def make_templates_from_plugin_path(plugin_path):
    return make_templates_path(os.path.dirname(plugin_path))


def add_plugin_templates_path(path):
    tmpl_path = make_templates_from_plugin_path(path)
    if os.path.exists(tmpl_path):
        log.debug("Templates directory found for this plugin [{}]".format(tmpl_path))
        TEMPLATE_PATH.insert(0, tmpl_path)  # for webviews
        return Environment(loader=FileSystemLoader([system_templates_path, tmpl_path]))
    log.debug("No templates directory found for this plugin [Looking for {}]".format(tmpl_path))
    return Environment(loader=FileSystemLoader([system_templates_path]))

def remove_plugin_templates_path(path):
    tmpl_path = make_templates_from_plugin_path(path)
    if tmpl_path in TEMPLATE_PATH:
        TEMPLATE_PATH.remove(tmpl_path)  # for webviews
