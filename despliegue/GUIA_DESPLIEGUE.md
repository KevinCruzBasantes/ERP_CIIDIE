# Guía de despliegue — ERP CIIDIE en servidorciidie

Destino: Debian 12 · Python 3.11 · MariaDB 10.11 · Nginx · IP 10.3.21.120.
El proyecto usa **Django 5.2 LTS** (fijado en requirements.txt porque
Django 6 exige Python 3.12, que Debian 12 no trae).

Arquitectura: Nginx (puerto **8082**) → gunicorn (127.0.0.1:8001, systemd)
→ MariaDB. Nginx sirve `/static/` y `/media/` directamente.

Todos los archivos mencionados están en esta carpeta `despliegue/`.

---

## 1. Paquetes del sistema

```bash
apt update
apt install -y python3-venv python3-dev build-essential pkg-config \
               default-libmysqlclient-dev git
```

## 2. Usuario y directorios

```bash
useradd --system --create-home --home-dir /opt/erp_ciidie --shell /usr/sbin/nologin erp
mkdir -p /opt/erp_ciidie/{app,backups} /var/log/erp-ciidie
chown -R erp:erp /opt/erp_ciidie /var/log/erp-ciidie
```

## 3. Copiar el proyecto

Desde tu máquina (PowerShell), copia el proyecto **sin** `media/` de pruebas:

```powershell
scp -r "Z:\Proyecto ERP\ERP_CIIDIE" root@10.3.21.120:/opt/erp_ciidie/app
```

(o `git clone` si el repositorio está en un remoto). Luego en el servidor:

```bash
chown -R erp:erp /opt/erp_ciidie/app
```

## 4. Entorno virtual y dependencias

```bash
python3 -m venv /opt/erp_ciidie/venv
/opt/erp_ciidie/venv/bin/pip install --upgrade pip
/opt/erp_ciidie/venv/bin/pip install -r /opt/erp_ciidie/app/requirements.txt
```

## 5. MariaDB

**5a. Tablas de zona horaria — paso OBLIGATORIO.** El proyecto usa
`USE_TZ` con hora de Guayaquil y filtros por fecha (`__date`); sin estas
tablas los reportes filtrados devuelven vacío **sin dar error**:

```bash
mariadb-tzinfo-to-sql /usr/share/zoneinfo | mariadb mysql
systemctl restart mariadb
```

**5b. Base y usuario** (elige una contraseña fuerte):

```sql
-- mariadb -u root
CREATE DATABASE erp_ciidie CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'erp'@'localhost' IDENTIFIED BY 'LA_CONTRASEÑA_ELEGIDA';
GRANT ALL PRIVILEGES ON erp_ciidie.* TO 'erp'@'localhost';
-- Solo si quieres poder correr la suite de tests en el servidor:
GRANT ALL PRIVILEGES ON test_erp_ciidie.* TO 'erp'@'localhost';
FLUSH PRIVILEGES;
```

## 6. Variables de entorno

```bash
cp /opt/erp_ciidie/app/despliegue/erp-ciidie.env.example /etc/erp-ciidie.env
chown root:erp /etc/erp-ciidie.env && chmod 640 /etc/erp-ciidie.env
```

Editar `/etc/erp-ciidie.env`: poner la contraseña de MariaDB y una
`DJANGO_SECRET_KEY` nueva, generada con:

```bash
/opt/erp_ciidie/venv/bin/python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

## 7. Migraciones, estáticos y primer usuario

```bash
cd /opt/erp_ciidie/app
set -a; source /etc/erp-ciidie.env; set +a
/opt/erp_ciidie/venv/bin/python manage.py migrate
/opt/erp_ciidie/venv/bin/python manage.py collectstatic --noinput
/opt/erp_ciidie/venv/bin/python manage.py createsuperuser
/opt/erp_ciidie/venv/bin/python manage.py check --deploy   # avisos informativos
```

**Datos iniciales**: la base arranca vacía. Entrar como superusuario y crear
los roles (ADMINISTRADOR, TECNICO, ESTUDIANTE, OPERADOR), usuarios, máquinas
y catálogos desde la propia aplicación — igual que se hizo en local. (La BD
local es de pruebas; no se migra.)

## 8. Servicio gunicorn

```bash
cp /opt/erp_ciidie/app/despliegue/erp-ciidie.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now erp-ciidie
systemctl status erp-ciidie          # debe decir "active (running)"
```

## 9. Nginx

El sitio escucha en el **8080** para no chocar con filebrowser/inventario.
Verificar primero qué puertos ya están tomados:

```bash
nginx -T | grep -E "listen|server_name"
```

```bash
cp /opt/erp_ciidie/app/despliegue/nginx-erp-ciidie.conf /etc/nginx/sites-available/erp-ciidie
ln -s /etc/nginx/sites-available/erp-ciidie /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
```

## 10. Tareas programadas

```bash
cp /opt/erp_ciidie/app/despliegue/erp-ciidie.cron /etc/cron.d/erp-ciidie
chmod 644 /etc/cron.d/erp-ciidie
```

Incluye: `generar_alertas` diario a las 06:00 y respaldo `mariadb-dump`
a las 02:30 con retención de 30 días (el respaldo requiere `/root/.my.cnf`
o socket auth de root).

## 11. Verificación final

1. `http://10.3.21.120:8082/` → landing con selector de perfil.
2. Iniciar sesión con el superusuario.
3. Crear un rol y un usuario de prueba; entrar con él.
4. Generar el reporte "Respaldo completo" en Reportes (ejercita BD + Excel + media).
5. Esperar 30 min inactivo o probar el cierre de sesión automático.
6. `bash -c 'set -a; source /etc/erp-ciidie.env; cd /opt/erp_ciidie/app && /opt/erp_ciidie/venv/bin/python manage.py generar_alertas'` a mano una vez.

## Notas y deuda aceptada

- **HTTP sin TLS en red interna** — aceptado por decisión del proyecto.
  Si algún día se expone fuera de la red, agregar HTTPS y
  `SECURE_*`/`SESSION_COOKIE_SECURE`.
- **/media/ sin autenticación** — los Excel de reportes y fotos quedan
  descargables para quien tenga la URL exacta dentro de la red (deuda ya
  documentada en AUDITORIA_PRUEBAS.md).
- Actualizaciones futuras: subir el código, y correr
  `migrate` + `collectstatic` + `systemctl restart erp-ciidie`.
