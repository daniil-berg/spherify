from typing import Tuple as _Tuple
from pathlib import Path as _Path
from argparse import ArgumentParser

DIMENSIONS = 3

INPUT_PATH = 'image_path'
SAVE_DIRECTORY = 'save_directory'
OUT_FILE_PREFIX, DEFAULT_OUT_FILE_PREFIX = 'output_file_prefix', 'sph_'
NO_DISPLAY = 'no_display'
CENTER_POINT, DEFAULT_CENTER_POINT = 'center_point', '0,0,0'
RADIUS, DEFAULT_RADIUS = 'radius', 1.0
SAMPLING_DENSITY, DEFAULT_SAMPLING_DENSITY = 'sampling_density', 1
SNAPSHOT_WIDTH, DEFAULT_SNAPSHOT_WIDTH = 'snapshot_width', 500
SNAPSHOT_HEIGHT, DEFAULT_SNAPSHOT_HEIGHT = 'snapshot_height', 500
JULIA_BINARY, DEFAULT_JULIA_BINARY = 'julia_binary', 'julia'
VERBOSE = 'verbose'
CONSECUTIVE = 'consecutive'
GET_EXEC_TIME = 'get_exec_time'


def get_arg_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description="Project an image onto a 2-sphere and snapshot the result."
    )
    parser.add_argument(
        INPUT_PATH,
        type=_Path,
        nargs='+',
        help="Path to the image file to use for input."
    )
    parser.add_argument(
        '-d', '--' + SAVE_DIRECTORY.replace('_', '-'),
        type=_Path,
        help="If passed a path, the resulting image(s) will be saved there. "
             "Write permissions are obviously required there. If omitted, "
             "the results are not saved, but simply displayed on screen."
    )
    parser.add_argument(
        '-f', '--' + OUT_FILE_PREFIX.replace('_', '-'),
        default=DEFAULT_OUT_FILE_PREFIX,
        help=f"If the `--{SAVE_DIRECTORY.replace('_', '-')}` option is used, "
             f"this prefix is added to the input file's name to make the name "
             f"of the output file. Defaults to `{DEFAULT_OUT_FILE_PREFIX}`."
    )
    parser.add_argument(
        '-D', '--' + NO_DISPLAY.replace('_', '-'),
        action='store_true',
        help=f"If this flag is set, the resulting image will not be displayed "
             f"on screen at the end. This can be useful, if instead of viewing "
             f"the result directly, the `--{SAVE_DIRECTORY.replace('_', '-')}` "
             f"path is specified for saving the resulting image."
    )
    parser.add_argument(
        '-c', '--' + CENTER_POINT.replace('_', '-'),
        type=_point_as_tuple,
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
        '-J', '--' + JULIA_BINARY.replace('_', '-'),
        default=DEFAULT_JULIA_BINARY,
        help=f"Specifies the Julia executable/command in the current "
             f"environment or the path to the Julia binary. Assuming it to be "
             f"located inside a directory included in the `PATH` environment "
             f"variable, the default is simply `{DEFAULT_JULIA_BINARY}`."
    )
    parser.add_argument(
        '-v', '--' + VERBOSE,
        action='store_true',
        help="Setting this flag produces a little bit of informative output "
             "during the program's runtime. By default, no output is streamed, "
             "if the program runs without warnings or errors."
    )
    parser.add_argument(
        '-C', '--' + CONSECUTIVE,
        action='store_true',
        help="If this flag is set, the program runs in consecutive mode i.e. "
             "without any concurrency. Otherwise the Python `asyncio` library "
             "is employed to process all images concurrently. If a lot of high "
             "resolution images need to be processed, running concurrently can "
             "cause memory issues because all input *and* output images will "
             "be loaded into memory at the same time."
    )
    parser.add_argument(
        '-T', '--' + GET_EXEC_TIME.replace('_', '-'),
        action='store_true',
        help="Setting this flag causes the total program execution time to be "
             "measured and printed out at the very end."
    )
    return parser


def _point_as_tuple(input_string: str) -> _Tuple[float]:
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


class AbortExecution(Exception):
    pass
