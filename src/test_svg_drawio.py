import math
import numbers
import os
import re
import tempfile
import unittest

from collections import namedtuple
from typing import Any, List

from svg_drawio import (
    convert_one_path, convert_svg, normalize_path, normalized_to_d_path,
    rotate_path,
    Path, PathCommand
)


class AssertMixin:
    def assertListAlmostEqual(self, a: List[numbers], b: List[numbers]):
        self.assertEqual(len(a), len(b))

        for ai, bi in zip(a, b):
            self.assertAlmostEqual(ai, bi)

    def assertNestedAlmostEqual(self, a: Any, b: Any):
        if isinstance(a, numbers.Real) and isinstance(b, numbers.Real):
            self.assertAlmostEqual(a, b)
        elif isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
            self.assertEqual(len(a), len(b))
            for ai, bi in zip(a, b):
                self.assertNestedAlmostEqual(ai, bi)
        else:
            self.assertEqual(a, b)


class TestNormalize(AssertMixin, unittest.TestCase):
    def test_normalize_path(self):
        Case = namedtuple("Case", ["name", "d_path", "expected_tuple_list"])

        cases = [
            Case("HorizontalVertical",
                 "M10,10 h80 v50 l-30,20 H10 Z",
                 [
                     ('M', [10.0, 10.0]),
                     ('L', [90.0, 10.0]),
                     ('L', [90.0, 60.0]),
                     ('L', [60.0, 80.0]),
                     ('L', [10.0, 80.0]),
                     ('Z', [])]
                 ),
            Case("Multiple H and V",
                 "M0,0 h10 20 30 v40 50",
                 [('M', [0, 0]),
                  ('L', [10, 0]),
                  ('L', [30, 0]),
                  ('L', [60, 0]),
                  ('L', [60, 40]),
                  ('L', [60, 90])]
                 ),
            Case("Curve", "M 30,30 c 10,20 25,00 50,10",
                 [
                     ('M', [30.0, 30.0]),
                     ('C', [40.0, 50.0, 55.0, 30.0, 80.0, 40.0])
                 ]),
            Case("Quad", "M 10, 20 q 25,-10 30,20",
                 [
                     ('M', [10.0, 20.0]),
                     ('Q', [35.0, 10.0, 40.0, 40.0])
                 ]),
            Case("Arc", "M 6,10 a 6 4 10 1 0 8,0",
                 [
                     ('M', [6, 10.0]), ('A', [6, 4, 10, 1, 0, 14, 10])
                 ]),
            Case("implicit L", "M 10 10 20 20 30 30",
                 [
                     ('M', [10, 10]), ('L', [20, 20]), ('L', [30, 30])
                 ]),
            Case("implicit relative L", "M 10 10 m 0 5 20 30 40 40",
                 [
                     ('M', [10, 10]), ('M', [10, 15]),
                     ('L', [30, 45]), ('L', [70, 85])
                 ]),
            Case("multiple L", "M 0 0 L 10 10 20 20 30 30",
                 [
                     ('M', [0, 0]), ('L', [10, 10]),
                     ('L', [20, 20]), ('L', [30, 30])
                 ]),
            Case("multiple C", "M 0 0 C 1 1 2 2 3 3 4 4 5 5 6 6",
                 [
                     ('M', [0, 0]),
                     ('C', [1, 1, 2, 2, 3, 3]),
                     ('C', [4, 4, 5, 5, 6, 6])
                 ]),
            Case("SmoothCurve after Curve",
                 "M 10 80 C 40 10, 65 10, 95 80 S 150 150, 180 80",
                 [
                     ('M', [10, 80]),
                     ('C', [40, 10, 65, 10, 95, 80]),
                     # Reflected control point: x1=2*95-65=125, y1=2*80-10=150
                     ('C', [125, 150, 150, 150, 180, 80])
                 ]),
            Case("SmoothCurve without preceding Curve",
                 "M 10 80 S 150 150, 180 80",
                 [
                     ('M', [10, 80]),
                     # No reflection, first control point is current point (10, 80)
                     ('C', [10, 80, 150, 150, 180, 80])
                 ]),
            Case("relative SmoothCurve",
                 "m 10 80 c 30 -70, 55 -70, 85 0 s 55 70, 85 0",
                 [
                     ('M', [10, 80]),
                     ('C', [40, 10, 65, 10, 95, 80]),
                     # Reflected: x1=2*95-65=125, y1=2*80-10=150
                     # Relative s: x2=95+55=150, y2=80+70=150, x=95+85=180, y=80+0=80
                     ('C', [125, 150, 150, 150, 180, 80])
                 ]),
            Case("minus, without space", "M 50 50 L 10-5",
                 [
                     ('M', [50, 50]),
                     ('L', [10, -5])
                 ]),
            Case("scientific", "M 50 50 L 100 1E2",
                 [
                     ('M', [50, 50]),
                     ('L', [100, 100])
                 ]),
            Case("scientific2", "M 50 50 l -0.1 1E-2 ",
                 [
                     ('M', [50, 50]),
                     ('L', [49.9, 50.01])
                 ]),
            Case("scientific3, preceding comma", "M .5 .5 L -.5 +.5 ",
                 [
                     ('M', [0.5, 0.5]),
                     ('L', [-0.5, 0.5])
                 ]),
            Case("scientific4", "M 5 6 L 1e2 5 V 1E+2 L -.5e-2 33",
                 [
                     ('M', [5, 6]),
                     ('L', [100, 5]),
                     ('L', [100, 100]),
                     ('L', [-0.005, 33])
                 ]),
            Case("preceding plus", "M +10 -0",
                 [
                     ('M', [10, 0])
                 ]),
            Case("superfluous white space", "M 10 10,, 20 20 30 30",
                 [
                     ('M', [10, 10]), ('L', [20, 20]), ('L', [30, 30])
                 ]),
            Case("only empty", "       ", []),
            Case("weird missing space", "L1e-2.3", [('L', [0.01, 0.3])])
        ]
        for name, d_path, expected in cases:
            with self.subTest(name=name):
                self.assertNestedAlmostEqual(normalize_path(d_path), expected)

    def test_normalize_invalid_token(self):
        with self.assertRaises(ValueError):
            normalize_path("M10,10 X40")

    def test_normalize_invalid_scientific_token(self):
        with self.assertRaises(ValueError):
            # rogue E that does not add up to scientific notation
            normalize_path("M 20 21 E 20")

    def test_normalize_invalid_scientific_token_at_begin(self):
        with self.assertRaises(ValueError):
            # rogue E that does not add up to scientific notation
            normalize_path("E 11 12 V 42")

    def test_normalize_invalid_too_few_values_c(self):
        with self.assertRaises(ValueError):
            # rogue E that does not add up to scientific notation
            normalize_path("C 1 2 3 4 5")

    def test_normalize_invalid_too_few_values_a(self):
        with self.assertRaises(ValueError):
            normalize_path("A 1 1 0 0 1 5")

    def test_normalize_invalid_too_few_values_q(self):
        with self.assertRaises(ValueError):
            normalize_path("Q 1 1 0")

    def test_normalize_invalid_arc_large(self):
        with self.assertRaises(ValueError):
            # 4th param, large-arc-flag is supposed to be a binary flag
            normalize_path("A 1 1 0 2 1 5 5")

        with self.assertRaises(ValueError):
            normalize_path("a 1 1 0 2 1 5 5")

    def test_normalize_invalid_arc_sweep(self):
        with self.assertRaises(ValueError):
            # 5th param, sweep-flag is supposed to be a binary flag
            normalize_path("A 1 1 0 0 3 5 5")

        with self.assertRaises(ValueError):
            normalize_path("a 1 1 0 0 3 5 5")

    def test_de_normalize(self):
        normalized_d = [('M', [30.0, 30.0]),
                        ('C', [40.0, 50.0, 55.0, 30.0, 80.0, 40.0])]
        self.assertEqual(
            normalized_to_d_path(normalized_d),
            "M 30.0 30.0 C 40.0 50.0 55.0 30.0 80.0 40.0"
        )


