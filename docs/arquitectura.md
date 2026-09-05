# Arquitectura del proyecto

Este documento describe las decisiones estructurales de la aplicación: el
estilo de monolito modular, las capas de cada módulo, el modelo de datos, la
seguridad y la organización del frontend. Complementa al `README.md`, que
cubre la puesta en marcha.

---

## 1. Estilo arquitectónico: Monolito Modular

La aplicación se despliega como **un solo proceso** (FastAPI + Uvicorn) que
sirve la API y la SPA, pero su código interior está organizado en **módulos de
negocio** con fronteras explícitas. El objetivo es obtener las ventajas de
claridad y aislamiento de los microservicios sin pagar sus costes de
operación: una sola base de datos transaccional, un despliegue, cero
comunicación por red entre módulos.

Reglas que mantienen las fronteras:

1. Cada módulo expone una **fachada mínima** (`router.py` + `service.py`);
   ningún otro módulo importa sus `repository` ni sus `models` internos de
   acceso directo, salvo los modelos ORM compartidos por relaciones de
   integridad referencial.
2. Las dependencias entre módulos apuntan **hacia lo estable**: los módulos de
   dominio (`users`) no importan de los módulos de caso de uso
   (`dashboard`), sino al contrario.
3. `app/core/` es infraestructura transversal (configuración, base de datos,
   seguridad); `app/shared/` son utilidades de dominio compartidas
   (excepciones, catálogo de monedas, paginación). Ninguno de los dos
   conoce módulos de negocio concretos.
4. Si mañana un módulo necesitara extraerse a un servicio independiente, su
   paquete ya contiene todo lo necesario (modelos, reglas, schemas), por lo
   que la extracción sería un movimiento de carpetas, no una reescritura.

---

## 2. Módulos y responsabilidades

```
app/
├── core/
│   ├── config.py        # Settings (pydantic-settings), validación fail-fast de DATABASE_URL
│   ├── database.py      # engine async, fábrica de sesiones, utcnow, Base declarativa
│   ├── security.py      # hash bcrypt, JWT (access/refresh), hash SHA-256 de tokens
│   ├── deps.py          # DB (sesión por petición), UsuarioActual (JWT → User)
│   └── rate_limit.py    # limiter de slowapi (login anti fuerza bruta)
├── modules/
│   ├── auth/            # /auth: registro, login, refresh (rotación), logout[-todos]
│   │   ├── models.py    #   RefreshToken (hash en BD, revocable)
│   │   ├── schemas.py   #   TokenOut, RefreshRequest
│   │   ├── service.py   #   emisión/rotación/revocación de tokens
│   │   ├── repository.py#   consultas de refresh tokens
│   │   ├── dependencies.py # UsuarioActual (re-exportado desde core)
│   │   └── router.py
│   ├── users/           # /usuarios: perfil, contraseña, preferencias (moneda)
│   │   ├── models.py    #   User, Preferencia (tabla preferencias_usuario)
│   │   ├── schemas.py   #   UserCreate/Out/Update, PasswordChange, Preferencias*
│   │   ├── service.py   #   reglas de perfil y preferencias
│   │   ├── repository.py
│   │   └── router.py
│   ├── categories/      # /categorias: CRUD privado por usuario
│   ├── transactions/    # /movimientos: CRUD (moneda) + filtros + paginación
│   ├── goals/           # /metas: CRUD (moneda) + aportes + progreso calculado
│   ├── dashboard/       # /panel: agregaciones (?moneda=, SQL + Pandas)
│   ├── analysis/        # predicción (regresión lineal) y anomalías (sklearn)
│   ├── exchange_rates/  # /tasas: Frankfurter v2 + caché MySQL + convert()
│   └── exports/         # /exports: CSV (Pandas) y PDF (ReportLab) en memoria
└── shared/
    ├── exceptions.py    # NoEncontrado (404 anti-IDOR), Conflicto (409), EntradaInvalida (422)
    ├── moneda.py        # enum Moneda: COP | USD | EUR
    └── pagination.py    # utilidades de paginación
```

