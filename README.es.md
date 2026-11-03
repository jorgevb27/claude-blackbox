<p align="center">
  <img src="assets/banner.svg" alt="claude-blackbox — la caja negra para Claude Code" width="100%">
</p>

<p align="center">
  <a href="https://github.com/jorgevb27/claude-blackbox/stargazers"><img src="https://img.shields.io/github/stars/jorgevb27/claude-blackbox?style=for-the-badge&color=ff8a3d&labelColor=161b22" alt="Estrellas"></a>
  <a href="https://github.com/jorgevb27/claude-blackbox/releases/latest"><img src="https://img.shields.io/github/v/release/jorgevb27/claude-blackbox?style=for-the-badge&color=ff8a3d&labelColor=161b22" alt="Release"></a>
  <a href="https://github.com/jorgevb27/claude-blackbox/actions/workflows/test.yml"><img src="https://img.shields.io/github/actions/workflow/status/jorgevb27/claude-blackbox/test.yml?style=for-the-badge&label=tests&labelColor=161b22" alt="Tests"></a>
  <img src="https://img.shields.io/badge/dependencias-0-3fb950?style=for-the-badge&labelColor=161b22" alt="Cero dependencias">
  <a href="LICENSE"><img src="https://img.shields.io/badge/licencia-MIT-8b949e?style=for-the-badge&labelColor=161b22" alt="MIT"></a>
</p>

<p align="center">
  <a href="README.md">English</a> · <b>Español</b>
  &nbsp;|&nbsp;
  📗 <a href="docs/MANUAL.es.md"><b>Manual de uso</b></a> · 📘 <a href="docs/MANUAL.en.md">English manual</a>
</p>

<p align="center">
  <a href="#-instalación">Instalación</a> ·
  <a href="#-cómo-se-ve">Cómo se ve</a> ·
  <a href="#-cómo-funciona">Cómo funciona</a> ·
  <a href="#-privacidad">Privacidad</a> ·
  <a href="#-preguntas-frecuentes">FAQ</a>
</p>

---

**Se corta la luz. La PC se reinicia. Se cierra la terminal. Se compacta el contexto.**
Y Claude no tiene idea de qué estaba haciendo hace cinco minutos. Peor todavía: puede asumir que esa migración que quedó a la mitad terminó bien.

**claude-blackbox** graba todo lo que Claude hace en tu proyecto (prompts, comandos, archivos editados y decisiones) en una línea de tiempo local que aguanta cortes.
Cuando arranca la sesión siguiente, Claude **ya sabe dónde quedó**, cuál es el próximo paso y qué comando nunca terminó.

<p align="center"><img src="assets/before-after.svg" alt="Sin y con claude-blackbox después de un corte de luz" width="100%"></p>

<table>
<tr>
<td align="center" width="25%"><h3>🛬</h3><b>Retoma solo</b><br><sub>el estado se carga en cada sesión nueva</sub></td>
<td align="center" width="25%"><h3>⚠️</h3><b>Comandos interrumpidos</b><br><sub>detecta lo que "empezó y no terminó"</sub></td>
<td align="center" width="25%"><h3>🔐</h3><b>Tapa secretos</b><br><sub>claves y tokens enmascarados antes de guardar</sub></td>
<td align="center" width="25%"><h3>🪶</h3><b>Cero dependencias</b><br><sub>un solo archivo Python · Win/macOS/Linux</sub></td>
</tr>
</table>

## 🚀 Instalación

**Claude Code: plugin (recomendado, 2 comandos)**

```
/plugin marketplace add jorgevb27/claude-blackbox
/plugin install claude-blackbox@claude-blackbox
```

Reiniciá Claude Code y la caja negra ya está grabando.

<details>
<summary><b>O copiala a un solo proyecto (macOS / Linux / Windows)</b></summary>

```bash
git clone --depth 1 https://github.com/jorgevb27/claude-blackbox /tmp/claude-blackbox
mkdir -p .claude/skills && cp -r /tmp/claude-blackbox/skills/claude-blackbox .claude/skills/
python3 .claude/skills/claude-blackbox/scripts/blackbox.py install-hooks
```

```powershell
git clone --depth 1 https://github.com/jorgevb27/claude-blackbox $env:TEMP\claude-blackbox
New-Item -ItemType Directory -Force .claude\skills | Out-Null
Copy-Item -Recurse $env:TEMP\claude-blackbox\skills\claude-blackbox .claude\skills\
python .claude\skills\claude-blackbox\scripts\blackbox.py install-hooks
```

`install-hooks` **agrega** los hooks a tu `.claude/settings.json` existente: nunca lo pisa y antes guarda una copia `.bak`.
</details>

