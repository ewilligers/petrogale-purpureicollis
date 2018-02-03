#!/usr/bin/env python

from google.appengine.ext import ndb
from jinja2 import Environment, FileSystemLoader
from json import dumps
from os import path
from re import compile
from sets import Set
from webapp2 import RequestHandler, WSGIApplication


JINJA_ENVIRONMENT = Environment(
    loader=FileSystemLoader(path.dirname(__file__)))


class Measurement(ndb.Model):
  context = ndb.StringProperty()
  serialization = ndb.StringProperty()


class Submission(ndb.Model):
  browser = ndb.StringProperty(indexed=True, required=True)
  version = ndb.IntegerProperty()
  measurements = ndb.StructuredProperty(Measurement, repeated=True)


class RecordPage(RequestHandler):
    def get(self):
      record_request_template_values = {
        'error': ''
      }
      record_request_template = JINJA_ENVIRONMENT.get_template('templates/record_request.html')
      self.response.write(record_request_template.render(record_request_template_values))

    def post(self):
      error = ''
      browser = self.request.get('browser', default_value='unknown')
      if browser not in ['Chrome', 'Edge', 'Firefox', 'Opera', 'Safari']:
        error = 'Unknown browser'

      try:
        version = int(self.request.get('version', default_value='0'))
      except:
        version = 0
        error = 'Unknown version'

      keyRegex = compile(r"^result_(\d+)_(\d+)$")
      valueRegex = compile(r"^([ %\(\)\+\-\.\da-z]+)$")

      measurements = []
      for key, value in self.request.POST.iteritems():
        match = keyRegex.match(key)
        if match:
          if valueRegex.match(value):
            measurements.append(Measurement(
              context = key,
              serialization = value
            ))
          else:
            error = 'Bad <position> value'

      if error == '':
        submission = Submission(
          browser = browser,
          version = version,
          measurements = measurements
        )
        try:
          submission_key = submission.put()
        except:
          error = 'Failed to store measurement'

      if error == '':
        record_acknowledgement_template_values = {
          'browser': browser,
          'version': version,
          'submission_key': submission_key
        }
        record_acknowledgement_template = JINJA_ENVIRONMENT.get_template('templates/record_acknowledgement.html')
        self.response.write(record_acknowledgement_template.render(record_acknowledgement_template_values))
      else:
        record_request_template_values = {
          'error': error
        }
        record_request_template = JINJA_ENVIRONMENT.get_template('templates/record_request.html')
        self.response.write(record_request_template.render(record_request_template_values))

class SearchPage(RequestHandler):
    def get(self):
      browsers = Set()
      submissions = {}
      query = Submission.query().order(Submission.version)
      for submission in query.iter():
        def measurement_to_dict(measurement):
          return { 'context': measurement.context, 'serialization': measurement.serialization }

        browsers.add(submission.browser)
        submissions[submission.browser] = {
          'browser': submission.browser,
          'version': submission.version,
          'measurements': map(measurement_to_dict, submission.measurements)
        }

      submissions = map(lambda browser: submissions[browser], sorted(browsers))
      search_request_template_values = {
        'submissions': dumps(submissions)
      }
      search_request_template = JINJA_ENVIRONMENT.get_template('templates/search_request.html')
      self.response.write(search_request_template.render(search_request_template_values))


app = WSGIApplication([
    ('/ray/position/record/', RecordPage),
    ('/ray/position/search/', SearchPage),
])
