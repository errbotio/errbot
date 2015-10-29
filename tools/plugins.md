If you are looking for errbot documentation, it is there: [errbot.net](http://errbot.net/).

### All errbot plugins found from github

{% for plugin in plugins %}
## {{loop.index}}\. <img src="{{plugin.avatar_url}}" width="32">  [{{plugin.name}}](https://github.com/{{plugin.repo}})

{{plugin.documentation}}

- Python {{plugin.python}}
- Install: `!repos install https://github.com/{{plugin.repo}}.git`

---
{% endfor %}
