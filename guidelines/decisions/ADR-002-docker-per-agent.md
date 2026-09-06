# ADR-002: Un Contenedor Docker por Rol de Agente

**Status:** Accepted  
**Date:** 2026-09-06

## Contexto
Los agentes tienen distintos perfiles: diferentes dependencias, variables de entorno,
posiblemente diferentes modelos LLM o incluso lenguajes en el futuro.

## Decisión
Cada rol de agente corre en su propio contenedor Docker:
- `analyst`, `architect`, `backend_dev`, `frontend_dev`, `qa` → un container cada uno
- Todos heredan de una imagen base común (`agents/base/Dockerfile.base`)
- El orquestador es un container separado
- Se comunican vía Redis Pub/Sub (mensajes asincrónicos)

## Alternativas consideradas
1. **Todos los agentes en un solo proceso** — simple pero limita escalabilidad y aislamiento.
2. **Un container por instancia de tarea** — más aislamiento pero overhead de startup alto.

## Consecuencias
- ✅ Cada agente escala independientemente
- ✅ Fallo de un agente no afecta a los demás
- ✅ Distintas dependencias/modelos por container sin conflictos
- ✅ Despliegue en K8s natural (un Deployment por rol)
- ⚠️ Overhead de Docker networking — mitigado con Redis en la misma red
