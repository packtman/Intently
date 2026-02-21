# Interactive Threat Model Canvas — Implementation Spec

> A drag-and-drop visual canvas where users map data flows, trust boundaries, and actors. The AI suggests threats directly on the canvas based on the topology. Exportable as a threat model document.

---

## Summary

The **Interactive Threat Model Canvas** extends the existing attack flow diagram and threat analysis features into a fully interactive, visual threat modeling workspace. Users can:

- **Drag-and-drop** actors, data stores, processes, and external entities onto a canvas
- **Draw data flows** between elements to represent how data moves through the system
- **Define trust boundaries** as visual regions that group elements by trust level
- **Receive AI-powered threat suggestions** overlaid directly on the canvas topology
- **Auto-populate** from an existing review's delta analysis / codebase profile
- **Export** the completed threat model as a structured document (Markdown, JSON, or PDF-ready HTML)

This builds on top of the existing `ImpactGraph` canvas rendering pattern (force-directed graph on `<canvas>`), the `AttackFlowDiagram` component, the `DeltaAnalysisResult` data (trust boundaries, data flows, endpoints), and the `ThreatPatternMatcher` engine.

---

## Architecture Context

### Existing Files Involved

| Area | File | Relevance |
|------|------|-----------|
| **Canvas rendering** | `frontend/src/components/review/ImpactGraph.tsx` | Reference for canvas-based force simulation, node rendering, click interaction — the new canvas will follow a similar pattern but with drag-and-drop, zoom/pan, and richer node types |
| **Attack flow** | `frontend/src/components/security/AttackFlowDiagram.tsx` | Linear attack flow steps — canvas will absorb this as an overlay layer |
| **Deep threat** | `frontend/src/components/security/DeepThreatSection.tsx` | Threat model summary UI — canvas export should produce data compatible with this |
| **Threat patterns** | `src/context_graph/security/threat_patterns.py` | STRIDE pattern matcher — canvas AI suggestions will invoke this + LLM |
| **Delta analyzer** | `src/context_graph/security/delta_analyzer.py` | `DeltaAnalysisResult` has `trust_boundary_impacts`, `new_data_flows`, `new_endpoints` — used to auto-populate canvas |
| **Review engine** | `src/context_graph/security/review_engine.py` | Orchestrates security review — canvas will call a new dedicated threat canvas endpoint |
| **Core models** | `src/context_graph/core/models.py` | `EntityType`, `RelationshipType`, `SecurityFinding` — canvas nodes map to these |
| **Feature flags** | `src/context_graph/config/features.py` | 5-location checklist for `enable_threat_canvas` |
| **API main** | `src/context_graph/api/main.py` | Router registration |
| **Frontend API** | `frontend/src/services/api.ts` | API service methods |
| **Desktop API** | `desktop/src/services/api.ts` | Same methods with `baseUrl` |
| **Frontend types** | `frontend/src/types/index.ts` | TypeScript type definitions |
| **Frontend layout** | `frontend/src/components/Layout.tsx` | Nav items |
| **Frontend app** | `frontend/src/App.tsx` | Route definitions |
| **Desktop layout** | `desktop/src/components/Layout.tsx` | Nav items (with desktop patterns) |
| **Desktop app** | `desktop/src/App.tsx` | Route definitions |
| **Review detail** | `frontend/src/pages/ReviewDetail.tsx` | Tab for canvas access from review context |
| **Storage** | `src/context_graph/storage/sqlite.py` | Persist canvas state |

### Patterns to Follow

- **Canvas rendering**: `ImpactGraph.tsx` — HTML5 canvas with manual force simulation, click handling, filter controls
- **API routes**: `codebase_profile_routes.py` — `APIRouter` with `@requires_feature` decorators
- **Feature flags**: 5-location pattern in `features.py` (class default, `from_env`, `all_enabled`, `to_dict`, `get_enabled_features`)
- **Storage**: JSON blob in SQLite, following `codebase_profiles` table pattern
- **Dual-app**: every frontend component must exist in both `frontend/` and `desktop/` with `baseUrl` handling in desktop

### What Must NOT Break

- Existing review pipeline (no changes to `SecurityReviewEngine`)
- Existing `ImpactGraph`, `AttackFlowDiagram`, `DeepThreatSection` components
- Existing SQLite tables (additive schema only)
- Existing frontend routes and navigation
- Existing API endpoints

