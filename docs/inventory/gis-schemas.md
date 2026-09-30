# rmigis-agp-toolbox: GIS Schema Definitions, Feature Classes, Topology, and Survey123

**Inventory of**: YAML schema definitions, feature class structures, topology rules, Survey123 forms, and how the ArcGIS Pro toolbox applies them.  
**Source repository**: `~/sources/rmigis-agp-toolbox` (read-only)

---

## Overview

`rmigis-agp-toolbox` is an ArcGIS Pro Python Toolbox (`rmigis_agp_toolbox.pyt`) that automates GIS schema creation, domain synchronization, feature service publishing, and enterprise geodatabase (EGDB) operations for RMI Valuation workflows. It applies YAML-defined schemas (feature classes, fields, domains, and topology) to PostgreSQL/EGDB backends and publishes them to ArcGIS Enterprise Portal.

**Repository structure** (~/sources/rmigis-agp-toolbox/):
- `rmigis_agp_toolbox.pyt`: Toolbox entry point
- `tools/`: Tool implementations (23 tools across project setup, real property, track improvement, domains, publishing, services)
- `utils/`: Shared orchestration, schema/domain I/O, publishing, service auditing, topology
- `config/settings.yaml`: Configuration defaults and paths
- `templates/`: YAML schemas for three domains: real property, track improvement, building & site
- `layers/`: `.lyrx` layer files for symbology and map authoring
- `lookup/`: Reference data (county spatial reference index)
- `maintenance/`: Validation and schema maintenance scripts
- `YAML_TOOLBOX_MIGRATION_PLAN.md`: Future modernization roadmap (arcgispro-yaml-pyt framework)
- `EGDB_UPDATE_WORKFLOW.md`, `TRACK_IMPR_TOPOLOGY_*`: Implementation guides

---

## YAML Schema Structure

### Schema Organization: Directory-Based with Shared Configuration

**Feature class definitions** are organized by domain in three `templates/` subdirectories:

#### 1. **Track Improvement** (`templates/track_impr/`)

21 feature classes + 1 lookup table, covering railroad corridor inventory:

**Feature Classes (point, line, polygon)**:
- `bungalow_pnt_fc` — Instrument House/Case Point (POINT)
- `signal_pnt_fc` — Signal Point (POINT)
- `turnout_pnt_fc` — Turnout Point (POINT)
- `turnout_cx_pnt_fc` — Turnout Complex Point (POINT)
- `diamond_pnt_fc` — Diamond Crossing Point (POINT)
- `derail_pnt_fc` — Derail Point (POINT)
- `milepost_pnt_fc` — Milepost Point (POINT)
- `xing_pnt_fc` — Grade Crossing Point (POINT)
- `xing_struct_tbl` — Crossing Structure Lookup (TABLE)
- `wayside_det_pnt_fc` — Wayside Detector Point (POINT)
- `wayside_det_ontrk_pnt_fc` — On-Track Detector Point (POINT)
- `wayside_det_offtrk_pnt_fc` — Off-Track Detector Point (POINT)
- `tank_pnt_fc` — Tank/Reservoir Point (POINT)
- `lub_pnt_fc` — Lubrication Point (POINT)
- `gen_pnt_fc` — Generator Point (POINT)
- `rail_insp_pnt_fc` — Rail Inspection Point (POINT)
- `track_centerline_fc` — Track Centerline (POLYLINE)
- `track_cl_parent_fc` — Track Centerline Parent (POLYLINE)
- `track_node_fc` — Track Node Point (POINT)
- `slide_fence_line_fc` — Slide Fence Line (POLYLINE)

**Shared configuration** (`_shared.yaml`):
- Version, author, last-updated metadata
- Pre/post-inspection style definitions
- Topology defaults (feature dataset suffix, topology suffix, cluster tolerance, validation settings)

