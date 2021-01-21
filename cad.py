import math
import Part
import MeshPart

rt = 10.87 / 2
inflection_angle_deg = 30.0
exit_angle_deg = 12
nozzle_expansion_ratio = 3.7

delta = 0.01

exit_radius = math.sqrt(rt * rt * nozzle_expansion_ratio)

outside_radius = 55.0 / 2

# converging_radius_koef = 1.5
diverging_radius_koef = 0.382

inflection_angle = math.radians(inflection_angle_deg)
exit_angle = math.radians(exit_angle_deg)
diverging_radius = diverging_radius_koef * rt


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

xy_i = circle_point(inflection_angle, diverging_radius, 0, (1 + diverging_radius_koef) * rt)
abc = parabola_koef(inflection_angle, exit_angle, exit_radius, xy_i)

# converging part

y = outside_radius
converging_radius = outside_radius - rt

px = -converging_radius
# py = outside_radius
py = 0

edges = []

x = 0

while True:
    y = y - delta

    if y < rt:
        break
    else:
        x = - math.sqrt(sqr(converging_radius) - sqr(y - outside_radius))

    edges.append(Part.makeLine((px, py, 0), (x, y, 0)))
    px = x
    py = y

# diverging part
while True:
    y = py + delta

    if y > exit_radius:
        break
    else:
        if y < xy_i[1]:
            # circle
            x = math.sqrt(sqr(diverging_radius) - sqr(y - (rt + diverging_radius)))
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

nozzle = nozzle_face.revolve(FreeCAD.Vector(1, 0, 0), FreeCAD.Vector(360, 0, 0))

App.newDocument("Nozzle")
App.setActiveDocument("Nozzle")

nozzle_mesh = FreeCAD.ActiveDocument.addObject("Mesh::Feature", "NozzleMesh")
nozzle_mesh.Mesh = MeshPart.meshFromShape(Shape=nozzle, MaxLength=1)
nozzle_mesh.ViewObject.DisplayMode = "Flat Lines"

# Part.show(nozzle_mesh)

App.ActiveDocument.recompute()
Gui.ActiveDocument.ActiveView.viewAxometric()
Gui.SendMsgToActiveView("ViewFit")
