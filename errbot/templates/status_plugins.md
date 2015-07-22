{% macro status(name) -%}
    {% if name == 'L' -%}
        **L**{color='green'}
    {%- elif name == 'U' -%}
        **U**
    {%- elif name == 'C' -%}
        **C**{color='yellow'}
    {%- elif name == 'B' -%}
        **B**{color='red'}
    {%- elif name == 'BL' -%}
        **B**{color='red'},**L**{color='green'}
    {%- elif name == 'BU' -%}
        **B**{color='red'},**U**
    {%- endif %}
{%- endmacro %}
With these plugins ({{ status('L').strip() }} = Loaded, {{ status('U').strip() }} = Unloaded, {{ status('B').strip() }} = Blacklisted, {{ status('C').strip() }} = Needs to be configured):
{% for state, name in plugins_statuses %}
[{{ status(state).strip() }}] {{ name }}
{% endfor %}
