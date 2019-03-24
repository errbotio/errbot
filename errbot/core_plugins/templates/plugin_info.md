#### Plugin info from {{ plugin_info.location }}
name: {{ plugin_info.name }}

module: {{ plugin_info.module }}

full_module_path: {{ plugin_info.location.parent / (plugin_info.module + '.py') }}

core: {{ plugin_info.core }}

{% if plugin_info.dependencies  %}
dependencies: {{ ', '.join(plugin_info.dependencies) }}
{% endif %}

class: {{ plugin.__module__ + "." + plugin.__class__.__name__ }}

storage namespace: {{ plugin.namespace }}

log destination: {{ plugin.log.name }}

log level: {{ logging.getLevelName(plugin.log.level) }}

{% if plugin.keys %}
**storage content**

Key                  | Value
-------------------- | -----------------------
{% for key, value in plugin.items() %}{{ key.ljust(20) }} | `{{ value }}`
{% endfor %}
{% endif %}

{% if plugin.config  %}
**config content**

Key                  | Value
-------------------- | -----------------------
{% for key, value in plugin.config.items() %}{{ key.ljust(20) }} | `{{ value }}`
{% endfor %}
{% endif %}




