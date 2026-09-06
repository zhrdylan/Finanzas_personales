# Flux — Finanzas Personales

Aplicación web **full-stack** para la gestión de finanzas personales: registro de
ingresos y gastos, categorías personalizables, **metas de ahorro con progreso**,
**moneda de visualización configurable (COP / USD / EUR)**, panel financiero con
gráficos interactivos, **predicción del gasto del próximo mes (regresión lineal)**
y **detección de movimientos anómalos (IsolationForest / Z modificado con severidad)**.

El proyecto está construido como un **Monolito Modular** con arquitectura en
capas dentro de cada módulo de negocio, con **MySQL 9.6 como único motor de base
de datos** (no existe soporte ni fallback a SQLite).

---

## 1. Stack tecnológico

| Capa        | Tecnología                                             |
|-------------|--------------------------------------------------------|
| Backend     | Python 3.11+, FastAPI 0.141, Pydantic 2.13, Uvicorn    |
| ORM         | SQLAlchemy 2.0 (async) + Alembic (migraciones)         |
| Base datos  | **MySQL 9.6** (driver asíncrono `aiomysql`)            |
| Frontend    | HTML5 semántico y accesible (sin `<span>`, `<dialog>` nativo), CSS3 modular, JavaScript ES Modules (vanilla) |
| Gráficos    | Chart.js (servido localmente, sin CDN)                 |
| Análisis    | Pandas + Scikit-learn (solo dentro del módulo `analysis`) |
| Tasas       | httpx → Frankfurter v2 (solo backend, sin API key)     |
| Exportación | Pandas (CSV) + ReportLab (PDF), en memoria             |
| Calidad     | Ruff (lint + format), Pytest, Bandit, pip-audit        |

Sin React, sin Vue, sin Tailwind, sin frameworks frontend ni backend distintos
de los listados. El frontend es una SPA servida por el propio FastAPI.

---

## 2. Arquitectura: Monolito Modular

Cada módulo de negocio vive en `app/modules/<modulo>/` y mantiene la misma
separación interna de responsabilidades:

```
Router (HTTP)  →  Schemas (Pydantic)  →  Service (reglas)  →  Repository (consultas)  →  Models (ORM)
```

- **Router**: define endpoints, valida entrada con Pydantic y delega. Sin lógica de negocio.
- **Service**: reglas de negocio, cálculos y coordinación. No ejecuta SQL directo.
- **Repository**: consultas SQLAlchemy (siempre filtradas por `usuario_id`).
- **Models**: tablas ORM del módulo.
- `app/core/` contiene la infraestructura transversal (configuración, base de
  datos, seguridad, dependencias) y `app/shared/` los elementos compartidos
  (excepciones de dominio, paginación, catálogo de monedas).

Detalles completos en [`docs/arquitectura.md`](docs/arquitectura.md).

---

## 3. Estructura del proyecto

```
finanzas-personales/
├── alembic/                      # Migraciones (0001–0004: base, metas, notas, tasas+monedas)
│   └── versions/
├── app/
│   ├── core/                     # config, database (engine async), security (bcrypt+JWT), deps, rate_limit
│   ├── modules/
│   │   ├── auth/                 # registro, login (rate limit), refresh rotativo, logout
│   │   ├── users/                # perfil, contraseña y preferencias (moneda)
│   │   ├── categories/           # CRUD de categorías por usuario
│   │   ├── transactions/         # CRUD de movimientos (moneda, filtros, paginación)
│   │   ├── goals/                # metas de ahorro (moneda) + aportes + progreso
│   │   ├── dashboard/            # agregaciones del panel (?moneda=, SQL + Pandas)
│   │   ├── analysis/             # predicción (regresión) y anomalías (sklearn)
│   │   ├── exchange_rates/       # tasas Frankfurter v2 + caché MySQL + convert()
│   │   └── exports/              # CSV (Pandas) y PDF (ReportLab) en memoria
│   ├── shared/                   # excepciones de dominio, moneda, paginación
│   ├── templates/index.html      # SPA (plantillas <template> por vista)
│   └── static/
│       ├── css/                  # tokens, reset, base, layout, components/, views/, responsive
│       ├── img/                  # logo-icon.png (sidebar/login), favicon.ico
│       ├── js/
│       │   ├── core/             # api (HTTP + renovación de tokens), router, sesión, config
│       │   ├── services/         # endpoints.js (único punto de acceso a la API)
│       │   ├── utils/            # dom, formato (moneda/fechas), formularios, modal, ui
│       │   └── modules/          # auth, dashboard, transactions, categories, goals, analysis, profile
│       └── vendor/chart.umd.js
├── tests/                        # unit/ + api/ + integration/ (sin frontend/tests)
├── docs/arquitectura.md
├── requirements.txt              # dependencias de producción (versiones fijadas)
├── requirements-dev.txt          # herramientas de desarrollo (tests, lint, seguridad)
├── pyproject.toml                # configuración de Ruff, Pytest y Bandit
├── alembic.ini
└── .env.example                  # plantilla de configuración (NUNCA subir .env)
```

