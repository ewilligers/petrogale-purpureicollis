#!/usr/bin/env python

from abc import ABCMeta, abstractmethod
from itertools import chain, permutations, product
from jinja2 import Environment, escape, FileSystemLoader
from os import path
from webapp2 import RequestHandler, WSGIApplication

LONGHANDS = [
  '<angle>',
  '<basic-shape>',
  '<geometry-box>',
  '<offset-anchor>',
  '<offset-distance>',
  '<offset-path>',
  '<offset-position>',
  '<offset-rotation>',
  '<path()>',
  '<size>',
  '<url>',
  '<length-percentage>'
]

SEPARATORS = [
  '(',
  ')',
  '/',
  'contain',
  'none',
  'ray',
  'bottom',
  'center',
  'left',
  'right',
  'top',
]

ATOMS = LONGHANDS + SEPARATORS

#https://drafts.csswg.org/css-values-4/#component-combinators
# A double ampersand (&&) separates two or more components, all of which must occur, in any order.
# A double bar (||) separates two or more options: one or more of them must occur, in any order.
# A bar (|) separates two or more alternatives: exactly one of them must occur.
# Brackets ([ ]) are for grouping.
# Juxtaposition is stronger than the double ampersand, the double ampersand is stronger than the
# double bar, and the double bar is stronger than the bar.

# https://drafts.csswg.org/css-values-4/#component-multipliers
# A question mark (?) indicates that the preceding type, word, or group is optional (occurs zero or
# one times).
# An exclamation point (!) after a group indicates that the group is required and must produce at
# least one value.
TOKENS = ATOMS + [
  '&&',
  '||',
  '|',
  '[',
  ']',
  '?',
  '!'
]

class GrammarError(Exception):
    def __init__(self, message):
        self.message = message

# returns a list of atoms
def tokenise(grammar):
  result = []
  position = 0
  while position < len(grammar):
    if grammar[position].isspace():
      position += 1
      continue

    for token in TOKENS:
      if grammar[position:position+len(token)] == token:
        result.append(token)
        position += len(token)
        break
    else:
      raise GrammarError('Unknown token at "{}"'.format(grammar[position:]))
  return result

class Node(object):
  __metaclass__ = ABCMeta
  def __init__(self):
    pass

  @abstractmethod
  def atoms(self):
    pass

  @abstractmethod
  def expansions(self):
    pass

class Atom(Node):
  def __init__(self, value):
    self.value = value

  def __str__(self):
    return str(self.value)

  def atoms(self):
    return [self.value]

  def expansions(self):
    return [[self.value]]

class Bracketed(Node):
  def __init__(self, body):
    self.body = body

  def __str__(self):
    return '[ ' + str(self.body) + ' ]'

  def atoms(self):
    return self.body.atoms()

  def expansions(self):
    return self.body.expansions()

class Exclamation(Node):
  def __init__(self, body):
    self.body = body

  def __str__(self):
    return str(self.body) + '!'

  def atoms(self):
    return self.body.atoms()

  def expansions(self):
    return [item for item in self.body.expansions() if len(item) > 0]

class Question(Node):
  def __init__(self, body):
    self.body = body

  def __str__(self):
    return str(self.body) + '?'

  def atoms(self):
    return self.body.atoms()

  def expansions(self):
    return chain([[]], self.body.expansions())

class Juxtaposition(Node):
  def __init__(self, contents):
    self.contents = contents

  def __str__(self):
    return ' '.join(map(str, self.contents))

  def atoms(self):
    return [atom for node in self.contents for atom in node.atoms()]

  def expansions(self):
    return [list(chain(*list(expansion))) for expansion in product(*map(lambda item: item.expansions(), self.contents))]

class DoubleAmperstand(Node):
  def __init__(self, contents):
    self.contents = contents

  def __str__(self):
    return ' && '.join(map(str, self.contents))

  def atoms(self):
    return [atom for node in self.contents for atom in node.atoms()]

  def expansions(self):
    return [list(chain(*list(expansion))) for sequence in permutations(self.contents) for expansion in product(*map(lambda item: item.expansions(), sequence))]

class DoubleBar(Node):
  def __init__(self, contents):
    self.contents = contents

  def __str__(self):
    return ' || '.join(map(str, self.contents))

  def atoms(self):
    return [atom for node in self.contents for atom in node.atoms()]

  def expansions(self):
    return [list(chain(*list(expansion))) for r in range(1, len(self.contents)+1) for sequence in permutations(self.contents, r) for expansion in product(*map(lambda item: item.expansions(), sequence))]

class SingleBar(Node):
  def __init__(self, contents):
    self.contents = contents

  def __str__(self):
    return ' | '.join(map(str, self.contents))

  def atoms(self):
    return [atom for node in self.contents for atom in node.atoms()]

  def expansions(self):
    return chain(*[item.expansions() for item in self.contents])

def parse(tokens):
  remaining = list(tokens)
  remaining.append(None)
  (result, remaining) = parseSingleBar(remaining)
  if remaining != [None]:
    # e.g. superflous ] in '[/]]'
    raise GrammarError('Unexpected input at "{}"'.format(' '.join(remaining[:-1])))
  return result

def parseSingleBar(remaining):
  (first, remaining) = parseDoubleBar(remaining)
  result = [first]
  while remaining[0] == '|':
    (next, remaining) = parseDoubleBar(remaining[1:])
    result.append(next)

  if len(result) == 1:
    return (result[0], remaining)
  return (SingleBar(result), remaining)

