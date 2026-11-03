# 📗 claude-blackbox: Manual de uso

<p align="center"><img src="../assets/banner.svg" alt="claude-blackbox" width="100%"></p>

> [English](MANUAL.en.md) · **Español** · [← Volver al README](../README.es.md)

Todo lo que necesitás para instalar, usar y confiar en la caja negra de Claude Code. La configuración lleva **2 minutos**.

**Contenido**

1. [Qué hace](#1-qué-hace)
2. [Requisitos](#2-requisitos)
3. [Instalación](#3-instalación)
4. [Verificar que está grabando](#4-verificar-que-está-grabando)
5. [Uso diario](#5-uso-diario)
6. [Después de un corte de luz o un cuelgue](#6-después-de-un-corte-de-luz-o-un-cuelgue)
7. [Checkpoints y decisiones](#7-checkpoints-y-decisiones)
8. [Historial y línea de tiempo](#8-historial-y-línea-de-tiempo)
9. [Privacidad y secretos](#9-privacidad-y-secretos)
10. [Referencia de archivos](#10-referencia-de-archivos)
11. [Desinstalar](#11-desinstalar)
12. [Referencia del CLI](#12-referencia-del-cli)
13. [Solución de problemas](#13-solución-de-problemas)
14. [Límites](#14-límites)

> Todas las capturas de terminal de este manual son **salidas reales** de un proyecto de prueba; solo se acortaron las rutas.

---

## 1. Qué hace

<p align="center"><img src="../assets/before-after.svg" alt="Sin y con claude-blackbox" width="100%"></p>

claude-blackbox tiene dos capas:

| Capa | Archivo | Para qué sirve |
|---|---|---|
| **Estado de recuperación** | `.blackbox/checkpoints/state.json` | Dónde quedó el trabajo: tarea, siguiente paso, archivos modificados y último comando |
| **Historial completo** | `.blackbox/history/` | Una línea de tiempo de solo agregado con prompts, comandos, archivos y decisiones |

Los **hooks** de Claude Code alimentan las dos capas solos. Cuando empieza una sesión nueva, el estado recuperado se carga en el contexto de Claude.

---

## 2. Requisitos

- **Claude Code** para la grabación automática, o **Claude.ai** si solo vas a usar checkpoints.
- **Python 3.8+**, que normalmente ya está instalado. En Windows sirve el de python.org o el de Microsoft Store.
- **Git** (opcional): si está, los checkpoints incluyen `git status`.

---

## 3. Instalación

### A) Plugin: todos tus proyectos (recomendado)

Dentro de Claude Code:

```
/plugin marketplace add jorgevb27/claude-blackbox
/plugin install claude-blackbox@claude-blackbox
```

Reiniciá Claude Code. Los hooks vienen incluidos en el plugin, así que no hay nada más que configurar.

### B) Un solo proyecto (copiando la carpeta)

macOS / Linux:

```bash
git clone --depth 1 https://github.com/jorgevb27/claude-blackbox /tmp/claude-blackbox
mkdir -p .claude/skills && cp -r /tmp/claude-blackbox/skills/claude-blackbox .claude/skills/
python3 .claude/skills/claude-blackbox/scripts/blackbox.py install-hooks
```

Windows (PowerShell):

```powershell
git clone --depth 1 https://github.com/jorgevb27/claude-blackbox $env:TEMP\claude-blackbox
New-Item -ItemType Directory -Force .claude\skills | Out-Null
Copy-Item -Recurse $env:TEMP\claude-blackbox\skills\claude-blackbox .claude\skills\
python .claude\skills\claude-blackbox\scripts\blackbox.py install-hooks
```

<p align="center"><img src="../assets/terminal-install.svg" alt="Salida de install-hooks" width="95%"></p>

`install-hooks`:
- **agrega** seis hooks a `.claude/settings.json` y conserva todo lo que ya tenías;
- antes guarda una copia en `.claude/settings.json.bak`;
- se puede **correr varias veces** sin que se duplique nada;
- suma `.blackbox/` a tu `.gitignore`.

### C) Todos tus proyectos, sin el plugin

```bash
python3 ruta/a/claude-blackbox/scripts/blackbox.py install-hooks --global
```

Esto escribe en `~/.claude/settings.json` usando la ruta completa del script, así que no muevas esa carpeta después.

### D) Claude.ai

Descargá `claude-blackbox-skill.zip` de la [última release](https://github.com/jorgevb27/claude-blackbox/releases/latest) →
**Configuración → Capacidades → Skills → Subir skill**. Claude guarda y lee checkpoints cuando se lo pedís; los hooks automáticos son exclusivos de Claude Code.

---

## 4. Verificar que está grabando

1. En Claude Code, ejecutá **`/hooks`**. Tienen que aparecer `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `PreCompact` y `Stop`.
2. Mandá cualquier prompt y fijate que en tu proyecto exista `.blackbox/history/events.jsonl` y que vaya creciendo.
3. Pedile a Claude: *"Mostrame el historial de blackbox."*

---

## 5. Uso diario

La mayor parte del tiempo **no hacés nada**. La caja negra graba sola, y la skill le indica a Claude que guarde un checkpoint después de cada paso importante.

Cosas útiles para decirle:

| Le decís | Qué pasa |
|---|---|
| *"Guardá un checkpoint: el siguiente paso es el webhook."* | `checkpoint --next "…"` |
| *"Decidimos usar Stripe Checkout, registralo."* | `checkpoint --decision "…"` → `decisions.md` |
| *"¿Dónde quedamos?"* | `resume` |
| *"¿Qué hicimos ayer?"* | `timeline` |
| *"¿Por qué elegimos Postgres?"* | Claude lee `decisions.md` |

> 💡 Buen hábito: antes de un paso riesgoso (una migración, un refactor grande), pedí un checkpoint con un `--next` claro.

---

## 6. Después de un corte de luz o un cuelgue

### Paso 1: volvé a abrir Claude Code

El hook `SessionStart` le pasa esto a Claude **automáticamente**:

<p align="center"><img src="../assets/terminal-sessionstart.svg" alt="Estado recuperado al iniciar" width="95%"></p>

### Paso 2: dejá que Claude verifique antes de seguir

Claude sabe que tiene que:
1. revisar si el **comando interrumpido** (acá, `alembic upgrade head`) llegó a ejecutarse;
2. mirar `git status` y los **archivos que quedaron a medio editar**;
3. seguir desde el **siguiente paso**.

### Paso 3 (opcional): ver el informe completo

```
python .claude/skills/claude-blackbox/scripts/blackbox.py resume
```

<details>
<summary>Ver la salida real de <code>resume</code></summary>
<p align="center"><img src="../assets/terminal-resume.svg" alt="Salida de resume" width="95%"></p>
</details>

> ⚠️ **Nunca asumas que un comando interrumpido terminó.** Para migraciones, revisá la tabla de migraciones de la base de datos; para instalaciones, el archivo de lock; para despliegues, el servidor de destino.

---

## 7. Checkpoints y decisiones

```bash
blackbox.py checkpoint --task "Checkout de Stripe en el carrito" \
                       --done "Cliente de Stripe + integración con el carrito, tests en verde" \
                       --next "Manejar el webhook payment_intent.succeeded" \
                       --decision "Usar Stripe Checkout (hosted) en vez de Elements"
```

| Opción | Se guarda como |
|---|---|
| `--task` | En qué estás trabajando (se mantiene hasta que lo cambies) |
| `--done` | Se agrega a la lista `completed` |
| `--next` | El siguiente paso, que es desde donde retoma Claude |
| `--decision` | Se agrega a `decisions` y a `history/decisions.md` |
| `--note` | Una nota libre en la línea de tiempo |

Cada checkpoint se escribe de forma **atómica** (archivo temporal + `fsync` + renombrar), así que un corte de luz nunca puede dejar `state.json` escrito a la mitad.
Además se guarda una copia en `snapshots/`, que conserva los últimos 50.

---

## 8. Historial y línea de tiempo

```
blackbox.py timeline       # todo, agrupado por día → sesión
blackbox.py history -n 30  # los últimos 30 eventos
```

<p align="center"><img src="../assets/terminal-timeline.svg" alt="Salida de timeline" width="95%"></p>

También podés abrir directamente estos archivos:

- `history/prompts.md`: tus prompts por sesión (con los secretos tapados)
- `history/commands.log`: cada comando que ejecutó Claude
- `history/decisions.md`: tu registro de decisiones

Cada evento guarda además el `transcript_path` de Claude Code, así que siempre podés encontrar la conversación completa en `~/.claude/projects/`.

---

## 9. Privacidad y secretos

- **Solo local.** Nunca hace llamadas de red.
- **La carpeta se ignora sola.** `.blackbox/` trae su propio `.gitignore` con `*`, así que nunca se sube a git, la hayas instalado como la hayas instalado.
- **Se tapa antes de escribir en el disco:**

| Tipo | Patrón de ejemplo |
|---|---|
| Claves de OpenAI / Anthropic | `sk-…` |
| Stripe | `sk_live_…`, `sk_test_…`, `rk_…`, `whsec_…` |
| GitHub | `ghp_…`, `github_pat_…` |
| AWS | `AKIA…` |
| Google | `AIza…` |
| Slack | `xoxb-…` |
| JWT | `eyJ….eyJ….…` |
| Encabezados y asignaciones | `Bearer …`, `password=…`, `token: …`, `api_key=…` |
| Claves privadas | `-----BEGIN … PRIVATE KEY-----` |
| Credenciales en URLs | `postgres://usuario:clave@host` |

- **Nunca se guarda:** ni el contenido de los archivos ni la salida de los comandos. Solo se registran las rutas de los archivos y los comandos.

> El enmascarado se basa en patrones conocidos. Igual conviene no pegar secretos en los prompts: usá variables de entorno o un gestor de secretos.

---

## 10. Referencia de archivos

```
.blackbox/
├── .gitignore                 "*", la carpeta se ignora sola
├── checkpoints/state.json     último estado recuperable (atómico)
├── snapshots/state-*.json     últimos 50 checkpoints
└── history/
    ├── events.jsonl           solo agregado, un evento JSON por línea
    ├── prompts.md             prompts por sesión (enmascarados)
    ├── commands.log           comandos ejecutados
    └── decisions.md           registro de decisiones
```

Campos de `state.json`: `task`, `next_step`, `completed`, `decisions`, `files_changed`, `last_prompt`, `last_command`, `session_id`, `git`, `updated_at`, `last_event_id`.

---

## 11. Desinstalar

| Cómo la instalaste | Pasos |
|---|---|
| Plugin | `/plugin uninstall claude-blackbox@claude-blackbox` |
| Copia en el proyecto | Restaurá `.claude/settings.json.bak`, o borrá las entradas de hooks cuyo comando contenga `blackbox`. Después borrá `.claude/skills/claude-blackbox/` |
| Global | Quitá las entradas de hooks con `blackbox` de `~/.claude/settings.json` |

Tu historial grabado queda en `.blackbox/` hasta que lo borres.

---

## 12. Referencia del CLI

El script es `skills/claude-blackbox/scripts/blackbox.py`. En Windows usá `python`, y en macOS o Linux, `python3`.

| Comando | Descripción |
|---|---|
| `resume` | Verifica y después muestra el estado, el comando interrumpido, git y los últimos 10 eventos |
| `status` | El último checkpoint |
| `verify` | Chequeo de integridad (tolera líneas cortadas) |
| `checkpoint [--task] [--next] [--done] [--decision] [--note]` | Guarda el progreso |
| `history [-n N]` | Los últimos N eventos (por defecto, 20) |
| `timeline` | Todos los eventos por día → sesión |
| `install-hooks [--global]` | Agrega los hooks a `settings.json` sin romper nada |
| `hook` | Uso interno: lo llama Claude Code con el JSON del evento por stdin |
| `--version` | Muestra la versión |

---

## 13. Solución de problemas

| Problema | Solución |
|---|---|
| Nunca aparece `.blackbox/` | Ejecutá `/hooks` para confirmar que los hooks están. Reiniciá Claude Code después de instalar |
| Los logs de los hooks dicen `Python 3.8+ not found` | Instalá Python y asegurate de que `python3`, `python` o `py` esté en el PATH |
| En Windows los hooks no corren | Claude Code ejecuta los hooks con Git Bash, así que instalá **Git for Windows** |
| `state.json is corrupt` | Copiá el archivo más reciente de `.blackbox/snapshots/` encima de `checkpoints/state.json` |
| `torn line(s) in events.jsonl` | Es normal después de un corte de luz, y se ignora solo |
| `settings.json is not valid JSON` | Primero arreglá el JSON. `install-hooks` no toca un archivo roto |
| Hooks duplicados | No debería pasar (`install-hooks` no duplica). Si los editaste a mano, restaurá desde el `.bak` |

---

## 14. Límites

- Lo que Claude estaba generando **solo en memoria** cuando se cortó la luz no se puede recuperar.
- Si la instalás con el proyecto ya empezado, la grabación arranca en ese momento, aunque las transcripciones anteriores siguen en `~/.claude/projects/`.
- El enmascarado detecta los formatos más comunes, no todos los secretos posibles.

---

<p align="center">¿Te salvó una sesión? <a href="https://github.com/jorgevb27/claude-blackbox">⭐ Dale una estrella al repo</a> · <a href="https://github.com/jorgevb27/claude-blackbox/issues">Reportá un problema</a></p>