---

## 4. Requisitos previos

1. **Python 3.11 o superior** (`python --version`).
2. **Laragon** (o cualquier instalación local de **MySQL 9.6**).
   - Descarga: <https://laragon.org/download/> (edición *Full* incluye MySQL).
   - MySQL 9.6 es la versión objetivo del proyecto; MySQL 8.4+ también funciona
     por compatibilidad de protocolo, pero la documentación asume 9.6.
3. No se requiere Docker. No se requiere Node.js (no se usa en este proyecto).

---

## 5. Puesta en marcha con Laragon + MySQL 9.6 (paso a paso)

### 5.1 Iniciar MySQL desde Laragon

1. Abre **Laragon** y pulsa **Iniciar todo** (o solo el botón de MySQL).
2. Verifica que el estado de MySQL esté en verde (puerto por defecto `3306`).

### 5.2 Crear la base de datos en phpMyAdmin

1. En Laragon, clic derecho → **Tools → phpMyAdmin** (o `http://localhost/phpmyadmin`).
2. En Laragon por defecto el usuario `root` **no tiene contraseña**.
3. Crea la base de datos (pestaña *SQL*):

   ```sql
   CREATE DATABASE finanzas_personales
     CHARACTER SET utf8mb4
     COLLATE utf8mb4_unicode_ci;
   ```

   > El collation `utf8mb4_unicode_ci` es importante: garantiza acentos y ñ.

   Si prefieres un usuario dedicado en lugar de `root`:

   ```sql
   CREATE USER 'finanzas'@'localhost' IDENTIFIED BY 'TuContraseñaSegura';
   GRANT ALL PRIVILEGES ON finanzas_personales.* TO 'finanzas'@'localhost';
   FLUSH PRIVILEGES;
   ```

### 5.3 Obtener el proyecto y crear el entorno virtual

```bat
cd C:\laragon\www\finanzas-personales
python -m venv .venv
.venv\Scripts\activate
```

### 5.4 Instalar dependencias

```bat
pip install -r requirements.txt
:: Opcional (tests, lint, seguridad):
pip install -r requirements-dev.txt
```

### 5.5 Configurar variables de entorno

```bat
copy .env.example .env
```

Edita `.env` y ajusta **al menos** estas dos variables:

```ini
SECRET_KEY=<genera una con: python -c "import secrets; print(secrets.token_hex(32))">
DATABASE_URL=mysql+aiomysql://root:@127.0.0.1:3306/finanzas_personales
```

- En Laragon por defecto (root sin contraseña) la URL queda como arriba.
- Si tu root tiene contraseña: `mysql+aiomysql://root:TuContraseña@127.0.0.1:3306/finanzas_personales`.
- Si la contraseña contiene caracteres especiales, codifícalos en la URL
  (`@` → `%40`, `:` → `%3A`, `/` → `%2F`).
- La URL **debe** empezar por `mysql+aiomysql://`: la aplicación rechaza
  cualquier otro motor al arrancar (no existe fallback a SQLite).

### 5.6 Ejecutar las migraciones de Alembic