---

## Implementation Order

1. **Feature flag** — `enable_threat_canvas` in all 5 locations in `features.py`
2. **Canvas data models** (Python) — Pydantic models for canvas elements (nodes, edges, boundaries, threat overlays)
3. **SQLite schema + storage** — `threat_canvas_models` table for persisting canvas state per review
4. **AI threat suggestion engine** — new module `src/context_graph/security/canvas_threat_analyzer.py` that takes a canvas topology and returns threat suggestions using STRIDE + LLM
5. **API routes** — `src/context_graph/api/threat_canvas_routes.py` with CRUD + AI suggest + export endpoints
6. **Register routes** in `api/main.py`
7. **Frontend types** — TypeScript interfaces for canvas elements
8. **Frontend canvas component** — `frontend/src/components/security/ThreatCanvas.tsx` — the core drag-and-drop canvas
9. **Frontend page** — `frontend/src/pages/ThreatCanvas.tsx` — standalone page wrapping the canvas
10. **Frontend wiring** — nav item in `Layout.tsx`, route in `App.tsx`, tab in `ReviewDetail.tsx`
11. **Frontend API methods** — add canvas methods to `frontend/src/services/api.ts`
12. **Desktop page** — `desktop/src/pages/ThreatCanvas.tsx` (same UI, uses `baseUrl`)
13. **Desktop component** — `desktop/src/components/security/ThreatCanvas.tsx`
14. **Desktop wiring** — nav item, route, API methods with `baseUrl`
15. **Export functionality** — Markdown / JSON export endpoint + frontend download button

---

## File Action Table

| File | Action |
|------|--------|
| `src/context_graph/config/features.py` | **MODIFY** — add `enable_threat_canvas` flag in all 5 locations |
| `src/context_graph/security/canvas_threat_analyzer.py` | **CREATE** — AI threat suggestion engine for canvas topology |
| `src/context_graph/api/threat_canvas_routes.py` | **CREATE** — API endpoints for canvas CRUD, AI suggest, export |
| `src/context_graph/api/main.py` | **MODIFY** — import and register `threat_canvas_routes` router |
| `src/context_graph/storage/sqlite.py` | **MODIFY** — add `THREAT_CANVAS_SCHEMA` table and canvas CRUD methods |
| `frontend/src/types/index.ts` | **MODIFY** — add canvas TypeScript types |
| `frontend/src/components/security/ThreatCanvas.tsx` | **CREATE** — core interactive canvas component |
| `frontend/src/components/security/index.ts` | **MODIFY** — export `ThreatCanvas` |
| `frontend/src/pages/ThreatCanvas.tsx` | **CREATE** — standalone threat canvas page |
| `frontend/src/services/api.ts` | **MODIFY** — add canvas API methods |
| `frontend/src/components/Layout.tsx` | **MODIFY** — add nav item for Threat Canvas |
| `frontend/src/App.tsx` | **MODIFY** — add route for `/threat-canvas` |
| `frontend/src/pages/ReviewDetail.tsx` | **MODIFY** — add "Threat Canvas" tab |
| `desktop/src/components/security/ThreatCanvas.tsx` | **CREATE** — same canvas component with `baseUrl` |
| `desktop/src/pages/ThreatCanvas.tsx` | **CREATE** — same page with `baseUrl` |
| `desktop/src/services/api.ts` | **MODIFY** — add canvas API methods with `baseUrl` |
| `desktop/src/components/Layout.tsx` | **MODIFY** — add nav item |
| `desktop/src/App.tsx` | **MODIFY** — add route |
| `desktop/src/pages/ReviewDetail.tsx` | **MODIFY** — add "Threat Canvas" tab |

---

## Key Implementation Details

### 1. Feature Flag

```python
# In features.py — class default
enable_threat_canvas: bool = False

# In from_env()
enable_threat_canvas=_env_bool("FEATURE_THREAT_CANVAS"),

# In all_enabled()
enable_threat_canvas=True,

# In to_dict()
"threat_canvas": self.enable_threat_canvas,

# In get_enabled_features()
if self.enable_threat_canvas:
    enabled.append("threat_canvas")
```

Environment variable: `FEATURE_THREAT_CANVAS=true`

