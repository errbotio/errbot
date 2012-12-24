from flask.views import View
from flask import Flask, request, send_file, redirect, Response
import logging
from errbot import holder

OK = Response()


class WebView(View):
    def __init__(self, func, form_param):
        self.func = func
        self.form_param = form_param
        self.method_filter = lambda object: ismethod(object) and self.func.__name__ == object.__name__

    def dispatch_request(self, *args, **kwargs):
        name_to_find = self.func.__name__
        for obj in get_all_active_plugin_objects():  # horrible hack to find back the bound method from the unbound function the decorator was able to give us
            matching_members = getmembers(obj, self.method_filter)
            if matching_members:
                name, func = matching_members[0]
                if self.form_param:
                    content = request.form[self.form_param]
                    try:
                        content = loads(content)
                    except ValueError:
                        logging.debug('The form parameter is not JSON, return it as a string')
                    response = func(content, **kwargs)
                else:
                    data = request.json if request.json else request.data  # flask will find out automagically if it is a JSON structure
                    response = func(data if data else request.form, **kwargs)  # or it will magically parse a form so adapt for our users
                return response if response else OK  # assume None as an OK response (simplifies the client side)

        raise Exception('Problem finding back the correct Handler for func %s', name_to_find)


def webhook(*args, **kwargs):
    """
        Simple shortcut for the plugins to be notified on webhooks
    """

    def decorate(method, uri_rule, methods=('POST', 'GET'), form_param=None):
        logging.info("webhooks:  Bind %s to %s" % (uri_rule, method.__name__))

        for rule in holder.flask_app.url_map._rules:
            if rule.rule == uri_rule:
                holder.flask_app.view_functions[rule.endpoint] = WebView.as_view(method.__name__, method, form_param)  # in case of reload just update the view fonction reference
                return method

        holder.flask_app.add_url_rule(uri_rule, view_func=WebView.as_view(method.__name__, method, form_param), methods=methods)
        return method

    if isinstance(args[0], basestring):
        return lambda method: decorate(method, args[0], **kwargs)
    return decorate(args[0], '/' + args[0].__name__ + '/', **kwargs)