def parseDoubleBar(remaining):
  (first, remaining) = parseDoubleAmperstand(remaining)
  result = [first]
  while remaining[0] == '||':
    (next, remaining) = parseDoubleAmperstand(remaining[1:])
    result.append(next)

  if len(result) == 1:
    return (result[0], remaining)
  return (DoubleBar(result), remaining)

def parseDoubleAmperstand(remaining):
  (first, remaining) = parseJuxtaposition(remaining)
  result = [first]
  while remaining[0] == '&&':
    (next, remaining) = parseJuxtaposition(remaining[1:])
    result.append(next)

  if len(result) == 1:
    return (result[0], remaining)
  return (DoubleAmperstand(result), remaining)

def parseJuxtaposition(remaining):
  (first, remaining) = parseSingle(remaining)
  result = [first]
  while remaining[0] not in [']', '&&', '||', '|', None]:
    (next, remaining) = parseSingle(remaining)
    result.append(next)

  if len(result) == 1:
    return (result[0], remaining)
  return (Juxtaposition(result), remaining)

def parseSingle(remaining):
  if remaining[0] == '[':
    (body, remaining) = parseSingleBar(remaining[1:])
    if remaining[0] != ']':
      raise GrammarError('Expected ] at "{}"'.format(' '.join(remaining[:-1])))
    body = Bracketed(body)
    remaining = remaining[1:]
  elif remaining[0] in ATOMS:
    body = Atom(remaining[0])
    remaining = remaining[1:]
    if remaining[0] == '!':
      raise GrammarError('Unexpected ! after {}'.format(str(body)))
  elif remaining[0] == None:
    raise GrammarError('Unexpected end of input')
  else:
    raise GrammarError('Unexpected token at "{}"'.format(' '.join(remaining[:-1])))

  if remaining[0] == '!':
    return (Exclamation(body), remaining[1:])

  if remaining[0] == '?':
    return (Question(body), remaining[1:])

  return (body, remaining)

def unique(sequence):
  items = list(sequence)
  return [item for index,item in enumerate(items) if items.index(item) == index]

def repeated(sequence):
  items = list(sequence)
  return sorted(set([item for index,item in enumerate(items) if items.index(item) < index]))

ANGLE_VALUES = [
  '0deg'
]

SHAPE_VALUES = [
  'circle(50% at 50% 50%)'
]

BOX_VALUES = [
  'margin-box'
]

ANCHOR_VALUES = [
  '0px 0px',
  '0px',
  'auto',
]

DISTANCE_VALUES = [
  '0px',
  '100%',
]

PATH_VALUES = [
  'none',
  'ray(0deg)',
]

POSITION_VALUES = [
  '0px 0px',
  '0px',
  'auto',
]

ROTATION_VALUES = [
  '0deg auto',
  '0deg',
  'auto 0deg',
  'auto',
]

PATH_VALUES = [
  "path('m 0 0 h 1')"
]

SIZE_VALUES = [
  'closest-side'
]

URL_VALUES = [
  "url('https://www.example.com/shape#element')"
]

LENGTH_PERCENTAGE_VALUES = [
  '0%',
]

LONGHAND_EXPANSIONS = {
  '<angle>': ANGLE_VALUES,
  '<basic-shape>': SHAPE_VALUES,
  '<geometry-box>': BOX_VALUES,
  '<offset-anchor>': ANCHOR_VALUES,
  '<offset-distance>': DISTANCE_VALUES,
  '<offset-path>': PATH_VALUES,
  '<offset-position>': POSITION_VALUES,
  '<offset-rotation>': ROTATION_VALUES,
  '<path()>': PATH_VALUES,
  '<size>': SIZE_VALUES,
  '<url>': URL_VALUES,
  '<length-percentage>': LENGTH_PERCENTAGE_VALUES,
}

SEPARATOR_EXPANSIONS = dict((separator, [separator]) for separator in SEPARATORS)

ATOM_EXPANSIONS = dict(chain(LONGHAND_EXPANSIONS.iteritems(), SEPARATOR_EXPANSIONS.iteritems()))

class AmbiguitySearch(object):
  def __init__(self, root):
    self.root = root
    atoms = set(root.atoms())
    atoms.discard('/')
    self.longhands = list(atoms)

    self.expansions = unique(root.expansions())

  def search(self):
    possibilities = list([' '.join(concrete) for expansion in self.expansions for concrete in product(*map(lambda atom: ATOM_EXPANSIONS[atom], expansion))])
    return repeated(possibilities)

JINJA_ENVIRONMENT = Environment(
    loader=FileSystemLoader(path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)



class MainPage(RequestHandler):
    def get(self):
        shorthand_template = JINJA_ENVIRONMENT.get_template('templates/shorthand.html')

        response = ''
        try:
          offset_value = self.request.get('offset_value', '')
          tokens = tokenise(offset_value)
          error = ''
        except GrammarError as err:
          offset_value = ''
          error = 'Unexpected token'

        if offset_value != '':
          try:
            root = parse(tokens)
            ambiguitySearch = AmbiguitySearch(root)
            response = '<br />'.join(map(escape, sorted(map(lambda expansion: ' '.join(expansion), ambiguitySearch.expansions))))
            if [] in ambiguitySearch.expansions:
              raise GrammarError('Empty string should not be accepted.')

            ambiguities = ambiguitySearch.search()
            if ambiguities:
              response = '<br />'.join(sorted(ambiguities))
              raise GrammarError('Ambiguities')

          except GrammarError as err:
            error = err.message

        shorthand_template_values = {
            'offset_value': offset_value,
            'error': error,
            'response': response
        }
        self.response.write(shorthand_template.render(shorthand_template_values))



app = WSGIApplication([
    ('/ray/shorthand/', MainPage),
])
