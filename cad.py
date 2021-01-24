import math
import Part
import MeshPart
import FreeCAD as App
import FreeCADGui as Gui


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


def build_nozzle(
        throat_radius=10.87 / 2,
        inflection_angle_deg=30.0,
        exit_angle_deg=12,
        nozzle_expansion_ratio=3.7,
        outside_radius=55.0 / 2,
        delta=0.25
):
    exit_radius = math.sqrt(throat_radius * throat_radius * nozzle_expansion_ratio)

    # typical Rao throat parameters
    converging_radius_koef = 1.5
    diverging_radius_koef = 0.382

    inflection_angle = math.radians(inflection_angle_deg)
    exit_angle = math.radians(exit_angle_deg)
    diverging_radius = diverging_radius_koef * throat_radius

    inflection_point = circle_point(inflection_angle, diverging_radius, 0, (1 + diverging_radius_koef) * throat_radius)
    abc = parabola_koef(inflection_angle, exit_angle, exit_radius, inflection_point)

    # converging part

    converging_radius = throat_radius * converging_radius_koef
    circle_center = 0, throat_radius + converging_radius

    edges = []

    x = 0
    y = circle_center[1]

    px = -converging_radius
    py = 0

    while True:
        y = y - delta

        if y < throat_radius:
            break
        else:
            x = - math.sqrt(sqr(converging_radius) - sqr(y - circle_center[1]))

        edges.append(Part.makeLine((px, py, 0), (x, y, 0)))
        px = x
        py = y

    # diverging part
    while True:
        y = py + delta

        if y > exit_radius:
            break
        else:
            if y < inflection_point[1]:
                # circle
                x = math.sqrt(sqr(diverging_radius) - sqr(y - (throat_radius + diverging_radius)))
            else:
                # parabola
                x = abc[0] * sqr(y) + abc[1] * y + abc[2]

        edges.append(Part.makeLine((px, py, 0), (x, y, 0)))
        px = x
        py = y

    # back to the axis
    edges.append(Part.makeLine((px, py, 0), (px, 0, 0)))
    edges.append(Part.makeLine((px, 0, 0), (-converging_radius, 0, 0)))

    nozzle_contour = Part.Wire(edges)
    nozzle_face = Part.Face(nozzle_contour)

    return nozzle_face.revolve(App.Vector(1, 0, 0), App.Vector(360, 0, 0))


nozzle = build_nozzle()

App.newDocument("Nozzle")
App.setActiveDocument("Nozzle")

nozzle_mesh = App.ActiveDocument.addObject("Mesh::Feature", "NozzleMesh")
nozzle_mesh.Mesh = MeshPart.meshFromShape(Shape=nozzle, MaxLength=1)
# nozzle_mesh.ViewObject.DisplayMode = "Flat Lines"

# Part.show(nozzle_mesh)

App.ActiveDocument.recompute()
Gui.ActiveDocument.ActiveView.viewAxometric()
Gui.SendMsgToActiveView("ViewFit")
