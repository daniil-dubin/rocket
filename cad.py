import math
import Part
import MeshPart
import FreeCAD as App
import FreeCADGui as Gui

# typical Rao throat parameters
converging_radius_koef = 1.5
diverging_radius_koef = 0.382


def sqr(x):
    return x * x


def circle_point(tangent_angle, radius, cx, cy):
    angle = tangent_angle - math.radians(90)
    return math.cos(angle) * radius + cx, math.sin(angle) * radius + cy


def parabola_koef(infliction_angle, exit_angle, exit_radius, inflection_point):
    infliction_tg = math.tan(infliction_angle)
    exit_tg = math.tan(exit_angle)
    y_exit = exit_radius
    a = (1.0 / exit_tg - 1.0 / infliction_tg) / 2.0 / (y_exit - inflection_point[1])
    b = 1.0 / infliction_tg - 2 * inflection_point[1] * a
    c = inflection_point[0] - sqr(inflection_point[1]) * a - inflection_point[1] * b
    return a, b, c


class Nozzle:
    def __init__(self,
                 throat_radius=10.87 / 2,
                 inflection_angle_deg=30.0,
                 exit_angle_deg=12,
                 nozzle_expansion_ratio=3.7):
        self.throat_radius = throat_radius
        self.inflection_angle_deg = inflection_angle_deg
        self.exit_angle_deg = exit_angle_deg
        self.nozzle_expansion_ratio = nozzle_expansion_ratio
        self.solid = None
        self.converging_length = None
        self.diverging_length = None
        self.exit_radius = None

    def length(self):
        return self.converging_length + self.diverging_length

    def build(self,
              delta=0.25,
              delta_phi=math.radians(2)):
        exit_radius = math.sqrt(throat_radius * throat_radius * self.nozzle_expansion_ratio)

        inflection_angle = math.radians(self.inflection_angle_deg)
        exit_angle = math.radians(self.exit_angle_deg)
        diverging_radius = diverging_radius_koef * throat_radius

        inflection_point = circle_point(inflection_angle, diverging_radius, 0,
                                        (1 + diverging_radius_koef) * throat_radius)

        edges = []

        # converging arc

        converging_radius = throat_radius * converging_radius_koef
        converging_circle_center = 0, throat_radius + converging_radius

        x = 0
        y = converging_circle_center[1]

        px = -converging_radius
        py = 0

        phi = math.radians(180)

        while phi <= math.radians(270):
            x = math.cos(phi) * converging_radius + converging_circle_center[0]
            y = math.sin(phi) * converging_radius + converging_circle_center[1]

            edges.append(Part.makeLine((px, py, 0), (x, y, 0)))
            px = x
            py = y

            phi = phi + delta_phi

        # diverging arc
        diverging_circle_center = 0, throat_radius + diverging_radius

        while y < inflection_point[1]:
            x = math.cos(phi) * diverging_radius + diverging_circle_center[0]
            y = math.sin(phi) * diverging_radius + diverging_circle_center[1]

            edges.append(Part.makeLine((px, py, 0), (x, y, 0)))
            px = x
            py = y

            phi = phi + delta_phi

        # diverging parabola
        abc = parabola_koef(inflection_angle, exit_angle, exit_radius, inflection_point)

        while y <= exit_radius:
            y = py + delta
            ny = min(y, exit_radius)
            x = abc[0] * sqr(ny) + abc[1] * ny + abc[2]

            edges.append(Part.makeLine((px, py, 0), (x, ny, 0)))
            px = x
            py = ny

        # back to the axis
        edges.append(Part.makeLine((px, py, 0), (px, 0, 0)))
        edges.append(Part.makeLine((px, 0, 0), (-converging_radius, 0, 0)))

        nozzle_contour = Part.Wire(edges)
        nozzle_face = Part.Face(nozzle_contour)

        self.solid = nozzle_face.revolve(App.Vector(1, 0, 0), App.Vector(360, 0, 0))
        self.converging_length = converging_radius
        self.diverging_length = px
        self.exit_radius = exit_radius


class Sketch:
    def __init__(self, x0, y0):
        self.edges = []
        self.x0 = x0
        self.y0 = y0
        self.px = x0
        self.py = y0

    def close(self):
        self.mv(self.x0, self.y0)

    def mv_x(self, x):
        self.mv(x, self.py)

    def mv_dx(self, dx):
        self.mv_x(self.px + dx)

    def mv_dy(self, dy):
        self.mv_y(self.py + dy)

    def mv_y(self, y):
        self.mv(self.px, y)

    def mv(self, x, y):
        if self.px != x or self.py != y:
            self.edges.append(Part.makeLine((self.px, self.py, 0), (x, y, 0)))
            self.px = x
            self.py = y

    def to_wire(self):
        return Part.Wire(self.edges)

    def to_face(self):
        return Part.Face(self.to_wire())

    def circle(self, center, radius, angle_from, angle_to, delta_angle=5):
        phi = angle_from
        while phi < angle_to:
            rad = math.radians(phi)
            self.mv(math.cos(rad) * radius + center[0],
                    math.sin(rad) * radius + center[1])
            phi = phi + delta_angle

        rad = math.radians(angle_to)
        self.mv(math.cos(rad) * radius + center[0],
                math.sin(rad) * radius + center[1])

    def circle_offset(self, center_offset, radius, angle_from, angle_to, delta_angle=5):
        self.circle([self.px + center_offset[0], self.py + center_offset[1]], radius, angle_from, angle_to, delta_angle)