### 2. Canvas Data Models (Python — Pydantic for API, stored as JSON in SQLite)

```python
# In threat_canvas_routes.py or a shared models module

class CanvasNodeType(str, Enum):
    ACTOR = "actor"               # External user/system
    PROCESS = "process"           # Internal process/service  
    DATA_STORE = "data_store"     # Database, file, cache
    EXTERNAL_ENTITY = "external"  # Third-party service
    TRUST_BOUNDARY = "trust_boundary"  # Visual region

class CanvasNode(BaseModel):
    id: str
    type: CanvasNodeType
    label: str
    x: float
    y: float
    width: float = 120
    height: float = 80
    properties: dict[str, Any] = {}
    # e.g., { "handles_pii": true, "requires_auth": true, "protocol": "HTTPS" }

class CanvasEdge(BaseModel):
    id: str
    source_id: str
    target_id: str
    label: str = ""
    data_classification: str = "unclassified"
    # e.g., "pii", "credentials", "public", "internal"
    protocol: str = ""
    # e.g., "HTTPS", "gRPC", "SQL", "message_queue"
    bidirectional: bool = False

class TrustBoundary(BaseModel):
    id: str
    label: str
    x: float
    y: float
    width: float
    height: float
    trust_level: int = 0  # 0 = untrusted, 1 = DMZ, 2 = internal, 3 = highly trusted
    color: str = "#ef4444"

class ThreatOverlay(BaseModel):
    id: str
    threat_id: str
    category: str          # STRIDE category
    title: str
    description: str
    severity: str           # critical, high, medium, low
    affected_node_ids: list[str]
    affected_edge_ids: list[str]
    mitigation: str
    confidence: float
    source: str = "ai"     # "ai" or "manual"

class CanvasState(BaseModel):
    canvas_id: str
    review_id: str | None = None
    title: str = "Untitled Threat Model"
    nodes: list[CanvasNode]
    edges: list[CanvasEdge]
    boundaries: list[TrustBoundary]
    threats: list[ThreatOverlay] = []
    metadata: dict[str, Any] = {}
    created_at: str
    updated_at: str
```

### 3. SQLite Schema

```sql
CREATE TABLE IF NOT EXISTS threat_canvases (
    id TEXT PRIMARY KEY,
    review_id TEXT,
    title TEXT NOT NULL,
    canvas_state_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (review_id) REFERENCES reviews(review_id)
);
```

Canvas state is stored as a single JSON blob (the full `CanvasState` serialized). This keeps the schema simple and avoids complex relational joins for what is essentially a document.

### 4. AI Threat Suggestion Engine (`canvas_threat_analyzer.py`)

This module takes the canvas topology and returns threat suggestions:

```python
class CanvasThreatAnalyzer:
    """Analyzes canvas topology for threats using STRIDE + LLM."""
    
    async def analyze(
        self,
        canvas: CanvasState,
        existing_findings: list[SecurityFinding] | None = None,
    ) -> list[ThreatOverlay]:
        """
        Analyze canvas for threats.
        
        Strategy:
        1. Pattern-based: Apply STRIDE per element type
           - Each data flow crossing a trust boundary = potential threat
           - Each actor->process edge without auth = spoofing risk
           - Each data store with PII = info disclosure risk
        2. LLM-based: Send topology description to LLM for deeper analysis
           - Build natural language description of the topology
           - Ask for STRIDE threats specific to the topology
           - Map LLM responses back to canvas elements
        """
```

**Pattern-based rules (fast, no LLM cost):**
- Data flow crossing trust boundary without encryption → INFO_DISCLOSURE
- External actor accessing process without auth → SPOOFING  
- Process writing to data store without validation → TAMPERING
- No audit logging on sensitive data access → REPUDIATION
- Public-facing process without rate limiting → DENIAL_OF_SERVICE
- Direct external access to data store → ELEVATION_OF_PRIVILEGE

**LLM-based (deeper, uses existing `ParallelLLMAnalyzer` infrastructure):**
- Serialize topology to natural language
- Prompt: "Given this data flow diagram with the following elements and trust boundaries, identify STRIDE threats specific to this architecture"
- Map LLM findings back to specific `affected_node_ids` and `affected_edge_ids`

### 5. API Endpoints

