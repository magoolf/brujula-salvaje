"""Comando anonimizar_cuentas (infra/scheduler/crontab, scripts/ops/post-restore-local.sh)."""

from apps.ops.management.tarea import ComandoTarea


class Command(ComandoTarea):
    help = "Anonimiza las cuentas desactivadas hace más de 30 días."
    nombre = "anonimizar_cuentas"
