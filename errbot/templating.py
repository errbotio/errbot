import logging
import os
from errbot.plugin_info import PluginInfo
from jinja2 import Environment, FileSystemLoader
from pathlib import Path

log = logging.getLogger(__name__)


def make_templates_path(root: Path) -> Path:
    return root / 'templates'


system_templates_path = str(make_templates_path(Path(__file__).parent))
template_path = [system_templates_path]
env = Environment(loader=FileSystemLoader(template_path),
                  trim_blocks=True,
                  keep_trailing_newline=False,
                  autoescape=True)


def tenv():
    return env


def add_plugin_templates_path(plugin_info: PluginInfo):
    global env
    tmpl_path = make_templates_path(plugin_info.location.parent)
    if tmpl_path.exists():
        log.debug('Templates directory found for this plugin [%s]', tmpl_path)
        template_path.append(str(tmpl_path))  # for webhooks

        # Ditch and recreate a new templating environment
        env = Environment(loader=FileSystemLoader(template_path), autoescape=True)
        return
    log.debug('No templates directory found for this plugin [Looking for %s]', tmpl_path)


def remove_plugin_templates_path(plugin_info: PluginInfo):
    global env
    tmpl_path = str(make_templates_path(plugin_info.location.parent))
    if tmpl_path in template_path:
        template_path.remove(tmpl_path)
        # Ditch and recreate a new templating environment
        env = Environment(loader=FileSystemLoader(template_path), autoescape=True)
