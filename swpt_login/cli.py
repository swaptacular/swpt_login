import logging
import time
import sys
import click
import signal
import ipaddress
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
from swpt_login.hydra import invalidate_credentials
from swpt_login.models import UserRegistration
from swpt_login.extensions import db
from swpt_login.redis import set_for_period


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
        "The number of worker processes."
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


@swpt_login.command("suspend_user_registrations")
@with_appcontext
@click.argument("user_ids", nargs=-1)
def suspend_user_registrations(user_ids: list[str]) -> None:
    """Suspend the registrations of users.
    """

    for user_id in user_ids:
        user = (
            UserRegistration.query
            .filter_by(user_id=user_id, status=0)
            .with_for_update()
            .one_or_none()
        )
        if user:
            assert user.status == 0
            invalidate_credentials(user_id)
            user.status = 1
            db.session.commit()


@swpt_login.command("resume_user_registrations")
@with_appcontext
@click.argument("user_ids", nargs=-1)
def resume_user_registrations(user_ids: list[str]) -> None:
    """Resume suspended user registrations.
    """

    for user_id in user_ids:
        user = (
            UserRegistration.query
            .filter_by(user_id=user_id)
            .with_for_update()
            .one_or_none()
        )
        if user:
            user.status = 0
            db.session.commit()


@swpt_login.command("ban_ip_addresses")
@with_appcontext
@click.option(
    "-h",
    "--hours",
    type=int,
    default=24,
    help="The number of hours to ban the IP addresses for (default 24h).",
)
@click.argument("ip_addresses", nargs=-1)
def ban_ip_addresses(ip_addresses: list[str], hours: int) -> None:
    """Ban a list of IP addresses from initiating email sending.

    IP_ADDRESSES should be a list of IP addresses or IP networks. For
    example: "1.2.3.4 1.2.3.128/29" will ban 1.2.3.4, 1.2.3.129, and
    1.2.3.130.

    """
    logger = logging.getLogger(__name__)
    period_seconds = 60 * 60 * hours

    for ip_address_or_network in ip_addresses:
        ip_network = ipaddress.ip_network(ip_address_or_network)
        for host in ip_network.hosts():
            ip = str(host)
            set_for_period(
                key=f"ip:{ip}",
                value="1000000000",  # some very big value
                period_seconds=period_seconds,
            )
            logger.debug("Banned %s for %i hours.", ip, hours)
