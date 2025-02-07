# -*- coding: utf-8 -*-
## @package scenegraphitems
# functions for using QGraphicsItems in CGT
#
# @copyright 2020 University of Leeds, Leeds, UK.
# @author j.h.pickering@leeds.ac.uk and j.leng@leeds.ac.uk
'''
Licensed under the Apache License, Version 2.0 (the "License"); you may not use
this file except in compliance with the License. You may obtain a copy of the
License at http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed
under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

This work was funded by Joanna Leng's EPSRC funded RSE Fellowship (EP/R025819/1)
'''
# set up linting conditions
# pylint: disable = c-extension-no-member
from math import (sqrt, isfinite)

import PyQt5.QtGui as qg
import PyQt5.QtCore as qc
import PyQt5.QtWidgets as qw

from cgt.util.markers import (MarkerTypes, ItemDataTypes, get_point_of_point)

def difference_to_distance(difference, scale):
    """
    convert a difference object to distance to
        Args:
            difference (ImageLineDifference) the difference
            scale (float) the pixel size
        Returns:
            the average seperation as a distance
    """
    return difference.average * scale

def difference_list_to_velocities(diff_list, scale, fps):
    """
    converts a list of (frame interval, difference) tuples to a list of velocities
        Args:
            diff_list (tuple(int, ImageLineDifference)) the list of inputs
            scale (float) the size of a pixel
            fps (int) the number of frames per second
        Returns:
            a list of velocities
    """
    velocities = []
    for frames, diff in diff_list:
        distance = difference_to_distance(diff, scale)
        time = frames/fps
        velocity = distance/time

        if velocity < 0.0:
            velocities.append(-velocity)
        else:
            velocities.append(velocity)

    return velocities

def rectangle_properties(rectangle):
    """
    find the top left, bottom right and centre of a rectangle
        Args:
            rectangle (QRect) the rectangle
        Returns:
            top left, top right, bottom left, bottom right, centre (QPoint)
    """
    top_left = rectangle.topLeft()
    top_right = rectangle.topRight()
    bottom_left = rectangle.bottomLeft()
    bottom_right = rectangle.bottomRight()
    ctr = top_left + bottom_right
    ctr /= 2

    return top_left, top_right, bottom_left, bottom_right, ctr

def qpoint_sepertation_squared(point_a, point_b):
    """
    find the square of the distance apart of two points
        Args:
            point_a (QPoint) first point
            point_b (QPoint) second point
        Returns:
            the square of the distance from a to b
    """
    difference = point_a - point_b
    return difference.x()*difference.x() + difference.y()*difference.y()

def make_positive_rect(corner, opposite_corner):
    """
    draw a rectangle with positive size (x, y) from two points
        Args:
            corner (QPointF) scene coordinates of a corner
            opposite_corner (QPointF) scene coordinates of the opposing corner
    """
    # get the width and height (strictly positive)
    width = abs(opposite_corner.x()-corner.x())
    height = abs(opposite_corner.y()-corner.y())

    # find the top left of the new adjusted rectangle
    top_left_x = min(opposite_corner.x(), corner.x())
    top_left_y = min(opposite_corner.y(), corner.y())

    return qc.QRectF(top_left_x, top_left_y, width, height)

def length_squared(point):
    """
    square of length from origin of a point
        Args:
            point (QPointF) the point
        Returns
            square of length
    """
    return point.x()*point.x() + point.y()*point.y()

def make_cross_path(point):
    """
    make the path object corresponding to a cross centred at a scene point
        Args:
            point (QPointF) location in scene coordinates
        Returns:
            the path (QPainterPath) for the cross
    """
    path = qg.QPainterPath()

    up_right = qc.QPointF(10.0, 10.0)
    up_left = qc.QPointF(-10.0, 10.0)

    path.moveTo(point)
    path.lineTo(point+up_right)
    path.moveTo(point)
    path.lineTo(point+up_left)
    path.moveTo(point)
    path.lineTo(point-up_right)
    path.moveTo(point)
    path.lineTo(point-up_left)

    return path

