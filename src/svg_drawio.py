"""Some methods to ease the conversion of SVG paths
to the Draw-IO-XML shape format."""

import math
import os
import re
import xml.etree.ElementTree as ET

from typing import List, Tuple, TypeAlias

EXAMPLE_SVG = os.path.join("..", "examples", "Example.svg")
NUM_RE = re.compile(
    r"""[+-]?              # optional sign
        (?:\d*\.\d+|\d+)   # real or integer
        (?:[eE][+-]?\d+)?  # optional exponent
    """,
    re.VERBOSE,
)

PathSegment: TypeAlias = Tuple[str, List[float]]
NormalizedPath: TypeAlias = List[PathSegment]


def normalize_path(d: str) -> NormalizedPath:
    """
    Normalize a path, i.e. a path d attribute that contains
    relative commands is converted to absolute commands.
    Horizontal/Vertical (hHvV) -> Line
    Commands with relative coordinates (mlcqa->MLCQA)

    # Example:
    normalized = normalize_path(EXAMPLE_RELATIVE_D)
    for cmd, pts in normalized:
        print(cmd, pts)
    """
    if re.search(r"[^0-9\s,.\-+eE MmLlHhVvCcSsQqTtAaZz]", d):
        raise ValueError(f"Path contains invalid characters: {d}")
    if re.search(r"(?<![0-9.\-+eE])[eE](?![0-9])", d):
        raise ValueError(f"Invalid 'E' outside of scientific notation: {d}")
    # Regex: Command char + all following numbers/separators
    tokens = re.findall(r"([MmLlHhVvCcSsQqTtAaZz])([^MmLlHhVvCcSsQqTtAaZz]*)", d)

    cx = cy = 0.0  # current point
    sx = sy = 0.0  # starting point for 'Z'
    out: List[Tuple[str, List[float]]] = []
    last_cmd = ""
    last_x2 = last_y2 = 0.0  # for C/S
    last_q_x1 = last_q_y1 = 0.0  # for Q/T

    def to_floats(s: str) -> List[float]:
        # split on comma and whitespace
        return [float(num) for num in NUM_RE.findall(s)]

    for cmd, raw in tokens:
        pts = to_floats(raw)
        absolute = cmd.isupper()
        C = cmd.upper()

        i = 0
        # 'Z' is special: close path
        if C == "Z":
            out.append(("Z", []))
            cx, cy = sx, sy
            last_cmd = C
            continue

        # multiple segments of same type can be subsequent
        while i < len(pts):
            if C not in ["C", "S", "Q", "T"]:
                last_cmd = ""

            if C == "M":
                x, y = pts[i], pts[i + 1]
                if not absolute:
                    x += cx
                    y += cy
                cx, cy = x, y
                sx, sy = x, y
                out.append(("M", [x, y]))
                i += 2
                # if after Move more coordinates follow,
                # a Line is implictly according to SVG spec
                C = "L"
                if cmd == C:
                    # only for "M", relative "m" is possible
                    absolute = True
                cmd = "L"
            elif C == "L":
                x, y = pts[i], pts[i + 1]
                if not absolute:
                    x += cx
                    y += cy
                cx, cy = x, y
                out.append(("L", [x, y]))
                i += 2
            elif C == "H":
                x = pts[i]
                if not absolute:
                    x += cx
                cx = x
                out.append(("L", [x, cy]))
                i += 1
            elif C == "V":
                y = pts[i]
                if not absolute:
                    y += cy
                cy = y
                out.append(("L", [cx, y]))
                i += 1
            elif C == "C":
                # (x1,y1,x2,y2,x,y)
                seg = pts[i : i + 6]
                if len(seg) != 6:
                    raise ValueError("Curve needs 6 parameters")
                if not absolute:
                    seg = [
                        seg[0] + cx,
                        seg[1] + cy,
                        seg[2] + cx,
                        seg[3] + cy,
                        seg[4] + cx,
                        seg[5] + cy,
                    ]
                cx, cy = seg[4], seg[5]
                last_x2, last_y2 = seg[2], seg[3]
                out.append(("C", seg))
                i += 6
            elif C == "S":
                seg = pts[i : i + 4]
                if len(seg) != 4:
                    raise ValueError("Smooth curve needs 4 parameters")

                # Calculate first control point based on previous command
                if last_cmd in ["C", "S"]:
                    x1 = 2 * cx - last_x2
                    y1 = 2 * cy - last_y2
                else:
                    # No previous curve, so no reflection
                    x1, y1 = cx, cy

                x2, y, end_x, end_y = seg
                if not absolute:
                    x2 += cx
                    y += cy
                    end_x += cx
                    end_y += cy

                full_seg = [x1, y1, x2, y, end_x, end_y]
                # Output as a standard 'C' command
                out.append(("C", full_seg))

                # Update state for the *next* 'S' command
                last_x2, last_y2 = x2, y
                cx, cy = end_x, end_y
                i += 4
            elif C == "Q":
                # (x1,y1,x,y)
                seg = pts[i : i + 4]
                if len(seg) != 4:
                    raise ValueError("Quad needs 4 parameters")
                if not absolute:
                    seg = [seg[0] + cx, seg[1] + cy, seg[2] + cx, seg[3] + cy]
                last_q_x1, last_q_y1 = seg[0], seg[1]
                cx, cy = seg[2], seg[3]
                out.append(("Q", seg))
                i += 4
            elif C == "T":
                seg = pts[i : i + 2]
                if len(seg) != 2:
                    raise ValueError("Smooth quad needs 2 parameters")

                if last_cmd in ["Q", "T"]:
                    x1 = 2 * cx - last_q_x1
                    y1 = 2 * cy - last_q_y1
                else:
                    x1, y1 = cx, cy

                end_x, end_y = seg
                if not absolute:
                    end_x += cx
                    end_y += cy

                full_seg = [x1, y1, end_x, end_y]
                # Output as a standard 'Q' command
                out.append(("Q", full_seg))

                last_q_x1, last_q_y1 = x1, y1
                cx, cy = end_x, end_y
                i += 2
            elif C == "A":
                # (rx,ry,rot,large,sweep,x,y)
                seg = pts[i : i + 7]
                if len(seg) != 7:
                    raise ValueError("Arc needs 7 parameters")
                if not absolute:
                    seg = seg[:5] + [seg[5] + cx, seg[6] + cy]
                if seg[3] not in (0, 1):
                    raise ValueError("large-arg-flag is a flag and can only be 0 or 1")
                if seg[4] not in (0, 1):
                    raise ValueError("sweep-flag is a flag and can only be 0 or 1")

                cx, cy = seg[5], seg[6]
                out.append(("A", seg))
                i += 7
            else:
                raise ValueError(f"Unknown command: {cmd}")
            last_cmd = C

    return out