**Per-FC YAML files** (e.g., `bungalow_pnt_fc.yaml`):
```yaml
base_name: bungalow_inv_pt           # Unqualified feature class name
alias: Instrument House/Case Point   # Portal display name
fc_type: POINT                       # POINT | POLYLINE | POLYGON
feat_group: track                    # Feature domain group
proj_desig: custom                   # custom | county (drives coordinate system)
proj_epsg: null                      # EPSG code or null (use default)
reg_vers_en_rep: true                # Register as versioned (EGDB)
create_flag: false                   # Initial creation flag
replace_flag: false                  # Replace existing flag
attr_rule_path: null                 # Path to attribute rule CSV (optional)
create_type: create                  # Literal ArcGIS GeoProcessing type
enable_attach: true                  # Enable attachments
display_field: asset_id              # Portal display field
lyrx: bungalow_inv_pt.lyrx          # Pre/post-insp symbology file
styles:
  pre_insp: bungalow_inv_pt.lyrx     # Pre-inspection style layer
  post_insp: bungalow_inv_pt.lyrx    # Post-inspection style layer
publish:
  capabilities:
    allow_editing: true              # Feature service is editable
    allow_extract: true              # Download/export allowed
    enable_sync: false               # Offline sync disabled
  instance:
    type: shared                     # shared | dedicated
    min: null                        # Min pooled instances
    max: null                        # Max pooled instances
topology:                            # (See topology rules section below)
  include: false
  rank: null
  rules: []
fields_order:                        # 81 fields in order (see fields section)
- OBJECTID
- Shape
- GlobalID
- asset_id
- ... (77 more field names, see fields section)
```

**Field catalog** (`trk_impr_field_catalog.yaml`, ~2,600 lines):

- **Templates** section: Reusable field definitions
  - `id_base`: TEXT(12), nullable — for asset identifiers
  - `yes_no_base`: SHORT, nullable, domain `rmi_trk_yes_no` — binary fields
  - `mp_base`: DOUBLE, nullable — milepost measurements
  - `cond_base`: SHORT, nullable, domain `rmi_trk_rating` — condition fields
  - `year_base`: SHORT, nullable, domain `rmi_trk_year` — year of manufacture
  - `name_base`: TEXT(50), nullable — free text
  - `trk_type_base`: TEXT(6), domain `rmi_trk_type` — track classification
  - `rail_wgt_base`: TEXT(5), domain `rmi_trk_weight` — rail weight (pounds)
  - `frog_size_base`: TEXT(5), domain `rmi_trk_frog_sz` — turnout frog size
  - `mfr_base`: TEXT(50) — manufacturer name
  - (and 13 more specialized templates)

- **Fields** section: 400+ named field definitions, inheritable from templates
  - Inheritance pattern: `inherit: year_base` + optional overrides (alias, domain, etc.)
  - System fields: OBJECTID, Shape, Shape_Length, GlobalID
  - Location fields: asset_id, asset_name, rr_fac_num, mp_pre, mp_rr, mp_meas, location, section, lat, long
  - Relationship fields: rel_sig_loc_id, rel_parent_trk_id, rel_bglw_id, etc. (foreign keys to other FCs)
  - Status fields: status (ACTIVE|OOS|RETIRED|REMOVED), include (Y/N)
  - Inspection fields: inspected, insp_datetime, insp_order, insp_label, insp_day, notes_pre_insp, notes_insp, notes_post_insp
  - Flexible attributes: flex_attr1..5 (free text columns for schema-less data)
  - Editor tracking: created_user, created_date, last_edited_user, last_edited_date
  - Schema version: schema_version (default = 1.0.0, for TIVS/CTVS compatibility)

**Domains** (`trk_impr_domains.yaml`, ~500 lines):

27 coded-value and range domains used across Track Improvement FCs:

