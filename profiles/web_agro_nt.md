# Profile: web.agro.nt — Frontend Developer

## Descripción del proyecto
Frontend del sistema agrícola de gestión. React + TypeScript + Vite + Material UI.
Se conecta al backend `api_agricola2g` (.NET 9) en `https://api.agricola2g.net`.
Repo: `vega-bo/web.agro.nt` — proyecto en producción.

---

## Stack tecnológico

| Herramienta | Versión | Rol |
|---|---|---|
| React | 18 | UI framework |
| TypeScript | 5 | Tipado estático |
| Vite | 6 | Bundler / dev server |
| Material UI (MUI) | v7 | Componentes UI principales |
| Tailwind CSS | 4 | Utilidades de layout/espaciado |
| lucide-react | latest | Iconos |
| date-fns | latest | Formateo de fechas |
| @mui/x-date-pickers | latest | DatePicker (con date-fns adapter) |
| xlsx-js-style | latest | Exportación a Excel |
| @supabase/supabase-js | latest | Autenticación suplementaria |

**Env variable:** `VITE_API_BASE_URL` — base de la API (ej. `https://api.agricola2g.net`)

---

## Arquitectura — Clean Architecture en 4 capas

```
src/
├── application/          → Interfaces de aplicación, SessionService
├── infrastructure/       → Implementaciones: HTTP, Services, Storage
│   ├── http/apiFetch.ts  → Wrapper fetch centralizado (maneja 401)
│   ├── services/         → XService.ts — clases con instancias exportadas
│   └── storage/          → tokenStorage (localStorage)
├── presentation/         → UI: pages, components, hooks, context
│   ├── pages/            → Una página por módulo (ej. EgresosContable.tsx)
│   ├── components/       → Subdirectorios por módulo (ej. egreso/, movimiento/)
│   ├── context/          → AuthContext, NotificationContext
│   └── hooks/            → usePageTitle, useNotification, custom hooks
└── shared/
    └── types/index.ts    → TODOS los tipos TypeScript del proyecto
```

**Regla de dependencias:** `presentation` → `infrastructure` → `application` → `shared`
Nunca importar `presentation` desde `infrastructure`.

---

## Routing — formComponents en App.tsx

El routing no usa React Router con rutas declarativas. El menú viene del backend (`appsettings.json` → BD `seg.Programas`) y contiene un campo `Form` que mapea a un componente React:

```tsx
// src/App.tsx
const formComponents: Record<string, React.ReactNode> = {
  EgresosContable:     <EgresosContable />,
  CampaniasForm:       <CampaniaPage />,
  MovimientosContable: <MovimientosContable />,
  // Nuevo módulo → agregar aquí con la misma clave que BD.seg.Programas.Form
};
```

**Al agregar un nuevo módulo:**
1. Crear el componente de página en `src/presentation/pages/NuevoModulo.tsx`
2. Importarlo en `App.tsx` y registrarlo en `formComponents`
3. La clave debe coincidir EXACTAMENTE con el campo `Form` en `seg.Programas`

---

## Patrón HTTP — apiFetch

```ts
// src/infrastructure/http/apiFetch.ts
// Wrapper sobre fetch que dispara un evento personalizado en 401:
window.dispatchEvent(new CustomEvent('auth:session-expired'));

// Usar SIEMPRE apiFetch en lugar de fetch directo:
const res = await apiFetch(`${API_BASE}/egresos/search`, {
  method: 'POST',
  headers: this.getHeaders(),
  body: JSON.stringify(filters),
});
```

**NUNCA** llamar `fetch(...)` directamente. Solo `apiFetch`.

---

## Patrón de Services

Cada módulo tiene su propio servicio en `src/infrastructure/services/`:

```ts
// Patrón: clase + instancia exportada como singleton
export class EgresoService {
  private getHeaders() {
    const token = tokenStorage.get();
    return {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    };
  }

  private getAuthHeader() {
    // Solo Authorization (sin Content-Type) — para multipart/form-data
    const token = tokenStorage.get();
    return { Authorization: `Bearer ${token}` };
  }

  async searchEgresos(filters: EgresoFilters): Promise<{ data: EgresoResult[]; total: number }> {
    const res = await apiFetch(`${API_BASE}/egresos/search`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify(filters),
    });
    if (!res.ok) throw new Error('Error al buscar egresos');
    const body = await res.json();
    return {
      data: body.data?.collection ?? [],
      total: body.data?.recordsTotal ?? 0,
    };
  }
}

export const egresoService = new EgresoService();  // ← singleton exportado
```

**Reglas de services:**
- Clase con métodos `async` que retornan el tipo esperado o lanzan `Error`
- Siempre exportar instancia singleton al final: `export const xService = new XService()`
- Leer el token con `tokenStorage.get()` en cada request (no cachear el token)
- `getHeaders()` para JSON, `getAuthHeader()` (sin Content-Type) para file upload
- Las páginas/componentes importan `xService` (instancia), nunca la clase

---

## Patrón de Páginas