### Flujo de una petición (ejemplo: crear movimiento)

```
POST /api/v1/movimientos  (Authorization: Bearer …)
  → core/deps.UsuarioActual      valida el JWT y carga el User (id SIEMPRE del token)
  → transactions/router.crear    valida el cuerpo con MovimientoCreate (Pydantic)
  → transactions/service         comprueba que la categoría es propia y del tipo correcto
  → transactions/repository      INSERT parametrizado vía ORM (usuario_id del token)
  → 201 MovimientoOut
```

### Frontera del análisis

El módulo `analysis` tiene una restricción deliberada: **solo lee**. Recibe
sesiones de base de datos para consultar movimientos históricos, ejecuta sus
modelos (Pandas / scikit-learn) y devuelve estructuras de solo lectura
(`schemas.py`). Ninguna función de `analysis` ejecuta `INSERT`, `UPDATE` ni
`DELETE`; los módulos de escritura (`transactions`, `goals`) nunca importan de
`analysis`. Así, experimentar con modelos no puede corromper datos financieros.

---

## 3. Modelo de datos (MySQL 9.6)

Creado por las migraciones de Alembic (`0001`–`0004`: base, metas,
notas, tasas+monedas).

| Tabla                  | Propósito                                  | Puntos clave                                                             |
|------------------------|--------------------------------------------|--------------------------------------------------------------------------|
| `usuarios`             | cuentas de usuario                         | `username` y `email` únicos; hash bcrypt; `is_active`                     |
| `refresh_tokens`       | sesiones persistentes                      | guarda solo el **hash SHA-256**; `expira`, `revocado`; rotación de un uso |
| `categorias`           | categorías privadas por usuario            | UNIQUE (usuario, nombre, tipo); CHECK de tipo                             |
| `movimientos`          | ingresos y gastos                          | `monto DECIMAL(12,2)`; `moneda` CHECK COP/USD/EUR (default COP); CHECK de tipo, monto > 0 y método de pago; índice (usuario, fecha) |
| `metas`                | metas de ahorro                            | `moneda` CHECK COP/USD/EUR (default COP); `monto_objetivo > 0`, `monto_actual >= 0` (CHECK); FK CASCADE |
| `preferencias_usuario` | 1:1 con usuario                            | `moneda` CHECK IN ('COP','USD','EUR'); PK = `usuario_id`                  |
| `exchange_rates`       | caché de tasas Frankfurter v2              | `rate DECIMAL(18,6)`; UNIQUE (base, quote, fecha); global (sin usuario)   |

Decisiones de modelado:

- **Eliminación en cascada** de `usuarios` hacia todos sus datos (derecho al
  olvido): categorías, movimientos, metas, sesiones y preferencias.
- **RESTRICT** entre `movimientos.categoria_id` y `categorias.id`: no se puede
  borrar una categoría con movimientos; el servicio lo detecta antes y
  responde 409 con un mensaje accionable.
- El `tipo` del movimiento se desnormaliza desde su categoría (evita un JOIN
  en cada agregación del panel); la consistencia la garantiza el servicio
  (valida coincidencia en creación y edición).
- Importes siempre `DECIMAL(12,2)` mapeados a `Decimal` de Python; `FLOAT`
  está prohibido para dinero en este proyecto.
- Índices: únicos en `username`, `email`, `token_hash`; compuesto
  `(usuario_id, fecha)` en movimientos para las consultas por rango del panel.

---

## 4. Seguridad

Capas aplicadas (revisar `README.md §6.1` para el detalle funcional):

- **Autenticación**: bcrypt (12 rondas) + JWT HS256; access token corto y
  refresh rotativo revocable; comparación de contraseñas con tiempo constante
  frente a usuarios inexistentes (hash señuelo).
