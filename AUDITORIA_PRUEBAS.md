# Auditoría por pruebas unitarias — evaluación pre-producción

Objetivo: determinar si el sistema está listo para subirse a un servidor.
Metodología: 3 etapas de pruebas; los bugs se documentaron al detectarse y
se corrigieron todos al cierre de la Etapa 3.

**Estado final (2026-07-07): 125 pruebas, todas en verde. 5 bugs
detectados y corregidos.** Correr la suite: `python manage.py test`

---

## Etapa 1 — Permisos, modelos y signals (2026-07-07)

**80 pruebas · 77 en verde · 3 en rojo (2 bugs reales)**

Cobertura: matriz de roles de `usuarios/permisos.py` (incluida regresión del
bug de tildes), propiedades y validaciones de modelos de las 6 apps,
signals de alertas (tpm) y de órdenes automáticas (mantenimiento).

### Bugs detectados

| ID | Severidad | Descripción | Evidencia |
|----|-----------|-------------|-----------|
| BUG-01 | Media | `TransferenciaPieza.__str__` (maquinas/models.py:349) hace `self.maquina_origen.codigo` sin proteger el `None` — ambos FKs son `null=True` (transferencias desde/hacia bodega). Revienta el admin, logs o cualquier plantilla que muestre la transferencia. | `maquinas.tests.TransferenciaPiezaTest.test_str_sin_maquina_origen_no_debe_reventar` |
| BUG-02 | Alta | `sincronizar_estado_maquina` (mantenimiento/signals.py:32) decide usando `instance.maquina.estado` **en memoria**, que puede estar desactualizado respecto a la BD. Consecuencia: al finalizar/cancelar una OM la máquina puede quedarse en MANTENIMIENTO para siempre y las alertas de reservas afectadas no se resuelven. | `mantenimiento.tests.SincronizacionEstadoMaquinaTest.test_finalizar_la_om_devuelve_la_maquina_a_operativa` y `test_reserva_aprobada_recibe_alerta_y_se_resuelve_al_finalizar` |

### Observaciones (no bloquean producción, decidir después)

