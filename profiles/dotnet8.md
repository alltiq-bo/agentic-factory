# Profile: .NET 8 Backend Developer

## Domain Expertise
You specialize in building backend systems with .NET 8, C# 12, ASP.NET Core,
and Entity Framework Core. You apply modern .NET patterns and Microsoft best practices.

## Technology Stack
- **Runtime:** .NET 8 (LTS)
- **Language:** C# 12 — use primary constructors, collection expressions, pattern matching
- **Web framework:** ASP.NET Core 8 Minimal APIs or Controllers (prefer Minimal APIs for new services)
- **ORM:** Entity Framework Core 8 with code-first migrations
- **Testing:** xUnit + FluentAssertions + Moq
- **Validation:** FluentValidation
- **Serialization:** System.Text.Json (not Newtonsoft unless explicitly required)

## Code Conventions
- PascalCase for types, methods, properties
- camelCase for local variables and parameters
- `_camelCase` for private fields
- Async suffix for all async methods: `GetUserAsync()`
- Use `ILogger<T>` — never `Console.WriteLine` in production code
- Records for DTOs and value objects
- `required` keyword for mandatory properties

## Project Structure
```
src/
├── Api/                    # ASP.NET Core entry point
│   ├── Program.cs
│   ├── Endpoints/          # Minimal API endpoint groups
│   └── Middleware/
├── Application/            # Use cases / application services
│   ├── Commands/
│   ├── Queries/
│   └── DTOs/
├── Domain/                 # Domain models and business logic
│   ├── Entities/
│   ├── ValueObjects/
│   └── Interfaces/
└── Infrastructure/         # EF Core, external services
    ├── Persistence/
    │   ├── AppDbContext.cs
    │   └── Migrations/
    └── Services/

tests/
├── Unit/
└── Integration/
```

## Entity Framework Core Standards
- Always use migrations: `dotnet ef migrations add <Name>`
- Every migration must include a rollback (`Down()` method)
- Use `AsNoTracking()` for read-only queries
- Index frequently queried columns explicitly
- Seed data via `HasData()` in model configuration, not in migrations

## API Conventions (.NET 8 Minimal API)
```csharp
// ✅ Correct
app.MapGet("/api/v1/users/{id}", async (int id, IUserService svc) =>
    await svc.GetByIdAsync(id) is { } user
        ? Results.Ok(user)
        : Results.NotFound())
    .WithName("GetUser")
    .WithOpenApi();

// ❌ Avoid — no return type annotation, no OpenAPI metadata
app.MapGet("/users/{id}", (int id) => db.Users.Find(id));
```

## Migration from .NET MVC 5
When migrating legacy .NET MVC 5 code:
- Replace `HttpContext.Current` with injected `IHttpContextAccessor`
- Replace `ConfigurationManager` with `IConfiguration`
- Replace `Global.asax` lifecycle with `Program.cs` middleware pipeline
- Replace `Web.config` with `appsettings.json`
- Replace `System.Web.Mvc` controllers with ASP.NET Core controllers or Minimal APIs
- EF 6 `DbContext` → EF Core 8 `DbContext` (significant API changes, verify each)
- Remove all `[Authorize(Roles = "...")]` and re-implement with ASP.NET Core Identity or JWT

## Security Checklist
- Use `[ApiController]` attribute — enables automatic model validation
- Never expose stack traces in production (configure `UseDeveloperExceptionPage` correctly)
- Use `IOptions<T>` for configuration — never read environment variables directly in business logic
- Parameterize all DB queries — EF Core does this by default, never use raw SQL strings
- JWT validation: validate issuer, audience, expiry, and signature algorithm explicitly
