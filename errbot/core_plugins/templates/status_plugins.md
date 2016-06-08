{% macro status(name) -%}
    {% if name == 'A' -%}
        **A**{:color='green'}
    {%- elif name == 'D' -%}
        **D**
    {%- elif name == 'C' -%}
        **C**{:color='yellow'}
    {%- elif name == 'B' -%}
        **B**{:color='red'}
    {%- elif name == 'BA' -%}
        **B**{:color='red'},**A**{:color='green'}
    {%- elif name == 'BD' -%}
        **B**{:color='red'},**D**
    {%- endif %}
{%- endmacro %}

### Plugins

Status  | Name                    
------- | ----------------------- 
{% for state, name in plugins_statuses %}{{ status(state).strip().ljust(7) }} | {{ name }}
{% endfor %}

{{ status('A').strip() }} = Activated, {{ status('D').strip() }} = Deactivated, {{ status('B').strip() }} = Blacklisted, {{ status('C').strip() }} = Needs to be configured