- **Autorización**: todo endpoint resuelve el `usuario_id` desde el JWT y las
  consultas lo filtran en la cláusula `WHERE` (backend, no frontend). Pedir un
  recurso ajeno devuelve 404 sin revelar existencia.
- **Inyección SQL**: todas las consultas pasan por el ORM/SQLAlchemy con
  parámetros enlazados; no hay SQL concatenado.
- **XSS**: la SPA nunca inyecta HTML de usuario; los datos se renderizan con
  `textContent`/`createElement` (ver `app/static/js/utils/dom.js`). Los únicos
  `innerHTML` usados contienen constantes SVG internas.
- **CSRF**: la autenticación es por cabecera `Authorization: Bearer` (no
  cookies), por lo que el vector clásico de CSRF no aplica; además CORS está
  restringido a los orígenes propios.
- **Mass assignment**: los schemas Pydantic declaran campos explícitos; los
  servicios aplican `model_dump(exclude_unset=True)` sobre campos conocidos.
- **Fuerza bruta**: rate limiting por IP en el login (`slowapi`).
- **Información**: errores 500 genéricos al cliente (el detalle queda en el
  log del servidor) y mensajes de login genéricos.
- **Credenciales**: solo variables de entorno; `SECRET_KEY` obligatoria con
  avisos si es débil o de ejemplo.

---

## 5. Frontend (SPA vanilla)

- **Un solo HTML** (`app/templates/index.html`) con `<template>` por vista;
  el router de hash clona la plantilla correspondiente dentro del shell.
- **Módulos ES** (`<script type="module">`), sin bundler ni frameworks:
  - `core/api.js`: cliente HTTP con renovación de tokens *single-flight*
    (una sola petición de refresh aunque haya peticiones paralelas).
  - `core/router.js`: guardias de sesión, título, limpieza de vistas
    (destruye gráficos Chart.js al cambiar de vista).
  - `core/sesion.js`: tokens + usuario cacheado (incluye la moneda) en
    `localStorage`; eventos `flux:*` para desacoplar módulos.
  - `services/endpoints.js`: **único** punto donde se construyen URLs de la
    API (evita lógica de API repetida en las vistas).
   - `utils/`: DOM seguro, formato de moneda/fechas, validación de formularios,
     modales (`<dialog>` nativo, ver Fase 3) y toasts, estados de
     carga/vacío/error.
  - `modules/<vista>/`: un módulo por vista (auth, panel, movimientos,
    categorías, metas, análisis, perfil) con controlador que devuelve su
    función de limpieza.
- **CSS modular**: `tokens.css` (design system del prototipo: paleta navy/azul
  Flux, gradiente *flow thread*, sombras *navy mist*, radios y tipografías),
  `reset.css`, `base.css`, `layout.css`, `components/` (botones, formularios,
  tarjetas, tablas, badges, modales, drawer, toasts), `views/` (estilos
  específicos por vista) y `responsive.css`. Sin Tailwind ni estilos inline
  salvo colores dinámicos de categoría (datos, no presentación).
- **Chart.js** se sirve desde `static/vendor/` (funciona sin internet).
- Logotipo propio en `static/img/` (`logo-icon.png` transparente en sidebar y
  login; `favicon.ico` como ícono del navegador).

### HTML semántico y accesibilidad (Fase 3, objetivo WCAG 2.2 AA)

El frontend elimina la "divitis" sin caer en "sectionitis": cada elemento usa
la etiqueta que representa su significado (primero HTML nativo, ARIA después).

- **Cero `<span>`** en plantillas y JS: el texto importante usa `<strong>`,
  el énfasis/estados `<em>`, lo secundario `<small>`, las fechas `<time
  datetime>`, los resultados `<output>`, los valores `<data value>` y los
  decorativos `<i aria-hidden>`. Los `<div>` restantes son solo agrupadores
  técnicos de layout (documentados en la auditoría de la fase).
