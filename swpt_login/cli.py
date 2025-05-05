import logging
import time
import sys
import click
import signal
from typing import Optional, Any
from flask import current_app
from flask.cli import with_appcontext
from flask_sqlalchemy.model import Model
from swpt_pythonlib.flask_signalbus import SignalBus, get_models_to_flush
from swpt_pythonlib.multiproc_utils import (
    spawn_worker_processes,
    try_unblock_signals,
    HANDLED_SIGNALS,
)


@click.group("swpt_login")
def swpt_login():
    """Perform swpt_login specific operations."""


@swpt_login.command("flush")
@with_appcontext
@click.option(
    "-p",
    "--processes",
    type=int,
    help=(
        "Then umber of worker processes."
        " If not specified, the value of the FLUSH_PROCESSES environment"
        " variable will be used, defaulting to 1 if empty."
    ),
)
@click.option(
    "-w",
    "--wait",
    type=float,
    help=(
        "Flush every FLOAT seconds."
        " If not specified, the value of the FLUSH_PERIOD environment"
        " variable will be used, defaulting to 2 seconds if empty."
    ),
)
@click.option(
    "--quit-early",
    is_flag=True,
    default=False,
    help="Exit after some time (mainly useful during testing).",
)
@click.argument("task_types", nargs=-1)
def flush(
    task_types: list[str],
    processes: int,
    wait: float,
    quit_early: bool,
) -> None:
    """Periodically process pending tasks.

    If a list of TASK_TYPES is given, flushes only these types of
    pending tasks. If no TASK_TYPES are specified, flushes all pending
    tasks.

    """

    logger = logging.getLogger(__name__)
    models_to_flush = get_models_to_flush(
        current_app.extensions["signalbus"], task_types
    )
    logger.info("Started processing pending tasks.")
    logger.info(
        "Started flushing %s.", ", ".join(m.__name__ for m in models_to_flush)
    )
    processes = (
        processes
        if processes is not None
        else current_app.config["FLUSH_PROCESSES"]
    )
    wait = (
        wait
        if wait is not None
        else current_app.config["FLUSH_PERIOD"]
    )

    def _flush(
        models_to_flush: list[type[Model]],
        wait: Optional[float],
    ) -> None:
        from swpt_login import create_app

        app = current_app if quit_early else create_app()
        stopped = False

        def stop(signum: Any = None, frame: Any = None) -> None:
            nonlocal stopped
            stopped = True

        for sig in HANDLED_SIGNALS:
            signal.signal(sig, stop)
        try_unblock_signals()

        with app.app_context():
            signalbus: SignalBus = current_app.extensions["signalbus"]
            while not stopped:
                started_at = time.time()
                try:
                    count = signalbus.flushmany(models_to_flush)
                except Exception:
                    logger.exception("Caught error while processing pending tasks.")
                    sys.exit(1)

                if count > 0:
                    logger.info("%i tasks have been successfully processed.", count)
                else:
                    logger.debug("0 tasks have been processed.")

                seconds_to_sleep = max(0.0, wait + started_at - time.time())
                if quit_early:
                    break
                time.sleep(seconds_to_sleep)

    if quit_early:
        _flush(models_to_flush, wait)
    else:
        spawn_worker_processes(
            processes=processes,
            target=_flush,
            models_to_flush=models_to_flush,
            wait=wait,
        )

    sys.exit(1)
