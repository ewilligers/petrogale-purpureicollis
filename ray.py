#!/usr/bin/env python

from jinja2 import Environment, FileSystemLoader
from math import cos, fabs, radians, sin, sqrt
from os import path
from webapp2 import RequestHandler, WSGIApplication

class Size:
    def __init__(self, width, height):
        self.width = width
        self.height = height
    def __str__(self):
        return 'Size({}, {})'.format(self.width, self.height)

class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y
    def __str__(self):
        return 'Point({}, {})'.format(self.x, self.y)

def translate(dx, dy):
    return lambda point: Point(point.x + dx, point.y + dy)

def rotate(angle):
    c = cos(radians(angle))
    s = sin(radians(angle))
    return lambda point: Point(
        c * point.x - s * point.y,
        c * point.y + s * point.x
    )


class Interval:
    def __init__(self, lower_bound, upper_bound):
        self.lower_bound = lower_bound
        self.upper_bound = upper_bound
    def __str__(self):
        return 'Interval({}, {})'.format(self.lower_bound, self.upper_bound)

def greatest_lower_bound(intervals):
    return max([interval.lower_bound for interval in intervals])

def least_upper_bound(intervals):
    return min([interval.upper_bound for interval in intervals])


class OffsetPath:
    def __init__(self, angle, size = None, contain = False):
        if size not in [
            'closest-side',
            'closest-corner',
            'farthest-side',
            'farthest-corner',
        ]:
            size = 'closest-side'

        self.angle = angle
        self.size = size
        self.contain = contain

    def __str__(self):
        return 'OffsetPath({}, {}, {})'.format(self.angle, self.size, self.contain)


class OffsetRotation:
    def __init__(self, auto = True, angle = 0):
        self.auto = auto
        self.angle = angle
    def __str__(self):
        return 'OffsetRotation({}, {})'.format(self.auto, self.angle)


class Element:
    # offset-distance is a percentage of the path length
    # offset-position and offset-anchor are points
    def __init__(self, id, size, background_color, offset_path, offset_distance, offset_rotation, offset_position, offset_anchor, container_size):
        self.id = id
        self.size = size
        self.background_color = background_color
        self.offset_path = offset_path
        self.offset_distance = offset_distance
        self.offset_rotation = offset_rotation
        self.offset_position = offset_position
        self.offset_anchor = offset_anchor
        self.container_size = container_size

        if offset_rotation.auto:
            rotation = offset_rotation.angle + (offset_path.angle - 90)
        else:
            rotation = offset_rotation.angle

        self.v = map(rotate(rotation), [
            Point(-offset_anchor.x,             -offset_anchor.y),
            Point(size.width - offset_anchor.x, -offset_anchor.y),
            Point(size.width - offset_anchor.x, size.height - offset_anchor.y),
            Point(-offset_anchor.x,             size.height - offset_anchor.y)
        ])

        self.path_length = self.compute_path_length()
        self.computed_offset = self.compute_offset()

        self.translation = Point(
            self.computed_offset * sin(radians(self.offset_path.angle)),
            -self.computed_offset * cos(radians(self.offset_path.angle))
        )

        if False:
            print(self.id)
            print(self.size)
            print(self.background_color)
            print(self.offset_path)
            print(self.offset_distance)
            print(self.offset_rotation)
            print(self.offset_position)
            print(self.offset_anchor)
            print(self.container_size)
            print(self.v)
            print(self.path_length)
            print(self.computed_offset)
            print(self.translation)

    def compute_path_length(self):
        x1 = fabs(self.offset_position.x)
        y1 = fabs(self.offset_position.y)
        x2 = fabs(self.container_size.width - self.offset_position.x)
        y2 = fabs(self.container_size.height - self.offset_position.y)

        if self.offset_path.size == 'closest-side' or self.offset_path.size == 'closest-corner':
            x = min(x1, x2)
            y = min(y1, y2)
        else:
            x = max(x1, x2)
            y = max(y1, y2)

        if self.offset_path.size == 'closest-side':
            return min(x, y)
        elif self.offset_path.size == 'farthest-side':
            return max(x, y)
        else:
            return sqrt(x*x + y*y)

    def compute_offset(self):
        radius = self.path_length
        computed_offset = radius * self.offset_distance / 100.
        if not self.offset_path.contain:
            return computed_offset

        def compute_bounds(vertex):
            d2 = radius**2 - vertex.y**2
            if d2 <= 0:
                return Interval(-vertex.x, -vertex.x)
            else:
                d = sqrt(d2)
                return Interval(-vertex.x - d, -vertex.x + d)

        vertices = map(rotate(90 - self.offset_path.angle), self.v)
        bounds = map(compute_bounds, vertices)
        low = greatest_lower_bound(bounds)
        high = least_upper_bound(bounds)

        if low >= high:
            return (low + high) / 2.
        elif computed_offset < low:
            return low
        elif computed_offset > high:
            return high
        else:
            return computed_offset


