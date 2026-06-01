import json
import logging
import threading
import time
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from . import crud, models
from .database import SessionLocal

log = logging.getLogger(__name__)


def _parse_hhmm(raw: str) -> tuple[int, int]:
    try:
        hh, mm = raw.strip().split(":", 1)
        hour, minute = int(hh), int(mm)
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return hour, minute
    except (AttributeError, ValueError):
        return 3, 0
    return 3, 0


def _load_preset_volumes(preset: models.MaintenancePreset) -> dict:
    try:
        return json.loads(preset.volumes_json or "{}")
    except (TypeError, ValueError):
        return {}


def _find_active_preset(db: Session, names: list[str]) -> models.MaintenancePreset | None:
    for name in names:
        p = (
            db.query(models.MaintenancePreset)
            .filter(models.MaintenancePreset.name == name)
            .filter(models.MaintenancePreset.is_active == True)  # noqa: E712
            .first()
        )
        if p:
            return p
    return None


def _already_logged_today(db: Session, run_date: datetime.date) -> bool:
    tag = f"[AUTO_SCHED {run_date.isoformat()}]"
    return (
        db.query(models.ServiceAction)
        .filter(models.ServiceAction.notes.contains(tag))
        .first()
        is not None
    )


def _latest_project_time(db: Session) -> datetime | None:
    return db.query(models.Project.created_at).order_by(models.Project.created_at.desc()).limit(1).scalar()


def _latest_deep_or_moist_time(db: Session) -> datetime | None:
    names = [
        "Deep Clean",
        "Automatic Moisturizing",
        "Safe Shutdown Moisturizing",
        "Automatic Deep Clean",
    ]
    return (
        db.query(models.ServiceAction.occurred_at)
        .filter(models.ServiceAction.name_snapshot.in_(names))
        .order_by(models.ServiceAction.occurred_at.desc())
        .limit(1)
        .scalar()
    )


def _latest_moist_time(db: Session) -> datetime | None:
    names = [
        "Automatic Moisturizing",
        "Safe Shutdown Moisturizing",
    ]
    return (
        db.query(models.ServiceAction.occurred_at)
        .filter(models.ServiceAction.name_snapshot.in_(names))
        .order_by(models.ServiceAction.occurred_at.desc())
        .limit(1)
        .scalar()
    )


def _latest_auto_flash_time(db: Session) -> datetime | None:
    return (
        db.query(models.ServiceAction.occurred_at)
        .filter(models.ServiceAction.name_snapshot == "Automatic Flash Clean")
        .order_by(models.ServiceAction.occurred_at.desc())
        .limit(1)
        .scalar()
    )


def run_auto_flash_clean_for_time(db: Session, run_at: datetime) -> None:
    last_print_at = _latest_project_time(db)
    last_moist_at = _latest_moist_time(db)
    last_flash_at = _latest_auto_flash_time(db)

    idle_over_10m = last_print_at is None or (run_at - last_print_at) >= timedelta(minutes=10)
    if not idle_over_10m:
        return

    # While the machine remains in moisturizing state, avoid repeated flash-clean logs.
    already_moisturized_without_new_print = (
        last_moist_at is not None
        and (last_print_at is None or last_moist_at >= last_print_at)
    )
    if already_moisturized_without_new_print:
        return

    if last_flash_at is not None and (run_at - last_flash_at) < timedelta(minutes=10):
        return

    preset = _find_active_preset(db, ["Automatic Flash Clean", "Flash Clean"])
    if not preset:
        log.warning("Auto flash clean: no flash clean preset found")
        return

    crud.log_service_action(
        db,
        preset_id=preset.id,
        kind=preset.kind,
        name="Automatic Flash Clean",
        volumes=_load_preset_volumes(preset),
        notes=f"[AUTO_FLASH {run_at.isoformat(timespec='minutes')}] trigger=idle>=10m",
        occurred_at=run_at,
    )


def run_auto_maintenance_for_time(db: Session, run_at: datetime) -> None:
    run_date = run_at.date()
    if _already_logged_today(db, run_date):
        return

    last_print_at = _latest_project_time(db)
    last_deep_or_moist_at = _latest_deep_or_moist_time(db)
    last_moist_at = _latest_moist_time(db)

    idle_over_1_day = last_print_at is None or (run_at - last_print_at) > timedelta(days=1)
    no_deep_or_moist_3d = (
        last_deep_or_moist_at is None or (run_at - last_deep_or_moist_at) >= timedelta(days=3)
    )

    auto_note = f"[AUTO_SCHED {run_date.isoformat()}] Scheduled maintenance sync"

    # Match eufy strategy: idle machines moisturize; otherwise enforce periodic deep clean.
    if idle_over_1_day:
        # If already moisturized and there has been no new print activity since,
        # skip re-logging to avoid fake repeated liquid consumption.
        already_moisturized_without_new_print = (
            last_moist_at is not None
            and (last_print_at is None or last_moist_at >= last_print_at)
        )
        if already_moisturized_without_new_print:
            return

        preset = _find_active_preset(db, ["Automatic Moisturizing", "Safe Shutdown Moisturizing"])
        if not preset:
            log.warning("Auto 3am maintenance: no moisturizing preset found")
            return
        crud.log_service_action(
            db,
            preset_id=preset.id,
            kind=preset.kind,
            name=preset.name,
            volumes=_load_preset_volumes(preset),
            notes=f"{auto_note} | trigger=idle>1d",
            occurred_at=run_at,
        )
        return

    if no_deep_or_moist_3d:
        preset = _find_active_preset(db, ["Automatic Deep Clean", "Deep Clean"])
        if not preset:
            log.warning("Auto 3am maintenance: no deep clean preset found")
            return
        crud.log_service_action(
            db,
            preset_id=preset.id,
            kind=preset.kind,
            name="Automatic Deep Clean",
            volumes=_load_preset_volumes(preset),
            notes=f"{auto_note} | trigger=no_deep_or_moist>=3d",
            occurred_at=run_at,
        )


def _scheduler_loop(default_hour: int, default_minute: int) -> None:
    last_checked_date: datetime.date | None = None
    while True:
        db = SessionLocal()
        try:
            now = datetime.now()
            cfg = crud.get_automation_config(db)

            enabled = bool(cfg.auto_maintenance_log_enabled)
            hour, minute = _parse_hhmm(cfg.auto_maintenance_log_time or f"{default_hour:02d}:{default_minute:02d}")
            should_run_today = now.hour > hour or (now.hour == hour and now.minute >= minute)

            if enabled:
                run_auto_flash_clean_for_time(db, now)

            if enabled and should_run_today and last_checked_date != now.date():
                run_at = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                run_auto_maintenance_for_time(db, run_at)
                last_checked_date = now.date()
        except Exception:
            log.exception("Auto maintenance scheduler failed")
        finally:
            db.close()

        # Keep a low footprint while still catching schedule time quickly.
        time.sleep(30)


def start_auto_maintenance_scheduler() -> None:
    hour, minute = _parse_hhmm("03:00")

    t = threading.Thread(
        target=_scheduler_loop,
        args=(hour, minute),
        daemon=True,
        name="auto-maintenance-scheduler",
    )
    t.start()
    log.info("Auto maintenance scheduler started")
