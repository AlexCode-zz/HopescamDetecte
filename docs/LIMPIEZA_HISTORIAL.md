# Limpieza del historial de Git — HopeScan

> **Estado:** completado el 2026-11-03. Historial reescrito con `git filter-repo` y force-push
> a `main` y `refactor/estructura-y-estabilidad`. Los objetos antiguos pueden seguir accesibles
> temporalmente por SHA viejo mientras GitHub haga garbage collection.

## Qué hay que purgar

| Ruta | Por qué | ¿Sigue en el árbol actual? |
|---|---|---|
| `patient_records.csv` | Datos personales reales, incluidos menores y DUI | No (se eliminó en `3455bf5`) |
| `.claude/**` | Symlinks locales hacia `.venv`, subidos por error | No (se eliminó en el commit de limpieza) |
| `.agents/**` | Symlinks locales hacia `.venv`, subidos por error | No (se eliminó en el commit de limpieza) |
| `.env` / `.streamlit/secrets.toml` | Secretos | Nunca estuvieron versionados, pero verifica |
| `.venv/**` | 1.5 GB de entorno local | Nunca estuvo versionado |

## Antes de empezar (obligatorio)

1. **Haz una copia de seguridad completa** del repositorio (incluido `.git`):
   ```bash
   cp -a HopescamDetecte HopescamDetecte.backup
   ```
2. **Avisa a cualquier colaborador** de que el historial se va a reescribir. Todos deberán
   volver a clonar el repositorio; un `pull` normal dejará el historial divergente.
3. **Rota cualquier secreto** que haya estado expuesto: contraseñas, API keys, tokens.
   Aunque el archivo no aparezca en el árbol, pudo estar en un commit.
4. **Cierra PRs abiertos** o prepárate para recrearlos: la reescritura cambia los SHA.
5. **No uses `git filter-branch`**; está obsoleto y es lento. Usa `git filter-repo` o BFG.

## Opción recomendada: `git filter-repo`

### Instalación

```bash
pip install git-filter-repo
# o, en Debian/Ubuntu: sudo apt install git-filter-repo
```

### 1. Purga de rutas

Desde una copia limpia y sin cambios pendientes:

```bash
cd HopescamDetecte
git status                 # debe estar limpio
git filter-repo \
  --path patient_records.csv \
  --path data/patient_records.csv \
  --path .claude \
  --path .agents \
  --invert-paths
```

`--invert-paths` significa "elimina estas rutas de todos los commits". Si además quieres
purgar el `.env` o los secretos (aunque no deberían estar), añade:

```bash
  --path .env \
  --path .streamlit/secrets.toml
```

### 2. Verificación local (antes de subir nada)

```bash
# No debe devolver nada:
git log --all --full-history --oneline -- patient_records.csv data/patient_records.csv .claude .agents

# Tampoco debe aparecer en ningún objeto:
git rev-list --objects --all | grep -iE 'patient_records|\.claude|\.agents'

# El repositorio debe seguir teniendo tus commits y archivos:
git log --oneline -10
git ls-files | head
```

### 3. Reemplazo del remoto

`git filter-repo` elimina el remoto `origin` por seguridad. Añádelo de nuevo y sube
**todas** las ramas y etiquetas reescritas:

```bash
git remote add origin https://github.com/AlexCode-zz/HopescamDetecte.git
git push --force --all origin
git push --force --tags origin
```

### 4. Limpieza del lado de GitHub

- Los objetos antiguos pueden seguir accesibles por URL directa/SHA durante un tiempo.
  Abre un ticket a GitHub Support pidiendo el *garbage collection* de los objetos
  inalcanzables, o espera al ciclo automático.
- Revisa **Settings → Branches** y las *releases* por si apuntan a commits antiguos.
- Si el repositorio tuvo forks, esos forks conservan el historial. Pide su eliminación
  o contacta a GitHub Support.

## Opción alternativa: BFG Repo-Cleaner

```bash
java -jar bfg.jar --delete-files patient_records.csv
java -jar bfg.jar --delete-folders .claude
java -jar bfg.jar --delete-folders .agents
git reflog expire --expire=now --all
git gc --prune=now --aggressive
git push --force --all
```

BFG solo borra archivos/carpetas; para cadenas de texto usa `--replace-text`.

## Después de la reescritura

1. Confirma que el CSV ya no se puede recuperar:
   ```bash
   git cat-file -p 5cd0be5:patient_records.csv   # debe fallar
   ```
2. Vuelve a clonar en otra carpeta y comprueba que `git log` no contiene los datos.
3. Rota los secretos y revisa los logs de acceso.
4. Documenta la fecha y el motivo en `docs/DECISIONES.md`.
5. Si los datos eran de pacientes reales, evalúa si corresponde una notificación
   según la normativa aplicable (en El Salvador, la Ley de Protección de Datos
   Personales y las obligaciones del centro de salud).

## Nota importante

La eliminación del historial **no garantiza** que los datos no hayan sido copiados,
indexados o descargados mientras el repositorio fue público. Trátalos como expuestos
y actúa en consecuencia (rotación, notificación, revisión de privacidad).