- **Landmarks y jerarquía**: `<aside>` (sidebar) + `<nav>` (secciones) +
  `<header class="topbar">` con el único `<h1>` por vista; cada plantilla
  aporta su `<h2>` y las subsecciones `<h3>` (sin saltos de nivel).
- **Iconos sin wrapper**: `pintarIconos()` (`utils/dom.js`) reemplaza
  cualquier `[data-icono]` directamente por el `<svg>` (hereda la clase para
  no romper el layout); los SVG dinámicos llevan `aria-hidden="true"`.
- **Navegación vs acción**: el chip de usuario y la tarjeta de predicción son
  `<a href>` nativos; el orden de columnas es `<button>` dentro de
  `th scope="col"`; las notificaciones son `<ul><li><button>`; la paginación
  es `<nav><ul><li><button aria-current>`.
- **Formularios**: `<form>` con `<fieldset><legend>` para grupos (tipo de
  movimiento/categoría, filtros, paleta de color); todo control tiene
  `<label for>` con `id` coincidente (sin `aria-label` redundantes).
- **Datos**: tablas reales con `<caption>` y `th scope="col/row"`; listas de
  tarjetas como `<ul><li><article>`; gráficos Chart.js en
  `<figure><figcaption>` con `canvas role="img"` y alternativa textual;
  progreso de metas con `<progress>` + `<output>`.
- **Diálogos nativos**: `utils/modal.js` (modales) y el drawer de movimientos
  usan `<dialog>` (`showModal`, evento `cancel`, clic en backdrop, retorno de
  foco, `aria-labelledby` con IDs únicos) en lugar de `div role="dialog"`.
- **Presentación separada**: el CSS nunca depende del tag (solo de clases),
  por lo que la semántica puede evolucionar sin romper el diseño; el JS
  usa IDs/`data-*` estables en vez de la estructura visual.

### Formato de moneda

`utils/formato.js` construye `Intl.NumberFormat` por moneda con caché. La
moneda vigente viaja en el usuario cacheado (campo `moneda`, desnormalizado
por `/usuarios/me` desde `preferencias_usuario`). Al cambiar la moneda en
Perfil se persiste vía `PATCH /usuarios/me/preferencias`, se actualiza el
usuario cacheado y se re-renderiza la vista.

### Tasas de cambio y conversión (Fase 2)

```
Frontend → FastAPI → ExchangeRateService → {Repository (MySQL), Client (Frankfurter v2)}
dashboard/goals/analysis/exports → solo ExchangeRateService.convert()
```

- `exchange_rates/` (capas `constants|exceptions|models|repository|client|
  service|router|schemas`): el **único** punto que habla con Frankfurter v2
  (`GET /v2/rate/{BASE}/{QUOTE}[?date=]`, sin key, timeout 8 s). El frontend
  nunca conoce esa URL.
- Caché persistente `exchange_rates` con UNIQUE (base, quote, fecha):
  exacta → proveedor (persiste) → última ≤ fecha (fallback) → 503
  `TasaNoDisponible` (nunca se inventa una tasa).
- La tasa de referencia es la **fecha del movimiento** (histórica
  determinística, reproducible sin snapshots por fila). Cálculos en
  `Decimal` (tasa 18,6; importes a 2 decimales `ROUND_HALF_UP`); los
  originales nunca se modifican.
- `dashboard`/`analysis` aceptan `?moneda=` (default: preferencia) y
  convierten antes de agregar; `transactions`/`goals` persisten y devuelven
  `moneda`; `exports` convierte por fila para CSV/PDF.

### Exportación CSV/PDF (Fase 2)

- `exports/` (`router|schemas|service|csv_generator|pdf_generator|
  exceptions`): `GET /api/v1/exports/transactions.csv|.pdf` con los filtros
  del listado + `visualizacion`. Usuario siempre del JWT (anti-IDOR).
