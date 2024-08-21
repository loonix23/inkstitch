# Authors: see git history
#
# Copyright (c) 2010 Authors
# Licensed under the GNU GPL version 3.0 or later.  See the file LICENSE for details.

import os
import sys
from copy import deepcopy
from random import random
from typing import List

import inkex
from shapely import geometry as shgeo
from shapely import get_coordinates

from .i18n import N_, _
from .svg import (apply_transforms, generate_unique_id,
                  get_correction_transform, get_document, get_node_transform)
from .svg.svg import copy_no_children, point_upwards
from .svg.tags import (CONNECTION_END, CONNECTION_START, CONNECTOR_TYPE,
                       INKSCAPE_LABEL, INKSTITCH_ATTRIBS, SVG_SYMBOL_TAG,
                       SVG_USE_TAG, XLINK_HREF)
from .utils import Point, cache, get_bundled_dir

COMMANDS = {
    # L10N command attached to an object
    "fill_start": N_("Fill stitch starting position"),

    # L10N command attached to an object
    "fill_end": N_("Fill stitch ending position"),

    # L10N command attached to an object
    "ripple_target": N_("Target position"),

    # L10N command attached to an object
    "run_start": N_("Auto-route running stitch starting position"),

    # L10N command attached to an object
    "run_end": N_("Auto-route running stitch ending position"),

    # L10N command attached to an object
    "satin_start": N_("Auto-route satin stitch starting position"),

    # L10N command attached to an object
    "satin_end": N_("Auto-route satin stitch ending position"),

    # L10N command attached to an object
    "stop": N_("Stop (pause machine) after sewing this object"),

    # L10N command attached to an object
    "trim": N_("Trim thread after sewing this object"),

    # L10N command attached to an object
    "ignore_object": N_("Ignore this object (do not stitch)"),

    # L10N command attached to an object
    "satin_cut_point": N_("Satin cut point (use with Cut Satin Column)"),

    # L10N command that affects a layer
    "ignore_layer": N_("Ignore layer (do not stitch any objects in this layer)"),

    # L10N command that affects entire document
    "origin": N_("Origin for exported embroidery files"),

    # L10N command that affects entire document
    "stop_position": N_("Jump destination for Stop commands (a.k.a. \"Frame Out position\")."),
}

OBJECT_COMMANDS = ["fill_start", "fill_end", "ripple_target", "run_start", "run_end", "satin_start", "satin_end",
                   "stop", "trim", "ignore_object", "satin_cut_point"]
FREE_MOVEMENT_OBJECT_COMMANDS = ["run_start", "run_end", "satin_start", "satin_end"]
LAYER_COMMANDS = ["ignore_layer"]
GLOBAL_COMMANDS = ["origin", "stop_position"]


class CommandParseError(Exception):
    pass


class BaseCommand(object):
    @property
    @cache
    def description(self):
        return get_command_description(self.command)

    def parse_symbol(self):
        if self.symbol.tag != SVG_SYMBOL_TAG:
            raise CommandParseError("use points to non-symbol")

        self.command = self.symbol.get('id')

        if self.command.startswith('inkstitch_'):
            self.command = self.command[10:]
            # It is possible that through copy paste or whatever user action a command is defined multiple times
            # in the defs section. In this case the id will be altered with an additional number (e.g. inkstitch_trim-5)
            # Let's make sure to remove the number part to recognize the command correctly
            self.command = self.command.split("-")[0]
        else:
            raise CommandParseError("symbol is not an Ink/Stitch command")

    def get_node_by_url(self, url):
        # url will be #path12345.  Find the corresponding object.
        if url is None:
            raise CommandParseError("url is None")

        if not url.startswith('#'):
            raise CommandParseError("invalid connection url: %s" % url)

        id = url[1:]

        try:
            return self.svg.xpath(".//*[@id='%s']" % id)[0]
        except (IndexError, AttributeError):
            raise CommandParseError("could not find node by url %s" % id)


