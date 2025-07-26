"""
Some methods to generate some paths / patterns programmatically.
(e.g. some that involve repition or are based on math / geometrical formula.
"""

import math


def gear_path(n, R, r, f=0.3):
    """
    Generates SVG path data for a cogwheel with n teeth,
    outer radius R, inner radius r, and tooth ratio f.
    Sweep flags are set to make the arcs convex.
    """
    pitch = (2 * math.pi) / n
    tip_angle = pitch * f
    # Start at -tip_angle/2 on the outer radius
    theta0 = -tip_angle / 2
    x0 = R * math.cos(theta0)
    y0 = R * math.sin(theta0)
    d = [f"M {x0:.3f},{y0:.3f}"]
    for i in range(n):
        a1 = i * pitch + tip_angle / 2
        a2 = (i + 1) * pitch - tip_angle / 2
        x1, y1 = R * math.cos(a1), R * math.sin(a1)
        x2, y2 = r * math.cos(a1), r * math.sin(a1)
        x3, y3 = r * math.cos(a2), r * math.sin(a2)
        x4, y4 = R * math.cos(a2), R * math.sin(a2)
        # 1) outer arc (convex): sweep-flag=0
        d.append(f"A {R:.3f},{R:.3f} 0 0,0 {x1:.3f},{y1:.3f}")
        # 2) radial to the root
        d.append(f"L {x2:.3f},{y2:.3f}")
        # 3) root arc (convex inside): sweep-flag=1
        d.append(f"A {r:.3f},{r:.3f} 0 0,1 {x3:.3f},{y3:.3f}")
        # 4) radial back to the outer radius
        d.append(f"L {x4:.3f},{y4:.3f}")
    d.append("Z")
    return " ".join(d)


def gear_path_flat(n, R, r, f=0.3):
    """
    Generates SVG path data for a cogwheel with n teeth,
    outer radius R, inner radius r, and tooth ratio f.
    Outer arc is flat line.
    """
    pitch = (2 * math.pi) / n
    tip_angle = pitch * f
    # Start at -tip_angle/2 on the outer radius
    theta0 = -tip_angle / 2
    x0 = R * math.cos(theta0)
    y0 = R * math.sin(theta0)
    d = [f"M {x0:.3f},{y0:.3f}"]
    for i in range(n):
        a1 = i * pitch + tip_angle / 2
        a2 = (i + 1) * pitch - tip_angle / 2
        x1, y1 = R * math.cos(a1), R * math.sin(a1)
        x2, y2 = r * math.cos(a1), r * math.sin(a1)
        x3, y3 = r * math.cos(a2), r * math.sin(a2)
        x4, y4 = R * math.cos(a2), R * math.sin(a2)
        # 1) Straight line to the top (instead of Arc)
        d.append(f"L {x1:.3f},{y1:.3f}")
        # 2) radial to the root
        d.append(f"L {x2:.3f},{y2:.3f}")
        # 3) root arc
        d.append(f"A {r:.3f},{r:.3f} 0 0,1 {x3:.3f},{y3:.3f}")
        # 4) radial back to the outer circle
        d.append(f"L {x4:.3f},{y4:.3f}")
    d.append("Z")
    return " ".join(d)


def main():
    # path generation
    path_data = gear_path_flat(8, 50, 40, f=0.5)
    print(path_data)


if __name__ == "__main__":
    main()
