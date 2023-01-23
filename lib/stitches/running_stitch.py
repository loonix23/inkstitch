# Authors: see git history
#
# Copyright (c) 2010 Authors
# Licensed under the GNU GPL version 3.0 or later.  See the file LICENSE for details.

import math
from math import tau
import typing
from copy import copy

import numpy as np
from shapely import geometry as shgeo
from ..utils import prng
from ..utils.geometry import Point

""" Utility functions to produce running stitches. """


def split_segment_even_n(a, b, segments: int, jitter_sigma: float = 0.0, random_seed=None) -> typing.List[shgeo.Point]:
    if segments <= 1:
        return []
    line = shgeo.LineString((a, b))

    splits = np.array(range(1, segments)) / segments
    if random_seed is not None:
        jitters = (prng.nUniformFloats(len(splits), random_seed) * 2) - 1
        splits = splits + jitters * (jitter_sigma / segments)

    # sort the splits in case a bad roll transposes any of them
    return [line.interpolate(x, normalized=True) for x in sorted(splits)]


def split_segment_even_dist(a, b, max_length: float, jitter_sigma: float = 0.0, random_seed=None) -> typing.List[shgeo.Point]:
    distance = shgeo.Point(a).distance(shgeo.Point(b))
    segments = math.ceil(distance / max_length)
    return split_segment_even_n(a, b, segments, jitter_sigma, random_seed)


def split_segment_random_phase(a, b, length: float, length_sigma: float, random_seed: str) -> typing.List[shgeo.Point]:
    line = shgeo.LineString([a, b])
    progress = length * prng.uniformFloats(random_seed, "phase")[0]
    splits = [progress]
    distance = line.length
    if progress >= distance:
        return []
    for x in prng.iterUniformFloats(random_seed):
        progress += length * (1 + length_sigma * (x - 0.5) * 2)
        if progress >= distance:
            break
        splits.append(progress)
    return [line.interpolate(x, normalized=False) for x in splits]


class AngleInterval():
    # Modular interval containing either the entire circle or less than half of it
    # partially based on https://fgiesen.wordpress.com/2015/09/24/intervals-in-modular-arithmetic/

    def __init__(self, a: float, b: float, all: bool = False):
        self.all = all
        self.a = a
        self.b = b

    @staticmethod
    def all():
        return AngleInterval(0, math.tau, True)

    @staticmethod
    def fromBall(p: Point, epsilon: float):
        d = p.length()
        if d <= epsilon:
            return AngleInterval.all()
        center = p.angle()
        delta = math.asin(epsilon / d)
        return AngleInterval(center - delta, center + delta)

    @staticmethod
    def fromSegment(a: Point, b: Point):
        angleA = a.angle()
        angleB = b.angle()
        diff = (angleB - angleA) % tau
        if diff == 0 or diff == math.pi:
            return None
        elif diff < math.pi:
            return AngleInterval(angleA - 1e-6, angleB + 1e-6)
        else:
            return AngleInterval(angleB - 1e-6, angleA + 1e-6)

    def containsAngle(self, angle: float):
        if self.all:
            return True
        return (angle - self.a) % tau <= (self.b - self.a) % tau

    def containsPoint(self, p: Point):
        return self.containsAngle(math.atan2(p.y, p.x))

    def intersect(self, other):
        # assume that each interval contains less than half the circle (or all of it)
        if other is None:
            return None
        elif self.all:
            return other
        elif other.all:
            return self
        elif self.containsAngle(other.a):
            if other.containsAngle(self.b):
                return AngleInterval(other.a, self.b)
            else:
                return AngleInterval(other.a, other.b)
        elif other.containsAngle(self.a):
            if self.containsAngle(other.b):
                return AngleInterval(self.a, other.b)
            else:
                return AngleInterval(self.a, self.b)
        else:
            return None

    def cutSegment(self, origin: Point, a: Point, b: Point):
        if self.all:
            return None
        segArc = AngleInterval.fromSegment(a - origin, b - origin)
        if segArc is None:
            return a  # b is exactly behind origin from a
        if segArc.containsAngle(self.a):
            return cut_segment_with_angle(origin, self.a, a, b)
        elif segArc.containsAngle(self.b):
            return cut_segment_with_angle(origin, self.b, a, b)
        else:
            return None


def cut_segment_with_angle(origin: Point, angle: float, a: Point, b: Point) -> Point:
    # Assumes the crossing is inside the segment
    p = a - origin
    d = b - a
    c = Point(math.cos(angle), math.sin(angle))
    t = (p.y*c.x - p.x*c.y) / (d.x*c.y - d.y*c.x)
    if t < -0.000001 or t > 1.000001:
        raise Exception("cut_segment_with_angle returned a parameter of {0} with points {1} {2} and cut line {3} ".format(t, p, b-origin, c))
    return a + d*t


