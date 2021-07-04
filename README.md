# Spherify

Project images onto spheres in 3D space and take snapshots.

### Dependencies

- [Python](https://www.python.org/) 3.7+
- [PIL](https://python-pillow.org/) ([Docs](https://pillow.readthedocs.io/en/stable/))
- [Julia](https://julialang.org/)

Should run on most Linux/Windows systems. Tested on Arch and Windows 10.

### Building

Clone this repo, install `build` via pip, then run `pip -m build` 
from the repository's root directory. This should produce a `dist/` 
subdirectory with a wheel (build) and archive (source) distribution.
The resulting `whl`-file can be installed via `pip install path/dist/***.whl`.

### Running

To get detailed help and usage info:
```shell
python -m spherify -h
```
Simple example to project a PNG onto a sphere centered at `(0, 0, 1000)` 
with radius `600` and display the snapshot:
```shell
python -m spherify -c 0,0,1000 -r 600 path/to/image.png
```
Same thing, but don't display and save to current working directory instead:
```shell
python -m spherify -c 0,0,1000 -r 600 -d . -D path/to/image.png
```
Read the help for additional options.

### Caution

This can be run on multiple images **concurrently** (by default). 
Depending on their number, resolution, and the system resources, 
this can quickly take up all available resources (incl. RAM and Swap) and 
render the system unresponsive.

To avoid this, consider doing them in batches or using the `-C` flag.

### Assignment

TU Berlin, Computerorientierte Mathematik 2, SS 2021

[Assignment PDF (German)](assignment_de.pdf)

Group No. 10

### Authors

[Private]

Fajnberg, Daniil

[Private]
