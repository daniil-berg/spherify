from typing import List, Tuple, Optional, Callable, Any
from logging import getLogger, INFO, WARNING, basicConfig as logConfig
from pathlib import Path
from distutils.util import strtobool
from subprocess import run, PIPE
from asyncio.subprocess import create_subprocess_shell as asyncrun
import asyncio

from PIL import ImageFile, UnidentifiedImageError
from PIL.Image import Image, open as img_from_file, frombytes as img_from_bytes

from cli import *


log = getLogger(__name__)
LOG_FORMAT = '%(message)s'

THIS_PATH = Path(__file__)

# Without this, some PNG files could not be read for some strange reason:
ImageFile.LOAD_TRUNCATED_IMAGES = True

IMG_MODE = 'RGBA'


class Handler:
    def __init__(self, **cli_kwargs):
        """
        Interprets CLI keyword arguments, prepares variables, sets up logger.
        """
        self.input_paths: List[Path] = cli_kwargs[INPUT_PATH]
        self.save_dir: Path = cli_kwargs[SAVE_DIRECTORY]
        self.out_file_prefix: str = cli_kwargs[OUT_FILE_PREFIX]
        self.display: bool = not cli_kwargs[NO_DISPLAY]
        self.center: str = ','.join(str(x) for x in cli_kwargs[CENTER_POINT])
        self.radius: float = cli_kwargs[RADIUS]
        self.sampling_density: int = cli_kwargs[SAMPLING_DENSITY]
        self.snap_w: int = cli_kwargs[SNAPSHOT_WIDTH]
        self.snap_h: int = cli_kwargs[SNAPSHOT_HEIGHT]
        self.julia_binary: str = cli_kwargs[JULIA_BINARY]
        self.julia_script: Path = THIS_PATH.with_suffix('.jl')
        self.concurrent: bool = not cli_kwargs[CONSECUTIVE]

        log_level = INFO if cli_kwargs[VERBOSE] else WARNING
        logConfig(level=log_level, format=LOG_FORMAT)

        if not self.display and self.save_dir is None:
            log.warning("The results will be neither displayed nor saved.")
            confirmed = input("Are you sure this is what you want? [y/n] ")
            if not strtobool(confirmed.lower()):
                raise AbortExecution
        self.results: List[Optional[Image]] = []

    def spherify_all(self) -> None:
        """
        Main method to perform the transformation for each input image.
        If `display` is `True`, each result is displayed at the end;
        beware that this spawns as many windows as there are transformed images.
        """
        if self.concurrent:
            asyncio.run(self._gather_results())
        else:
            self._gather_results_non_async()
        if self.display:
            for result in self.results:
                if isinstance(result, Image):
                    result.show()

    async def _gather_results(self) -> None:
        """
        Asynchronously runs the `spherify` coroutines on all the input paths.
        After finishing, the results list contains the result for every
        input path, i.e. either an `Image` object or `None`.
        """
        self.results = await asyncio.gather(*self.path_iter(self.spherify))

    def _gather_results_non_async(self) -> None:
        """
        Consecutively/sequentially runs each `spherify_non_async` method.
        After finishing, the results list contains the result for every
        input path, i.e. either an `Image` object or `None`.
        """
        self.results = [f for f in self.path_iter(self.spherify_non_async)]

    def path_iter(self, method: Callable) -> Any:
        """
        Produces the return value of a function call for each input path.
        If an input path is a directory, a coroutine for each file inside it
        will be produced.
        Subdirectories are silently skipped to avoid unknown recursion depth;
        otherwise no file checks are performed here.
        """
        for path in self.input_paths:
            files = list(path.iterdir()) if path.is_dir() else [path]
            for file in files:
                if file.is_dir():
                    continue
                yield method(img_path=file)

    async def spherify(self, img_path: Path) -> Optional[Image]:
        """
        Reads the image file into memory, calls the Julia program to perform the
        necessary calculations, and construct the resulting transformed image.
        If a save directory is set, that image is then saved.

        The stdout of the Julia subprocess is captured and an `Image` object is
        constructed again from the raw bytes received, that are assumed to
        be a multiple of 4 with every 4 bytes representing one RGBA pixel.
        """
        img = await load_image(img_path)
        if img is None:
            return
        stdout, stderr = await self.run_julia(img)
        if stderr:
            log.error(f"Julia program exited with an error:\n{stderr.decode()}")
            return
        result = self._process_julia_output(stdout, img.size)
        if self.save_dir is not None:
            await save_image(result, self.get_save_path(img_path))
        return result

    def spherify_non_async(self, img_path: Path) -> Optional[Image]:
        """Same as above, but without async capabilities"""
        img = load_image_non_async(img_path)
        if img is None:
            return
        stdout, stderr = self.run_julia_non_async(img)
        if stderr:
            log.error(f"Julia program exited with an error:\n{stderr.decode()}")
            return
        result = self._process_julia_output(stdout, img.size)
        if self.save_dir is not None:
            save_image_non_async(result, self.get_save_path(img_path))
        return result

    async def run_julia(self, img: Image) -> Tuple[bytes, bytes]:
        """
        Launches the Julia script as a subprocess.

        Image data is passed to and from the Julia subprocess in binary format
        since this appears to be the most efficient way possible;
        the `PIL.Image` class provides the `tobytes()` method for this, and
        since the RGBA mode for handling images represents every pixel by
        exactly 4 bytes, working with the raw bytes data becomes very easy.

        We return the subprocess' stdout and stderr after it is finished.
        """
        args = self.get_julia_command_args(img)
        cmd = ' '.join(args)
        log.info(f"Asynchronously launching subprocess: `{cmd}`")
        proc = await asyncrun(cmd=cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        return await proc.communicate(input=img.tobytes())

    def run_julia_non_async(self, img: Image) -> Tuple[bytes, bytes]:
        """Same as above, but without async capabilities"""
        args = self.get_julia_command_args(img)
        log.info(f"Launching subprocess: `{' '.join(args)}`")
        complete = run(args, input=img.tobytes(), capture_output=True)
        return complete.stdout, complete.stderr

    def get_julia_command_args(self, img: Image) -> List[str]:
        """Returns the Julia command to be run on an image in list format."""
        return [
            self.julia_binary,
            str(self.julia_script),
            f'{img.width},{img.height}',
            self.center,
            str(self.radius),
            str(self.sampling_density),
            f'{self.snap_w},{self.snap_h}'
        ]

    def _process_julia_output(self, stdout: bytes, old_size) -> Image:
        log.info(f"Received {len(stdout)} bytes from Julia subprocess")
        # TODO: The following line is just for testing purposes!
        result = img_from_bytes(IMG_MODE, old_size, stdout)
        # result = img_from_bytes(IMG_MODE, (snap_w, snap_h), stdout)
        log.info(f"Constructed a new {self.snap_w} x {self.snap_h} pixel image")
        return result

    def get_save_path(self, input_path: Path) -> Path:
        return Path(self.save_dir, self.out_file_prefix + input_path.name)


async def load_image(img_path: Path) -> Optional[Image]:
    """
    Attempts to open `img_path` as an image using the PIL package.
    If successful, the image is converted into RGBA mode and returned.
    """
    log.info(f"Opening `{img_path}` ({img_path.stat().st_size} bytes)")
    try:
        with open(img_path, 'rb') as f:
            img = img_from_file(f).convert(IMG_MODE)
    except PermissionError:
        log.error(f"No read permissions for file `{img_path}`; skipping...")
        return
    except UnidentifiedImageError:
        log.warning(f"Could not identify image `{img_path}`; skipping...")
        return
    log.info(f"Image of size {img.width} x {img.height} pixels loaded")
    return img


def load_image_non_async(img_path: Path) -> Optional[Image]:
    """Same as above, but without async capabilities"""
    log.info(f"Opening `{img_path}` ({img_path.stat().st_size} bytes)")
    try:
        with open(img_path, 'rb') as f:
            img = img_from_file(f).convert(IMG_MODE)
    except PermissionError:
        log.error(f"No read permissions for file `{img_path}`; skipping...")
        return
    except UnidentifiedImageError:
        log.warning(f"Could not identify image `{img_path}`; skipping...")
        return
    log.info(f"Image of size {img.width} x {img.height} pixels loaded")
    return img


async def save_image(image: Image, target_path: Path) -> None:
    log.info(f"Saving image to `{target_path}`...")
    image.save(target_path)
    log.info(f"Image saved successfully to `{target_path}`")


def save_image_non_async(image: Image, target_path: Path) -> None:
    log.info(f"Saving image to `{target_path}`...")
    image.save(target_path)
    log.info(f"Image saved successfully to `{target_path}`")
