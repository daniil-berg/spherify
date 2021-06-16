from logging import getLogger, INFO, CRITICAL, basicConfig as logConfig
from typing import Tuple
from argparse import ArgumentParser
from pathlib import Path
from subprocess import run, PIPE

from PIL import Image, ImageFile


log = getLogger()  # simply initialize the root logger
LOG_FORMAT = '%(message)s'

THIS_PATH = Path(__file__)

JULIA_COMMAND = 'julia'

# Without this, some PNG files could not be read for some strange reason:
ImageFile.LOAD_TRUNCATED_IMAGES = True

DIMENSIONS = 3

# CLI parameters
INPUT_IMAGE = 'image_path'
OUTPUT_FILE = 'output_file'
NO_DISPLAY = 'no_display'
CENTER_POINT, DEFAULT_CENTER_POINT = 'center_point', '0,0,0'
RADIUS, DEFAULT_RADIUS = 'radius', 1.0
SAMPLING_DENSITY, DEFAULT_SAMPLING_DENSITY = 'sampling_density', 1
SNAPSHOT_WIDTH, DEFAULT_SNAPSHOT_WIDTH = 'snapshot_width', 500
SNAPSHOT_HEIGHT, DEFAULT_SNAPSHOT_HEIGHT = 'snapshot_height', 500
VERBOSE = 'verbose'


def handle_arguments(**kwargs) -> None:
    """
    Handle CLI input provided as keyword arguments and call all other functions.
    Reads the image file into memory, calls the Julia program to perform the
    necessary calculations passing the image data to its standard input,
    reads its standard output to construct the resulting transformed image,
    and then displays and/or saves that result.

    Image data is passed to and from the Julia subprocess in binary format since
    this appears to be the most efficient way possible; the `PIL.Image` class
    provides the `tobytes()` method for this, and since the RGBA mode for
    handling images represents every pixel by exactly 4 bytes, working with the
    raw bytes data becomes very easy.

    The stdout of the Julia subprocess is captured and an `Image` object is then
    constructed again from the raw bytes received, which are assumed to again
    be a multiple of 4 with every 4 bytes representing one RGBA pixel.
    """
    log_level = INFO if kwargs[VERBOSE] else CRITICAL
    # By default, the root logger uses the stdout stream handler, so all we need
    # to do, is set the log-level low enough, if we want the messages to appear,
    # or high enough, if we want to silence them.
    logConfig(level=log_level, format=LOG_FORMAT)
    image_path = kwargs[INPUT_IMAGE]
    if not image_path.is_file():
        raise FileNotFoundError(f"No file found at {image_path}")
    log.info(f"Opening `{image_path}` ({image_path.stat().st_size} bytes)")
    with Image.open(image_path) as img:
        log.info(f"Image of size {img.width} x {img.height} pixels loaded")
        snap_w, snap_h = kwargs[SNAPSHOT_WIDTH], kwargs[SNAPSHOT_HEIGHT]
        args = [
            JULIA_COMMAND,
            str(THIS_PATH.with_suffix('.jl')),
            f'{img.width},{img.height}',
            ','.join(str(x) for x in kwargs[CENTER_POINT]),
            str(kwargs[RADIUS]),
            str(kwargs[SAMPLING_DENSITY]),
            f'{snap_w},{snap_h}'
        ]
        log.info(f"Launching subprocess: `{' '.join(args)}`")
        completed_proc = run(args, input=img.tobytes(), stdout=PIPE, check=True)
    # TODO: The following line is just for testing purposes!
    result = Image.frombytes('RGBA', img.size, completed_proc.stdout)
    # result = Image.frombytes('RGBA', (snap_w, snap_h), completed_proc.stdout)
    log.info(f"Received {len(completed_proc.stdout)} bytes from the subprocess "
             f"and constructed a {snap_w} x {snap_h} pixel image from them")
    out_path = kwargs[OUTPUT_FILE]
    if out_path is not None:
        log.info(f"Saving resulting image to `{out_path}`...")
        result.save(out_path)
        log.info("Image saved successfully")
    if not kwargs[NO_DISPLAY]:
        result.show()


def point_as_tuple(input_string: str) -> Tuple[float]:
    """
    Attempts to parse a string as a tuple of floats.
    Checks that the number of elements corresponds to the specified dimensions.
    The purpose of this function more than anything else is to validate correct
    syntax of a CLI argument that is supposed to be a point in space.
    """
    out = tuple(float(coordinate) for coordinate in input_string.split(','))
    if len(out) == DIMENSIONS:
        return out
    raise TypeError


def main() -> None:
    parser = ArgumentParser(
        description="Project an image onto a 2-sphere and snapshot the result."
    )
    parser.add_argument(
        INPUT_IMAGE,
        type=Path,
        help="Path to the image file to use for input."
    )
    parser.add_argument(
        '-o', '--' + OUTPUT_FILE.replace('_', '-'),
        type=Path,
        help="If passed a path, the resulting image will be saved there. "
             "Write permissions are obviously required there. If omitted, "
             "the result is not saved, but simply displayed on screen."
    )
    parser.add_argument(
        '-D', '--' + NO_DISPLAY.replace('_', '-'),
        action='store_true',
        help=f"If this flag is set, the resulting image will not be displayed "
             f"on screen at the end. This can be useful, if instead of viewing "
             f"the result directly, the `--{OUTPUT_FILE.replace('_', '-')}` "
             f"path is specified for saving the resulting image."
    )
    parser.add_argument(
        '-c', '--' + CENTER_POINT.replace('_', '-'),
        type=point_as_tuple,
        default=DEFAULT_CENTER_POINT,
        help=f"Specifies the center of the 2-sphere in 3D-space as a 3-tuple "
             f"of floating point numbers (or integers) separated by commas "
             f"without any spaces, for example `0.8,-1,420.69`. "
             f"Defaults to the origin i.e. `{DEFAULT_CENTER_POINT}`."
    )
    parser.add_argument(
        '-r', '--' + RADIUS,
        type=float,
        default=DEFAULT_RADIUS,
        help=f"Specifies the radius of the 2-sphere in 3D-space as a floating "
             f"point number (or integer). Defaults to {DEFAULT_RADIUS}."
    )
    parser.add_argument(
        '-s', '--' + SAMPLING_DENSITY.replace('_', '-'),
        type=int,
        default=DEFAULT_SAMPLING_DENSITY,
        help=f"Specifies the number of samples per pixel. "
             f"Defaults to {DEFAULT_SAMPLING_DENSITY}."
    )
    parser.add_argument(
        '-W', '--' + SNAPSHOT_WIDTH.replace('_', '-'),
        type=int,
        default=DEFAULT_SNAPSHOT_WIDTH,
        help=f"Specifies the width of the desired snapshot in pixels. "
             f"Defaults to {DEFAULT_SNAPSHOT_WIDTH}."
    )
    parser.add_argument(
        '-H', '--' + SNAPSHOT_HEIGHT.replace('_', '-'),
        type=int,
        default=DEFAULT_SNAPSHOT_HEIGHT,
        help=f"Specifies the height of the desired snapshot in pixels. "
             f"Defaults to {DEFAULT_SNAPSHOT_HEIGHT}."
    )
    parser.add_argument(
        '-v', '--' + VERBOSE,
        action='store_true',
        help="Setting this flag produces a little bit of informative output "
             "during the program's runtime. By default, no output is streamed, "
             "if the program runs without errors."
    )
    handle_arguments(**vars(parser.parse_args()))


if __name__ == '__main__':
    main()