class Command(BaseCommand):
    def __init__(self, connector):
        self.connector: inkex.Path = connector
        self.svg = self.connector.getroottree().getroot()

        self.parse_command()

    def parse_connector_path(self):
        path = inkex.paths.Path(self.connector.get('d')).to_superpath()
        return apply_transforms(path, self.connector)

    def parse_command(self):
        path = self.parse_connector_path()
        if len(path) == 0:
            raise CommandParseError("connector has no path information")

        neighbors = [
            (self.get_node_by_url(self.connector.get(CONNECTION_START)), path[0][0][1]),
            (self.get_node_by_url(self.connector.get(CONNECTION_END)), path[0][-1][1])
        ]

        self.symbol_is_end = neighbors[0][0].tag != SVG_USE_TAG
        if self.symbol_is_end:
            neighbors.reverse()

        if neighbors[0][0].tag != SVG_USE_TAG:
            raise CommandParseError("connector does not point to a use tag")

        self.use = neighbors[0][0]

        self.symbol = self.get_node_by_url(neighbors[0][0].get(XLINK_HREF))
        self.parse_symbol()

        self.target: inkex.BaseElement = neighbors[1][0]
        self.target_point = neighbors[1][1]

    def __repr__(self):
        return "Command('%s', %s)" % (self.command, self.target_point)

    def clone(self, new_target: inkex.BaseElement) -> inkex.BaseElement:
        """
        Clone this command and point it to the new target, positioning it relative to the new target the same as the target
        """
        group: inkex.BaseElement = self.connector.getparent()
        transform_relative_to_target = -self.target.composed_transform() @ group.composed_transform()

        # Clone group
        cloned_group = copy_no_children(self.connector.getparent())
        cloned_group.transform = new_target.transform @ transform_relative_to_target
        new_target.getparent().append(cloned_group)

        symbol = copy_no_children(self.use)
        cloned_group.append(symbol)
        point_upwards(symbol)

        # Copy connector
        connector = copy_no_children(self.connector)
        cloned_group.insert(0, connector)
        if self.symbol_is_end:
            symbol_attr = CONNECTION_END
            target_attr = CONNECTION_START
        else:
            symbol_attr = CONNECTION_START
            target_attr = CONNECTION_END
        connector.set(symbol_attr, f"#{symbol.get_id()}")
        connector.set(target_attr, f"#{new_target.get_id()}")

        return cloned_group


class StandaloneCommand(BaseCommand):
    def __init__(self, use):
        self.node = use
        self.svg = self.node.getroottree().getroot()

        self.parse_command()

    def parse_command(self):
        self.symbol = self.get_node_by_url(self.node.get(XLINK_HREF))

        if self.symbol.tag != SVG_SYMBOL_TAG:
            raise CommandParseError("use points to non-symbol")

        self.parse_symbol()

    @property
    @cache
    def point(self):
        pos = [float(self.node.get("x", 0)), float(self.node.get("y", 0))]
        transform = get_node_transform(self.node)
        pos = inkex.transforms.Transform(transform).apply_to_point(pos)

        return Point(*pos)


def get_command_description(command: str) -> str:
    return COMMANDS[command]


def point_command_symbols_up(node: inkex.BaseElement) -> None:
    """
    Find all command symbols in the subtree and alter their transformations so they're pointing upwards.
    """
    xpath = ".//svg:use"
    uses = node.xpath(xpath, namespaces=inkex.NSS)
    for use in uses:
        if use.href.get('id').startswith('inkstitch_'):
            point_upwards(use)


def find_commands(node: inkex.BaseElement) -> List[Command]:
    """Find the symbols this node is connected to and return them as Commands"""

    # find all paths that have this object as a connection
    id = node.get('id')
    xpath = f".//*[@inkscape:connection-start='#{id}' or @inkscape:connection-end='#{id}']"
    connectors = node.getroottree().getroot().xpath(xpath, namespaces=inkex.NSS)

    # try to turn them into commands
    commands = []
    for connector in connectors:
        try:
            commands.append(Command(connector))
        except CommandParseError:
            # Parsing the connector failed, meaning it's not actually an Ink/Stitch command.
            pass

    return commands


def layer_commands(layer, command):
    """Find standalone (unconnected) command symbols in this layer."""

    for global_command in global_commands(layer.getroottree().getroot(), command):
        if layer in global_command.node.iterancestors():
            yield global_command