def cgt_intersection(centred_normal, clone):
    """
    find intersection of centred_normal and clone
        Args:
            centred_normal (QLineF) the normal vector
            clone (QLineF) the clone
        Returns:
            intersection (QPointF) the intersection point
            extensiong (QLineF) the extension to clone if needed, else None
    """
    ## based on Graphics Gems III's "Faster Line Segment Intersection"
    a = centred_normal.p2() - centred_normal.p1()
    b = clone.p1() - clone.p2()
    c = centred_normal.p1() - clone.p1()

    # test if parallel
    denominator = a.y() * b.x() - a.x() * b.y()
    if denominator == 0 or not isfinite(denominator):
        raise ArithmeticError("Clone line is parallel to parent")

    # find the intersection
    reciprocal = 1.0 / denominator
    na = (b.y() * c.x() - b.x() * c.y()) * reciprocal
    intersection = centred_normal.p1() + (a * na)

    # test if outside clone segmet and assign extension as required
    nb = (a.x() * c.y() - a.y() * c.x()) * reciprocal
    extension = None
    if nb < 0.0:
        extension = qc.QLineF(clone.p1(), intersection)
    elif nb > 1.0:
        extension = qc.QLineF(clone.p2(), intersection)

    return intersection, extension

def make_arrow_head(line, length_cutoff=10):
    """
    if line.length() > length_cutoff add a small triangle to the end
        Args:
            line (QLineF) the line
            length_cutoff (float) the minimum length for a head to be added
        Returns:
            QPolygon the triangle
    """
    if line.length() < length_cutoff:
        return None

    # make normal based at p2
    delta_t = (line.length()-10.0)/line.length()
    normal = line.normalVector()
    offset = line.pointAt(delta_t)-line.p1()
    offset_normal = qc.QLineF(normal.p1()+offset, normal.p2()+offset)

    opposit_normal = qc.QLineF(offset_normal.p1(), offset_normal.pointAt(-1.0))

    offset_normal.setLength(5.0)
    opposit_normal.setLength(5.0)

    return qg.QPolygonF([line.p2(), offset_normal.p2(), opposit_normal.p2()])

def make_arrow(line, clone):
    """
    make the arrow line between a line and a parallel clone
        Args:
            line (QLineF) the parent line
            clone (QLineF) the parallel clone line
        Returns:
            arrow_line (QLineF) the arrow line (p1, p2) as parent to clone
            extension (QLineF) the extension to clone, None if not needed
    """
    # make normal based at centre of parent line
    normal = line.normalVector()
    centre = line.center()
    offset = centre-line.p1()
    centred_normal = qc.QLineF(normal.p1()+offset, normal.p2()+offset)

    intersection, extension = cgt_intersection(centred_normal, clone)
    arrow = qc.QLineF(centre, intersection)

    return arrow, extension

def perpendicular_dist_to_position(gline, scale):
    """
    find the distance to the position of a QGraphicsLine
        Args:
            gline (QGraphicsLine): the line
            scale (float): the pixel scale
    """
    unit_normal = gline.line().normalVector().unitVector()
    del_x = gline.pos().x()*unit_normal.dx()*scale
    del_y = gline.pos().y()*unit_normal.dy()*scale

    return sqrt(del_x*del_x + del_y*del_y)

def rect_to_tuple(rect):
    """
    convert a qrectangl to a tuple
        Args:
            rect (QRect)
        Returns:
            ((left, top, width, height))
    """
    array = []

    array.append(rect.left())
    array.append(rect.top())
    array.append(rect.width())
    array.append(rect.height())

    return array

def g_point_to_tuple(point):
    """
    convert the data in a QGraphicsPathItem reprsenting a point to a tuple
        Args:
            point (QGraphicsPathItem) the point for conversion
        Returns:
            list [x1, y1, px, py, frame]
    """
    array = []
    centre = point.data(ItemDataTypes.CROSS_CENTRE)
    position = point.pos()
    array.append(centre.x())
    array.append(centre.y())
    array.append(position.x())
    array.append(position.y())
    array.append(point.data(ItemDataTypes.FRAME_NUMBER))
    array.append(point.data(ItemDataTypes.REGION_INDEX))

    return array

