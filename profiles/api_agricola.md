# Profile: API Agrícola — Backend Developer

## Descripción del proyecto
API REST para gestión agropecuaria. Maneja campañas agrícolas, propiedades, egresos,
movimientos de caja, planillas de pago de trabajadores y módulos contables.
Proyecto en producción en `https://api.agricola2g.net`.

---

## Stack tecnológico
- **Runtime:** .NET 9
- **Framework:** ASP.NET Core 9 — Controllers (no Minimal APIs)
- **ORM:** Entity Framework Core con SQL Server (`UseSqlServer`)
- **Base de datos:** SQL Server
- **Autenticación:** JWT Bearer (`Microsoft.AspNetCore.Authentication.JwtBearer`)
- **Caché:** Redis via `Microsoft.Extensions.Caching.StackExchangeRedis`
- **Logging:** log4net (NO usar `ILogger<T>` — el proyecto usa log4net en todos los servicios)
- **Documentación:** Swagger con Swashbuckle + comentarios XML

---

## Arquitectura — Clean Architecture en 5 capas

```
ApiAgricola/          → Capa de presentación: Controllers, Filters, DTOs de entrada, Program.cs
Application/          → Casos de uso: Services, Interfaces de servicio, DTOs de aplicación, Enums
Domain/               → Núcleo: Entities, Interfaces de repositorio, Enums de dominio, Specifications
Infrastructure/       → Implementaciones: EF Core, Repositories, Redis, Scripts SQL
Core/                 → Cross-cutting: ConfigApp, Helpers comunes
```

**Regla estricta:** las dependencias solo van hacia adentro.
`ApiAgricola` → `Application` → `Domain` ← `Infrastructure`
`Infrastructure` NO puede ser referenciada desde `Application` directamente.

---

## Patrón de Controllers

Todo controller hereda de `BaseApiController` (público) o `BaseAuthApiController` (requiere JWT):

```csharp
[Route("api/v1/transactions/[controller]")]
public class EgresosController : BaseAuthApiController
{
    private static readonly ILog __log4Net = LogManager.GetLogger(typeof(EgresosController));
    private readonly IEgresoService _egresoService;

    public EgresosController(IEgresoService egresoService)
    {
        _egresoService = egresoService;
    }

    /// <summary>Buscar egresos con filtros</summary>
    [LogAcceso("Egresos", "SearchEgreso")]
    [ProducesResponseType(typeof(ResponseResultDto), (int)BusinessCodeEnum.Ok)]
    [HttpPost("search")]
    public async Task<IActionResult> Search([FromBody] EgresoFilterDto filters)
    {
        try
        {
            filters.IdUser = int.Parse(this.getIdUserSession());
            var result = await _egresoService.SearchEgreso(filters);
            return ResponseApp.From(result);
        }
        catch (Exception ex)
        {
            __log4Net.Fatal(ex.Message);
            return ResponseApp.From(ResponseApp.Error("Error interno al realizar búsqueda.", ex.Message));
        }
    }
}
```

**Convenciones de controllers:**
- Rutas en minúsculas: `api/v1/transactions/egresos`
- Siempre retornar `IActionResult` via `ResponseApp.From()`
- Siempre capturar excepciones con try/catch y loguear con `__log4Net.Fatal(ex.Message)`
- Comentarios XML `/// <summary>` en todos los endpoints (alimentan Swagger)
- Atributo `[LogAcceso("Módulo", "Acción")]` en operaciones que deben auditarse

---

## Patrón de respuesta — ResponseApp + ResponseMessageDto

**NUNCA** retornar `Ok(data)` o `BadRequest(data)` directamente. Siempre usar `ResponseApp`:

```csharp
// Factory de respuestas en ApiAgricola/Factories/ReponseApp.cs
ResponseApp.From(ResponseMessageDto response)  // mapea al HTTP status correcto
ResponseApp.Ok("mensaje", data)                // 200
ResponseApp.Error("mensaje", technicalMsg)     // 500
ResponseApp.NotFound("mensaje")               // 404
ResponseApp.BadRequest("mensaje")             // 400
```

**ResponseMessageDto:**
```csharp
public class ResponseMessageDto
{
    public bool Error { get; set; }
    public string? Status { get; set; }
    public BusinessCodeEnum Code { get; set; }
    public object? Data { get; set; }
    public string? Message { get; set; }
    public string? TechnicalMessage { get; set; }
}
```

**BusinessCodeEnum — códigos personalizados del proyecto:**
```csharp
Ok = 200, BadRequest = 400, Unauthorized = 401, NotFound = 404, Error = 500
// Personalizados:
DatosVacios = 1000, ParametroNoValido = 1001, PorValidacion = 1003
ExcepcionSQL = 1501, ExcepcionSinError = 1502
CaptchaRequerido = 1100, CaptchaInvalido = 1101, CuentaBloqueada = 1102
```

---

## Patrón de Services — BaseService

Los servicios heredan de `BaseService` y usan sus helpers de respuesta:

```csharp
public class EgresoService : BaseService, IEgresoService
{
    private static readonly ILog __log4Net = LogManager.GetLogger(typeof(EgresoService));

    public async Task<ResponseMessageDto> CreateEgreso(EgresoCreateDto dto, int idUsuario)
    {
        try
        {
            // lógica
            return ResponseSuccess("Egreso registrado.", result);
        }
        catch (Exception ex)
        {
            __log4Net.Fatal(ex);
            return ResponseError("Error al registrar egreso.", ex.Message);
        }
    }
}
```

**Reglas de servicios:**
- Siempre retornar `ResponseMessageDto` (nunca lanzar excepciones al controller)
- Log con `__log4Net.Fatal(ex)` en el catch — NO `Console.WriteLine`
- La lógica de negocio vive aquí, NO en controllers ni repositories

---

## Patrón de Repositories — BaseRepository + Specification

```csharp
// Domain/Interfaces/IBaseRepository.cs — contrato
public interface IBaseRepository<T> { ... }

// Infrastructure/Persistence/Base/BaseRepository.cs — implementación base con EF Core
public class BaseRepository<T> : IBaseRepository<T> where T : class
{
    protected readonly AppDbContext _context;
    // ApplySpecification(spec) aplica filtros, includes, ordenamiento
}

// Specification para queries complejas:
public class EgresoFilterSpecification : BaseSpecification<Egreso>
{
    public EgresoFilterSpecification(EgresoFilterDto filters) { ... }
}
```

**Reglas de repositories:**
- Usar `AsNoTracking()` en queries de solo lectura
- Proyecciones SQL-traducibles en `Select()` — NO mapeos en memoria dentro del query
- Transacciones explícitas para operaciones multi-tabla
- El mapeo post-fetch (ej. enum → string) se hace DESPUÉS del `ToListAsync()`

---

## Entidades de dominio principales

| Entidad | Descripción |
|---------|-------------|
| `Campanium` | Campaña agrícola (año/período de trabajo) |
| `Propiedade` | Propiedad/fundo agrícola |
| `Egreso` | Gasto/pago registrado (con comprobante adjunto) |
| `Ingreso` | Ingreso de caja |
| `Movimiento` | Movimiento de caja (conciliación) |
| `Trabajadore` | Trabajador agrícola |
| `PlanillaPago` | Planilla de pago de trabajadores |
| `Subcuenta` | Subcuenta contable (plan de cuentas) |
| `Banco` / `CajaEfectivo` | Medios de pago habilitados por usuario |
| `Permiso` / `Role` | Control de acceso por módulo y programa |
| `Usuario` | Usuario del sistema con roles y permisos |

**Convención de nombres de entidades:**
EF Core scaffoldeó con nombres en plural o con sufijos especiales:
`Accione`, `Propiedade`, `Configuracione` (singular en español con 'e' final).
Respetar estos nombres exactos al agregar nuevas entidades.

---

## Autenticación y sesión

- JWT Bearer — el token se valida en `BaseAuthApiController`
- El ID del usuario se extrae con `this.getIdUserSession()` (método del controller base)
- Los permisos por módulo/programa se cargan en sesión después del login
- `LogAccesoFilter` audita cada request con `[LogAcceso("Módulo", "Acción")]`

---

## Caché Redis

```csharp
// Inyectar ICacheService (implementado por RedisCacheService)
// InstanceName configurado en appsettings: "AgroAppRedis:"
private readonly ICacheService _cacheService;
```

Usar caché para: catálogos de campañas, propiedades, subcuentas, formas de pago.
No cachear datos transaccionales (egresos, movimientos, planillas).

---

## Manejo de archivos (comprobantes)

```csharp
// Dos instancias de IComprobanteFileService via Keyed DI:
[FromKeyedServices("egresos")] IComprobanteFileService comprobanteEgresos
[FromKeyedServices("ingresos")] IComprobanteFileService comprobanteIngresos

// Flujo de upload:
// 1. PUT /upload-comprobante → guarda en directorio temporal → retorna pathTemporal
// 2. POST /registrar (con pathTemporal) → crea el registro
// 3. _comprobanteFileService.Commit(path) → mueve de temporal a final
```

**Rutas configuradas en appsettings.json:**
- Egresos final: `C:\inetpub\wwwroot\Nuevatoledo\App_Data\Comprobante\Egresos`
- Ingresos final: `C:\inetpub\wwwroot\Nuevatoledo\App_Data\Comprobante\Ingresos`
- Temporal: `C:\inetpub\wwwroot\Nuevatoledo\App_Data\Temporal`

---

## Configuración — appsettings.json

```json
{
  "ConnectionStrings": {
    "sqlserver": "Server=SQL-DNS-WS19\\DBNT;Database=Agropecuaria;...",
    "Redis": "localhost:6379"
  },
  "AppConfig": {
    "RedisInstanceName": "AgroAppRedis:",
    "MovimientosCommandTimeoutSec": 180
  },
  "JwtSetting": {
    "SecretKey": "...",
    "TimeSessionMin": 120,
    "Issuer": "https://api.agricola2g.net"
  }
}
```

Acceder a configuración vía `ConfigApp` (inyectado como singleton), NO leer `IConfiguration` directamente en servicios de negocio.

---