def global_commands(svg, command):
    """Find standalone (unconnected) command symbols anywhere in the document."""

    for standalone_command in _standalone_commands(svg):
        if standalone_command.command == command:
            yield standalone_command


@cache
def global_command(svg, command):
    """Find a single command of the specified type.

    If more than one is found, print an error and exit.
    """

    commands = list(global_commands(svg, command))

    if len(commands) == 1:
        return commands[0]
    elif len(commands) > 1:
        print(_("Error: there is more than one %(command)s command in the document, but there can only be one.  "
                "Please remove all but one.") % dict(command=command), file=sys.stderr)

        # L10N This is a continuation of the previous error message, letting the user know
        # what command we're talking about since we don't normally expose the actual
        # command name to them.  Contents of %(description)s are in a separate translation
        # string.
        print(_("%(command)s: %(description)s") % dict(command=command, description=_(get_command_description(command))), file=sys.stderr)

        sys.exit(1)
    else:
        return None


def _standalone_commands(svg):
    """Find all unconnected command symbols in the SVG."""

    xpath = ".//svg:use[starts-with(@xlink:href, '#inkstitch_')]"
    symbols = svg.xpath(xpath, namespaces=inkex.NSS)

    for symbol in symbols:
        try:
            yield StandaloneCommand(symbol)
        except CommandParseError:
            pass


def is_command(node):
    return CONNECTION_START in node.attrib or CONNECTION_END in node.attrib


def is_command_symbol(node):
    symbol = None
    xlink = node.get(XLINK_HREF, "")
    if xlink.startswith("#inkstitch_"):
        symbol = node.get(XLINK_HREF)[11:]
    return symbol in COMMANDS


@cache
def symbols_path():
    return os.path.join(get_bundled_dir("symbols"), "inkstitch.svg")


@cache
def symbols_svg():
    with open(symbols_path()) as symbols_file:
        return inkex.load_svg(symbols_file).getroot()


@cache
def symbol_defs():
    return symbols_svg().defs


@cache
def ensure_symbol(svg, command):
    """Make sure the command's symbol definition exists in the <svg:defs> tag."""

    # using @cache really just makes sure that we don't bother ensuring the
    # same symbol is there twice, which would be wasted work

    path = "./*[@id='inkstitch_%s']" % command
    defs = svg.defs
    if defs.find(path) is None:
        defs.append(deepcopy(symbol_defs().find(path)))


def add_group(document, node, command):
    parent = node.getparent()
    description = _(get_command_description(command))
    group = inkex.Group(attrib={
        "id": generate_unique_id(document, "command_group"),
        INKSCAPE_LABEL: _("Ink/Stitch Command") + f": {description}",
        "transform": get_correction_transform(node)
    })
    parent.insert(parent.index(node) + 1, group)
    return group


def add_connector(document, symbol, command, element):
    # "I'd like it if I could position the connector endpoint nicely but inkscape just
    # moves it to the element's center immediately after the extension runs." - Lex Neva, rev. 4baced7085
    # "Maybe we should have the target point be a seperately-moveable node? Sometimes moving the command
    # node so the line drawn from the command to the centroid of the target is awkward anyway?" - CapellanCitizen

    # Inkscape will draw this connector line from the bounding box center of the two nodes, but
    # will stop at the first intersection with the path it's pointing to. It is necessary to
    # compute the target point accurately to what inkscape will do.
    # If not, then the target position will change when the document is loaded by inkscape and break.
    # For example, not doing this caused issues when implementing commands attached to clones.
    start_pos = (symbol.get('x'), symbol.get('y'))
    centroid_pos = element.node.bounding_box(inkex.Transform(get_node_transform(element.node.getparent()))).center
    connector_line = shgeo.LineString([start_pos, centroid_pos])
    if connector_line.intersects(element.shape):
        end_pos = get_coordinates(connector_line.intersection(element.shape))[0]
    else:
        # Sometimes the line won't intersect anything and will go straight to the centroid.
        end_pos = centroid_pos

    # Make sure the element's XML node has an id so that we can reference it.
    if element.node.get('id') is None:
        element.node.set('id', document.get_unique_id("object"))

    path = inkex.PathElement(attrib={
        "id": generate_unique_id(document, "command_connector"),
        "d": f"M {start_pos[0]},{start_pos[1]} {end_pos[0]},{end_pos[1]}",
        "style": "stroke:#000000;stroke-width:1px;stroke-opacity:0.5;fill:none;",
        CONNECTION_START: f"#{symbol.get('id')}",
        CONNECTION_END: f"#{element.node.get('id')}",

        # l10n: the name of the line that connects a command to the object it applies to
        INKSCAPE_LABEL: _("connector")
    })

    if command not in FREE_MOVEMENT_OBJECT_COMMANDS:
        path.attrib[CONNECTOR_TYPE] = "polyline"

    symbol.getparent().insert(0, path)