- **Coded-value domains** (list of [code, label] pairs):
  - `rmi_trk_yes_no`: [0, 'No'], [1, 'Yes']
  - `rmi_trk_rating`: [0, Failed], [1, Poor], [2, Fair], [3, Good], [4, Excellent], [5, New]
  - `rmi_trk_type`: MAIN, SIDING, YARD, IND, XOVER, OTHER, LADDER, MOW, LEAD, CONN, WYE, LAPINT
  - `rmi_trk_weight`: 67, 75, 80, 85, 90, 100, 112, 115, 119, 132, 133, 136, 140, 141, OTHER (rail weight in pounds)
  - `rmi_trk_frog_sz`: 4, 5, 6, 7, 8, 8.5, 9, 10, 11, 12, 14, 15, 16, 18, 20, 24, 30, OTHER
  - `rmi_trk_dens_cl`: [1, Main Track], [2, Secondary/Industry], [4, Yard Track]
  - `rmi_trk_status`: ACTIVE, OOS, RETIRED, REMOVED, NOTEXIST, OTHER
  - `rmi_trk_conn_type`: N (Normal), D (Diverging), C (Converging), I (Diamond), X (End), O (Other)
  - `rmi_trk_jw`: JNT (Jointed), WLD (Welded)
  - `rmi_trk_surface_type`: BALLAST, BR_DECK, SLB_TRK, EARTH, OTHER
  - `rmi_trk_ballast_profile`: S (Single), D (Double), M_IN (Multi-Inner), M_OUT (Multi-Outer)
  - `rmi_trk_tie_type`: WOOD, CONC, STEEL, COMP
  - `rmi_trk_ts_type`: S (Surfacing), T (Timber), TS (Both)
  - `rmi_trk_to_type`: SIDING, YARD, IND, XOVER, DXOVER, SSLIP, DSLIP, WYE, SWPDERAIL, LADDER, MOW, LEAD, CONN, OTHER (turnout types)
  - `rmi_trk_dir`: LEFT, RIGHT, EQUAL
  - `rmi_trk_frog_type`: SSGM, RBM, JUMP, RBW, WBM, SPRING, MPF, BRF, SMCF2, OTHER
  - `rmi_trk_stand_type`: HAND, POWER, DUAL
  - `rmi_trk_drl_type`: SLD (Slide), HNG (Hinged), SWP (Switch Point), OTH (Other)
  - `rmi_trk_lub_face`: GFL (Flange), TOR (Top of Rail), UNK (Unknown)
  - `rmi_trk_lub_pwr_type`: E (Electric), H (Hydraulic), M (Mechanical), S (Solar), U (Unknown)
  - `rmi_trk_tank_size`: 120g_v, 120g_h, 250g, 325g, 500g, 1000g, 1450g, 1990g (tank capacities)
  - `rmi_trk_tank_use`: SW_HTR (Switch Heater), GEN (Generator), OTH (Other)
  - `rmi_trk_gen_fuel`: NG, PG, DS, GAS, OTH
  - `rmi_trk_gen_use`: SIG, XING, SW_HTR, COMMS, OTHER
  - `rmi_trk_gen_size_unit`: kW, kVA, HP, OTH, UNK
  - `rmi_trk_gen_size_source`: NP (Nameplate), DOC, INT, EST, OTH, UNK
  - `rmi_trk_dd_type`: 12 dragging equipment/detector types (DED, HBD, HWD, XDCR, ABD_TADS, ABD_BAM, ACMW, TBOGI, THD, TPD, WIM, WILD, WPMS, WTD, OTHER)
  - `rmi_trk_sig_inst_side`: LEFT, RIGHT, BOTH
  - `rmi_trk_diamond_frog_type`: SSGM, RBM, JUMP, RBW, WBM, SPRING, OTHER (+ 2 additional)
  - (and others for specific asset types)

- **Range domains** (min-max constraints):
  - `rmi_trk_year`: [1880, 2030] — valid manufacture year

#### 2. **Real Property** (`templates/real_prop/`)

11 feature classes, supporting parcel, sale, improvement, and CoreLogic processing:

**Feature Classes**:
- `parcel_fc` — Corelogic Parcels (POLYGON), 120+ fields
- `sale_fc` — Sale Comparables (POLYGON)
- `subjectinsp_fc` — Subject Property Inspection (POINT)
- `subjectcl_fc` — Subject Centerline (POLYLINE)
- `subjectseg_fc` — Subject Segment (POLYGON)
- `subjectseg_line_fc` — Subject Segment Line (POLYLINE)
- `subjectlu_fc` — Subject Land Use (POLYGON)
- `subjectbuffer_fc` — Subject Buffer (POLYGON)
- `compinsp_fc` — Comparable Inspection (POINT)
- `costarexp_fc` — CoStar Export Load Table (TABLE)

**Field catalog** (`real_prop_field_catalog.yaml`, ~1,200 lines):
- Parcel identifiers: apn, apn2, frm_apn, legal1-3, township, range, section, etc.
- Sale metadata: sale_dt, deed_date, sell_name, owner names, grantor, grantee, doc_typ
- Property details: addr, city, county, zoning, zoning_juris, land_use, prop_ind, rmi_use
- Sale analysis: sale_query (computed field), sale_notes, sale_m_acres, sale_price, deed_tax, sale_pr_acre, sale_status, sale_substatus
- Verification: vrfd_acres, vrfd_sqft, vrfd_size_source, verified_by
- Coordinates: lat_ctr, long_ctr
- Assessment values: assd_val, assd_lan, assd_imp, mkt_val, appr_val
- Custom flexible fields: custom1-5 (TEXT(100), nullable)

