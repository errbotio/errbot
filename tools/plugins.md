If you are looking for errbot documentation, it is there: [errbot.io](http://errbot.io/).

### All errbot plugins found from github

{% for plugin in plugins %}
## {{loop.index}}\. <img src="{{plugin.avatar_url}}" width="32">  [{{plugin.name}}]({{plugin.repo}})

{{plugin.documentation}}

- Python {{plugin.python}}
- Install: `!repos install {{plugin.repo}}`
- Activity: {{plugin.score}}

---
{% endfor %}