class TestPath(AssertMixin, unittest.TestCase):
    def test_translate_m(self):
        c = PathCommand("M", [0.0, 0.0])
        c.translate(3, 4)
        self.assertListAlmostEqual(c.coordinates, [3, 4])

    def test_translate_q(self):
        c = PathCommand("Q", [1.0, 1.0, 2.0, 2.0])
        c.translate(3, 4)
        self.assertListAlmostEqual(c.coordinates, [4, 5, 5, 6])

    def test_translate_a(self):
        c = PathCommand("A", [5.0, 5.0, 0.0, 0, 1, 10.0, 10.0])
        c.translate(3, 4)
        self.assertListAlmostEqual(c.coordinates, [5, 5, 0, 0, 1, 13, 14])

    def test_path_command_equals(self):
        pc1 = PathCommand("M", [0, 1])
        pc2 = PathCommand("M", [0.0, 1.0])
        self.assertTrue(pc1 == pc2)
        self.assertFalse(pc1 != pc2)

        pc1 = PathCommand("M", [0, 1])
        pc2 = PathCommand("L", [0, 1])
        self.assertFalse(pc1 == pc2)
        self.assertTrue(pc1 != pc2)

        pc1 = PathCommand("M", [0, 1.1])
        pc2 = PathCommand("M", [0, 1.10000000001])
        self.assertTrue(pc1 == pc2)
        self.assertFalse(pc1 != pc2)

        pc1 = PathCommand("M", [0, 1.1])
        pc2 = PathCommand("M", [0, 1.100001])
        self.assertTrue(pc1 != pc2)
        self.assertFalse(pc1 == pc2)

        self.assertFalse(pc1 == "M 0 1.1")

    def test_path_equals(self):
        p = Path()
        p.commands = [PathCommand("M", [0, 1]),
                      PathCommand("L", [4, 4])]
        p2 = Path()
        p2.commands = [PathCommand("M", [0, 1]),
                       PathCommand("L", [4, 4])]
        self.assertTrue(p == p2)

        p3 = Path()
        p3.commands = [PathCommand("M", [0, 1]),
                       PathCommand("L", [4.0, 4.00000000001])]
        self.assertTrue(p == p3)

        p4 = Path()
        p4.commands = [PathCommand("M", [0, 1]),
                       PathCommand("L", [4.0, 4.00001])]
        self.assertFalse(p == p4)


