Internal webserver URI mapping [URI Regexp -> endpoint]:

{% for uri, endpoint in rules %}
- {{ uri|e }} -> {{ endpoint }}
{% endfor %}
