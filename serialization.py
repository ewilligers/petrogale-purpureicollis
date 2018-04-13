#!/usr/bin/env python

from google.appengine.api.mail import send_mail
from jinja2 import Environment, FileSystemLoader
from os import path
from webapp2 import RequestHandler, WSGIApplication


JINJA_ENVIRONMENT = Environment(
    loader=FileSystemLoader(path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)


class MainPage(RequestHandler):
    def get(self):
        main_template = JINJA_ENVIRONMENT.get_template('templates/serialization.html')
        main_template_values = {
          'divisor': self.request.get('divisor', ''),
          'quotient': self.request.get('quotient', ''),
          'property': self.request.get('property', ''),
          'assigned': self.request.get('assigned', '')
        }
        self.response.write(main_template.render(main_template_values))

    def post(self):
        main_template = JINJA_ENVIRONMENT.get_template('templates/serialization.html')
        main_template_values = {
          'divisor': self.request.get('divisor', ''),
          'quotient': self.request.get('quotient', ''),
          'property': self.request.get('property', ''),
          'assigned': self.request.get('assigned', ''),
          'serialized': self.request.get('serialized', ''),
          'computed': self.request.get('computed', ''),
          'useragent': self.request.headers['User-Agent']
        }
        try:
          divisor = int(self.request.get('divisor', '0'))
          quotient = int(self.request.get('quotient', '0'))
          if divisor > 1 and quotient > divisor and divisor * quotient == 323:
            send_mail(
              sender="serialization@petrogale-purpureicollis.appspotmail.com",
              to="ericwilligers+petrogale-purpureicollis@google.com",
              subject="CSS Serialization",
              body=main_template.render(main_template_values)
            )
            main_template_values['response'] = 'Email sent'

        except Exception, e:
          main_template_values['error'] = str(e)

        self.response.write(main_template.render(main_template_values))

app = WSGIApplication([
    ('/ray/serialization/', MainPage),
])