```tsx
// src/presentation/pages/EgresosContable.tsx — referencia canónica
export const EgresosContable = () => {
  usePageTitle('Egresos Contable');  // Siempre, primer hook

  // 1. Estado del resultado
  const [items, setItems] = useState<EgresoResult[]>([]);
  const [loading, setLoading] = useState(false);

  // 2. Estado de filtros: dos snapshots
  const [filters, setFilters] = useState<EgresoFilters>({ ...FILTROS_VACIOS });
  const [activeFiltersSnapshot, setActiveFiltersSnapshot] = useState<EgresoFilters>({ ...FILTROS_VACIOS });
  //    ^-- filters: lo que el usuario está editando en el formulario
  //    ^-- activeFiltersSnapshot: los filtros que se usaron en la última búsqueda (para paginación)

  // 3. Estado de selección de Autocomplete (objeto completo, no solo id)
  const [selectedCampania, setSelectedCampania] = useState<ItemCatalogo | null>(null);

  // 4. Contextos
  const { notifyError } = useNotification();

  // 5. La función de búsqueda siempre con useCallback
  const doSearch = useCallback(async (searchFilters: EgresoFilters) => {
    setLoading(true);
    try {
      const result = await xService.search(searchFilters);
      setItems(result.data);
    } catch (error) {
      notifyError((error as Error).message ?? 'Error al buscar');
    } finally {
      setLoading(false);
    }
  }, [notifyError]);

  // 6. Carga de catálogos al montar (solo catálogos, NO búsqueda automática)
  useEffect(() => {
    loadCatalogos();
  }, []);
  // EXCEPCIÓN: EgresosContable SÍ hace búsqueda inicial con campaña actual.
  // MovimientosContable arranca sin búsqueda — buscador limpio.

  // 7. handleSearch: toma snapshot y dispara búsqueda
  const handleSearch = () => {
    const snapshot = { ...filters, start: 0, length: rowsPerPage };
    setActiveFiltersSnapshot(snapshot);
    doSearch(snapshot);
  };

  // 8. Paginación: usa activeFiltersSnapshot, no filters
  const handlePageChange = (_: React.ChangeEvent<unknown>, page: number) => {
    doSearch({ ...activeFiltersSnapshot, start: (page - 1) * rowsPerPage });
  };

  return (
    <Box>
      <Typography variant="h1" sx={{ mb: 3 }}>Título del módulo</Typography>
      <FiltrosComponent ... onSearch={handleSearch} onClear={handleClear} />
      <ResultadoComponent items={items} loading={loading} ... />
    </Box>
  );
};
```

**Reglas de páginas:**
- `usePageTitle(título)` siempre como primer hook
- Separar `filters` (estado del form) de `activeFiltersSnapshot` (filtros de la última búsqueda)
- `doSearch` con `useCallback` — declarar ANTES de cualquier `useEffect` que lo use (evita TDZ)
- `useEffect` de catálogos con deps `[]` — nunca agregar `notifyError` (puede ser inestable)
- Paginación siempre opera sobre `activeFiltersSnapshot`
- `handleClear`: restaura campaña actual del catálogo pero resetea el resto

---

## Patrón de Filtros — Componentes

```tsx
// Estructura típica de un componente de filtros
interface XFiltrosProps {
  catalogos: CatalogoFiltroX;
  filters: XFilters;
  loading: boolean;
  // Selecciones como objetos completos (no solo IDs)
  selectedCampania: ItemCatalogo | null;
  // Callbacks individuales por campo
  onCampaniaChange: (val: ItemCatalogo | null) => void;
  onSearch: () => void;
  onClear: () => void;
}

// Autocomplete pattern
<Autocomplete
  size="small"
  options={catalogos.campanias}
  getOptionLabel={(o) => o.nombre}
  value={selectedCampania}
  onChange={(_, val) => onCampaniaChange(val)}
  renderInput={(params) => (
    <TextField {...params} label="Campaña" sx={{ bgcolor: '#E1F2ED' }} />
  )}
/>

// DatePicker pattern
<DatePicker
  label="Fecha Inicio"
  value={filters.fechaInicio ?? null}
  onChange={(val) => onFiltersChange((prev) => ({ ...prev, fechaInicio: val }))}
  slotProps={{ textField: { size: 'small', sx: { bgcolor: '#E1F2ED' } } }}
/>
```

---

## Patrón de Resultados — Componentes

```tsx
// Header flotante para tablas con overflow-x
// Ver MovimientosResultado.tsx como referencia de implementación completa:
//   Helpers → Styles → Props → HeaderRow → FloatingHeader → useScrollSync → useFloatingHeader → componente principal

// La técnica:
// 1. IntersectionObserver detecta cuando <thead> sale del viewport
// 2. createPortal renderiza el header fuera del Paper (escapa overflow-x: auto)
// 3. marginLeft: -scrollLeft sincroniza scroll horizontal
// 4. syncingRef + requestAnimationFrame previene loop circular scroll

// Exportación a Excel:
import * as XLSX from 'xlsx-js-style';
// Solo botón visible, implementar lógica de exportación con xlsx-js-style
```

