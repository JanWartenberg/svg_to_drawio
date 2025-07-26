# svg_to_drawio
Python helper to convert SVG files into draw.io shapes.

[DrawIO Shapes](https://www.drawio.com/doc/faq/custom-shapes) are specific templates of the diagram tool [draw io](https://www.drawio.com/).
Color styles can be applied to them. Strokewidth can be adapted within the tool.

Simply importing SVG files into draw.io does not allow this. For them colors and strokewidth are fixed.

Although the draw.io XML format follows concepts similar to SVG, it has a slight different syntax and a reduced set of features. It has less standard shapes, only likes absolute coordinates and does not provide transformations.


# Features

- Convert SVG Files to DrawIO
  - including normalizing relative paths to absolute paths
  - including resolving transformations
- Convert single paths, resp. "d" Attributes to DrawIO

[...]


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

# Usage hints

## Prepare input SVG 

- Resolve objects into paths. E.g. in Inkscape select all objects and apply `Path -> Object to Path`
- Make paths absolute, e.g. in Inkscape: `Extensions -> Modify Paths -> To absolute coordinates`
- Store absolute paths, e.g. Setting in Inkscape: `Edit -> Preferences -> Input/Output -> SVG output -> Path string format -> Absolute`

All these steps bring the input SVG "closer" to the simple format already. I cannot guarantee that it works for all constellations, but the steps above made it more probable for the examples I tried.

## Insert Shape to draw.io

In Draw.IO 
- select `Arrange > Insert > Shape`,
- paste in the path into the template.
  However: make sure you only overwrite the path within the template. width/height still need to be adapted to your needs. Also the background probably needs to be deleted or replaced.

## References

* Documentation of Custom Shapes: https://www.drawio.com/doc/faq/custom-shapes
* There is  https://svgtodraw.io/ which looks nice at first glance. It creates a DrawIO Library, which can be a collection of shapes. But the SVG images are not converted to proper DrawIO shapes.

*Note: There a multiple similar projects on Github, so far I did not find one that specifically solved my problem.*
