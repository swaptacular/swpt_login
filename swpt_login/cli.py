import logging
import time
import sys
import click
from flask import current_app
from flask.cli import with_appcontext


@click.group("swpt_login")
def swpt_login():
    """Perform swpt_login specific operations."""


@swpt_login.command("flush")
@with_appcontext
@click.option(
    "-w",
    "--wait",
    type=float,
    default=10.0,
    help=(
        "Flush every FLOAT seconds."
        " If not specified, it defaults to 10 seconds."
    ),
)
@click.option(
    "--quit-early",
    is_flag=True,
    default=False,
    help="Exit after some time (mainly useful during testing).",
)
def flush(wait: float, quit_early: bool) -> None:
    """Periodically process unprocessed `registered_user_signal` rows.
    """
    from swpt_pythonlib.flask_signalbus import SignalBus
    from swpt_login.models import RegisteredUserSignal

    logger = logging.getLogger(__name__)
    logger.info("Started processing unprocessed rows.")
    signalbus: SignalBus = current_app.extensions["signalbus"]

    while True:
        started_at = time.time()
        try:
            count = signalbus.flushmany([RegisteredUserSignal])
        except Exception:
            logger.exception("Caught error while processing unprocessed rows.")
            sys.exit(1)

        if count > 0:
            logger.info(
                "%i unprocessed rows have been successfully processed.", count
            )
        else:
            logger.debug("0 unprocessed rows have been processed.")

        seconds_to_sleep = max(0.0, wait + started_at - time.time())
        if quit_early:
            break
        time.sleep(seconds_to_sleep)

    sys.exit(1)