```bat
alembic upgrade head
```

Esto crea las tablas `usuarios`, `refresh_tokens`, `categorias`, `movimientos`,
`metas`, `preferencias_usuario` y `exchange_rates` (migraciones `0001`–`0004`:
base, metas, notas y tasas+monedas). Compruébalo en
phpMyAdmin si quieres.

### 5.7 Iniciar el backend

```bat
uvicorn app.main:app --reload
```

- API y SPA: <http://127.0.0.1:8000/>
- Documentación interactiva (Swagger): <http://127.0.0.1:8000/docs>

El frontend (SPA) se sirve desde el propio FastAPI: **no hay que arrancar nada
más**. Con `--reload` los cambios de Python recargan el servidor; los cambios
de CSS/JS solo requieren refrescar el navegador.

### 5.8 Comprobar la conexión

1. Abre <http://127.0.0.1:8000/api/v1/health> → debe responder `{"estado": "ok", ...}`.
2. Abre la app, crea una cuenta desde **Crear cuenta** y empieza a registrar
   movimientos. No existen cuentas de demostración ni datos precargados.

---

## 6. Funcionalidades

### 6.1 Autenticación y seguridad

- Registro e inicio de sesión con **bcrypt** (hash de contraseñas).
- **Inicio con Google** (opcional, `GOOGLE_CLIENT_ID`): botón GIS que verifica
  el ID token en el backend; crea la cuenta o vincula por correo verificado y
  emite los mismos tokens (con rotación y logout intactos).
- JWT con **access token** (30 min) + **refresh token** (7 días) con
  **rotación de un solo uso** y revocación (logout y logout de todos los
  dispositivos). En la BD solo se guarda el **hash SHA-256** del refresh token.
- Rate limiting del login (5 intentos/minuto por IP, configurable).
- Todos los recursos comprueban la pertenencia al usuario autenticado en el
  **backend** (prevención de IDOR: pedir `/movimientos/123` de otro usuario
  responde 404).
- Consultas siempre parametrizadas vía ORM; entrada validada con Pydantic;
  errores 500 sin filtrar detalles internos.

### 6.2 Monedas y tasas de cambio reales (COP / USD / EUR)

- La moneda de visualización se configura en **Perfil → Preferencias de
  cuenta** y se **persiste en MySQL** (tabla `preferencias_usuario`).
- Cada **movimiento** y cada **meta** guarda su **moneda original**
  (columnas `moneda`, migración `0004`; filas antiguas = `COP`).
- Conversión real con el módulo `exchange_rates` (Frankfurter **v2**, solo
  desde el backend, sin API key): `GET /api/v1/tasas?base=USD&quote=COP&fecha=2026-09-04`.
- Tasas **persistidas en MySQL** (tabla `exchange_rates`, clave única
  base/quote/fecha): caché exacta → proveedor → última almacenada
  (fallback); sin datos válidos responde **503 controlado** (nunca inventa
  tasas). La tasa usada es la de la **fecha del movimiento** (histórica
  determinística, reproducible). Todo en `Decimal` (tasa `18,6`, importes
  a 2 decimales `ROUND_HALF_UP`).
- El valor original **jamás se sobrescribe**: dashboard, metas, análisis y
  reportes convierten solo para mostrar.
- Formatos aplicados con `Intl.NumberFormat` según el locale de cada moneda:

  | Moneda | Locale | Ejemplo       |
  |--------|--------|---------------|
  | COP    | es-CO  | `$ 1.250.000` |
  | USD    | en-US  | `$1,250.00`   |
  | EUR    | es-ES  | `1.250,00 €`  |

- Dashboard y análisis aceptan `?moneda=` (por defecto, la preferencia);
  movimientos acepta `moneda` al crear/editar y como filtro.

### 6.3 Movimientos y categorías

- CRUD completo de ingresos/gastos con categoría, monto (`DECIMAL(12,2)` en
  la BD, nunca `FLOAT`), **moneda original (COP/USD/EUR)**, fecha,
  descripción, notas y método de pago.