JINJA_ENVIRONMENT = Environment(
    loader=FileSystemLoader(path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)


class MainPage(RequestHandler):
    def get(self):
        main_template = JINJA_ENVIRONMENT.get_template('templates/ray.html')
        item_template = JINJA_ENVIRONMENT.get_template('templates/item-fragment.html')

        items = []
        for index in range(1, 7):
            item_template_values = { 'item': { 'number': index, 'display': 'none' } }
            if index == 1:
                item_template_values['item']['display'] = 'block'
            items.append(item_template.render(item_template_values))

        main_template_values = { 'items': items }
        self.response.write(main_template.render(main_template_values))


class PlotPage(RequestHandler):
    def get(self):
        plot_template = JINJA_ENVIRONMENT.get_template('templates/plot.svg')

        image_size = Size(700, 700)
        label_position = Point(96, 36)
        stroke_begin = Point(132, 45)
        stroke_end = Point(150, 86)
        container_position = Point(100, 60)
        container_size = Size(500, 500)
        elements = []

        for index in range(1, 7):
            def getParam(name, default):
                return self.request.get('item{}_{}'.format(index, name), default)

            def getFloatParam(name, default):
                try:
                    return float(getParam(name, default))
                except:
                    return default

            box = 'box{}'.format(index)
            display = getParam('display', 'none')
            width = getFloatParam('width', 10)
            height = getFloatParam('height', 10)
            background_color = getParam('background', '#8080FF')
            position_x = getFloatParam('position_x', 50)
            position_y = getFloatParam('position_y', 50)
            path_function = getParam('function', 'ray')
            ray_size = getParam('size', 'closest-side')
            ray_contain = getParam('contain', 'unbounded')
            ray_angle = getFloatParam('direction', 90)
            distance = getFloatParam('distance', 100)
            rotation_auto = getParam('rotation_auto', '')
            rotation_angle = getFloatParam('rotation_angle', 0)
            anchor_x = getFloatParam('anchor_x', 50)
            anchor_y = getFloatParam('anchor_y', 50)

            if False:
                print(display)
                print(width)
                print(height)
                print(background_color)
                print(position_x)
                print(position_y)
                print(path_function)
                print(ray_size)
                print(ray_contain)
                print(ray_angle)
                print(distance)
                print(rotation_auto)
                print(rotation_angle)
                print(anchor_x)
                print(anchor_y)

            if display == 'block':
                element_size = Size(width * container_size.width / 100.0, height * container_size.height / 100.0)
                elements.append(Element(
                    id = box,
                    size = element_size,
                    background_color = background_color,
                    offset_path = OffsetPath(ray_angle, ray_size, ray_contain == 'contain'),
                    offset_distance = distance,
                    offset_rotation = OffsetRotation(rotation_auto == 'auto', rotation_angle),
                    offset_position = Point(position_x * container_size.width / 100.0, position_y * container_size.height / 100.0),
                    offset_anchor = Point(anchor_x * element_size.width / 100.0, anchor_y * element_size.height / 100.0),
                    container_size = container_size
                ))

        plot_template_values = {
            'image_size': image_size,
            'label_position': label_position,
            'stroke_begin': stroke_begin,
            'stroke_end': stroke_end,
            'container_position': container_position,
            'container_size': container_size,
            'elements': elements
        }
        self.response.headers.add_header('Content-Type', 'image/svg+xml')
        self.response.write(plot_template.render(plot_template_values))

app = WSGIApplication([
    ('/ray/plot', PlotPage),
    ('/ray/', MainPage),
])
