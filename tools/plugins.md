If you are looking for errbot documentation, it is there: [errbot.net](http://errbot.net/).

All errbot plugins found from github
====================================

{% for plugin in plugins %}
## {{loop.index}}\. [{{plugin.name}}](https://github.com/{{plugin.repo}}/blob/master/{{plugin.path}})

{{plugin.documentation}}

- Python {{plugin.python}}
- Install: `!repos install https://github.com/{{plugin.repo}}.git`

---
{% endfor %}
