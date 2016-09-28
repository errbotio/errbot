{% if card.summary %}
**{{card.summary}}**
{% endif %}
{% if not card.thumbnail %}
{% if card.link %}
##[{{ card.title }}]({{ card.link }})
{% else %}
##{{ card.title }}
{% endif %}
{% else %}
{% if card.link %}

| | 
|-:|:-
| ![{{ card.thumbnail }}]({{ card.thumbnail }}) | **[{{ card.title }}]({{ card.link }})**

{% else %}

| | 
|-:|:-
| ![{{ card.thumbnail }}]({{ card.thumbnail }}) | **{{ card.title }}**

{% endif %}
{% endif %}
{% if card.image %}

![{{ card.image }}]({{ card.image }}) {{ card.body }}
{: color='{{card.text_color}}' bgcolor='{{card.color}}' }

{% else %}

{{ card.body }}
{: color='{{card.text_color}}' bgcolor='{{card.color}}' }

{% endif %}

{% for key,_ in card.fields %}| {{ key }} {% endfor %}
{% for _ in card.fields %}| - {% endfor %}
{% for _,value in card.fields %}| {{ value }} {% endfor %}

