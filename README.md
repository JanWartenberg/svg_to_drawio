# svg_to_drawio
Python helper to convert SVG files into draw.io shapes.

[draw.io Shapes](https://www.drawio.com/doc/faq/custom-shapes) are specific templates of the diagram tool [draw io](https://www.drawio.com/).
Color styles can be applied to them. Strokewidth can be adapted within the tool.

Simply importing SVG files into draw.io does not allow this. For them colors and strokewidth are fixed.

Although the draw.io XML format follows concepts similar to SVG, it has a slight different syntax and a reduced set of features. It has less standard shapes, only likes absolute coordinates and does not provide transformations.


# Features

- Convert SVG Files to draw.io
  - including normalizing relative paths to absolute paths
  - including resolving transformations (translate, rotate, matrix)
- Convert single paths, resp. "d" Attributes to draw.io

- Example path generation
  - (a bit unrelated, but shows how repetitve SVG patterns can be created via script using math)


# Examples

## Convert a d-string directly
```
    d_str = "M 20,30 L 30,30 L 30,40 L 20,40"
    print(convert_d_to_drawio_xml(d_str))
```

Will provide:

```
<path>
        <move x="20" y="30" />
        <line x="30" y="30" />
        <line x="30" y="40" />
        <line x="20" y="40" />
</path>
```

## Convert a d-string with curves

```
from drawio_converter.svg_drawio import convert_d_to_drawio_xml

svg_d_string = """
M 10 80
C 40 10, 65 10, 95 80
S 150 150, 180 80

M 20 20
Q 50 0, 80 20
T 100 40
"""

drawio_xml_output = convert_d_to_drawio_xml(svg_d_string)
print(drawio_xml_output)
```

Will provide:
```
<path>
    <move x="10" y="80" />
    <curve x1="40" y1="10" x2="65" y2="10" x3="95" y3="80" />
    <curve x1="125" y1="150" x2="150" y2="150" x3="180" y3="80" />
    <move x="20" y="20" />
    <quad x1="50" y1="0" x2="80" y2="20" />
    <quad x1="110" y1="40" x2="100" y2="40" />
</path>
```


## Convert an SVG file
Run this from project root:

```
from src import convert_svg

print(convert_svg(r"examples\Example2.svg"))
```

Will print:
```
<path>
        <move x="20" y="0" />
        <curve x1="35" y1="30" x2="112.5" y2="25" x3="125" y3="50" />
        <curve x1="137.5" y1="75" x2="55" y2="70" x3="65" y3="90" />
</path>
```
Which, pasted into a draw.io shape will result in the same curve.


# Usage hints

## Prepare input SVG

- Resolve objects into paths. E.g. in Inkscape select all objects and apply `Path -> Object to Path`
- Make paths absolute, e.g. in Inkscape: `Extensions -> Modify Paths -> To absolute coordinates`
- Store absolute paths, e.g. Setting in Inkscape: `Edit -> Preferences -> Input/Output -> SVG output -> Path string format -> Absolute`

All these steps bring the input SVG "closer" to the simple format already. I cannot guarantee that it works for all constellations, but the steps above made it more probable for the examples I tried.

## Insert Shape to draw.io

In draw.io
- select `Arrange > Insert > Shape`,
- paste in the path into the template.
  However: make sure you only overwrite the path within the template. width/height still need to be adapted to your needs. Also the background probably needs to be deleted or replaced.

## References

* Documentation of Custom Shapes: https://www.drawio.com/doc/faq/custom-shapes
* There is  https://svgtodraw.io/ which looks nice at first glance. It creates a draw.io Library, which can be a collection of shapes. But the SVG images are not converted to proper draw.io shapes.

*Note: There a multiple similar projects on Github, so far I did not find one that specifically solved my problem.*
