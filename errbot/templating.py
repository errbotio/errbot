import logging
from pathlib import Path

from jinja2 import ChoiceLoader, Environment, FileSystemLoader, PrefixLoader

from errbot.plugin_info import PluginInfo

log = logging.getLogger(__name__)


def make_templates_path(root: Path) -> Path:
    return root / "templates"


system_templates_path = str(make_templates_path(Path(__file__).parent))
template_path = [system_templates_path]
plugin_templates = {}  # plugin_name -> FileSystemLoader


def _recreate_env():
    global env
    loaders = []
    if plugin_templates:
        loaders.append(PrefixLoader(plugin_templates))
    loaders.append(FileSystemLoader(template_path))

    env = Environment(
        loader=ChoiceLoader(loaders),
        trim_blocks=True,
        keep_trailing_newline=False,
        autoescape=True,
    )


_recreate_env()


def tenv() -> Environment:
    return env


def add_plugin_templates_path(plugin_info: PluginInfo) -> None:
    tmpl_path = make_templates_path(plugin_info.location.parent)
    if tmpl_path.exists():
        log.debug(
            "Templates directory found for %s plugin [%s]", plugin_info.name, tmpl_path
        )
        template_path.append(str(tmpl_path))  # for webhooks
        plugin_templates[plugin_info.name] = FileSystemLoader(str(tmpl_path))

        # Ditch and recreate a new templating environment
        _recreate_env()
        return
    log.debug(
        "No templates directory found for %s plugin in [%s]",
        plugin_info.name,
        tmpl_path,
    )


def remove_plugin_templates_path(plugin_info: PluginInfo) -> None:
    tmpl_path = str(make_templates_path(plugin_info.location.parent))
    changed = False
    if tmpl_path in template_path:
        template_path.remove(tmpl_path)
        changed = True

    if plugin_info.name in plugin_templates:
        del plugin_templates[plugin_info.name]
        changed = True

    if changed:
        # Ditch and recreate a new templating environment
        _recreate_env()
