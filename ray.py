#!/usr/bin/env python

from jinja2 import Environment, FileSystemLoader
from math import atan2, cos, degrees, fabs, pi, radians, sin, sqrt
from os import path
from webapp2 import RequestHandler, WSGIApplication

NUM_ITEMS = 6

class Size:
    def __init__(self, width, height):
        self.width = width
        self.height = height
    def __str__(self):
        return 'Size({}, {})'.format(self.width, self.height)

class Point:
    def __init__(self, x, y, r = None):
        self.x = x
        self.y = y
        self.r = r
        if self.r is None:
            self.r = sqrt(x*x + y*y)
    def __str__(self):
        return 'Point({}, {})'.format(self.x, self.y)

def triangle_area(p1, p2, p3):
    return fabs(p1.x * (p2.y - p3.y) + p2.x * (p3.y - p1.y) + p3.x * (p1.y - p2.y)) / 2

def encloses_origin(p1, p2, p3):
    def origin_right(begin, end):
        return (end.y * (begin.x - end.x) - end.x * (begin.y - end.y)) < 0

    d12 = origin_right(p1, p2)
    d23 = origin_right(p2, p3)
    d31 = origin_right(p3, p1)
    return d12 == d23 and d23 == d31

# Given two points on the unit circle, returns
# the area of the circular segment between the
# arc and the chord.
def segment_area(p1, p2):
    x = p1.x * p2.x + p1.y * p2.y
    y = p1.x * p2.y - p1.y * p2.x
    theta = fabs(atan2(y, x))
    return (theta - sin(theta)) / 2

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


# Find the distance to the container edge, in the direction given
# by angle. The offset-position is (distLeft, distTop), and the
#  container size is (distLeft + distRight, distTop + distBottom).
def distance_to_sides(distLeft, distTop, distRight, distBottom, angle):
    sn = sin(angle)
    cs = cos(angle)
    if sn >= 0:
        distHorizontal = distRight
    else:
        distHorizontal = distLeft
        sn = -sn

    if cs >= 0:
        distVertical = distTop
    else:
        distVertical = distBottom
        cs = -cs

    if distVertical * sn <= distHorizontal * cs:
        return distVertical / cs
    return distHorizontal / sn

class RayPath:
    def __init__(self, angle, size = None, contain = False):
        if size not in [
            'closest-side',
            'closest-corner',
            'farthest-side',
            'farthest-corner',
            'sides',
        ]:
            size = 'closest-side'

        self.angle = angle
        self.size = size
        self.contain = contain
        self.is_ray = True

    def __str__(self):
        return 'RayPath({}, {}, {})'.format(self.angle, self.size, self.contain)


class StringPath:
    def __init__(self, path, x, y, dx, dy):
        self.path = path
        self.x = x
        self.y = y
        self.dx = dx
        self.dy = dy
        self.angle = 90 - degrees(atan2(-dy, dx))
        self.is_ray = False

    def __str__(self):
        return 'StringPath({}, {}, {}, {}, {})'.format(self.path, self.x, self.y, self.dx, self.dy)


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

        if offset_path and offset_rotation.auto:
            rotation = offset_rotation.angle + (offset_path.angle - 90)
        else:
            rotation = offset_rotation.angle

        self.v = map(rotate(rotation), [
            Point(-offset_anchor.x,             -offset_anchor.y),
            Point(size.width - offset_anchor.x, -offset_anchor.y),
            Point(size.width - offset_anchor.x, size.height - offset_anchor.y),
            Point(-offset_anchor.x,             size.height - offset_anchor.y)
        ])

        if isinstance(offset_path, RayPath):
            self.path_length = self.compute_path_length()
            self.computed_offset = self.compute_offset()

            self.translation = Point(
                self.computed_offset * sin(radians(self.offset_path.angle)),
                -self.computed_offset * cos(radians(self.offset_path.angle))
            )
        elif isinstance(offset_path, StringPath):
            self.path_length = 0
            self.translation = Point(self.offset_path.x, self.offset_path.y)
        else:
            self.path_length = 0
            self.translation = Point(0, 0)


    def compute_path_length(self):
        x1 = fabs(self.offset_position.x)
        y1 = fabs(self.offset_position.y)
        x2 = fabs(self.container_size.width - self.offset_position.x)
        y2 = fabs(self.container_size.height - self.offset_position.y)

        if self.offset_path.size == 'sides':
            if self.offset_position.x <= 0 or self.offset_position.y <= 0 or self.offset_position.x >= self.container_size.width or self.offset_position.y >= self.container_size.height:
                return 0
            return distance_to_sides(x1, y1, x2, y2, radians(self.offset_path.angle))

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
        item_script_template = JINJA_ENVIRONMENT.get_template('templates/item-script-fragment.html')

        items = []
        for index in range(1, 7):
            item_template_values = { 'item': { 'number': index, 'display': 'none' } }
            if index == 1:
                item_template_values['item']['display'] = 'block'
            items.append({
                'specification': item_template.render(item_template_values),
                'script': item_script_template.render(item_template_values),
            })

        main_template_values = { 'items': items }
        self.response.write(main_template.render(main_template_values))


class PlotPage(RequestHandler):
    def get(self):
        self.post()

    def post(self):
        plot_template = JINJA_ENVIRONMENT.get_template('templates/plot.svg')

        image_size = Size(700, 700)
        label_position = Point(96, 36)
        stroke_begin = Point(132, 45)
        stroke_end = Point(150, 86)
        container_position = Point(100, 60)
        container_size = Size(500, 500)
        elements = []

        for index in range(1, NUM_ITEMS + 1):
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
            path = getParam('path', '')
            path_x = getFloatParam('path_x', 0)
            path_y = getFloatParam('path_y', 0)
            path_dx = getFloatParam('path_dx', 0)
            path_dy = getFloatParam('path_dy', 0)
            rotation_auto = getParam('rotation_auto', '')
            rotation_angle = getFloatParam('rotation_angle', 0)
            anchor = getParam('anchor', '')
            if anchor == '':
                anchor_x = getFloatParam('anchor_x', 50)
                anchor_y = getFloatParam('anchor_y', 50)
            elif path_function == 'none':
                anchor_x = position_x
                anchor_y = position_y
            else:
                anchor_x = 50
                anchor_y = 50

            if path_function == 'ray':
                offset_path = RayPath(ray_angle, ray_size, ray_contain == 'contain')
            elif path_function == 'path':
                offset_path = StringPath(path, path_x, path_y, path_dx, path_dy)
            else:
                offset_path = None

            if display == 'block':
                element_size = Size(width * container_size.width / 100.0, height * container_size.height / 100.0)
                elements.append(Element(
                    id = box,
                    size = element_size,
                    background_color = background_color,
                    offset_path = offset_path,
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