def chamber(port_radius,
            max_port_radius,
            grain_length,
            chamber_length=10,
            rounding_radius=3):
    sketch = Sketch(0, 0)
    sketch.mv_y(max_port_radius - rounding_radius)
    sketch.circle_offset([-rounding_radius, 0], rounding_radius, 0, 90, 10)
    sketch.mv_dx(-(chamber_length - 2 * rounding_radius))
    sketch.circle_offset([0, -rounding_radius], rounding_radius, 90, 180, 10)
    sketch.mv_y(port_radius)
    sketch.mv_x(-chamber_length - grain_length)
    sketch.mv_y(0)
    sketch.close()

    chamber_face = Part.Face(sketch.to_face())

    return chamber_face.revolve(App.Vector(1, 0, 0), App.Vector(360, 0, 0))


def build_nozzle_outer_shell(max_port_radius,
                             chamber_length,
                             nozzle,
                             wall_thickness,
                             socket_depth,
                             cone_height):
    sketch = Sketch(nozzle.diverging_length + cone_height, 0)
    sketch.mv_y(nozzle.exit_radius * 0.7 + wall_thickness)
    sketch.mv(nozzle.diverging_length, nozzle.exit_radius + wall_thickness)
    sketch.mv_x(0)
    sketch.mv(-nozzle.converging_length, max_port_radius + wall_thickness * 2)
    sketch.mv_dx(-chamber_length - socket_depth)
    sketch.mv_y(0)
    sketch.close()

    face = sketch.to_face()
    return face.revolve(App.Vector(1, 0, 0), App.Vector(360, 0, 0))


def build_grain_outer_shell(port_radius,
                            max_port_radius,
                            chamber_length,
                            nozzle,
                            grain_length,
                            wall_thickness,
                            socket_depth,
                            chamber_rounding_radius):
    sketch = Sketch(-nozzle.converging_length - (chamber_length - chamber_rounding_radius), 0)

    sketch.mv_y(max_port_radius + wall_thickness)
    sketch.mv_dx(-socket_depth - chamber_rounding_radius)
    sketch.mv_y(port_radius + wall_thickness)
    sketch.mv_x(-nozzle.converging_length - chamber_length - grain_length)
    sketch.mv_y(0)
    sketch.close()

    face = sketch.to_face()
    return face.revolve(App.Vector(1, 0, 0), App.Vector(360, 0, 0))


def build_single_shell(max_port_radius,
                       chamber_length,
                       nozzle,
                       wall_thickness,
                       socket_depth,
                       cone_height):
    sketch = Sketch(nozzle.diverging_length + cone_height, 0)
    sketch.mv_y(max_port_radius + wall_thickness)
    sketch.mv(nozzle.diverging_length, nozzle.exit_radius + wall_thickness)
    sketch.mv_x(0)
    sketch.mv(-nozzle.converging_length, max_port_radius + wall_thickness * 2)
    sketch.mv_dx(-chamber_length - socket_depth)
    sketch.mv_y(0)
    sketch.close()

    face = sketch.to_face()
    return face.revolve(App.Vector(1, 0, 0), App.Vector(360, 0, 0))


# CONFIGURATION

# nozzle
throat_radius = 10.87 / 2
inflection_angle_deg = 30.0
exit_angle_deg = 12
nozzle_expansion_ratio = 3.7

# chamber
port_radius = 21.6 / 2
max_port_radius = 40 / 2
grain_length = 230
chamber_length = 10
chamber_rounding_radius = 3

# cast
wall_thickness = 3
socket_depth = 15
cone_height = 10

# building
nozzle = Nozzle(throat_radius, inflection_angle_deg, exit_angle_deg, nozzle_expansion_ratio)
nozzle.build()

chamber = chamber(port_radius,
                  max_port_radius,
                  grain_length,
                  chamber_length,
                  chamber_rounding_radius)

chamber.translate(App.Vector(-nozzle.converging_length, 0, 0))

cone = Part.makeCone(nozzle.exit_radius, nozzle.exit_radius * 0.7, cone_height,
                     App.Vector(nozzle.diverging_length, 0, 0), App.Vector(1, 0, 0))

plug = chamber.fuse(nozzle.solid).fuse(cone)

nozzle_outer_shell = build_nozzle_outer_shell(max_port_radius=max_port_radius,
                                              chamber_length=chamber_length,
                                              nozzle=nozzle,
                                              wall_thickness=wall_thickness,
                                              socket_depth=socket_depth,
                                              cone_height=cone_height)

grain_outer_shell = build_grain_outer_shell(port_radius,
                                            max_port_radius,
                                            chamber_length,
                                            nozzle,
                                            grain_length,
                                            wall_thickness,
                                            socket_depth,
                                            chamber_rounding_radius)

# Part.show(plug)
# Part.show(nozzle_outer_shell)
# Part.show(grain_outer_shell)

cast_grain = grain_outer_shell.cut(plug)
cast_nozzle = nozzle_outer_shell.cut(plug).cut(grain_outer_shell)

box = Part.makeBox(1000, 1000, 1000)
box.translate(App.Vector(-500, -500, -1000))

cast_grain_half = cast_grain.cut(box)
cast_nozzle_half = cast_nozzle.cut(box)

# Part.show(cast_grain_half)
# Part.show(cast_nozzle_half)

App.newDocument("NozzleCast")
App.setActiveDocument("NozzleCast")

nozzle_cast_mesh = App.ActiveDocument.addObject("Mesh::Feature", "NozzleCastMesh")
nozzle_cast_mesh.Mesh = MeshPart.meshFromShape(Shape=cast_nozzle_half, MaxLength=1)

grain_cast_mesh = App.ActiveDocument.addObject("Mesh::Feature", "GrainCastMesh")
grain_cast_mesh.Mesh = MeshPart.meshFromShape(Shape=cast_grain_half, MaxLength=1)

App.ActiveDocument.recompute()
Gui.ActiveDocument.ActiveView.viewAxometric()
Gui.SendMsgToActiveView("ViewFit")
