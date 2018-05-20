import sys

import inspect
from configparser import ConfigParser
from dataclasses import dataclass
from importlib._bootstrap import module_from_spec
from importlib._bootstrap_external import spec_from_file_location

from errbot.utils import version2tuple
from pathlib import Path
from typing import Tuple, List, Type
from configparser import Error as ConfigParserError

VersionType = Tuple[int, int, int]


@dataclass
class PluginInfo:
    name: str
    module: str
    doc: str
    core: bool
    python_version: VersionType
    errbot_minversion: VersionType
    errbot_maxversion: VersionType
    dependencies: List[str]
    location: Path = None

    @staticmethod
    def load(plugfile_path: Path) -> 'PluginInfo':
        with plugfile_path.open(encoding='utf-8') as plugfile:
            return PluginInfo.load_file(plugfile, plugfile_path)

    @staticmethod
    def load_file(plugfile, location: Path) -> 'PluginInfo':
        cp = ConfigParser()
        cp.read_file(plugfile)
        pi = PluginInfo.parse(cp)
        pi.location = location
        return pi

    @staticmethod
    def parse(config: ConfigParser) -> 'PluginInfo':
        """
        Throws ConfigParserError with a meaningful message if the ConfigParser doesn't contain the minimal
         information required.
        """
        name = config.get('Core', 'Name')
        module = config.get('Core', 'Module')
        core = config.get('Core', 'Core', fallback='false').lower() == 'true'
        doc = config.get('Documentation', 'Description', fallback=None)

        python_version = config.get('Python', 'Version', fallback=None)
        # Old format backward compatibility
        if python_version:
            if python_version in ('2+', '3'):
                python_version = (3, 0, 0)
            elif python_version == '2':
                python_version = (2, 0, 0)
            else:
                try:
                    python_version = tuple(version2tuple(python_version)[0:3])  # We can ignore the alpha/beta part.
                except ValueError as ve:
                    raise ConfigParserError(f'Invalid Python Version format: {python_version} ({ve})')

        min_version = config.get('Errbot', 'Min', fallback=None)
        max_version = config.get('Errbot', 'Max', fallback=None)
        try:
            if min_version:
                min_version = version2tuple(min_version)
        except ValueError as ve:
            raise ConfigParserError(f'Invalid Errbot min version format: {min_version} ({ve})')

        try:
            if max_version:
                max_version = version2tuple(max_version)
        except ValueError as ve:
            raise ConfigParserError(f'Invalid Errbot max version format: {max_version} ({ve})')
        depends_on = config.get('Core', 'DependsOn', fallback=None)
        deps = [name.strip() for name in depends_on.split(',')] if depends_on else []

        return PluginInfo(name, module, doc, core, python_version, min_version, max_version, deps)

    def load_plugin_classes(self, base_module_name: str, baseclass: Type):
        # load the module
        module_name = base_module_name + '.' + self.module
        spec = spec_from_file_location(module_name, self.location.parent / (self.module + '.py'))
        modu1e = module_from_spec(spec)
        spec.loader.exec_module(modu1e)
        sys.modules[module_name] = modu1e

        # introspect the modules to find plugin classes
        def is_plugin(member):
            return inspect.isclass(member) and issubclass(member, baseclass) and member != baseclass

        plugin_classes = inspect.getmembers(modu1e, is_plugin)
        return plugin_classes
