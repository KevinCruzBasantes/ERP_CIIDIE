"""
tpm/management/commands/generar_alertas.py

Comando para generar alertas periódicas del sistema.
Ejecutar diariamente vía cron en el servidor ProLiant:

    # crontab -e
    0 7 * * * /var/www/erp_laboratorio/venv/bin/python \
              /var/www/erp_laboratorio/manage.py generar_alertas

Qué revisa este comando:
  1. Mantenimientos próximos (≤ 7 días)
  2. Mantenimientos vencidos (fecha_programada < hoy, no finalizados)
  3. Materiales con stock bajo o en mínimo
  4. Certificaciones de usuario por vencer (≤ 30 días)
  5. Certificaciones ya vencidas

No genera duplicados: usa get_or_create para cada alerta.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = 'Genera alertas automáticas del sistema (ejecutar diariamente vía cron)'

    def handle(self, *args, **options):
        hoy = timezone.now().date()
        creadas = 0
        omitidas = 0

        creadas += self._alertas_mantenimiento(hoy)
        creadas += self._alertas_stock()
        creadas += self._alertas_certificaciones(hoy)

        self.stdout.write(
            self.style.SUCCESS(
                f'Alertas generadas: {creadas} nuevas, {omitidas} ya existían'
            )
        )

    # ──────────────────────────────────────────────────────────────────
    def _alertas_mantenimiento(self, hoy):
        from mantenimiento.models import Mantenimiento
        from tpm.models import Alerta

        creadas = 0
        limite_proximo = hoy + timezone.timedelta(days=7)

        pendientes = Mantenimiento.objects.filter(
            estado__in=('PROGRAMADO', 'EN_PROCESO')
        ).select_related('maquina')

        for m in pendientes:
            if m.fecha_programada < hoy:
                # Vencido
                _, nueva = Alerta.objects.get_or_create(
                    tipo='MANTENIMIENTO_VENCIDO',
                    maquina=m.maquina,
                    referencia_id=m.pk,
                    referencia_tipo='Mantenimiento',
                    resuelta=False,
                    defaults={
                        'severidad': 'CRITICA',
                        'mensaje': (
                            f"Mantenimiento {m.get_tipo_display()} VENCIDO en "
                            f"{m.maquina.nombre}. Programado: {m.fecha_programada.strftime('%d/%m/%Y')}."
                        ),
                    }
                )
                if nueva:
                    creadas += 1

            elif m.fecha_programada <= limite_proximo:
                # Próximo (≤ 7 días)
                dias = (m.fecha_programada - hoy).days
                _, nueva = Alerta.objects.get_or_create(
                    tipo='MANTENIMIENTO_PROXIMO',
                    maquina=m.maquina,
                    referencia_id=m.pk,
                    referencia_tipo='Mantenimiento',
                    resuelta=False,
                    defaults={
                        'severidad': 'ADVERTENCIA',
                        'mensaje': (
                            f"Mantenimiento {m.get_tipo_display()} en "
                            f"{m.maquina.nombre} en {dias} día(s) "
                            f"({m.fecha_programada.strftime('%d/%m/%Y')})."
                        ),
                    }
                )
                if nueva:
                    creadas += 1

        return creadas

    # ──────────────────────────────────────────────────────────────────
    def _alertas_stock(self):
        from inventario.models import Material
        from tpm.models import Alerta

        creadas = 0

        materiales_bajos = Material.objects.filter(
            activo=True,
            stock_actual__lte=models.F('stock_minimo')
        )

        for mat in materiales_bajos:
            _, nueva = Alerta.objects.get_or_create(
                tipo='STOCK_BAJO',
                maquina=None,
                referencia_id=mat.pk,
                referencia_tipo='Material',
                resuelta=False,
                defaults={
                    'severidad': 'ADVERTENCIA',
                    'mensaje': (
                        f"Stock bajo: {mat.nombre} — "
                        f"Actual: {mat.stock_actual} {mat.unidad_medida} / "
                        f"Mínimo: {mat.stock_minimo} {mat.unidad_medida}."
                    ),
                }
            )
            if nueva:
                creadas += 1

        return creadas

    # ──────────────────────────────────────────────────────────────────
    def _alertas_certificaciones(self, hoy):
        from tpm.models import CertificacionUsuario, Alerta

        creadas = 0
        limite_proximo = hoy + timezone.timedelta(days=30)

        certs = CertificacionUsuario.objects.filter(
            fecha_vencimiento__lte=limite_proximo
        ).select_related('usuario', 'maquina')

        for cert in certs:
            if not cert.usuario:
                continue  # certificacion huerfana (usuario eliminado) - nada que alertar
            if cert.fecha_vencimiento < hoy:
                tipo = 'CERTIFICACION_VENCIDA'
                severidad = 'CRITICA'
                mensaje = (
                    f"Certificación VENCIDA: {cert.usuario.get_full_name()} "
                    f"para {cert.maquina.nombre}. "
                    f"Venció el {cert.fecha_vencimiento.strftime('%d/%m/%Y')}."
                )
            else:
                dias = (cert.fecha_vencimiento - hoy).days
                tipo = 'CERTIFICACION_POR_VENCER'
                severidad = 'ADVERTENCIA'
                mensaje = (
                    f"Certificación por vencer: {cert.usuario.get_full_name()} "
                    f"para {cert.maquina.nombre} vence en {dias} día(s) "
                    f"({cert.fecha_vencimiento.strftime('%d/%m/%Y')})."
                )

            _, nueva = Alerta.objects.get_or_create(
                tipo=tipo,
                referencia_id=cert.pk,
                referencia_tipo='CertificacionUsuario',
                resuelta=False,
                defaults={
                    'severidad': severidad,
                    'maquina': cert.maquina,
                    'mensaje': mensaje,
                }
            )
            if nueva:
                creadas += 1

        return creadas


# Necesario para el F() en _alertas_stock
from django.db import models