```
POST   /api/threat-canvas                    — Create new canvas (empty or from review)
GET    /api/threat-canvas                    — List all canvases
GET    /api/threat-canvas/{canvas_id}        — Get canvas state
PUT    /api/threat-canvas/{canvas_id}        — Update canvas state (save)
DELETE /api/threat-canvas/{canvas_id}        — Delete canvas

POST   /api/threat-canvas/{canvas_id}/suggest — AI threat suggestion
POST   /api/threat-canvas/{canvas_id}/populate — Auto-populate from review delta
GET    /api/threat-canvas/{canvas_id}/export   — Export as document (format=markdown|json)
```

**Auto-populate from review**: Takes a `review_id`, loads the `DeltaAnalysisResult` and dashboard data, and creates canvas nodes for:
- Each `new_endpoint` → Process node
- Each `new_data_model` → Data Store node  
- Each `trust_boundary_impact` → Trust Boundary region
- Each data flow from delta → Edge
- External integrations → External Entity node

### 6. Frontend Canvas Component (`ThreatCanvas.tsx`)

The canvas is built on **HTML5 Canvas** (consistent with `ImpactGraph.tsx`), enhanced with:

**Rendering layers (bottom to top):**
1. Grid background (subtle dots)
2. Trust boundary rectangles (semi-transparent colored regions)
3. Edges (lines with arrows, dashed for cross-boundary)
4. Nodes (icons + labels based on type)
5. Threat overlays (warning badges on affected elements)
6. Selection highlights

**Interaction model:**
- **Pan**: Mouse drag on empty space (or middle-click drag)
- **Zoom**: Scroll wheel
- **Select**: Click on node/edge
- **Move**: Drag selected node
- **Add node**: Click toolbox icon then click on canvas, or drag from toolbox
- **Add edge**: Click source node port, drag to target node port
- **Add boundary**: Click boundary tool, drag rectangle on canvas
- **Delete**: Select + Delete key or context menu

**Toolbox (left sidebar within canvas):**
- Actor (person icon)
- Process (circle)
- Data Store (cylinder)
- External Entity (rectangle with double border)
- Trust Boundary (dashed rectangle)
- Edge tool (arrow)

**Right panel (when node/edge selected):**
- Properties editor (label, type-specific fields like `handles_pii`, `requires_auth`)
- For edges: data classification, protocol
- For boundaries: trust level

**AI Suggest button:**
- Floating action button or toolbar button
- Calls `POST /api/threat-canvas/{id}/suggest`
- Displays threats as colored overlays on affected elements
- Threat list panel shows all identified threats with severity badges

**Export button:**
- Downloads threat model document
- Includes: diagram description, element inventory, data flow table, trust boundary map, threat table with STRIDE categories

**State management:**
- Local React state for canvas interactions (positions, selection, zoom/pan)
- Debounced auto-save to backend (PUT every 2 seconds of inactivity after changes)
- React Query for loading/saving

### 7. TypeScript Types

```typescript
// In frontend/src/types/index.ts

export type CanvasNodeType = 'actor' | 'process' | 'data_store' | 'external' | 'trust_boundary'

export interface CanvasNode {
  id: string
  type: CanvasNodeType
  label: string
  x: number
  y: number
  width: number
  height: number
  properties: Record<string, any>
}

export interface CanvasEdge {
  id: string
  source_id: string
  target_id: string
  label: string
  data_classification: string
  protocol: string
  bidirectional: boolean
}

export interface TrustBoundary {
  id: string
  label: string
  x: number
  y: number
  width: number
  height: number
  trust_level: number
  color: string
}

export interface ThreatOverlay {
  id: string
  threat_id: string
  category: string
  title: string
  description: string
  severity: 'critical' | 'high' | 'medium' | 'low'
  affected_node_ids: string[]
  affected_edge_ids: string[]
  mitigation: string
  confidence: number
  source: 'ai' | 'manual'
}

export interface CanvasState {
  canvas_id: string
  review_id?: string
  title: string
  nodes: CanvasNode[]
  edges: CanvasEdge[]
  boundaries: TrustBoundary[]
  threats: ThreatOverlay[]
  metadata: Record<string, any>
  created_at: string
  updated_at: string
}
```

### 8. Auto-Populate from Review