---

## Tipado — shared/types/index.ts

**TODOS** los tipos van en `src/shared/types/index.ts`. Nunca declarar tipos en componentes o servicios.

Convenciones de nombres:
- `ItemCatalogo` — para catálogos genéricos `{ id: number; nombre: string }`
- `XFilters` — filtros de búsqueda enviados al backend
- `XResult` — resultado de una fila en la lista
- `XCreateDto` / `XUpdateDto` — DTOs de creación/modificación
- `XDetalle` — objeto completo (GET por ID)
- `CatalogoFiltroX` — respuesta del endpoint `/filtros`

---

## Autenticación y sesión

```ts
// src/infrastructure/storage/tokenStorage.ts
tokenStorage.get()    // lee JWT de localStorage
tokenStorage.set(t)   // guarda JWT
tokenStorage.clear()  // logout

// src/application/ → SessionService
// src/presentation/context/AuthContext.tsx → proveedor de sesión
// Evento de sesión expirada: window.addEventListener('auth:session-expired', ...)
// El AuthContext escucha este evento y redirige al login
```

---

## Design System

### Colores corporativos
```ts
primary:    '#037553'   // botones, chips activos, focus rings
primaryHover: '#026647' // hover de botones
inputBg:    '#E1F2ED'   // bgcolor de todos los TextField/Autocomplete/DatePicker
```

### Reglas MUI
- `size="small"` en TODOS los campos (TextField, Autocomplete, DatePicker, Select, Button)
- `sx` numéricos multiplican por 8px → usar strings para valores exactos: `'17px'` no `2.125`
- `variant="h1"` para título principal de cada página
- Grid 2 con `container` y `item` para layouts de filtros

### Iconos
Siempre de `lucide-react`. No usar `@mui/icons-material`.

```tsx
import { Search, X, Download, Edit, Eye } from 'lucide-react';
```

---

## Contextos globales

```tsx
// useNotification — para errores y mensajes de feedback
const { notifyError, notifySuccess } = useNotification();
notifyError('Mensaje de error');
notifySuccess('Operación exitosa');

// usePageTitle — para el título del browser tab
usePageTitle('Nombre del módulo');
```

---

## Convenciones de código

- **PascalCase:** componentes React, interfaces TypeScript, types
- **camelCase:** variables, funciones, props, archivos de servicio (`egresoService`)
- **SCREAMING_SNAKE_CASE:** constantes de objeto vacío inicial (`FILTROS_VACIOS`)
- Componentes funcionales con `export const X = () => {}`
- No `export default` en componentes — siempre named export
- Hooks custom en `src/presentation/hooks/useX.ts`

---

## Endpoints del backend (referencia)

```
# Catálogos para filtros
GET  /api/v1/transactions/egresos/filtros
GET  /api/v1/transactions/movimientos/filtros

# Búsqueda (POST con body de filtros)
POST /api/v1/transactions/egresos/search
POST /api/v1/transactions/movimientos/search
POST /api/v1/transactions/campanias/search

# CRUD Egresos
POST /api/v1/transactions/egresos/registrar
PUT  /api/v1/transactions/egresos/modificar
PUT  /api/v1/transactions/egresos/modificar-estado
GET  /api/v1/transactions/egresos/{id}
PUT  /api/v1/transactions/egresos/upload-comprobante

# Subcatálogos dinámicos
GET  /api/v1/transactions/egresos/sectores?idPropiedad=X
GET  /api/v1/transactions/egresos/personas?search=X

# Seguridad
POST /api/v1/security/authenticate
```

**Respuesta del backend (envoltorio):**
```json
{
  "error": false,
  "code": 200,
  "message": "...",
  "data": { ... }
}
```
Siempre leer `body.data`, validar `body.error`, usar `body.message` para mensajes de error.

---

## Checklist para nuevos módulos

- [ ] Tipos definidos en `src/shared/types/index.ts`
- [ ] Servicio en `src/infrastructure/services/NuevoService.ts` con instancia singleton exportada
- [ ] Página en `src/presentation/pages/NuevoModulo.tsx` con `usePageTitle`
- [ ] Componente de filtros en `src/presentation/components/nuevo/NuevoFiltros.tsx`
- [ ] Componente de resultado en `src/presentation/components/nuevo/NuevoResultado.tsx`
- [ ] Registro en `formComponents` de `App.tsx` con clave igual a `seg.Programas.Form`
- [ ] `filters` y `activeFiltersSnapshot` separados para paginación correcta
- [ ] `doSearch` con `useCallback` declarado antes del `useEffect` que lo use
- [ ] `apiFetch` en lugar de `fetch` nativo
- [ ] Colores corporativos: `bgcolor: '#E1F2ED'` en inputs, `color: '#037553'` en primario
- [ ] `size="small"` en todos los controles MUI
- [ ] Iconos de `lucide-react`
- [ ] Exportación Excel con `xlsx-js-style` (botón visible, lógica implementada)
