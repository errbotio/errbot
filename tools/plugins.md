If you are looking for errbot documentation, it is there: [errbot.io](http://errbot.io/).

### All errbot plugins found from github

{% for plugin in plugins %}
{% set name = plugin[0] %}
{% set values = plugin[1] %}
## {{loop.index}}\. <img src="{{values.avatar_url}}" width="32">  [{{name}}]({{values.repo}})

{{values.documentation}}

- Python {{values.python}}
- Install: `!repos install {{values.repo}}`

---
{% endfor %}