- CSV con **Pandas** (UTF-8 con BOM); PDF con **ReportLab** en `BytesIO`
  (encabezado, resumen, detalle original+convertido, nota de conversión,
  pie paginado). `Content-Disposition` con nombre seguro generado en el
  backend (`flux_movimientos_AAAA-MM-DD.*`); nada queda en disco.
- Frontend: tarjeta "Exportar mis datos" en Perfil (`Descargar CSV/PDF`
  con estados normal/loading/disabled/error/éxito), descarga vía
  `core/api.js:descargarArchivo` (Blob + renovación de sesión); sin JSON
  (sigue eliminado).

---

## 6. Dependencias y compatibilidad

Versiones fijadas en `requirements.txt` (estables verificadas en PyPI al
momento de la actualización; no se usan pre-releases):

| Paquete            | Versión  | Nota                                                        |
|--------------------|----------|-------------------------------------------------------------|
| fastapi            | 0.141.1  |                                                             |
| uvicorn[standard]  | 0.52.4   |                                                             |
| python-multipart   | 0.0.32   | formularios OAuth2 del login                                |
| email-validator    | 2.3.0    | validación de correos (EmailStr)                            |
| pydantic           | 2.13.5   |                                                             |
| pydantic-settings  | 2.15.0   |                                                             |
| SQLAlchemy         | 2.0.52   | modo async con `aiomysql`                                   |
| alembic            | 1.19.1   |                                                             |
| aiomysql           | 0.3.2    | driver MySQL asíncrono                                      |
| PyJWT              | 2.13.0   | sustituye a python-jose (dependencia `ecdsa` vulnerable)    |
| cryptography       | 50.0.1   | auth `caching_sha2_password` de MySQL 8+/9.x                |
| bcrypt             | 5.0.0    | uso directo; `passlib` retirado (incompatible e inactivo)   |
| slowapi            | 0.1.10   |                                                             |
| pandas             | 3.0.5    | `analysis`, agregaciones del `dashboard` y CSV de `exports` |
| scikit-learn       | 1.9.0    | solo módulo `analysis`                                      |
| httpx              | 0.28.1   | solo `exchange_rates/client` (Frankfurter v2)               |
| reportlab          | 5.0.1    | solo `exports/pdf_generator` (trae `pillow`)                |

Desarrollo (`requirements-dev.txt`): `pytest`, `pytest-asyncio`, `httpx`,
`ruff`, `bandit`, `pip-audit`.

---

## 7. Estrategia de pruebas

- **Unitarias** (`tests/unit/`): validadores de schemas, funciones de
  seguridad (hash/tokens), motor de análisis con datos sintéticos y servicio
  de tasas con dobles (sin red ni BD). No requieren base de datos y corren
  en cualquier entorno.
- **API / integración** (`tests/api/`): ejercitan los endpoints extremo a
  extremo contra una base MySQL temporal (`TEST_DATABASE_URL`, base
  `finanzas_test`); cubren registro/login, autorización cruzada entre dos
  usuarios (IDOR), CRUD de categorías/movimientos/metas, preferencias de
  moneda, panel, tasas (proveedor mockeado, caché real) y exports CSV/PDF
  (contenido, filtros, vacíos, 401/IDOR). Se saltan con motivo explícito
  si no hay MySQL.
- **Convención**: todos los tests bajo `tests/` (no se creó `frontend/tests/`
  ni `docs/decisions/`).

---

## 8. Extensiones futuras (diseñadas para caber)

- **Presupuestos**: un módulo `budgets/` con la misma plantilla de capas;
  sumaría una tabla `presupuestos (usuario_id, categoria_id, mes, limite)`
  y consultas de consumo sobre `movimientos`.
- **Extracción a servicio**: `analysis` es el candidato natural (es de solo
  lectura y stateless); su paquete ya encapsula modelos y schemas.
- **Multi-moneda real**: implementada en Fase 2 (`exchange_rates` +
  columnas `moneda`); la tasa se resuelve por fecha contra el caché, sin
  snapshots por fila.