def g_line_to_tuple(line):
    """
    convert the data in a QGraphicsLineItem to a tuple
        Args:
            line (QGraphicsLineItem) the line
        Returns:
            list [x1, y1, x2, y2, px, py, frame]
    """
    array = []
    array.append(line.line().x1())
    array.append(line.line().y1())
    array.append(line.line().x2())
    array.append(line.line().y2())
    array.append(line.pos().x())
    array.append(line.pos().y())
    array.append(line.data(ItemDataTypes.FRAME_NUMBER))
    array.append(line.data(ItemDataTypes.REGION_INDEX))

    return array

def list_to_g_point(point, pen):
    """
    convert the data in a list to a graphics point
        Args:
            point (list [ID, x, y, pos_x, pos_y, frame, region]) the point as list
            pen (QPen) the drawing pen
        Returns:
            QGraphicsPathItem
    """
    centre_x = float(point[1])
    centre_y = float(point[2])
    position_x = float(point[3])
    position_y = float(point[4])
    frame = int(point[5])
    region = int(point[6])

    centre = qc.QPointF(centre_x, centre_y)
    position = qc.QPointF(position_x, position_y)

    path = make_cross_path(centre)
    item = qw.QGraphicsPathItem(path)
    item.setPos(position)
    item.setData(ItemDataTypes.ITEM_TYPE, MarkerTypes.POINT)
    item.setData(ItemDataTypes.FRAME_NUMBER, frame)
    item.setData(ItemDataTypes.REGION_INDEX, region)
    item.setData(ItemDataTypes.CROSS_CENTRE, centre)
    item.setPen(pen)
    item.setZValue(1.0)

    return item

def list_to_g_line(line, pen):
    """
    convert the data in a list to a graphics line
        Args:
            line (list [ID, x1, y1, x2, y2, pos_x, pos_y, frame, region]) the line as list
            pen (QPen) the drawing pen
        Returns:
            QGraphicsLineItem
    """
    x1 = float(line[1])
    y1 = float(line[2])
    x2 = float(line[3])
    y2 = float(line[4])
    position_x = float(line[5])
    position_y = float(line[6])
    frame = int(line[7])
    region = int(line[8])

    position = qc.QPointF(position_x, position_y)

    item = qw.QGraphicsLineItem(x1, y1, x2, y2)
    item.setPos(position)
    item.setData(ItemDataTypes.ITEM_TYPE, MarkerTypes.LINE)
    item.setData(ItemDataTypes.FRAME_NUMBER, frame)
    item.setData(ItemDataTypes.REGION_INDEX, region)
    item.setPen(pen)
    item.setZValue(1.0)

    return item

def get_rect_even_dimensions(rect_item, even_dimensions=True):
    """
    get the the graphics rectangle of the item, moved to position, with sides of even length
        Args:
            rect_item (QGraphicsRectItem)
            even_dimensions (bool): if False even dimensions are not enforced
        Returns
            (QRect): with even length sides
    """
    rect = rect_item.rect().toAlignedRect()
    pos = rect_item.pos().toPoint()
    rect.translate(pos)
    width = rect.width()
    height = rect.height()

    if not even_dimensions:
        return rect

    if width%2 == 1:
        rect.setWidth(width+1)

    if height%2 == 1:
        rect.setHeight(height+1)

    return rect
def compare_lines(first, second):
    """
    compare the lines withing two line items
        Args:
            first (QGraphicsLineItem):
            second (QGraphicsLineItem)
    """
    return first.line() == second.line()

def compare_points(first, second):
    """
    compare the points withing two line items
        Args:
            first (QGraphicsLineItem):
            second (QGraphicsLineItem)
    """
    return get_point_of_point(first) == get_point_of_point(second)