def normalized_to_d_path(np: NormalizedPath):
    d_path_again = ""
    for cmd, coords in np:
        d_path_again += cmd + " "
        d_path_again += " ".join([str(x) for x in coords])
        d_path_again += " "
    return d_path_again.rstrip()


def _fmt_num(n: float) -> str:
    """
    Format n to crop trailing zeros of a floating point number.
    e.g. 4.0 -> "4"  or 4.500000 -> "4.5"
    Maximum of 6 decimal places, trailing zeros and '.' are cropped.
    """
    s = f"{n:.6f}"
    s = s.rstrip("0").rstrip(".")
    return s if s else "0"


def rotate(x, y, theta, cx, cy):
    """Rotate (x,y) about (cx,cy) by theta."""
    x0, y0 = x - cx, y - cy
    xr = x0 * math.cos(theta) - y0 * math.sin(theta) + cx
    yr = x0 * math.sin(theta) + y0 * math.cos(theta) + cy
    return xr, yr


def rotate_path(path_d, theta, cx, cy):
    """Rotate given path.
    path_d: d attribute of path
    theta: angle in radians
    cx: rotation center x
    cy: rotation center y"""
    # Tokenize into commands and numbers
    tokens = re.findall(r"[MLZ]|-?\d+\.?\d*", path_d)

    new_tokens = []
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t in ("M", "L"):
            # command + two coords
            x = float(tokens[i + 1])
            y = float(tokens[i + 2])
            xr, yr = rotate(x, y, theta, cx, cy)
            new_tokens += [t, f"{xr:.6f}", f"{yr:.6f}"]
            i += 3
        elif t == "Z":
            new_tokens.append("Z")
            i += 1
        else:
            # shouldn't happen for well-formed M/L/Z only
            i += 1

    # Reassemble
    d_new = " ".join(new_tokens)
    return d_new


ALLOWED_PC_CHARS = ["M", "L", "Q", "C", "A"]
PC_PATHTYPE_MAP = {"M": "move", "L": "line", "Q": "quad", "C": "curve", "A": "arc"}
PC_NUM_ELEM_MAP = {
    "M": 2,
    "L": 2,
    "Q": 4,
    "C": 6,
    "A": 7,
}
PC_ATTR_MAP = {
    "M": ["x", "y"],
    "L": ["x", "y"],
    "Q": ["x1", "y1", "x2", "y2"],
    "C": ["x1", "y1", "x2", "y2", "x3", "y3"],
    "A": ["rx", "ry", "x-axis-rotation", "large-arc-flag", "sweep-flag", "x", "y"],
}


