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


# def arc(center_xy, radius, start_angle, end_angle):
#     return Part.ArcOfCircle(Part.Circle(App.Vector(center_xy[0], center_xy[1], 0),
#                                  App.Vector(0, 0, 1), radius),
#                      start_angle, end_angle)

def build_nozzle(
        throat_radius=10.87 / 2,
        inflection_angle_deg=30.0,
        exit_angle_deg=12,
        nozzle_expansion_ratio=3.7,
        outside_radius=55.0 / 2,
        delta=0.25,
        delta_phi=math.radians(1)
):
    exit_radius = math.sqrt(throat_radius * throat_radius * nozzle_expansion_ratio)

    inflection_angle = math.radians(inflection_angle_deg)
    exit_angle = math.radians(exit_angle_deg)
    diverging_radius = diverging_radius_koef * throat_radius

    inflection_point = circle_point(inflection_angle, diverging_radius, 0, (1 + diverging_radius_koef) * throat_radius)

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
        x = abc[0] * sqr(y) + abc[1] * y + abc[2]

        edges.append(Part.makeLine((px, py, 0), (x, y, 0)))
        px = x
        py = y

    # back to the axis
    edges.append(Part.makeLine((px, py, 0), (px, 0, 0)))
    edges.append(Part.makeLine((px, 0, 0), (-converging_radius, 0, 0)))

    nozzle_contour = Part.Wire(edges)
    nozzle_face = Part.Face(nozzle_contour)

    return nozzle_face.revolve(App.Vector(1, 0, 0), App.Vector(360, 0, 0)), px + converging_radius, converging_radius


def chamber(port_radius,
            max_port_radius,
            grain_length,
            chamber_length=10):
    edges = []
    prev = []

    def move(x, y):
        if len(prev) > 0:
            edges.append(Part.makeLine((prev[0], prev[1], 0), (x, y, 0)))
            prev[0] = x
            prev[1] = y
        else:
            prev.append(x)
            prev.append(y)

    move(0, 0)
    move(0, max_port_radius)
    move(-chamber_length, max_port_radius)
    move(-chamber_length, port_radius)
    move(-chamber_length - grain_length, port_radius)
    move(-chamber_length - grain_length, 0)
    move(0, 0)

    chamber_wire = Part.Wire(edges)
    chamber_face = Part.Face(chamber_wire)

    return chamber_face.revolve(App.Vector(1, 0, 0), App.Vector(360, 0, 0))


def cylinder(radius, length):
    wire = Part.Wire([
        Part.makeLine((0, 0, 0), (0, radius, 0)),
        Part.makeLine((0, radius, 0), (-length, radius, 0)),
        Part.makeLine((-length, radius, 0), (-length, 0, 0)),
        Part.makeLine((-length, 0, 0), (0, 0, 0))
    ])
    face = Part.Face(wire)
    return face.revolve(App.Vector(1, 0, 0), App.Vector(360, 0, 0))



throat_radius = 10.87 / 2

nozzle, nozzle_length, converging_length = build_nozzle(throat_radius=throat_radius)

chamber = chamber(21.6 / 2, 50 / 2, 230, 10)
chamber.translate(App.Vector(-throat_radius * converging_radius_koef, 0, 0))

plug = chamber.fuse(nozzle)

outer_shell = cylinder(55 / 2, nozzle_length + 230 + 10)
outer_shell.translate(App.Vector(nozzle_length - converging_length, 0, 0))

cast = outer_shell.cut(plug)

# Part.show(cast)
# Part.show(outer_shell)

App.newDocument("Nozzle")
App.setActiveDocument("Nozzle")

nozzle_mesh = App.ActiveDocument.addObject("Mesh::Feature", "NozzleMesh")
nozzle_mesh.Mesh = MeshPart.meshFromShape(Shape=cast, MaxLength=1)
# nozzle_mesh.ViewObject.DisplayMode = "Flat Lines"

# Part.show(nozzle_mesh)

App.ActiveDocument.recompute()
Gui.ActiveDocument.ActiveView.viewAxometric()
Gui.SendMsgToActiveView("ViewFit")