- Filtros por tipo, categoría, método de pago, **moneda**, rango de fechas
  y búsqueda de texto (concepto + notas), con paginación.
- Categorías con color e icono, privadas de cada usuario; no se puede eliminar
  una categoría con movimientos asociados (error 409 explicativo).

### 6.4 Metas de ahorro

- CRUD completo en el módulo `goals` (tabla `metas`).
- Crear meta con nombre, monto objetivo, **moneda (COP/USD/EUR)**,
  monto inicial opcional y fecha límite.
- **Registrar aportes** (`POST /metas/{id}/aportes`) que incrementan el ahorro.
- Porcentaje de progreso y estado calculados: *En curso* → *¡Buen avance!*
  (≥ 40 %) → *Meta cercana* (≥ 80 %) → *¡Alcanzada!* (100 %).
- Todo persistido en MySQL; sin datos mock.

### 6.5 Panel (dashboard) y análisis

- Panel con datos reales del usuario autenticado: ingresos, gastos, balance,
  porcentaje de ahorro, predicción del próximo mes, distribución de gastos por
  categoría (dona), evolución de 6 meses (línea) y movimientos recientes.
- Vista de **Análisis** separada: hero de predicción con distribución
  proyectada, ahorro mensual (%) y tabla de anomalías.
- Gráficos con **Chart.js** servido localmente (funciona sin internet).
- La predicción usa **regresión lineal** (scikit-learn) sobre los gastos
  mensuales; las anomalías usan **IsolationForest** (≥ 30 muestras) o
  **Z modificado (mediana ± MAD, ≥ 3.5)** (10–29) con severidad moderada/alta/crítica.
  Requieren historial suficiente; si no lo hay, la API
  responde con `disponible: false` y un mensaje claro (sin valores inventados).
- Frontera de arquitectura: `analysis` **solo lee** datos; nunca modifica
  movimientos. Predicción y anomalías convierten a la moneda pedida
  (`?moneda=`, por defecto la preferencia) antes de agregar.

### 6.6 Exportar mis datos (CSV / PDF)

- En **Perfil → Exportar mis datos**: `Descargar CSV` y `Descargar PDF`.
- Endpoints autenticados (usuario siempre del JWT, nunca `?user_id`):
  `GET /api/v1/exports/transactions.csv` y
  `GET /api/v1/exports/transactions.pdf`, con los mismos filtros del
  listado (`tipo`, `categoria_id`, `metodo_pago`, `moneda`,
  `fecha_desde/hasta`, `q`) más `visualizacion` (moneda de destino).
- CSV generado con **Pandas** (UTF-8 con BOM): fecha, tipo, descripción,
  categoría, monto/moneda original, moneda de visualización, tasa y fecha
  de tasa, monto convertido. Archivo `flux_movimientos_AAAA-MM-DD.csv`.
- PDF generado con **ReportLab** en memoria (`BytesIO`, sin archivos en el
  servidor): encabezado Flux, usuario/fecha/moneda, resumen, detalle con
  montos originales + convertidos, nota de conversión y pie con paginación.
- La exportación JSON/respaldo **sigue eliminada**.

---

## 7. Tests

Todos los tests viven en la carpeta raíz `tests/` (no existe `frontend/tests/`):

```
tests/
├── conftest.py           # URL de BD de pruebas desde TEST_DATABASE_URL
├── unit/                 # validadores, seguridad, motor de análisis (sin BD)
├── api/                  # pruebas de API extremo a extremo (requieren MySQL)
└── integration/          # marcador de pruebas de integración
```

```bat
:: Tests unitarios (no necesitan base de datos):
pytest -m "not integracion"

:: Tests completos contra MySQL (crea una BD temporal 'finanzas_test'):
::   1) define TEST_DATABASE_URL en el entorno, por ejemplo:
set TEST_DATABASE_URL=mysql+aiomysql://root:@127.0.0.1:3306/finanzas_test
::   2) ejecuta:
pytest
```

Las pruebas de API/integración se **saltan con un motivo explícito** si no hay
MySQL disponible (el proyecto no usa SQLite ni ninguna base embebida para test).