def add_symbol(document, group, command, pos):
    symbol = inkex.Use(attrib={
        "id": document.get_unique_id("command_use"),
        XLINK_HREF: "#inkstitch_%s" % command,
        "height": "100%",
        "width": "100%",
        "x": str(pos.x),
        "y": str(pos.y),

        # l10n: the name of a command symbol (example: scissors icon for trim command)
        INKSCAPE_LABEL: _("command marker"),
    })
    group.append(symbol)

    return symbol


def get_command_pos(element, index, total):
    # Put command symbols 30 pixels out from the shape, spaced evenly around it.

    # get a line running 30 pixels out from the shape

    if not isinstance(element.shape.buffer(30), shgeo.MultiPolygon):
        outline = element.shape.buffer(30).exterior
    else:
        polygons = element.shape.buffer(30).geoms
        polygon = polygons[len(polygons)-1]
        outline = polygon.exterior

    # find the top center point on the outline and start there
    top_center = shgeo.Point(outline.centroid.x, outline.bounds[1])
    start_position = outline.project(top_center, normalized=True)

    # pick this item's spot around the outline and perturb it a bit to avoid
    # stacking up commands if they add commands multiple times
    position = index / float(total)
    position += random() * 0.05
    position += start_position

    return outline.interpolate(position, normalized=True)


def remove_legacy_param(element, command):
    if command == "trim" or command == "stop":
        # If they had the old "TRIM after" or "STOP after" attributes set,
        # automatically delete them.  The new commands will do the same
        # thing.
        #
        # If we didn't delete these here, then things would get confusing.
        # If the user were to delete a "trim" symbol added by this extension
        # but the "embroider_trim_after" attribute is still set, then the
        # trim would keep happening.

        attribute = "embroider_%s_after" % command

        if attribute in element.node.attrib:
            del element.node.attrib[attribute]

        # Attributes have changed to be namespaced.
        # Let's check for them as well, they might have automatically changed.
        attribute = INKSTITCH_ATTRIBS["%s_after" % command]

        if attribute in element.node.attrib:
            del element.node.attrib[attribute]


def add_commands(element, commands, pos=None):
    svg = get_document(element.node)

    for i, command in enumerate(commands):
        ensure_symbol(svg, command)
        remove_legacy_param(element, command)

        group = add_group(svg, element.node, command)
        position = pos
        if position is None:
            position = get_command_pos(element, i, len(commands))

        symbol = add_symbol(svg, group, command, position)
        add_connector(svg, symbol, command, element)


def add_layer_commands(layer, commands):
    svg = layer.root

    if not layer.tag_name == 'svg':
        correction_transform = get_correction_transform(layer)
    else:
        # No layer selected while trying to include only layer commands: return a error message and exit
        # Since global and layer commands will not be inserted at the same time, we can check the first command only
        if commands[0] in LAYER_COMMANDS:
            inkex.errormsg(_('Please select a layer to include layer commands.'))
            sys.exit(1)

        # global commands do not necesarrily need a layer
        correction_transform = ''

    for i, command in enumerate(commands):
        ensure_symbol(svg, command)
        description = _(get_command_description(command))
        layer.append(inkex.Use(attrib={
            "id": generate_unique_id(svg, "use"),
            INKSCAPE_LABEL: _("Ink/Stitch Command") + f": {description}",
            XLINK_HREF: "#inkstitch_%s" % command,
            "height": "100%",
            "width": "100%",
            "x": str(i * 20),
            "y": "-10",
            "transform": correction_transform
        }))
