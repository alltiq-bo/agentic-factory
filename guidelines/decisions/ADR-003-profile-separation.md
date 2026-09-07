# ADR-003: Profile como artefacto externo separado del Role

**Status:** Accepted
**Date:** 2026-09-06

## Contexto
El primer diseño tenía el `system_prompt` del agente hardcodeado en la clase Python.
Para crear un `backend_developer` de Java en lugar de .NET había que crear una nueva clase o parchear el string. Eso hace que agregar equipos requiera modificar código.

## Decisión
El conocimiento especializado vive en `profiles/<name>.md` — archivos Markdown externos.
El `ContextBuilder` los carga e inyecta al system prompt del agente junto con las instrucciones del rol. El agente base es siempre el mismo; lo que cambia entre equipos es el profile.

## Consecuencias
- ✅ Nuevo equipo = nuevos archivos `.md`, cero código
- ✅ Actualizar el conocimiento de un profile no requiere redeploy
- ✅ El profile puede mejorarse con sugerencias de QA (ciclo de retroalimentación)
- ⚠️ El contenido del profile no es validado estructuralmente — es texto libre
