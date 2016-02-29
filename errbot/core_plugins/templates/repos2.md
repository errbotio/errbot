{% if error %}
{{error}}
{% else %}
Status  | Name                    | Description
------- | ----------------------- | ------------
{% for repo in repos %}         | {{('**'+repo.entry_name+'**').ljust(22)}} | {{repo.documentation}}
{% endfor %}
{% endif %}