**Claude.ai:** descargá [`claude-blackbox-skill.zip`](https://github.com/jorgevb27/claude-blackbox/releases/latest) → *Configuración → Capacidades → Skills → Subir skill*. En Claude.ai tenés el flujo de checkpoints; la grabación automática necesita los hooks de Claude Code.

👉 Todas las opciones, paso a paso: **[Manual de uso](docs/MANUAL.es.md)**

## 🎬 Cómo se ve

<sub>Todas las capturas son salidas reales de un proyecto de prueba; solo se acortaron las rutas.</sub>

**1. La instalás una vez y Claude guarda checkpoints mientras trabaja**

<p align="center"><img src="assets/terminal-install.svg" alt="install-hooks y un checkpoint" width="90%"></p>

**2. ⚡ Se corta la luz. Al volver a abrir, Claude recibe esto automáticamente, sin que tengas que ejecutar nada**

<p align="center"><img src="assets/terminal-sessionstart.svg" alt="Estado recuperado al iniciar la sesión" width="90%"></p>

**3. La historia completa, cuando quieras**

<p align="center"><img src="assets/terminal-timeline.svg" alt="Línea de tiempo por día y sesión" width="90%"></p>

<details>
<summary><b>Ver el informe completo de <code>resume</code></b></summary>
<p align="center"><img src="assets/terminal-resume.svg" alt="Informe completo de resume" width="90%"></p>
</details>

## 🧠 Cómo funciona

<p align="center"><img src="assets/how-it-works.svg" alt="Hooks → grabador → archivos de .blackbox → de vuelta a la siguiente sesión" width="100%"></p>

| Hook | Qué graba |
|---|---|
| `SessionStart` | el inicio de la sesión, e **inyecta el estado recuperado en Claude** |
| `UserPromptSubmit` | tu prompt (con los secretos tapados) |
| `PreToolUse` (Bash) | "el comando empezó", que es la clave para detectar interrupciones |
| `PostToolUse` | "el comando terminó", y cada archivo que Claude escribe o edita |
| `PreCompact` · `Stop` | checkpoint + `git status` + snapshot |

Cada escritura es **atómica y con `fsync`**, se guardan los últimos 50 snapshots, y si un corte de luz deja una línea a la mitad, simplemente se saltea.

## 🕹️ Uso

La mayor parte del tiempo **no hacés nada**: graba sola, y Claude guarda checkpoints después de cada paso. También podés pedírselo directamente:

> *"¿Dónde quedamos?"* · *"Guardá un checkpoint"* · *"Mostrame la línea de tiempo del proyecto"* · *"¿Qué decidimos sobre los pagos?"*

| Comando | Qué hace |
|---|---|
| `blackbox.py resume` | Todo lo que necesitás después de un corte: estado, comando interrumpido, git y últimos eventos |
| `blackbox.py checkpoint --task "…" --done "…" --next "…"` | Guarda el progreso |
| `blackbox.py checkpoint --decision "…"` | Registra una decisión en `decisions.md` |
| `blackbox.py timeline` · `history -n 30` | La historia completa · los últimos eventos |
| `blackbox.py status` · `verify` | Último checkpoint · chequeo de integridad |
| `blackbox.py install-hooks [--global]` | Agrega los hooks a este proyecto, o a todos |

## 🔐 Privacidad

- **100 % local.** Son archivos de texto dentro de `.blackbox/`, en tu proyecto, y nunca se envía nada a ningún lado.
- **Nunca se sube a git.** `.blackbox/` trae su propio `.gitignore`, en cualquier forma de instalación.
- **Se tapa antes de escribir:** `sk-…` de OpenAI/Anthropic, `sk_live_…`/`whsec_…` de Stripe, `ghp_…` de GitHub, `AKIA…` de AWS, `AIza…` de Google, `xox…` de Slack, JWTs, tokens `Bearer`, valores de `password=`/`token=`/`api_key=`, claves privadas y credenciales dentro de URLs.
- **No se guarda:** ni el contenido de los archivos ni la salida de los comandos. Solo se registran *rutas* de archivos y *comandos*.

## ❓ Preguntas frecuentes

<details><summary><b>¿Hace más lento a Claude?</b></summary>
No. Cada hook tarda unos milisegundos de escritura local, tiene un timeout de 10 segundos y nunca rompe tu sesión, aunque no tengas Python instalado.
</details>

<details><summary><b>¿Recupera lo que Claude estaba escribiendo cuando se cortó la luz?</b></summary>
No, y nada puede hacerlo: lo que estaba solo en memoria se pierde. Lo que tenés es el último checkpoint, el comando interrumpido, los archivos modificados y la ruta de la transcripción. Normalmente con eso alcanza para seguir.
</details>

<details><summary><b>La instalé con el proyecto ya empezado. ¿Tengo el historial anterior?</b></summary>
La grabación empieza al instalarla. Las transcripciones anteriores de Claude Code siguen en <code>~/.claude/projects/</code>, y Claude puede leerlas si se lo pedís.
</details>

<details><summary><b>¿Cómo la desinstalo?</b></summary>
Plugin: <code>/plugin uninstall claude-blackbox@claude-blackbox</code>. Si la copiaste: restaurá <code>.claude/settings.json.bak</code> o borrá las entradas de hooks que contengan <code>blackbox</code>. Después borrá <code>.claude/skills/claude-blackbox/</code> y, si querés, <code>.blackbox/</code>. Más detalle en el <a href="docs/MANUAL.es.md#11-desinstalar">manual</a>.
</details>

## 🤝 Contribuir

Issues y PRs bienvenidos. Algunas ideas: un visor HTML de la línea de tiempo, resúmenes diarios, un indexador de transcripciones, un panel para VS Code.
Los tests se corren con `python -m unittest discover -s tests`, y la CI los ejecuta en Windows, macOS y Linux.
Si alguna vez te salvó una sesión, **una ⭐ ayuda a que otros la encuentren.**

**Más del mismo autor:** 🔍 [system-auditor-ai](https://github.com/jorgevb27/system-auditor-ai) · 🛡️ [claude-security-auditor-pro](https://github.com/jorgevb27/claude-security-auditor-pro)

## 📄 Licencia

[MIT](LICENSE) © jorgevb27
