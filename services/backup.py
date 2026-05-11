import os
import shutil
import time
from datetime import date, datetime, timedelta

import requests

from core import db
from core.models import AccessEvent, Curso, IPBanido, LogAcesso, SecurityEvent
from services.analytics import analytics_snapshot


def _database_file(app):
    uri = app.config["SQLALCHEMY_DATABASE_URI"]
    if not uri.startswith("sqlite:///"):
        raise RuntimeError("Backup local automático está implementado para SQLite neste projeto atual.")
    return uri.replace("sqlite:///", "")


def build_backup(app):
    backup_dir = os.path.join(app.root_path, "backups")
    os.makedirs(backup_dir, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    database_source = _database_file(app)
    database_target = os.path.join(backup_dir, f"database-{stamp}.db")
    report_target = os.path.join(backup_dir, f"relatorio-{stamp}.txt")
    shutil.copy2(database_source, database_target)

    analytics = analytics_snapshot()
    cursos_total = Curso.query.count()
    cliques_total = db.session.query(db.func.coalesce(db.func.sum(Curso.cliques), 0)).scalar()
    acessos_total = AccessEvent.query.count()
    acessos_cursos = LogAcesso.query.count()
    bans_total = IPBanido.query.count()
    eventos_seg = SecurityEvent.query.count()
    top_cursos = Curso.query.order_by(Curso.cliques.desc()).limit(20).all()
    ultimos_acessos = AccessEvent.query.order_by(AccessEvent.created_at.desc()).limit(80).all()
    ultimos_cursos = LogAcesso.query.order_by(LogAcesso.id.desc()).limit(80).all()
    eventos = SecurityEvent.query.order_by(SecurityEvent.created_at.desc()).limit(60).all()

    lines = [
        "RELATORIO DIARIO EDUCALIVRE SOC",
        f"Gerado em: {datetime.now().isoformat(timespec='seconds')}",
        "",
        "RESUMO",
        f"Cursos cadastrados: {cursos_total}",
        f"Cliques totais: {cliques_total}",
        f"Acessos registrados: {acessos_total}",
        f"Acessos a cursos: {acessos_cursos}",
        f"IPs bloqueados: {bans_total}",
        f"Eventos de seguranca: {eventos_seg}",
        f"DAU: {analytics['dau']}",
        f"MAU: {analytics['mau']}",
        f"Retencao estimada: {analytics['retention']}%",
        "",
        "TOP CURSOS",
    ]
    lines.extend([f"- #{curso.id} {curso.nome}: {curso.cliques or 0} clique(s)" for curso in top_cursos])

    lines.extend(["", "ULTIMOS ACESSOS GERAIS"])
    for event in ultimos_acessos:
        lines.append(
            f"- {event.created_at} | {event.ip} | {event.country}/{event.city} | "
            f"{event.provider} | {event.method} {event.path} | bot={event.is_bot} vpn={event.is_vpn} tor={event.is_tor}"
        )

    lines.extend(["", "ULTIMOS ACESSOS A CURSOS"])
    for event in ultimos_cursos:
        lines.append(f"- #{event.id} | curso={event.curso_id} | ip={event.ip} | data={event.data}")

    lines.extend(["", "EVENTOS DE SEGURANCA"])
    for event in eventos:
        lines.append(f"- {event.created_at} | {event.severity} | {event.event_type} | {event.ip} | {event.message}")

    with open(report_target, "w", encoding="utf-8") as report:
        report.write("\n".join(lines))

    return database_target, report_target, {
        "cursos": cursos_total,
        "cliques": int(cliques_total or 0),
        "acessos": acessos_total,
        "bans": bans_total,
        "eventos": eventos_seg,
        "dau": analytics["dau"],
        "mau": analytics["mau"],
    }


def _telegram_config():
    return os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")


def send_backup_to_telegram(app):
    token, chat_id = _telegram_config()
    if not token or not chat_id:
        raise RuntimeError("TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID precisam estar configurados no .env.")

    database_file, report_file, summary = build_backup(app)
    caption = (
        "Backup diario EducaLivre SOC\n"
        f"Cursos: {summary['cursos']} | Cliques: {summary['cliques']} | Acessos: {summary['acessos']}\n"
        f"DAU: {summary['dau']} | MAU: {summary['mau']} | Bans: {summary['bans']}"
    )

    api = f"https://api.telegram.org/bot{token}"
    for path, label in ((database_file, "Banco SQLite"), (report_file, "Relatorio completo")):
        with open(path, "rb") as document:
            response = requests.post(
                f"{api}/sendDocument",
                data={"chat_id": chat_id, "caption": f"{label}\n{caption}"},
                files={"document": document},
                timeout=30,
            )
        response.raise_for_status()

    cleanup_summary = cleanup_after_backup()
    summary["cleanup"] = cleanup_summary
    return database_file, report_file, summary


def cleanup_after_backup():
    if os.environ.get("CLEANUP_AFTER_BACKUP", "1") != "1":
        return {"enabled": False, "removed": 0}

    retention_days = int(os.environ.get("BACKUP_CLEANUP_RETENTION_DAYS", "30"))
    cutoff_dt = datetime.utcnow() - timedelta(days=retention_days)
    cutoff_text = cutoff_dt.isoformat(timespec="seconds")

    access_deleted = AccessEvent.query.filter(AccessEvent.created_at < cutoff_dt).delete(synchronize_session=False)
    security_deleted = SecurityEvent.query.filter(SecurityEvent.created_at < cutoff_dt).delete(synchronize_session=False)
    course_access_deleted = LogAcesso.query.filter(LogAcesso.data < cutoff_text).delete(synchronize_session=False)
    db.session.commit()

    return {
        "enabled": True,
        "retention_days": retention_days,
        "access_events_removed": access_deleted,
        "security_events_removed": security_deleted,
        "course_access_removed": course_access_deleted,
        "removed": access_deleted + security_deleted + course_access_deleted,
    }


def start_daily_backup_scheduler(app):
    if os.environ.get("BACKUP_DAILY_ENABLED", "1") != "1":
        app.logger.info("Backup diario desativado por BACKUP_DAILY_ENABLED=0")
        return

    hour = int(os.environ.get("BACKUP_DAILY_HOUR", "3"))
    state = {"last_run": None}

    def loop():
        while True:
            now = datetime.now()
            if now.hour == hour and state["last_run"] != date.today():
                with app.app_context():
                    try:
                        send_backup_to_telegram(app)
                        state["last_run"] = date.today()
                        app.logger.info("Backup diario enviado ao Telegram")
                    except Exception:
                        app.logger.exception("Falha ao enviar backup diario")
                        state["last_run"] = date.today()
            time.sleep(60)

    return loop
