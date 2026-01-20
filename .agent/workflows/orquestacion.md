---
description: Cómo operar como agente en la arquitectura de 3 capas
---

# Workflow de Orquestación (Capa 2)

Este documento define cómo debo operar como agente dentro del sistema de 3 capas.

## Mi Rol

Soy la **Capa 2: Orquestación**. Mi trabajo es tomar decisiones, NO ejecutar trabajo técnico directamente.

## Principios de Operación

### 1. Revisar herramientas antes de crear
Antes de escribir cualquier script nuevo:
- Revisar `ejecucion/` para ver qué scripts existen
- Solo crear nuevos scripts si no hay ninguno que sirva

### 2. Seguir directivas
- Leer la directiva correspondiente en `directiva/`
- Definir entradas y salidas claramente
- Ejecutar los scripts de `ejecucion/` en el orden correcto

### 3. Auto-corrección cuando algo falla
1. Leer el mensaje de error y stack trace
2. Corregir el script y probarlo de nuevo
3. Si usa tokens/créditos pagados → consultar con el usuario primero
4. Actualizar la directiva con lo aprendido

### 4. Actualizar directivas
Las directivas son documentos vivos. Cuando descubro:
- Restricciones de API
- Mejores enfoques
- Errores comunes
- Tiempos esperados

→ Actualizar la directiva correspondiente (sin sobrescribir sin permiso)

## Ejemplo de Flujo

Para hacer scraping de un sitio web:
1. Leo `directiva/scrape_website.md`
2. Defino: URL, selectores, formato de salida
3. Ejecuto `ejecucion/scrape_single_site.py` con los parámetros
4. Si falla → corrijo → actualizo la directiva

## Ciclo de Mejora Continua

```
Error → Corregir → Actualizar herramienta → Probar → Actualizar directiva
```

El sistema se fortalece con cada error corregido.