**Domains** (`real_prop_domains.yaml`, ~500 lines):
- `rmi_prop_doc_typ`: WARRANTY DEED, QUIT CLAIM, etc.
- `rmi_prop_zoning`: Zoning type codes
- `rmi_prop_land_use`: Land use classifications
- `rmi_prop_sale_status`: ACCEPTED, REJECTED, PENDING, COMPLETED, etc.

#### 3. **Building & Site Improvement** (`templates/bldg_site/`)

3 feature classes for on-site asset inventory:

**Feature Classes**:
- `site_asset_pnt_fc` — Site Asset Point (POINT, 50+ fields)
- `site_asset_line_fc` — Site Asset Line (POLYLINE, 50+ fields)
- `site_asset_poly_fc` — Site Asset Polygon (POLYGON, 50+ fields)

All three share similar structure: asset_id, asset_type, material, condition, dimensions, inspection fields, notes, editor tracking, etc.

**Field catalog** (`bldg_site_field_catalog.yaml`, ~800 lines):
- Asset identification: asset_id, asset_name, asset_type
- Physical properties: material, color, condition, age, dimensions (height, width, depth)
- Condition assessment: overall_condition, cond_structural, cond_functional, cond_aesthetic
- Inspection: inspected, insp_datetime, insp_notes, insp_photos
- Editor tracking and flexible attributes

---

## Topology Implementation

**Status**: **SUSPENDED** (pending ArcGIS Pro compatibility resolution)

Track Improvement topologies are planned but currently disabled. Implementation code and design are preserved for future re-enablement.

### Design: Per-FC YAML Topology Metadata

Each feature class YAML includes a `topology` block:

```yaml
topology:
  include: true|false      # Include in topology membership
  rank: <int|null>         # XY rank (1 = highest authority); null = auto
  rules:
    - type: Must Not Have Dangles         # ArcGIS topology rule name
      target: null                        # null for single-class rules
      notes: "optional explanation"       # ignored by execution
    - type: Must Be Covered By
      target: track_centerline_fc         # target FC key for two-class rules
```

### Topology Datasets and Naming

From `templates/track_impr/_shared.yaml`:
```yaml
topology_defaults:
  feature_dataset_suffix: track_impr_fd          # name suffix
  topology_suffix: track_topology                # name suffix
  cluster_tolerance: null                        # ArcGIS auto-default
  member_source_mode: create_in_fd               # create directly in FD
  validate_on_create: true                       # validation on schema creation
  publish_error_layers: false                    # publish validation error layers
```

**Naming** (deterministic, project-scoped):
- Feature Dataset: `<proj_num>_track_impr_fd` (e.g., `25-100_track_impr_fd`)
- Topology: `<proj_num>_track_topology` (e.g., `25-100_track_topology`)

### Rank Assignment (Confirmed Baseline)

- **Rank 1** (authoritative): `track_cl_parent_fc`, `turnout_pnt_fc`, `turnout_cx_pnt_fc`, `diamond_pnt_fc`
- **Rank 2**: `track_centerline_fc`
- **Rank 3**: `track_node_fc`
- **Rank 4** (refinement): `derail_pnt_fc`, `lub_pnt_fc`, `milepost_pnt_fc`, `xing_pnt_fc`, `wayside_det_ontrk_pnt_fc`

Rank 1 members intentionally share the highest rank; conflicts among them are manual-review errors, not auto-correctable drift.

### Baseline Topology Rules (Not Yet Implemented)

```yaml
track_cl_parent_fc:
  - type: Must Not Self-Overlap
    target: null
  - type: Must Not Self-Intersect
    target: null

track_centerline_fc:
  - type: Must Be Covered By
    target: track_cl_parent_fc
  - type: Must Not Have Dangles
    target: null
```

**Suspended tools** in `tools/`:
- `create_track_impr_topo_tool.py` — Create topology-aware Track Improvement FCs
- `create_track_impr_existing_topology_tool.py` — Attach to existing topologies
- `publish_topology_feature_service_tool.py` — Publish topology-enabled services

**Implementation guide**: `TRACK_IMPR_TOPOLOGY_IMPLEMENTATION_PLAN.md`

---

## Survey123 Forms

**Finding**: No Survey123 form definitions found in the repository.