class TransformationMatrix:
    """
    Represents a 2D affine transformation matrix (a, b, c, d, e, f).
    [ a c e ]
    [ b d f ]
    [ 0 0 1 ]
    """

    def __init__(self, a=1, b=0, c=0, d=1, e=0, f=0):
        self.values = (a, b, c, d, e, f)

    def __matmul__(self, other):
        """Multiply this matrix with another (self @ other)."""
        a1, b1, c1, d1, e1, f1 = self.values
        a2, b2, c2, d2, e2, f2 = other.values
        a = a1 * a2 + c1 * b2
        b = b1 * a2 + d1 * b2
        c = a1 * c2 + c1 * d2
        d = b1 * c2 + d1 * d2
        e = a1 * e2 + c1 * f2 + e1
        f = b1 * e2 + d1 * f2 + f1
        return TransformationMatrix(a, b, c, d, e, f)

    def apply_to_point(self, x, y):
        """Applies the transformation to a point (x, y)."""
        a, b, c, d, e, f = self.values
        x_new = a * x + c * y + e
        y_new = b * x + d * y + f
        return x_new, y_new

    @staticmethod
    def from_string(s: str):
        """Parses an SVG transform attribute string."""
        matrix = TransformationMatrix()
        if not s:
            return matrix

        # find transformations like "translate(..)", "rotate(..)"
        transform_re = re.compile(r"(\w+)\(([^)]+)\)")
        for name, params_str in transform_re.findall(s):
            params = [float(p) for p in re.split(r"[ ,]+", params_str.strip())]
            op_matrix = TransformationMatrix()

            if name == "translate":
                tx = params[0]
                ty = params[1] if len(params) > 1 else 0
                op_matrix = TransformationMatrix(1, 0, 0, 1, tx, ty)
            elif name == "rotate":
                angle = math.radians(params[0])
                cx = params[1] if len(params) > 1 else 0
                cy = params[2] if len(params) > 2 else 0

                # Rotate: composition of  T(-cx,-cy) * R(a) * T(cx,cy)
                cos_a = math.cos(angle)
                sin_a = math.sin(angle)

                t1 = TransformationMatrix(1, 0, 0, 1, cx, cy)
                rot = TransformationMatrix(cos_a, sin_a, -sin_a, cos_a, 0, 0)
                t2 = TransformationMatrix(1, 0, 0, 1, -cx, -cy)
                op_matrix = t1 @ rot @ t2
            elif name == "matrix":
                op_matrix = TransformationMatrix(*params)

            matrix = op_matrix @ matrix

        return matrix


class PathCommand:
    """Proper object of an individual 'command' of a path.
    That is a 'move' or 'line' or ... component."""

    def __init__(self, cmd: str, coords: List[float]):
        if cmd not in ALLOWED_PC_CHARS:
            raise ValueError(f"Only allowed chars: {ALLOWED_PC_CHARS}")

        if len(coords) != PC_NUM_ELEM_MAP[cmd]:
            raise ValueError(
                f"Found {len(coords)} coordinates for {PC_PATHTYPE_MAP[cmd]}"
                f", expected {PC_NUM_ELEM_MAP[cmd]}"
            )

        self.path_type = cmd
        self.coordinates = coords

    @classmethod
    def from_d_str(cls, d_str: str):
        segments = normalize_path(d_str)
        if len(segments) > 1:
            raise ValueError("expect only 1 command to construct PathCommand")
        cm, coords = segments[0]
        return cls(cm, coords)

    def __str__(self):
        return f"{self.path_type}: {self.coordinates}"

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        if self.path_type != other.path_type:
            return False
        for ai, bi in zip(self.coordinates, other.coordinates):
            if not math.isclose(ai, bi):
                return False
        return True

    def translate(self, x, y):
        """Translates the command. Kept for convenience."""
        matrix = TransformationMatrix(1, 0, 0, 1, x, y)
        self.transform(matrix)

    def transform(self, matrix: TransformationMatrix):
        """Applies a transformation matrix to the command's coordinates."""
        new_coords = list(self.coordinates)

        # Arcs are tricky. We transform the endpoint.
        # A full solution would involve transforming the ellipse itself,
        # but for many cases, just transforming the target point is enough.
        # The rotation angle of the arc also needs to be adjusted.
        if self.path_type == "A":
            # Transform endpoint
            x, y = matrix.apply_to_point(new_coords[5], new_coords[6])
            new_coords[5], new_coords[6] = x, y
            # TODO: A more complete implementation would also adjust rx, ry,
            # and x-axis-rotation based on the matrix.
        else:
            # For M, L, C, Q transform all control points
            for i in range(0, len(new_coords), 2):
                x, y = matrix.apply_to_point(new_coords[i], new_coords[i + 1])
                new_coords[i], new_coords[i + 1] = x, y

        self.coordinates = new_coords

    def to_xml(self):
        coords = ""
        for attr, val in zip(PC_ATTR_MAP[self.path_type], self.coordinates):
            coords += f'{attr}="{_fmt_num(val)}" '

        return f"<{PC_PATHTYPE_MAP[self.path_type]} {coords}/>"


