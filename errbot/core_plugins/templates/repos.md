{% macro status(installed, public) -%}
{% if installed %}**I**{% else %} {% endif %}{% if public %} {% else %}**P**{% endif %}{%- endmacro %}

Status  | Name                    | Description
------- | ----------------------- | ------------
{% for installed, public, name, desc in repos %}{{ status(installed, public).ljust(7) }} | {{ ('**'+name+'**').ljust(22) }} | {{ desc }}
{% endfor %}