- No `.json`, `.xlsx`, `.form`, or `*.survey123` files present.
- No references to Survey123 integration in the toolbox code.
- **Note**: MISSION.md mentions "virtual inspection through Survey123" in the CIV module context, but Survey123 is integrated in rmi-platform (the main app), not in rmigis-agp-toolbox.

**Related MISSION context** (rmi-platform/CIV): 360° panoramas are inspected via Survey123 forms linked to the Oriented Imagery Dataset (OID), managed at the platform level, not in the GIS toolbox.

---

## How the Toolbox Applies Schemas

### 1. **Schema Loading** (`utils/schema_yaml.py`)

Two modes:
- **Directory-based** (current): Load `_shared.yaml` + individual FC `*.yaml` files from a directory (e.g., `templates/track_impr/`)
- **Legacy single-file** (supported for backward compatibility): Load all FCs from one consolidated YAML

**Loader logic**:
1. If path is a directory: Load `_shared.yaml` (version, author, styles), then all `*.yaml` files (each becomes one FC)
2. If path is a file: Load single consolidated YAML
3. Merge with field catalog (`field_catalog.yaml`): Resolve field templates and inheritance
4. Return `fc_props` dict (FC metadata) and `fields_by_fc` dict (ordered field definitions per FC)

**Field resolution**:
- Templates (reusable base definitions): `templates: { id_base: {...}, year_base: {...}, ... }`
- Fields (full definitions, can inherit): `fields: { asset_id: { inherit: id_base, alias: "Asset ID" }, ... }`
- Inheritance chain: merge left-to-right through `inherit` list, then overlay inline properties
- Canonicalization: Normalize type spellings (STRING → TEXT, INTEGER → LONG, etc.)

**Validation output**:
- Per-FC `_validation` block: errors (null entries, unknown names, unresolved fields, duplicates) and warnings
- Raises exception if schema is invalid

### 2. **Feature Class Creation** (`utils/fc_builder.py` + `tools/create_track_impr_tool.py`)

**Orchestration pipeline** (`utils/fc_orchestrator.py`):

1. **Load schema bundle**: FC definitions + field catalog
2. **Prepare domains**: Validate domains against field usage; import into staging FGDB
3. **Plan actions**: Compute which FCs to create/replace, where (FGDB, EGDB, both)
4. **Stage 1 - Create in FGDB**: `arcpy.CreateFeatureclass()` + add fields + assign domains
5. **Stage 2 - Domain-specific processing** (Real Property only): Load CoreLogic parcels, recalculate sale_query computed field
6. **Stage 3 - Copy to EGDB**: `arcpy.Copy_management()` + set editor tracking + set editor group permissions
7. **Stage 4 - Cleanup**: Delete staging FGDB (optional)

**Field application**:
- Iterate `fields_by_fc[fc_key]` in order
- For each field: `arcpy.AddField(fc, name, type, length, domain=domain_name, ...)`
- Editor-tracking fields (created_user, created_date, etc.) are set via `arcpy.EnableEditorTracking()`
- Attachments: `arcpy.EnableAttachments()` if `enable_attach: true`
- Geometry type and spatial reference set during FC creation

**Spatial reference resolution**:
- `proj_desig: custom` → use tool parameter `custom_cs` (user specifies in UI)
- `proj_desig: county` → look up in `lookup/county_sr_index.yaml` by county FIPS code
- `proj_epsg` (if present) → override with explicit EPSG code

**Configuration reference**: `config/settings.yaml`
```yaml
schemas:
  trk_impr_fc_def: ${paths.templates}/track_impr       # directory of FC YAMLs
  trk_impr_field_catalog: ${paths.templates}/trk_impr_field_catalog.yaml
  trk_impr_domains: ${paths.templates}/trk_impr_domains.yaml
  real_prop_fc_def: ${paths.templates}/real_prop
  real_prop_field_catalog: ${paths.templates}/real_prop_field_catalog.yaml
  real_prop_domains: ${paths.templates}/real_prop_domains.yaml
  bldg_site_fc_def: ${paths.templates}/bldg_site
  bldg_site_field_catalog: ${paths.templates}/bldg_site_field_catalog.yaml
  bldg_site_domains: ${paths.templates}/bldg_site_domains.yaml
```

### 3. **Domain Synchronization** (`utils/domains_io.py` + `tools/sync_domains_tool.py`)

