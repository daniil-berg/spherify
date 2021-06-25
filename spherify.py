from logging import getLogger, INFO, WARNING, basicConfig as logConfig
from typing import Tuple, Optional
from argparse import ArgumentParser
from pathlib import Path
from subprocess import run, PIPE

from PIL import ImageFile, UnidentifiedImageError
from PIL.Image import Image, open as img_from_file, frombytes as img_from_bytes


log = getLogger()  # simply initialize the root logger
LOG_FORMAT = '%(message)s'

THIS_PATH = Path(__file__)

# Without this, some PNG files could not be read for some strange reason:
ImageFile.LOAD_TRUNCATED_IMAGES = True

IMAGE_MODE = 'RGBA'

DIMENSIONS = 3

# CLI parameters
INPUT_PATH = 'image_path'
SAVE_DIRECTORY = 'save_directory'
OUTPUT_FILE_PREFIX, DEFAULT_OUTPUT_FILE_PREFIX = 'output_file_prefix', 'sph_'
NO_DISPLAY = 'no_display'
CENTER_POINT, DEFAULT_CENTER_POINT = 'center_point', '0,0,0'
RADIUS, DEFAULT_RADIUS = 'radius', 1.0
SAMPLING_DENSITY, DEFAULT_SAMPLING_DENSITY = 'sampling_density', 1
SNAPSHOT_WIDTH, DEFAULT_SNAPSHOT_WIDTH = 'snapshot_width', 500
SNAPSHOT_HEIGHT, DEFAULT_SNAPSHOT_HEIGHT = 'snapshot_height', 500
JULIA_BINARY, DEFAULT_JULIA_BINARY = 'julia_binary', 'julia'
VERBOSE = 'verbose'


def handle_arguments(**kwargs) -> None:
    """
    Handle CLI input provided as keyword arguments and call main functions.

    By default, the root logger uses the stdout stream handler, so all we need
    to do, is set the log-level low enough, if we want the messages to appear,
    or high enough, if we want to silence them.
    """
    log_level = INFO if kwargs[VERBOSE] else WARNING
    logConfig(level=log_level, format=LOG_FORMAT)
    save_dir, display = kwargs[SAVE_DIRECTORY], not kwargs[NO_DISPLAY]
    if not display and save_dir is None:
        log.warning("The results will be neither displayed nor saved...")
    for path in kwargs[INPUT_PATH]:
        files = list(path.iterdir()) if path.is_dir() else [path]
        for file in files:
            if file.is_dir():
                continue
            result = load_and_process(
                image_path=file,
                julia=kwargs[JULIA_BINARY],
                center_point=kwargs[CENTER_POINT],
                radius=kwargs[RADIUS],
                sampling_density=kwargs[SAMPLING_DENSITY],
                snap_w=kwargs[SNAPSHOT_WIDTH],
                snap_h=kwargs[SNAPSHOT_HEIGHT]
            )
            if result is None:
                continue
            # Decide how to proceed with the resulting image:
            if save_dir is not None:
                out = Path(save_dir, kwargs[OUTPUT_FILE_PREFIX] + file.name)
                log.info(f"Saving resulting image to `{out}`...")
                result.save(out)
                log.info("Image saved successfully")
            if display:
                result.show()


def load_and_process(image_path: Path, julia: str,
                     center_point: Tuple[float],
                     radius: float, sampling_density: int,
                     snap_w: int, snap_h: int) -> Optional[Image]:
    """
    Reads the image file into memory, calls the Julia program to perform the
    necessary calculations passing the image data to its standard input, and
    reads its standard output to construct the resulting transformed image.

    Image data is passed to and from the Julia subprocess in binary format since
    this appears to be the most efficient way possible; the `PIL.Image` class
    provides the `tobytes()` method for this, and since the RGBA mode for
    handling images represents every pixel by exactly 4 bytes, working with the
    raw bytes data becomes very easy.

    The stdout of the Julia subprocess is captured and an `Image` object is then
    constructed again from the raw bytes received, which are assumed to again
    be a multiple of 4 with every 4 bytes representing one RGBA pixel.
    This `Image` object is returned.
    """
    log.info(f"Opening `{image_path}` ({image_path.stat().st_size} bytes)")
    try:
        with open(image_path, 'rb') as f:
            img = img_from_file(f).convert(IMAGE_MODE)
    except PermissionError:
        log.error(f"No read permissions for file `{image_path}`; skipping...")
        return
    except UnidentifiedImageError:
        log.warning(f"Could not identify image `{image_path}`; skipping...")
        return
    log.info(f"Image of size {img.width} x {img.height} pixels loaded")
    # Create a list of commandline arguments to launch the Julia subprocess,
    # the first being the Julia binary, the second being the actual script,
    # and the rest being the required arguments for that script, i.e.
    # image size, center, radius, density, and snapshot size.
    args = [
        julia,
        str(THIS_PATH.with_suffix('.jl')),
        f'{img.width},{img.height}',
        ','.join(str(x) for x in center_point),
        str(radius),
        str(sampling_density),
        f'{snap_w},{snap_h}'
    ]
    log.info(f"Launching subprocess: `{' '.join(args)}`")
    # Here we pass the image bytes to the subprocess stdin, and also capture
    # its stdout after it is finished; if errors occur in the subprocess
    # i.e. the exit code is not 0, setting `check=True` will cause an
    # exception to be raised immediately afterwards.
    completed = run(args, input=img.tobytes(), stdout=PIPE, check=True)
    log.info(f"Received {len(completed.stdout)} bytes from the subprocess "
             f"and constructed a {snap_w} x {snap_h} pixel image from them")
    # TODO: The following line is just for testing purposes!
    return img_from_bytes(IMAGE_MODE, img.size, completed.stdout)
    # return img_from_bytes(IMAGE_MODE, (snap_w, snap_h), completed.stdout)


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
        INPUT_PATH,
        type=Path,
        nargs='+',
        help="Path to the image file to use for input."
    )
    parser.add_argument(
        '-d', '--' + SAVE_DIRECTORY.replace('_', '-'),
        type=Path,
        help="If passed a path, the resulting image(s) will be saved there. "
             "Write permissions are obviously required there. If omitted, "
             "the results are not saved, but simply displayed on screen."
    )
    parser.add_argument(
        '-f', '--' + OUTPUT_FILE_PREFIX.replace('_', '-'),
        default=DEFAULT_OUTPUT_FILE_PREFIX,
        help=f"If the `--{SAVE_DIRECTORY.replace('_', '-')}` option is used, "
             f"this prefix is added to the input file's name to make the name "
             f"of the output file. Defaults to `{DEFAULT_OUTPUT_FILE_PREFIX}`."
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
             "if the program runs without errors."
    )
    handle_arguments(**vars(parser.parse_args()))


if __name__ == '__main__':
    main()