When opening the canvas from a review context, the canvas pre-populates by reading:
- `dashboard.delta_summary` → nodes for endpoints, data models
- `dashboard.llm_analysis.threat_analysis.trust_boundaries` → trust boundary regions
- `dashboard.llm_analysis.threat_analysis.data_flow_risks` → edges
- `dashboard.llm_analysis.threat_analysis.attack_surface` → external entity nodes
- Existing findings → pre-populated threat overlays

This gives users a head start instead of a blank canvas.

### 9. Export Format (Markdown)

```markdown
# Threat Model: {title}

## System Overview
{Auto-generated description from canvas elements}

## Data Flow Diagram Elements

### Actors
| ID | Name | Properties |
|----|------|-----------|
| ... | ... | ... |

### Processes
| ID | Name | Auth Required | Handles PII |
|----|------|--------------|-------------|
| ... | ... | ... | ... |

### Data Stores
| ID | Name | Classification | Encryption |
|----|------|---------------|------------|
| ... | ... | ... | ... |

### External Entities
| ID | Name | Protocol | Trust Level |
|----|------|----------|-------------|
| ... | ... | ... | ... |

## Data Flows
| From | To | Data Classification | Protocol | Crosses Boundary |
|------|----|-------------------|----------|-----------------|
| ... | ... | ... | ... | ... |

## Trust Boundaries
| Boundary | Trust Level | Elements |
|----------|-------------|----------|
| ... | ... | ... |

## Identified Threats (STRIDE)

### Spoofing
| Threat | Severity | Affected Elements | Mitigation |
|--------|----------|--------------------|------------|
| ... | ... | ... | ... |

### Tampering
...

### Repudiation
...

### Information Disclosure
...

### Denial of Service
...

### Elevation of Privilege
...

## Risk Summary
- Total threats: {count}
- Critical: {count}
- High: {count}
- Medium: {count}
- Low: {count}

## Mitigations Priority List
1. {highest priority mitigation}
2. ...
```

---

## Desktop-Specific Considerations

- Desktop `ThreatCanvas.tsx` must use `${backendUrl}/api/threat-canvas/...` for all API calls
- Use `window.electronAPI?.getBackendUrl()` pattern from `desktop/src/hooks/useBackend.tsx`
- Canvas rendering is identical (HTML5 Canvas works in Electron)
- File export could optionally use Electron's `dialog.showSaveDialog` for native save dialog

---

## Constraints Checklist

- [x] Type hints (`from __future__ import annotations`)
- [x] Feature flag in all 5 locations (class default, from_env, all_enabled, to_dict, get_enabled_features)
- [x] Dual-app: frontend AND desktop updated
- [x] Desktop uses `${backendUrl}`, frontend uses relative URLs
- [x] Lazy imports for heavy/optional dependencies (LLM providers in canvas_threat_analyzer)
- [x] No breaking changes to existing APIs
- [x] Dependencies — no new Python deps needed (uses existing FastAPI, Pydantic, aiosqlite, LLM providers); no new npm deps needed (HTML5 Canvas is native)
- [x] Additive SQLite schema only (new table, no changes to existing tables)

---

## Verification Plan

### Manual Testing
1. Enable feature flag: `FEATURE_THREAT_CANVAS=true`
2. Navigate to `/threat-canvas` — should see empty canvas with toolbox
3. Add nodes (actor, process, data store) by clicking toolbox and placing on canvas
4. Draw edges between nodes
5. Add a trust boundary around internal processes
6. Click "AI Suggest" — should receive threat overlay suggestions
7. Open from a review context — canvas should auto-populate with review data
8. Export as Markdown — verify document contains all elements and threats
9. Reload page — canvas state should persist (auto-save)
10. Verify desktop app has identical functionality

### Backward Compatibility
- With `FEATURE_THREAT_CANVAS=false` (default): no nav item, no routes, API returns 403
- Existing review detail page unchanged (new tab only appears when feature enabled)
- No changes to existing threat analysis pipeline
- No new Python or npm dependencies

### Edge Cases
- Empty canvas (no elements) — AI suggest should return empty/message
- Canvas with no edges — should still identify node-level threats
- Very large canvas (50+ nodes) — performance should remain smooth
- Canvas from review with no delta data — graceful fallback to empty canvas
- Concurrent saves — last-write-wins (simple for MVP)