class TestConvert(unittest.TestCase):
    def test_convert_one(self):
        ret = convert_one_path("M10,10 L10, 20")

        self.assertEqual(ret.commands[0].path_type, "M")
        self.assertEqual(ret.commands[1].path_type, "L")
        self.assertEqual(ret.close, False)

    def test_convert_one_closed(self):
        ret = convert_one_path("M10,10 L10, 20 L20, 20 Z")
        self.assertEqual(ret.close, True)

    def test_convert_to_xml(self):
        newpath = convert_one_path("M10,10 L10, 20 L20, 20 Z")
        newpath.translate(50, 50)
        ret = newpath.to_xml()

        xml_output = """<path>
\t<move x="60" y="60" />
\t<line x="60" y="70" />
\t<line x="70" y="70" />
\t<close/>
</path>"""
        self.assertEqual(ret, xml_output)

    def test_xml_mappings(self):
        Case = namedtuple("Case", ["name", "cmd", "coords", "expected_xml"])
        cases = [
            Case("move",  "M", [7, 8], '<move x="7" y="8" />'),
            Case("line",  "L", [1, 2], '<line x="1" y="2" />'),
            # counter checked this in Draw.IO and Browser
            Case("quad", "Q", [10, 45, 30, 40],
                 '<quad x1="10" y1="45" x2="30" y2="40" />'),
            # counter checked this in Draw.IO and Browser
            Case("curve", "C", [-2, 10, 3, 4, 5, 6],
                 '<curve x1="-2" y1="10" x2="3" y2="4" x3="5" y3="6" />'),
            # counter checked this in Draw.IO and Browser
            Case("arc", "A", [5.0, 6.0, 30.0, 1.0, 0.0, 100.0, 200.0],
                 '<arc rx="5" ry="6" x-axis-rotation="30" '
                 'large-arc-flag="1" sweep-flag="0" x="100" y="200" />'
                 )
        ]
        for name, cmd, coords, expected_xml in cases:
            with self.subTest(name=name):
                pc = PathCommand(cmd, coords).to_xml()
                self.assertEqual(pc, expected_xml)


