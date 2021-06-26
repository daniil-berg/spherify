import timeit

from cli import get_arg_parser, GET_EXEC_TIME, AbortExecution
from spherify import Handler


def main() -> None:
    """
    Parse CLI arguments, instantiate handler and run main method.
    Possibly register and print the execution time.
    """
    cli_args = get_arg_parser().parse_args()
    start = timeit.default_timer()
    try:
        handler = Handler(**vars(cli_args))
    except AbortExecution:
        print("Aborted.")
        return
    handler.spherify_all()
    if getattr(cli_args, GET_EXEC_TIME):
        print(f"Execution time: {round(timeit.default_timer() - start, 1)} s")


if __name__ == '__main__':
    main()