**Workflow**:
1. Load domains YAML
2. Inspect target geodatabase for existing domains
3. Compare: new, modified, unchanged
4. Plan: additive by default (add new, update labels, keep existing codes)
5. Execute (or dry-run): `arcpy.CreateDomain()`, `arcpy.AddCodedValue()`, `arcpy.AssignDomainToField()`

**Conservative by design**:
- Never deletes coded values unless explicitly enabled (`--allow-remove-missing`)
- Never changes field type (additive only)
- Dry-run mode reports differences without modifying GDB

### 4. **Publishing and Service Auditing** (`utils/publish_util.py`, `utils/service_audit.py`)

**Publishing workflow** (`tools/publish_feature_services_tool.py`):
1. Apply `.lyrx` symbology layers to map (via `CreateMap` tool)
2. Create `map.aprx` with selected FCs
3. Publish to Portal: `arcgis.gis.GIS.content.publish()`
4. Set capabilities (allow_editing, allow_extract, enable_sync)
5. Update sharing (Portal folder, owner groups)

**Service auditing** (`tools/audit_track_impr_services_tool.py`):
- Read feature service REST JSON from Portal
- Compare against YAML schema definitions and field catalog
- Report differences by severity: error (schema mismatch), warning (property mismatch), info (metadata mismatch)
- Handle field name normalization (EGDB services may expose lowercased names; comparison is case-insensitive)
- Validate domain assignments and coded value consistency
- Output: CSV or markdown report

### 5. **Apply Missing Schema Fields** (`tools/apply_schema_fields_tool.py`)

**In-place schema evolution** (without rebuild/migrate):
1. Load target FC schema from geodatabase
2. Compare against YAML definitions
3. Plan: missing fields (add), extra fields (drop if enabled), type mismatches (warn, skip)
4. Backup existing data (optional, on by default)
5. Stop feature services backing the dataset (if EGDB)
6. Execute: `arcpy.AddField()` for new fields, `arcpy.DeleteField()` for retired fields (if enabled)
7. Sync domain values (add/update, not remove by default)
8. Restart services
9. (User must separately republish to update service definition)

---

## Field Naming and Constraints

### Naming Conventions

**Case**: lower_snake_case (e.g., `tie_spacing_ft`)  
**Length**: Under 64 characters for compatibility with ArcGIS text field limits

**Common suffixes**:
- `_ft`: feet (distance)
- `_mi`: miles
- `_acres`: area in acres
- `_sqft`: area in square feet
- `_cnt`: count
- `_dt`: date
- `_year`: year
- `_cond`: condition rating
- `_id`: identifier or foreign key
- `_pnt_fc`, `_line_fc`, `_poly_fc`: relationship references to other feature classes

### Reserved Names (Avoided)

ArcGIS system fields (auto-managed):
- OBJECTID, GlobalID, Shape, Shape_Length, Shape_Area
- created_user, created_date, last_edited_user, last_edited_date (editor tracking)

### Domains and Constraints

**Domain types**:
- **Coded value**: Discrete list of [code, label] pairs (enums)
- **Range**: Min-max bounds for numeric fields

**Assignment**: Via field catalog field definition
```yaml
asset_id:
  name: asset_id
  type: TEXT
  length: 12
  domain: rmi_trk_asset_id_domain    # (if domain existed)
  nullable: true
```

**Constraint enforcement**:
- Not enforced by the toolbox at creation time (domains are imported but geodatabase validation rules manage it)
- Service-level constraints via feature service capabilities (editability, attachment rules, etc.)

---

## Related Tables and Relationships

**Relationship classes** (defined in FC YAML, preserved for post-create assembly):

```yaml
relationships:
  - name: rel_bglw_to_sig_mount      # relationship name
    target_fc: signal_pnt_fc          # related table
    origin_pkey: GlobalID
    origin_fkey: rel_sig_id
    cardinality: "1:M"                # one-to-many
    composed: false
```

**Implementation**: Not yet wired in current tools; framework in place (`fc_orchestrator.py` preserves metadata).

**Related tables** (transitive dependencies):

```yaml
related_tables:
  - xing_struct_tbl                  # auto-include when creating xing_pnt_fc
```

When a parent FC is selected for creation, dependent tables are auto-included in the runbook.

---

## Project Setup and Workspace Configuration

### Create Project Tool

**Input parameters**:
- Project number (e.g., `25-100`)
- Database server, database name
- SDE/RDO connection toggles
- EGDB enablement toggle (requires keycode file)
- Portal group creation toggle
- Datastore registration toggle

