#!/usr/bin/env python

from cgi import FieldStorage
from jinja2 import Environment, FileSystemLoader
from os import path
from webapp2 import RequestHandler, WSGIApplication

JINJA_ENVIRONMENT = Environment(
    loader=FileSystemLoader(path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'])


# How should we handle " in the text?
def escape(text):
  return text


class MainPage(RequestHandler):
    def post(self):
        main_template = JINJA_ENVIRONMENT.get_template('share-target-destination.template.html')


        main_template_values = {
          'generation_location': 'server-side',
          'received_title': escape(self.request.POST.get('received_title', '')),
          'received_text': escape(self.request.POST.get('received_text', '')),
          'received_url': escape(self.request.POST.get('received_url', ''))
        }

        def process_attachments(field):
          received_file = self.request.POST.getall(field)
          attachments = [{'content': f.file.read(),
                           'filename': f.filename} for f in received_file if f != '']

          if len(attachments) > 0:
            file_contents = ", ".join([attachment['content'] for attachment in attachments])
            main_template_values[field] = file_contents

        process_attachments('received_html_files')
        process_attachments('received_css_files')

        print(main_template_values)
        self.response.write(main_template.render(main_template_values))


app = WSGIApplication([
    ('/ray/upload', MainPage),
])