## Logging — log4net

```csharp
// En cada clase que necesite log:
private static readonly ILog __log4Net = LogManager.GetLogger(typeof(MiClase));

// Uso:
__log4Net.Fatal(ex.Message);   // errores graves / excepciones
__log4Net.Error(ex.Message);   // errores recuperables
__log4Net.Info("mensaje");     // información de flujo
__log4Net.Debug("mensaje");    // debugging
```

Configuración en `log4net.config`. Persistencia en SQL Server via `MicroKnights.Log4NetAdoNetAppender`.

---

## Registro de dependencias — Program.cs

Orden de registro:
1. `ConfigApp` como singleton
2. `AppDbContext` con SQL Server
3. Repositories (`AddScoped`)
4. Services (`AddScoped`)
5. Redis cache
6. CORS (`AllowReact` policy)
7. JWT authentication
8. Controllers con `LogAccesoFilter`
9. Swagger con Bearer auth

---

## Convenciones de código

- **PascalCase:** clases, métodos, propiedades, interfaces (`IEgresoService`)
- **camelCase:** variables locales, parámetros
- **Prefijo `__`:** campos de log estático (`__log4Net`)
- **Prefijo `_`:** campos privados de instancia (`_egresoService`)
- **Sufijo `Dto`:** todos los objetos de transferencia de datos
- **Sufijo `Service`:** servicios de aplicación
- **Sufijo `Repository`:** repositorios de infraestructura
- **Prefijo `I`:** interfaces

---

## Flujo de desarrollo

Cuando recibas una tarea de implementación, seguir este proceso en orden:

### 1. Analizar el requerimiento
Antes de escribir código, identificar:
- **Entidades de dominio** involucradas (¿son existentes o nuevas?)
- **Operaciones**: qué endpoints expone (GET/POST/PUT) y qué hace cada uno
- **DTOs necesarios**: filtros de entrada, resultados de salida, DTOs de creación/modificación
- **Queries**: ¿es un query simple con EF Specification o requiere ADO.NET directo (UNION, query complejo)?
- **Archivos a crear o modificar**: listar explícitamente antes de empezar

### 2. Orden de implementación (siempre de adentro hacia afuera)
```
1. Domain/Entities/          → entidad si es nueva
2. Domain/DTOs/              → DTOs de respuesta y filtros de dominio
3. Domain/Interfaces/        → IXRepository con la firma de métodos
4. Application/DTOs/         → DTOs de aplicación (lo que el controller recibe/envía)
5. Application/Interfaces/   → IXService con la firma de métodos
6. Application/Services/     → XService : BaseService, IXService
7. Infrastructure/Persistence/Repositories/ → XRepository : BaseRepository<T>, IXRepository
8. ApiAgricola/Controllers/  → XController : BaseAuthApiController
9. ApiAgricola/Program.cs    → registrar IXRepository + IXService como AddScoped
```
Nunca saltar pasos ni implementar en orden inverso — las dependencias van de adentro hacia afuera.

### 3. Formato de entrega
Para cada archivo, entregar:
- **Ruta completa** desde la raíz del proyecto (ej. `Application/Services/PlanillaService.cs`)
- **Código completo** del archivo — no fragmentos ni pseudocódigo
- Si es una **modificación** a un archivo existente, indicar qué sección se agrega/cambia

### 4. Manejo de ambigüedad
- Si un requerimiento no especifica algo (ej. ¿requiere paginación? ¿qué campos filtrar?), **asumir el comportamiento más conservador** y documentar la suposición al inicio del entregable
- Si hay un patrón análogo en el proyecto (ej. EgresosController para un nuevo módulo similar), seguirlo exactamente
- **No inventar patrones** que no estén en este perfil — usar siempre el más cercano y señalarlo

### 5. Lo que NO hacer
- No usar `ILogger<T>` — siempre `log4net`
- No agregar EF Migrations — el schema es DB-first vía scripts SQL en `Infrastructure/Scripts/`
- No retornar `Ok(data)` directamente — siempre `ResponseApp.From(result)`
- No lanzar excepciones desde servicios al controller — siempre retornar `ResponseMessageDto`
- No leer `IConfiguration` directamente en servicios — usar `ConfigApp`
- No referenciar `Infrastructure` desde `Application`

---

## Checklist para nuevos endpoints

- [ ] Controller hereda de `BaseApiController` o `BaseAuthApiController` según requiera auth
- [ ] Ruta en formato `api/v1/{área}/{recurso}` en minúsculas
- [ ] Comentario XML `/// <summary>` para Swagger
- [ ] `[LogAcceso]` si la operación debe auditarse
- [ ] `[ProducesResponseType]` con el tipo de respuesta y el BusinessCodeEnum
- [ ] Try/catch con `__log4Net.Fatal` y `ResponseApp.From(ResponseApp.Error(...))`
- [ ] Retorno siempre via `ResponseApp.From(result)`
- [ ] Service retorna `ResponseMessageDto` (nunca lanza excepciones al controller)
- [ ] Repository usa `AsNoTracking()` para queries de lectura
- [ ] Registrar servicio e interfaz en `Program.cs`