class TestTransformations(unittest.TestCase):
    def test_rotate(self):
        # TODO
        # integrate it into Path/PathCommand classes
        # we could extend this, that a string containing the whole <path ...>
        # is given and parsed for its transformation type + parameters
        # Original path data & rotation center/angle
        ROTATION_D_ORIG = "M 70 5 L 95 5 L 95 15 L 70 15 Z"

        cx, cy = 70, 15
        theta = math.radians(45)  # π/4
        ret = rotate_path(ROTATION_D_ORIG, theta, cx, cy)

        # TODO better to create an assertPathAlmostEqual
        #  probably even as part of the classes
        self.assertEqual(
            ret,
            "M 77.071068 7.928932 L 94.748737 25.606602 L 87.677670 "
            "32.677670 L 70.000000 15.000000 Z")

    def _normalize_xml(self, xml_string: str) -> str:
        """Removes whitespace between XML tags for robust comparison."""
        return re.sub(r'>\s+<', '><', xml_string).strip()

    def test_convert_svg_with_recursive_transforms(self):
        """
        Tests the full conversion of an SVG with nested transformations
        using a temporary file.
        """
        svg_content = """
        <svg width="200" height="200" xmlns="http://www.w3.org/2000/svg">
          <g transform="translate(50, 50)">
            <g transform="rotate(45)">
              <!-- This path starts at (10,10) relative to its rotated group -->
              <path d="M 10 10 L 60 10" stroke="black" />
            </g>
            <!-- This path is just translated -->
            <path d="M 0 20 L 50 20" stroke="red" />
          </g>
        </svg>
        """

        # Manually calculated expected output
        # Path 1: M(10,10) -> rotate(45) -> M(0, 14.142136)
        #             -> translate(50,50) -> M(50, 64.142136)
        #         L(60,10) -> rotate(45) -> L(35.355339, 49.497475)
        #             -> translate(50,50) -> L(85.355339, 99.497475)
        # Path 2: M(0,20) -> translate(50,50) -> M(50, 70)
        #         L(50,20) -> translate(50,50) -> L(100, 70)
        # The final XML merges these into a single <path>
        expected_xml = """
        <path>
            <move x="50" y="64.142136" />
            <line x="85.355339" y="99.497475" />
            <move x="50" y="70" />
            <line x="100" y="70" />
        </path>
        """

        # Create a named temporary file that is automatically deleted on exit
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".svg", delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write(svg_content)
            tmp_path = tmp.name  # Get the path to the temp file

        try:
            actual_xml = convert_svg(tmp_path)

            # Normalize both strings to ignore whitespace differences
            normalized_actual = self._normalize_xml(actual_xml)
            normalized_expected = self._normalize_xml(expected_xml)

            self.assertEqual(normalized_actual, normalized_expected)
        finally:
            os.remove(tmp_path)  # delete even if test fails


if __name__ == "__main__":
    unittest.main()
