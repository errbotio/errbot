If you are looking for errbot documentation, it is there: [errbot.net](http://errbot.net/).

All errbot plugins found from github
====================================

{% for plugin in plugins %}
[{{plugin.name}}](https://github.com/{{plugin.repo}}):

{{plugin.documentation}}

- Python {{plugin.python}}
- Install: `!repos install https://github.com/{{plugin.repo}}.git`

{% endfor %}
