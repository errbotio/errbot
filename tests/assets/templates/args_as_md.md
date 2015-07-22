  {% for arg in args -%}{% set tag = loop.cycle('**', '_') -%}
  {{ tag }}{{ arg }}{{ tag }}
  {%- endfor %}