---

## 8. Calidad de código y seguridad

```bat
:: Lint + formato (Ruff)
ruff check app tests
ruff format --check app tests

:: Análisis estático de seguridad
bandit -c pyproject.toml -r app

:: Auditoría de dependencias vulnerables
pip-audit
```

Configuración en `pyproject.toml` (Ruff con reglas `E,W,F,I,B,UP,S,SIM,C4`).

---

## 9. Variables de entorno

Documentadas en `.env.example`. Resumen:

| Variable                      | Obligatoria | Descripción                                          |
|-------------------------------|-------------|------------------------------------------------------|
| `SECRET_KEY`                  | Sí          | Clave de firma JWT. Genera una propia (32+ hex).     |
| `DATABASE_URL`                | Sí          | `mysql+aiomysql://usuario:clave@host:3306/bd`.       |
| `GOOGLE_CLIENT_ID`            | No          | Client ID de Google (vacío = botón apagado).         |
| `ALGORITHM`                   | No          | Algoritmo JWT (por defecto `HS256`).                 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No          | Vida del access token (30).                          |
| `REFRESH_TOKEN_EXPIRE_DAYS`   | No          | Vida del refresh token (7).                          |
| `CORS_ORIGINS`                | No          | Orígenes permitidos separados por coma.              |
| `LOGIN_RATE_LIMIT`            | No          | P. ej. `5/minute`.                                   |
| `EXCHANGE_BASE_URL`           | No          | API Frankfurter v2 (`https://api.frankfurter.dev/v2`). |
| `EXCHANGE_TIMEOUT_S`          | No          | Timeout al proveedor en segundos (8).                |
| `DEBUG`                       | No          | `false` por defecto.                                 |

El archivo `.env` nunca se sube al repositorio (está en `.gitignore`) y las
credenciales de MySQL no aparecen hardcodeadas en el código.

---

## 10. Decisiones relevantes

- **MySQL 9.6 como único motor**: cualquier otra URL de BD hace fallar el
  arranque (fail-fast, sin fallback silencioso).
- **`DECIMAL(12,2)`** para importes monetarios (nunca `FLOAT`), con
  restricciones `CHECK` en la base de datos.
- **bcrypt directo** en lugar de `passlib` (librería sin mantenimiento e
  incompatible con bcrypt ≥ 4.1); el formato de hash es el mismo.
- **PyJWT** en lugar de `python-jose` (cuya dependencia transitiva `ecdsa`
  arrastra una vulnerabilidad conocida sin versión corregida).
- **Sin exportación de respaldos JSON** ni **cuentas de demostración**: se
  eliminaron por decisión de producto; el seed con credenciales embebidas
  también fue retirado.
- Migraciones **incrementales y no destructivas**: `0002` solo añade tablas
  nuevas (`metas`, `preferencias_usuario`); `0003` añade `movimientos.notas`;
  `0004` crea `exchange_rates` y añade `moneda` (default `COP`) a
  `movimientos` y `metas`, sin tocar el esquema existente.
- **Tasas Frankfurter v2** (solo backend, sin key): caché persistente con
  fallback a la última almacenada; 503 controlado sin datos; `Decimal`
  en todo cálculo (tasa `18,6`, importes a 2 decimales).
- **CSV con Pandas y PDF con ReportLab** (Fase 2, en memoria, sin JSON).
- **Frontend semántico y accesible** (Fase 3, objetivo WCAG 2.2 AA): cero
  `<span>` en plantillas y JS, landmarks y jerarquía de encabezados
  coherentes, iconos como `<svg>` directo, modales y drawer con `<dialog>`
  nativo, formularios con `fieldset/legend` y `label`, tablas con `caption`
  y `scope`, gráficos en `figure` y fechas/valores con `time`/`output`/`data`.
  Detalle en [`docs/arquitectura.md`](docs/arquitectura.md) §5.

## 11. Hoja de ruta (ideas, no implementadas)

- Presupuestos por categoría (con alertas al superar un umbral).
- Modo oscuro y PWA.