- **OBS-01**: el docstring de `tpm/signals.py` promete un signal de
  `CertificacionUsuario` ("al guardar, revisa si hay alertas previas que
  limpiar") que **no existe** en el archivo. O falta el signal o sobra la doc.
- **OBS-02**: los permisos por rol usan coincidencia por subcadena
  (`'phd' in rol`): un rol hipotético "Estudiante de PhD" sería admin.
  Con el catálogo actual de roles no pasa, pero es frágil ante roles nuevos.

### Infraestructura de pruebas

- `testing_comun.py` (raíz): fábricas de usuarios/roles, máquinas,
  certificaciones, reservas, OTs y códigos de parada.
- `config/settings.py`: hasher MD5 solo cuando corre `manage.py test`
  (la suite pasó de 141 s a segundos).

---

## Etapa 2 — Vistas críticas (2026-07-07)

**36 pruebas · 31 en verde · 5 en rojo (3 bugs reales nuevos)**

Cobertura: login (por username y por cédula, cuentas suspendidas), matriz de
control de acceso (8 vistas × 4 roles), middleware de restricción de
estudiantes, CRUD de usuarios (incl. eliminación con reservas), flujo completo
reserva → aprobar → OT → cerrar (incl. regresión del 500 por certificación
vencida), consumos de material y endpoints JSON de operadores.

### Bugs detectados

| ID | Severidad | Descripción | Evidencia |
|----|-----------|-------------|-----------|
| BUG-03 | Media | Los endpoints JSON de operadores y el queryset del formulario de reservas filtran `rol__nombre='OPERADOR'` **exacto** (reservas/views.py:69,119 y forms.py:42), mientras `permisos.py` normaliza mayúsculas/tildes. Un operador con rol "Operador" existe para el sistema (ve su dashboard) pero es inseleccionable para los estudiantes. | `reservas.tests_vistas.OperadoresCertificadosEndpointTest.test_rol_con_otra_capitalizacion_tambien_deberia_aparecer` |
| BUG-04 | Media | `dashboard_admin` y `dashboard_tecnico` solo tienen `@login_required`. El middleware frena a los estudiantes, pero un **operador o un usuario sin rol** puede abrirlos por URL directa y ver todos los KPIs administrativos. | `usuarios.tests_vistas.DashboardsPorRolTest` (3 tests) |
| BUG-05 | **Alta** | **Registrar consumo de material desde la orden de trabajo nunca funciona.** La vista convierte la cantidad con `float()` (reservas/views.py:504) y `ConsumoMaterial.save()` hace `stock_actual -= cantidad` (Decimal −= float) → `TypeError`, que la vista atrapa y muestra como mensaje de error críptico. El consumo jamás se registra ni se descuenta stock. | `reservas.tests_vistas.FlujoOrdenTrabajoTest.test_registrar_consumo_descuenta_stock` |

### Verificado en verde (destacable)

- Nadie puede aprobar su propia reserva; el autorizador queda registrado.
- Cerrar una OT dos veces no duplica las horas acumuladas de la máquina.
- Regresión del 500 al cerrar orden con certificación vencida: sigue arreglada.
- Eliminar un usuario conserva sus reservas con `usuario=NULL` (SET_NULL).
- Cuentas suspendidas no pueden iniciar sesión; login por cédula funciona.

## Etapa 3 — Reportes y correcciones (2026-07-07)

**9 pruebas de reportes · todas en verde al primer intento** (el módulo
recién renovado no tenía bugs): los 6 endpoints generan Excel válido, el
historial guarda el mismo archivo re-descargable con período y autor, los
roles sin permiso quedan fuera, y el respaldo completo incluye las ~30
tablas con hoja índice y **sin** la columna `password`.

### Correcciones aplicadas (todas con test de regresión)

| ID | Corrección |
|----|-----------|
| BUG-01 | `TransferenciaPieza.__str__` muestra "bodega" cuando origen/destino es NULL (maquinas/models.py). |
| BUG-02 | `sincronizar_estado_maquina` consulta el estado de la máquina en BD en vez del objeto en memoria (mantenimiento/signals.py). |
| BUG-03 | Filtros de rol de operador ahora usan `__iexact` en los 2 endpoints JSON y en `ReservaForm` (reservas/views.py, forms.py). |
| BUG-04 | `dashboard_admin` y `dashboard_tecnico` exigen `es_admin_o_tecnico` (usuarios/views.py). |
| BUG-05 | `registrar_consumo` convierte la cantidad con `Decimal` — registrar consumos desde la OT vuelve a funcionar (reservas/views.py). |
| OBS-01 | Docstring de tpm/signals.py ya no promete un signal inexistente. |

OBS-02 (roles por subcadena) queda documentada como decisión de diseño, sin cambio.

---

## Veredicto: ¿listo para producción?

**Funcionalmente sí** — la lógica de negocio (permisos, reservas,
mantenimiento, TPM, inventario, reportes) está verificada por 125 pruebas y
los 5 bugs encontrados quedaron corregidos. El más grave (BUG-05, consumos
de material inoperantes) habría aparecido el primer día de uso real.

**Checklist de despliegue pendiente** (config, no código — nada de esto lo
cubre la suite):

1. `DEBUG = False` y `ALLOWED_HOSTS` con el dominio/IP del servidor.
2. `SECRET_KEY` fuera del código (variable de entorno) — la actual empieza
   con `django-insecure-` y está en el repositorio.
3. Credenciales de PostgreSQL por variables de entorno.
4. `media/` (reportes Excel, fotos de bitácora) se sirve sin autenticación —
   deuda ya conocida; al menos no exponer el directorio en el servidor web.
5. `python manage.py collectstatic` + servir estáticos desde el servidor web.
6. Respaldos programados de la base (el reporte "Respaldo completo" ayuda,
   pero no reemplaza un `pg_dump` automatizado).
7. Programar el management command `generar_alertas` (cron diario) en el
   servidor — hoy depende de ejecutarlo a mano.