**Outputs**:
- PostgreSQL database with `{proj_num}_*` schema
- `.sde` connection files (SDE and RDO)
- ArcGIS Enterprise geodatabase workspace
- Portal group for project (`{proj_num}`)
- Datastore registration (if enabled)

**Workspaces**:
- **Staging FGDB**: Temporary workspace for feature class creation (automatically created)
- **Production EGDB**: Enterprise geodatabase, persisted for service publishing

---

## Configuration and Customization

### config/settings.yaml

**Paths**:
```yaml
paths:
  templates: E:/DevProjects/rmigis-agp-toolbox/templates
  lookup: E:/DevProjects/rmigis-agp-toolbox/lookup
  layers: E:/DevProjects/rmigis-agp-toolbox/layers
```

**Defaults**:
```yaml
defaults:
  database_server: rmi-aurora-pgsql-01.clviyz7iqqkm.us-east-1.rds.amazonaws.com
  keyring_service: rmigis_agp_toolbox
  db_admin_user: rmidbadmin
  sde_user: sde
  rdo_user: rmidataowner
```

**Schemas**:
```yaml
schemas:
  trk_impr_fc_def: ${paths.templates}/track_impr
  trk_impr_field_catalog: ${paths.templates}/trk_impr_field_catalog.yaml
  trk_impr_domains: ${paths.templates}/trk_impr_domains.yaml
  real_prop_fc_def: ${paths.templates}/real_prop
  real_prop_field_catalog: ${paths.templates}/real_prop_field_catalog.yaml
  real_prop_domains: ${paths.templates}/real_prop_domains.yaml
  bldg_site_fc_def: ${paths.templates}/bldg_site
  bldg_site_field_catalog: ${paths.templates}/bldg_site_field_catalog.yaml
  bldg_site_domains: ${paths.templates}/bldg_site_domains.yaml
```

**Portal and ArcGIS Server**:
```yaml
arcgis:
  portal_url: https://maps.rmigis.cloud/portal
  server_url: https://maps.rmigis.cloud/arcgis
  services_user: camrex
  default_grp_members:
    - cwrexiv
    - cwrexiii
```

### Environment Overrides

Two mechanisms:
1. **Environment variable** `RMI_TOOLBOX_SETTINGS`: Path to alternate `settings.yaml`
2. **Environment variable** `RMI_TOOLBOX_OVERRIDES`: JSON string merged into loaded config

---

## Known Schema Issues and Maintenance

### Current Gaps (from EGDB_UPDATE_WORKFLOW.md, Phase 0)

**High-risk update** (`xing_inv_pt`):
- 13 fields removed (embedded bungalow details migrating to `bungalow_inv_pt`)
- Data loss risk if existing crossing records have populated bungalow columns
- Mitigation: Export data before update, or migrate to relationship class

**Field additions/renames** (recent commits):
- `track_cl_inv`: 3 new fields, 1 renamed (tie spacing units)
- `rail_inv_pt`: 3 new fields, 1 renamed (tie spacing units)
- `turnout_inv_pt`: 4 new fields (removal tracking + point type)
- `bungalow_inv_pt`: 1 new field (shared flag)

**Domain changes**:
- New: `rmi_trk_rail_grade` (8 codes), `rmi_trk_pnt_type` (10 codes)
- Modified: `rmi_trk_bglw_use` (+1), `rmi_trk_bglw_size` (+4), `rmi_trk_xing_config` (+1)

### Maintenance Scripts

**In** `maintenance/`:
- `split_fc_definitions.py`: Split/reshape FC definitions
- `test_schema_loader.py`: Validate schema loader against config
- `test_fc_base_name.py`: Validate FC naming expectations
- `test_service_audit.py`: Exercise service diff engine (no arcpy needed)
- `test_schema_sync.py`: Exercise field-sync planner (stubbed workspace, no GDB needed)

Run from project root using ArcGIS Pro Python environment when applicable.

---

## Tools and Workflows

### Tool Categories

**Project Setup**:
- Create Project Tool
- Project County/Zone Identification
- Set DB Passwords Tool

**Feature Class Creation**:
- Create Real Property Feature Classes
- Create Track Improvement Feature Classes
- Create Building & Site Improvement Feature Classes
- Load CoStar Export
- Recalculate Sale Query

**Domains & Fields**:
- Export Domains
- Import Domains
- Sync Domains to Geodatabase
- Apply Missing Schema Fields
- Generate Field Definitions

