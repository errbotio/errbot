import logging
import os
from jinja2 import Environment, FileSystemLoader
from bottle import TEMPLATE_PATH

log = logging.getLogger(__name__)

template_path = []


def make_templates_path(root):
    return os.path.join(root, 'templates')


def add_template_path(path):
    template_path.append(path)  # for webhooks
    TEMPLATE_PATH.insert(0, path)  # for views


system_templates_path = make_templates_path(os.path.dirname(__file__))
add_template_path(system_templates_path)
env = Environment(loader=FileSystemLoader(template_path),
                  trim_blocks=True,
                  keep_trailing_newline=False)


def tenv():
    return env


def make_templates_from_plugin_path(plugin_path):
    return make_templates_path(os.path.dirname(plugin_path))


def make_custom_template_path(plugin_name, config):
    if getattr(config, 'TEMPLATES_EXTRA_DIR', None):
        overridden = os.path.join(config.TEMPLATES_EXTRA_DIR, plugin_name)
        if os.path.exists(overridden):
            return overridden


def add_plugin_templates_path(path, plugin_name, config=None):
    global env
    tmpl_path = make_templates_from_plugin_path(path)
    if os.path.exists(tmpl_path):
        custom_path = make_custom_template_path(plugin_name, config)
        if custom_path:
            log.debug('Custom templates directory found for plugin %s [%s]' %
                      (plugin_name, custom_path))
            add_template_path(custom_path)
        log.debug("Templates directory found for this plugin [%s]" % tmpl_path)
        add_template_path(tmpl_path)
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