class Path:
    def __init__(self):
        self.commands: list[PathCommand] = []
        self._close: bool = False

    @property
    def close(self):
        return self._close

    @close.setter
    def close(self, val):
        self._close = val

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        if len(self.commands) != len(other.commands):
            return False
        return all([sc == oc for sc, oc in zip(self.commands, other.commands)])

    def append(self, el):
        self.commands.append(el)

    def extend(self, elems):
        self.commands.extend(elems)

    def translate(self, x, y):
        """Translates the entire path."""
        matrix = TransformationMatrix(1, 0, 0, 1, x, y)
        self.transform(matrix)

    def transform(self, matrix: TransformationMatrix):
        """Applies a transformation matrix to all commands in the path."""
        for command in self.commands:
            command.transform(matrix)

    def to_xml(self):
        if self.close:
            closepath = "\t<close/>\n"
        else:
            closepath = ""
        all_path_elems = [pe.to_xml() for pe in self.commands]
        all_path_elems = "\n\t".join(all_path_elems)
        return f"<path>\n\t{all_path_elems}\n{closepath}</path>"


def split_by_chars(input_str: str, chars: str):
    """Split an input string into list of strings,
    split it by chars  (string that can serve as delimiters)
    also strip it of any whitespace"""
    elem_fragments = re.split(f"([{chars}])", input_str)
    elem_fragments = [x for x in elem_fragments if len(x) > 0]
    elem_fragments = [x for x in elem_fragments if x != " " and x != ","]
    return elem_fragments


def convert_one_path(d: str) -> Path:
    segments = normalize_path(d)
    path = Path()

    for cmd, coords in segments:
        if cmd == "Z":
            path.close = True
        else:
            path.append(PathCommand(cmd, coords))

    return path


def convert_d_to_drawio_xml(d_string: str):
    """
    Converts a single SVG 'd' attribute string into a Draw.IO XML path string.
    This function processes the path, normalizes it, and returns the XML
    representation ready to be inserted into a Draw.IO custom shape.
    """
    path_obj = convert_one_path(d_string)
    return path_obj.to_xml()


def convert_svg(svg_input_path: str) -> str:
    """
    Takes an SVG file path, parses it recursively, applies transformations,
    and converts all found paths to a single Draw.IO XML <path> element.
    """
    tree = ET.parse(svg_input_path)
    root = tree.getroot()
    namespace = ""  # find namespace if available
    if "}" in root.tag:
        namespace = root.tag.split("}")[0][1:]
    all_paths: List[Path] = []

    def _get_tag(tag_name):
        """Get the tag, considering namespaces."""
        return f"{{{namespace}}}{tag_name}" if namespace else tag_name

    def _parse_node(element, parent_transform: TransformationMatrix):
        """Parse a node (recursively) and apply transformations."""
        local_transform_str = element.get("transform", "")
        local_transform = TransformationMatrix.from_string(local_transform_str)
        current_transform = parent_transform @ local_transform

        if element.tag == _get_tag("path"):
            d = element.get("d")
            if d:
                path_obj = convert_one_path(d)
                path_obj.transform(current_transform)
                all_paths.append(path_obj)

        for child in element:
            _parse_node(child, current_transform)

    # Start recursion from the root with an identity matrix
    _parse_node(root, TransformationMatrix())

    # Combine all collected and transformed paths into one XML string
    if not all_paths:
        return ""
    full_xml = "".join([p.to_xml() for p in all_paths])
    return merge_paths(full_xml)


def merge_paths(paths: str):
    """Merge multiple paths into one.
    In DrawIO XML the last paths might 'overpaint' the ones before."""
    paths = re.sub(r"(<path>|<path\s*\/\s*>|<\s*/path\s*>)", "", paths)
    paths = paths.replace("\r\n", "\n")  # normalize
    paths = re.sub(r"\n{3,}", "\n\n", paths)  # collapse multiple blank lines
    paths = f"<path>{paths}</path>"
    return paths


def main():
    # ret = convert_one_path("M10,10 L10, 20")
    # print(ret.to_xml())

    print(convert_svg(EXAMPLE_SVG))


if __name__ == "__main__":
    main()