def cut_segment_with_circle(origin: Point, r: float, a: Point, b: Point) -> Point:
    # assumes that a is inside the circle and b is outside
    p = a - origin
    d = b - a
    # inner products
    p2 = p * p
    d2 = d * d
    r2 = r * r
    pd = p * d
    # r2 = p2 + 2*pd*t + d2*t*t, quadratic formula
    t = (math.sqrt(pd*pd + r2*d2 - p2*d2) - pd) / d2
    if t < -0.000001 or t > 1.000001:
        raise Exception("cut_segment_with_circle returned a parameter of {0}".format(t))
    return a + d*t


def take_stitch(start: Point, points: typing.Sequence[Point], idx: int, stitch_length: float, tolerance: float):
    # Based on a single step of the Zhao-Saalfeld curve simplification algorithm.
    # https://cartogis.org/docs/proceedings/archive/auto-carto-13/pdf/linear-time-sleeve-fitting-polyline-simplification-algorithms.pdf
    # Adds early termination condition based on stitch length.
    if idx >= len(points):
        return None, None

    sleeve = AngleInterval.all()
    last = start
    for i in range(idx, len(points)):
        p = points[i]
        if sleeve.containsPoint(p - start):
            if start.distance(p) < stitch_length:
                sleeve = sleeve.intersect(AngleInterval.fromBall(p - start, tolerance))
                last = p
                continue
            else:
                cut = cut_segment_with_circle(start, stitch_length, last, p)
                return cut, i
        else:
            cut = sleeve.cutSegment(start, last, p)
            if start.distance(cut) > stitch_length:
                cut = cut_segment_with_circle(start, stitch_length, last, p)
            return cut, i
    return points[-1], None


def stitch_curve_even(points: typing.Sequence[Point], stitch_length: float, tolerance: float):
    # includes end point but not start point.
    if len(points) < 2:
        return []
    distLeft = [0] * len(points)
    for i in reversed(range(0, len(points) - 1)):
        distLeft[i] = distLeft[i + 1] + points[i].distance(points[i+1])

    i = 1
    last = points[0]
    stitches = []
    while i is not None and i < len(points):
        d = last.distance(points[i]) + distLeft[i]
        if d == 0:
            return stitches
        stitch_len = d / math.ceil(d / stitch_length) + 0.000001  # correction for rounding error

        stitch, newidx = take_stitch(last, points, i, stitch_len, tolerance)
        i = newidx
        if stitch is not None:
            stitches.append(stitch)
            last = stitch
    return stitches


def path_to_curves(points: typing.List[Point]):
    # split a path at obvious corner points so that they get stitched exactly
    if len(points) < 3:
        return [points]
    curves = []
    last = 0
    last_seg = points[1] - points[0]
    for i in range(1, len(points) - 1):
        a = last_seg
        b = points[i + 1] - points[i]
        aabb = (a * a) * (b * b)
        abab = (a * b) * abs(a * b)
        if aabb > 0 and 2 * abab < aabb:
            # inner angle of at most 135 deg
            curves.append(points[last: i + 1])
            last = i
        if b * b > 0:
            last_seg = b
    curves.append(points[last:])
    return curves


def running_stitch(points, stitch_length, tolerance):
    stitches = [points[0]]
    for curve in path_to_curves(points):
        stitches.extend(stitch_curve_even(curve, stitch_length, tolerance))
    return stitches


def bean_stitch(stitches, repeats):
    """Generate bean stitch from a set of stitches.

    "Bean" stitch is made by backtracking each stitch to make it heavier.  A
    simple bean stitch would be two stitches forward, one stitch back, two
    stitches forward, etc.  This would result in each stitch being tripled.

    We'll say that the above counts as 1 repeat.  Backtracking each stitch
    repeatedly will result in a heavier bean stitch.  There will always be
    an odd number of threads piled up for each stitch.

    Repeats is a list of a repeated pattern e.g. [0, 1, 3] doesn't repeat the first stitch,
    goes back and forth on the second stitch, goes goes 3 times back and forth on the third stitch,
    and starts the pattern again by not repeating the fourth stitch, etc.
    """

    if len(stitches) < 2:
        return stitches

    repeat_list_length = len(repeats)
    repeat_list_pos = 0

    new_stitches = [stitches[0]]

    for stitch in stitches:
        new_stitches.append(stitch)

        for i in range(repeats[repeat_list_pos]):
            new_stitches.extend(copy(new_stitches[-2:]))

        repeat_list_pos += 1
        if repeat_list_pos == repeat_list_length:
            repeat_list_pos = 0

    return new_stitches