**Data Management**:
- Backup EGDB to FGDB
- Load Track Improvement FCs to EGDB

**Map Authoring & Publishing**:
- Create Map
- Publish Feature Services

**Services Management**:
- Manage RMI GIS Services (start/stop ArcGIS Server services)

**Auditing**:
- Audit Track Improvement Feature Services (read-only schema comparison)

### EGDB Update Workflow

**Recommended phased approach** (see EGDB_UPDATE_WORKFLOW.md):

1. **Backup**: `Backup EGDB to FGDB` → timestamped FGDB + domains YAML + manifest
2. **Dry-run domain sync**: `Sync Domains to Geodatabase` with `Dry Run: TRUE`
3. **Apply domains**: Re-run with `Dry Run: FALSE`
4. **Pilot load**: Load 1-2 FCs from FGDB to EGDB
5. **Full rollout**: Load remaining FCs
6. **Audit**: `Audit Track Improvement Feature Services` to verify

---

## Future Work

### Migration to arcgispro-yaml-pyt Framework

**Status**: Planning (documented in `YAML_TOOLBOX_MIGRATION_PLAN.md`)

**Goals**:
- Decouple tool logic from parameter definitions
- YAML-based tool configurations (not Python)
- Automated unit tests (mocked arcpy)
- Improved maintainability and developer ergonomics

**Proposed structure** (rmigis-yaml-toolbox):
```
rmigis-yaml-toolbox/
├── tools/
│   ├── ProjectIdentification/
│   │   ├── tool.yaml           # Tool parameters (YAML)
│   │   ├── tool.py             # Logic only
│   │   └── test_tool.py        # Unit tests
│   ├── CreateProjectTool/
│   │   └── ...
│   └── ...
├── utils/                       # Shared (from current repo)
├── config/                      # Configuration (from current repo)
├── templates/                   # Schemas (from current repo)
├── rmigis_yaml_toolbox.pyt     # Generated entry point
└── generate_toolbox.py          # Build script
```

---

## File Paths Summary

| What | Path |
|---|---|
| Toolbox entry point | `rmigis_agp_toolbox.pyt` |
| Tools | `tools/*.py` (23 files) |
| Utilities | `utils/*.py` (27 files) |
| Track Improvement schema | `templates/track_impr/` (21 FC YAML + shared) |
| Real Property schema | `templates/real_prop/` (11 FC YAML + shared) |
| Building & Site schema | `templates/bldg_site/` (3 FC YAML + shared) |
| Field catalogs | `templates/*_field_catalog.yaml` (3 files) |
| Domain definitions | `templates/*_domains.yaml` (3 files) |
| Configuration | `config/settings.yaml` |
| Layer files (symbology) | `layers/` |
| Reference data | `lookup/county_sr_index.yaml` |
| Maintenance scripts | `maintenance/*.py` (5 scripts) |
| Topology design | `TRACK_IMPR_TOPOLOGY_IMPLEMENTATION_PLAN.md` |
| EGDB update guide | `EGDB_UPDATE_WORKFLOW.md` |
| Migration plan | `YAML_TOOLBOX_MIGRATION_PLAN.md` |
| README | `README.md` |

---

## Summary

`rmigis-agp-toolbox` is a mature, YAML-driven ArcGIS Pro Python Toolbox that:

1. **Defines schemas declaratively** in YAML: feature classes, fields (with template inheritance), domains, and topology rules
2. **Organizes schemas by domain**: Track Improvement (21 FCs, 400+ fields), Real Property (11 FCs), Building & Site (3 FCs)
3. **Applies schemas programmatically**: Loads YAML, validates, creates FCs in FGDB, synchronizes domains, copies to EGDB, publishes services
4. **Supports lifecycle operations**: Backup, domain sync, field updates, service auditing, all with safe defaults (additive, dry-run capable)
5. **Integrates with enterprise GIS**: ArcGIS Enterprise Portal, PostgreSQL, branch-versioned EGDB, feature services
6. **Preserves unimplemented work**: Topology framework is complete but disabled pending ArcGIS Pro compatibility fixes

**No Survey123 forms** are defined in the toolbox; they live in rmi-platform (the main application) and link to the OID.

**Next work** (per YAML_TOOLBOX_MIGRATION_PLAN.md): Modernize to arcgispro-yaml-pyt framework for better testability and maintainability.
