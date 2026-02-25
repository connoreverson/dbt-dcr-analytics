The purpose of this document is to establish what "done" looks like for any file or folder in the dbt project — so that analysts can evaluate their own work before it reaches review, and so that reviewers can assess completeness against a shared standard rather than individual preference. Each section is organized by the type of work it governs; the rules within each section are specific enough to act on, but leave room for the professional judgment of the analyst where the situation warrants it.

## **Cross-Model Standards**

These standards apply to all SQL models across all layers.

### **DAG Direction and Layer Dependencies**

#### **Rule: ALL-DAG-01 Unidirectional Dependency Flow**

Dependencies must flow in one direction: sources → staging (and base) → integration → marts (facts, dimensions, reports). Models must never reference a downstream layer and must never skip a layer; a staging model cannot reference an integration model, and a fact model cannot reference a staging model directly.

#### **Rule: ALL-DAG-02 No Circular Dependencies**

No model may create a dependency that forms a cycle in the DAG. If dbt raises a circular dependency error, restructure the models so that shared logic is extracted into a model at an earlier layer or into a macro.

### **Project Configuration**

#### **Rule: ALL-CFG-01 Centralize Configs in dbt\_project.yml**

Model configurations — including materialization, schema routing, and tags — must be set as layer-wide defaults in dbt\_project.yml. Per-model {{ config() }} blocks in SQL files should only be used for individual exceptions to the project-level defaults.

#### **Rule: ALL-CFG-02 Config Block Placement**

When a per-model {{ config() }} block is needed, it must be the first statement in the SQL file, before any CTEs or SQL logic.

#### **Rule: ALL-CFG-03 Package Version Pinning**

All packages declared in packages.yml must specify a version or version range; unpinned packages introduce a risk that upstream changes could break the project without warning.

### **Naming Conventions**

#### **Rule: ALL-NAME-01 File Name Prefixes**

SQL files must be prefixed with 'stg', 'base', 'int', 'fct', 'dim', or 'rpt' according to their layer. YAML property files must have a leading underscore (e.g., '\_models.yml', '\_sources.yml').

#### **Rule: ALL-NAME-02 Plural Phrasing**

File names must use plural phrasing: 'stg\_salesforce\_\_accounts' (not the singular 'account'), 'int\_projects' (not 'project').

#### **Rule: ALL-NAME-03 Abbreviation Restraint**

Do not abbreviate words or phrases that are fewer than 20 characters long. The gain in brevity is offset by the loss of intuitiveness; 'activity\_id' should not become 'actv\_id'. Conversely, abbreviate names that would otherwise be excessively long; 'int\_delivery\_framework\_\_integrated\_disbursement\_and\_information\_system.sql' should become 'int\_delivery\_framework\_\_idis.sql'.

#### **Rule: ALL-NAME-04 Business Concept Phrasing**

File names must represent business concepts rather than business system names. Prefer 'stg\_salesforce\_\_accounts' over 'stg\_salesforce\_\_account\_\_c' if the source system uses unintuitive internal naming.

### **SQL Formatting**

#### **Rule: ALL-FMT-01 File Length**

Models should generally stay under 200 lines. Deviations are acceptable when necessary, but a model that grows substantially beyond this guideline warrants a closer look at whether its logic could be broken into upstream models or macros.

#### **Rule: ALL-FMT-02 Line Length**

Each line should be fewer than 80 characters.

#### **Rule: ALL-FMT-03 Lowercase Keywords**

All SQL keywords must be lowercase: 'select \* from requests', not 'SELECT \* FROM requests'.

#### **Rule: ALL-FMT-04 Lowercase Function Names**

All function names must be lowercase: 'sum(amount)', not 'SUM(amount)'.

#### **Rule: ALL-FMT-05 Snake Case Field Names**

All field names must be snake\_case and lowercase: 'request\_id', not 'Request\_id', 'request-id', 'requestId', 'RequestId', 'requestid', or '\`request id\`'.

#### **Rule: ALL-FMT-06 Predicate Indentation**

Where and when clause predicates must be indented on new lines for readability.

```sql
-- ✅ Good
select *
from requests
where
    status = 'active'
    and created_at >= '2024-01-01'
    and amount > 0

-- ❌ Bad
select *
from requests
where status = 'active' and created_at >= '2024-01-01' and amount > 0
```

#### **Rule: ALL-FMT-07 Table Aliasing**

When joining tables and referencing columns from both, follow this order of preference: first, reference the full table name instead of an alias when the table name is short (roughly fewer than 20 characters); second, rename the CTE to a shorter phrase if possible; lastly, alias to something descriptive. Do not alias tables with single-letter variables (such as 'a' and 'b') or unintuitive abbreviations (such as 'rq' instead of 'requests' or 'df' instead of 'delivery\_frameworks').

```sql
-- ✅ Good: use full CTE name when short
select
    requests.request_id,
    requests.amount,
    statuses.status_label
from requests
left join statuses
    on requests.status_id = statuses.status_id

-- ✅ Good: descriptive alias when name is long
select
    apps.application_id,
    apps.submitted_at,
    reviewers.reviewer_name
from grant_applications as apps
left join application_reviewers as reviewers
    on apps.application_id = reviewers.application_id

-- ❌ Bad: single-letter aliases
select
    a.application_id,
    a.submitted_at,
    b.reviewer_name
from grant_applications a
left join application_reviewers b
    on a.application_id = b.application_id
```

### **CTE Standards**

#### **Rule: ALL-CTE-01 Import CTEs at Top**

All {{ ref() }} and {{ source() }} statements must be isolated in import CTEs at the top of the model.

```sql
-- ✅ Good
with

payments as (
    select * from {{ ref('stg_stripe__payments') }}
),

orders as (
    select * from {{ ref('stg_shopify__orders') }}
),

payments_joined_to_orders as (
    select
        payments.payment_id,
        payments.amount,
        orders.order_date
    from payments
    left join orders
        on payments.order_id = orders.order_id
)

select * from payments_joined_to_orders

-- ❌ Bad: ref() buried in transformation logic
with

payments_joined_to_orders as (
    select
        payments.payment_id,
        payments.amount,
        orders.order_date
    from {{ ref('stg_stripe__payments') }} as payments
    left join {{ ref('stg_shopify__orders') }} as orders
        on payments.order_id = orders.order_id
)

select * from payments_joined_to_orders
```

#### **Rule: ALL-CTE-02 Explicit Joins with Aliases**

All joins must be explicit (e.g., 'left join', 'inner join') and all joined columns must be prefixed with a CTE or table alias.

#### **Rule: ALL-CTE-03 Meaningful CTE Names**

CTE names must be meaningful and succinct: import CTEs should include the object being imported (e.g., 'grant\_applications', 'payments', 'budget\_lines'); simple transformation CTEs should include the object and a verb (e.g., 'payments\_to\_fund\_grain', 'asset\_id\_added\_to\_payments'); complex transformations should have the subject, object, and verb (e.g., 'payments\_joined\_to\_budgets').

#### **Rule: ALL-CTE-04 No Duplicative CTEs Across Models**

If the same CTE logic appears in more than one model, reconstruct it into a dedicated upstream model or a macro.

#### **Rule: ALL-CTE-05 Single Unit of Work**

Each CTE must perform a single unit of work. Joining requests to users is acceptable as one step; joining requests to users and counting them by user in the same CTE is not.

```sql
-- ✅ Good: each CTE does one thing
requests_joined_to_users as (
    select
        requests.request_id,
        requests.amount,
        users.user_name
    from requests
    left join users
        on requests.user_id = users.user_id
),

requests_counted_by_user as (
    select
        user_name,
        count(*) as request_count,
        sum(amount) as total_amount
    from requests_joined_to_users
    group by user_name
)

-- ❌ Bad: join and aggregation in one CTE
requests_by_user as (
    select
        users.user_name,
        count(*) as request_count,
        sum(requests.amount) as total_amount
    from requests
    left join users
        on requests.user_id = users.user_id
    group by users.user_name
)
```

#### **Rule: ALL-CTE-06 Comment Confusing CTEs**

CTEs with non-obvious logic must have a comment above them explaining their purpose.

#### **Rule: ALL-CTE-07 Primary Key First**

In transformation CTEs and the final select, the primary key or object identifier must be the first selected field (renamed if appropriate). Import CTEs that simply select from a ref or source are exempt from this rule.

```sql
-- ✅ Good: PK is the first field
payments_enriched as (
    select
        payments.payment_id,
        payments.amount,
        orders.order_date
    from payments
    left join orders
        on payments.order_id = orders.order_id
)

-- ❌ Bad: PK buried in the middle
payments_enriched as (
    select
        payments.amount,
        orders.order_date,
        payments.payment_id
    from payments
    left join orders
        on payments.order_id = orders.order_id
)
```

#### **Rule: ALL-CTE-08 Column Alias Prefixing**

All columns in joins and final selects must be correctly prefixed with their CTE or table alias.

#### **Rule: ALL-CTE-09 No Direct Database References**

From statements must use {{ ref() }}, CTEs, or {{ source() }} (in the case of staging models); never BigQuery fully qualified table names.

#### **Rule: ALL-CTE-10 Early Aggregation**

Aggregations must occur as early in each script as possible to prevent cardinality issues in downstream CTEs and joins.

#### **Rule: ALL-CTE-11 Simple Final Select**

The final statement of the model must be a simple 'select \* from \<final\_cte\>' with no additional logic.

```sql
-- ✅ Good
final as (
    select
        payment_id,
        amount,
        order_date
    from payments_enriched
)

select * from final

-- ❌ Bad: additional logic in the final select
select
    payment_id,
    amount,
    order_date,
    case when amount > 1000 then 'large' else 'small' end as size_tier
from payments_enriched
```

### **Functional & Performance Integrity**

#### **Rule: ALL-PERF-01 Use Macros Over Boilerplate**

Use dbt macros and custom Jinja instead of verbose, repetitive SQL statements; particularly long and fragile case statements that could be expressed as a macro or a seed-driven lookup.

```sql
-- ✅ Good: seed-driven lookup joined in
status_labels as (
    select * from {{ ref('grant_status_mappings') }}
),

grants_labeled as (
    select
        grants.grant_id,
        status_labels.status_label
    from grants
    left join status_labels
        on grants.status_code = status_labels.status_code
)

-- ❌ Bad: fragile case statement that duplicates seed data
grants_labeled as (
    select
        grant_id,
        case
            when status_code = 'AP' then 'Approved'
            when status_code = 'DN' then 'Denied'
            when status_code = 'PD' then 'Pending'
            when status_code = 'RV' then 'Under Review'
            when status_code = 'CL' then 'Closed'
            -- 20 more lines ...
        end as status_label
    from grants
)
```

#### **Rule: ALL-PERF-02 Reproducible Primary Keys**

Primary keys must be generated in a reproducible way (e.g., using {{ dbt\_utils.generate\_surrogate\_key() }}) so that the same input always produces the same key. Never use random functions like GENERATE\_UUID().

#### **Rule: ALL-PERF-03 Avoid Select Distinct and Union Distinct**

Do not use 'select distinct' or 'union distinct'. In most SQL dialects, bare 'union' is equivalent to 'union distinct'; always use 'union all' explicitly. These operations are computationally expensive and may indicate a workaround for insufficiently processed upstream data. If deduplication is needed, address the root cause in an earlier model layer.

```sql
-- ✅ Good: explicit union all
select * from system_a_awards
union all
select * from system_b_awards

-- ❌ Bad: bare union (silently deduplicates)
select * from system_a_awards
union
select * from system_b_awards
```

#### **Rule: ALL-PERF-04 CTEs Over Subqueries**

Models must use CTEs instead of subqueries; CTEs are easier to read, easier to debug, and easier to restructure when the model evolves.

### **Data Testing Philosophy**

The purpose of testing is not to check a box; it is to develop and demonstrate a working understanding of the data going into, being processed in, and coming out of each model. An analyst whose tests pass but who cannot explain what the tests protect against — or what risks remain untested — has not finished the work.

#### **Rule: ALL-TST-01 Test What You Deliver and What You Depend On**

Test expectations about inputs as early as possible (at the source or staging layer) and test expectations about outputs when they are delivered (at the marts layer). In intermediate layers, test the things most likely to create problems: business rules, complex joins, and any logic that has failed or surprised you before.

#### **Rule: ALL-TST-02 Justify Your Testing Choices (in comments or meta tags, not descriptions)**

The rationale for why tests were chosen and what data quality risks they cover must be documented. However, this rationale must NOT be placed in the user-facing model or column `description` fields, as it clutters the document and buries the actual data definition. Instead, document testing rationale in a `meta` block within the YAML, or as an inline SQL comment within the model file itself. A reviewer should be able to find and understand what the analyst verified and what assumptions remain.

###### **Example**

"tests verify that the primary key remains unique after the union (protecting against overlapping ID ranges across systems)" belongs via a code comment or a meta tag. The YAML `description` should remain solely focused on defining the business entity and grain.

###### **Red-flag words in descriptions**

If a model or column description contains any of these words, the sentence almost certainly belongs in a `meta: testing_rationale:` block instead: `unique`, `not_null`, `fan-out`, `deduplication`, `protecting against`, `tests verify`, `collision`, `ensures that`, `guards against`. Descriptions should answer "what is this data?" — not "why did we test it?"

###### **Good vs. bad description examples**

```yaml
# BAD — restates tests, explains pipeline mechanics
description: >
  Deduplicated customer records from VistaReserve. Tests verify
  that the primary key is unique and strictly non-null, protecting
  against duplicate dimension rows that would fan out downstream joins.
  The base model's window function selects the most recent record.

# GOOD — explains the business entity
description: >
  Known individuals who transact with DCR through reservations,
  point-of-sale purchases, or pass registrations. One row per
  distinct customer. Columns are renamed from VistaReserve's
  internal conventions to CDM-adjacent business names.
```

#### **Rule: ALL-TST-03 Exploratory Data Profiling During Development**

Before finalizing a model, profile the data flowing through it. This is a development practice, not an artifact that persists in the codebase. At minimum, the analyst should investigate: row counts before and after each join or filter to confirm that cardinality behaves as expected; value distributions for key columns to confirm that the data looks reasonable; null rates for columns that the model depends on; and any unexpected duplicates, orphans, or outliers. The profiling itself does not need to be committed, but the insights it produces should inform the tests the analyst writes and the rationale they document.

###### **Techniques**

Use 'dbt show' to preview model output during development. Run ad-hoc count(\*) queries on individual CTEs by temporarily making them the final select to verify row counts at each transformation step. Compare counts before and after a join to detect fan-out (the count should not increase unless the join is intentionally one-to-many). Query 'select column, count(\*) from model group by column order by count(\*) desc' to inspect value distributions and spot unexpected nulls, blanks, or dominant values. These checks take minutes and frequently surface issues that formal tests would miss until production.

---

## **SQL Models**

### **Staging SQL Models**

#### **Purpose**

Staging models exist to make source data usable: they standardize column names, correct data types, and reshape each source table so that downstream models can consume it without guessing at meaning or format.

#### **Scope**

Must have exactly one staging model for each source table that will be consumed by a downstream integration model.

#### **Structure**

##### **Rule: SQL-STG-01 Directory Syntax**

Saved in './models/staging/{source}/\*'

##### **Rule: SQL-STG-02 File Name Syntax**

Phrased like 'stg\_\<source\>\_\_\<entity\>.sql'

##### **Rule: SQL-STG-03 Entity Word Choice**

Rephrase from system logic to business meaning, substituting intuitive words and adding pluralization as needed.

##### **Rule: SQL-STG-04 File Name Underscore Delimitation**

One underscore between the 'stg' prefix and source; 'stg\_salesforce'.

Two underscores between the source and entity; 'stg\_salesforce\_\_accounts.sql'

#### **Input Restrictions**

##### **Rule: SQL-STG-05 Consume Source Tables or Base Models**

Must import data from source tables using the {{ source() }} macro. If a base model exists for the source table (see the Base Models section), import from the base model using the {{ ref() }} macro instead.

##### **Rule: SQL-STG-06 No Joins, Aggregations, or Record Filtering**

Staging models must not contain joins, aggregations, or record filtering. If a staging model seems to require any of these operations, create a base model to handle the pre-processing and have the staging model consume the base model's output.

#### **Transformations**

##### **Rule: SQL-STG-07 Add a Hash Key**

If one does not already exist, create a hash key column called 'hk\_\<entity\>' using macro {{ dbt\_utils.generate\_surrogate\_key() }}.

The hash key must incorporate all fields that are needed to uniquely identify a record across systems and over time.

```sql
-- ✅ Good: reproducible hash key from business keys
select
    {{ dbt_utils.generate_surrogate_key([
        'source_system',
        'account_id'
    ]) }} as hk_accounts,
    account_id,
    account_name
from source

-- ❌ Bad: non-reproducible key from generate_uuid()
select
    generate_uuid() as hk_accounts,
    account_id,
    account_name
from source
```

##### **Rule: SQL-STG-08 Optional, Pick Relevant Columns**

May select all columns from the source table.

Can exclude columns that contain no useful data, are restricted for security or compliance purposes, or that — after consulting the business — have no known use.

##### **Rule: SQL-STG-09 Rename Columns for Understandability**

Must assign names to columns that people will understand and recognize across the project, especially when the names from the source system are unintuitive.

Should use field names from an appropriate Microsoft Common Data Model entity if possible.

```sql
-- ✅ Good: intuitive, CDM-aligned names
select
    acct_nbr as account_id,
    acct_nm as account_name,
    crt_dt as created_at,
    mod_dt as modified_at
from source

-- ❌ Bad: source system abbreviations kept as-is
select
    acct_nbr,
    acct_nm,
    crt_dt,
    mod_dt
from source
```

##### **Rule: SQL-STG-10 Recast Sub-Optimally Formatted Source Data**

Must convert incoming data to the most appropriate data types.

###### **Examples**

Parse date and time information incorrectly loaded as strings to timestamps, dates, or times.

Cast decimals incorrectly loaded as floats or numeric to integer.

##### **Rule: SQL-STG-11 Standardize Value Formats**

Can apply hard rules that change the format or representation of data so it is easier to work with, without changing its meaning.

###### **Examples**

Trimming whitespace from a string.

Removing special characters like HTML artifacts in strings.

Correcting casing like messy titles.

##### **Rule: SQL-STG-12 Parse and Flatten Structure**

Can extract nested or composite data into discrete columns so downstream models can reference them directly without parsing.

###### **Examples**

Splitting a composite identifier into its constituent parts.

Extracting values from a stringified JSON.

### **Base Models**

#### **Purpose**

Base models prevent repetitive or complex processing from cluttering staging and integration models; they isolate pre-processing logic — unions, splits, deduplication — so that the models consuming them can remain simple and readable.

#### **Scope**

Base models are optional. They should only be created when pre-processing a source table before staging improves the readability of the code or the performance of the materialization.

#### **Structure**

##### **Rule: SQL-BASE-01 Directory Syntax**

Saved in './models/staging/{source}/base/\*'

##### **Rule: SQL-BASE-02 File Name Syntax**

Phrased like 'base\_\<source\>\_\_\<entity\>.sql'

##### **Rule: SQL-BASE-03 Entity Name Word Choice**

Rephrase from system logic to business meaning, substituting intuitive words and adding pluralization as needed.

##### **Rule: SQL-BASE-04 File Name Underscore Delimitation**

One underscore between the 'base' prefix and source; 'base\_salesforce'.

Two underscores between the source and entity; 'base\_salesforce\_\_accounts.sql'

#### **Input Restrictions**

##### **Rule: SQL-BASE-05 Consume Source Tables**

Must import data from source tables using the {{ source() }} macro.

#### **Transformations**

##### **Rule: SQL-BASE-06 Combine Multiple Tables**

Can union or join multiple source tables that logically represent the same entity into a single output so that downstream staging models receive a consolidated input.

###### **Examples**

Unioning sharded tables.

Joining frequently crossreferenced tables.

##### **Rule: SQL-BASE-07 Split Up a Single Table**

Can filter or partition a single source table that contains multiple entity types into separate base models, each representing one entity, so that downstream staging models each handle a single coherent dataset.

###### **Examples**

Separating the single source table, 'transactions\_dtl', into three models representing the records it contains: 'base\_neighborly\_coloradodola\_\_budget\_line\_items', and 'base\_neighborly\_coloradodola\_\_draw\_line\_items'.

##### **Rule: SQL-BASE-08 Add Columns**

Can extract or derive columns from complex source structures so that downstream staging models do not need to repeat the parsing logic.

###### **Examples**

Extracting JSON or struct keys and values.

##### **Rule: SQL-BASE-09 Complex Deduplication**

Can remove duplicate records from source data when the deduplication logic is too complex for a simple staging model (e.g., requiring window functions to select the most recent version of a record based on multiple timestamp columns).

### **Integration Models**

#### **Purpose**

Integration models harmonize and collate data across source systems into third-normal form models that represent organization-wide entities — producing one authoritative version of each business concept regardless of where the data originated.

**An integration model that only renames columns from a single staging source is wrong.** If a model consumes one staging source and performs only column renames, it is functioning as a second staging model — not an integration model. Every integration model must perform at least one substantive transformation: unioning data across systems, joining to enrich records, deduplicating/harmonizing records, or generating surrogate keys. If the SPEC specifies multiple input sources for a model, all must be consumed.

#### **Scope**

Must have one or more integration models for all facts and dimensions.

#### **Structure**

##### **Rule: SQL-INT-01 Directory Syntax**

Saved in './models/integration/\*'

##### **Rule: SQL-INT-02 File Name Syntax**

Phrased like 'int\_\<entity\>.sql'

##### **Rule: SQL-INT-03 Entity Name Word Choice**

Must be an entity from the Microsoft Common Data Model.

##### **Rule: SQL-INT-04 File Name Underscore Delimitation**

One underscore between the 'int' prefix and entity; 'int\_projects'.

##### **Rule: SQL-INT-05 Microsoft Common Data Model Column Conformance**

Integration model columns must conform with the Microsoft Common Data Model definition for the entity that corresponds to the model. The non-profit core manifest is preferred, but a different manifest can be used when an appropriate schema is not available in it. Integration models may not contain columns — aside from foreign keys or surrogate keys — that are not specified by the Common Data Model entity definition. If a staging model produces columns that are valuable but not in the CDM, those columns must be dropped from the integration model; they can be joined back in at the marts layer from the staging model if needed. If an analyst believes a non-CDM column belongs in the integration layer, they must request an exception from their supervisor and document the rationale in the model description.

When applying CDM column names to this project, convert from the CDM's camelCase to snake\_case and from singular to plural where appropriate. Lookup columns that are integer values in the CDM can be simplified to strings.

```sql
-- ✅ Good: only CDM columns plus keys; non-CDM data dropped
select
    projects.project_sk,
    projects.project_id,
    projects.name,                  -- CDM column
    projects.description,           -- CDM column
    projects.start_date,            -- CDM column
    projects.end_date,              -- CDM column
    projects.status                 -- CDM column
from projects

-- ❌ Bad: non-CDM columns kept in the integration model
select
    projects.project_sk,
    projects.project_id,
    projects.name,
    projects.description,
    projects.start_date,
    projects.end_date,
    projects.status,
    projects.internal_tracking_code, -- not in CDM
    projects.legacy_system_flag      -- not in CDM
from projects
```

##### **Rule: SQL-INT-06 Surrogate Key Naming**

Surrogate keys in integration models must be named '\<object\>\_sk'.

#### **Input Restrictions**

##### **Rule: SQL-INT-07 Consume Staging Models**

Must import data from one or more staging models using the {{ ref() }} macro.

#### **Transformations**

##### **Rule: SQL-INT-08 Union Data Across Systems**

Data on individual business concepts is often stored in multiple systems; union it into single integration models to produce a comprehensive dataset.

##### **Rule: SQL-INT-09 Filter Irrelevant Data**

Exclude records from integration models that are not relevant to the integration entity being modeled.

###### **Examples**

The integration model represents grant awards, but the staging table contains both grant applications and awards; exclude the applications from the integration model.

##### **Rule: SQL-INT-10 Join to Enrich Records**

Present the columns and values in the integration model with the most accurate, complete, and fresh information across all applicable staging models.

##### **Rule: SQL-INT-11 Harmonize and Deduplicate Records**

Each row in the integration model must represent a distinct record across all upstream staging models and source tables. Execute coalesce statements, case statements, joins, window functions, and aggregations as needed.

##### **Rule: SQL-INT-12 Minimal Renaming**

Minor changes to column name syntax may be needed, but widespread or duplicative renaming is a sign that staging model column names are insufficiently standardized — fix the problem at its source.

### **Fact Models**

#### **Purpose**

Fact models store the measurable results of business process events at a declared grain, so that the data can be analyzed efficiently and accurately across one or more dimensions.

#### **Scope**

Must have a fact model for each business process event being consumed in a downstream report model or exposure.

#### **Structure**

##### **Rule: SQL-FCT-01 Directory Syntax**

Saved in './models/marts/{owner}/\*'

##### **Rule: SQL-FCT-02 File Name Syntax**

Phrased like 'fct\_\<business\_process\_event\>.sql'

##### **Rule: SQL-FCT-03 Business Process Event Word Choice**

Must accurately and succinctly describe the business process event and its grain. The name should sound like an "event noun" or a log of activity; for example, 'fct\_project\_completions' rather than 'fct\_projects'.

##### **Rule: SQL-FCT-04 File Name Underscore Delimitation**

One underscore between the 'fct' prefix and business process event; 'fct\_awards'.

#### **Input Restrictions**

##### **Rule: SQL-FCT-05 Consume Integration Models**

Must import data from one or more integration models using the {{ ref() }} macro.

#### **Transformations**

##### **Rule: SQL-FCT-06 Declare the Grain**

Model the result of the business process with a consistent grain; each row must correspond to a physical observable event, not the demands of a particular report. Where possible, prefer the atomic grain — the lowest level at which data is captured by the business process — over a summarized grain.

##### **Rule: SQL-FCT-07 Compute Numeric Measurements**

Identify the measurements that result from the business process event that have a one-to-one relationship with the event being measured.

###### **Examples**

The amount of dollars approved in a particular grant award.

The quantity of products requested in a funding application.

##### **Rule: SQL-FCT-08 Join in Dimension Keys**

Each fact row must have a non-null foreign key to all relevant dimensions so downstream models can provide context on the who, what, where, when, why, and how of the facts as needed.

### **Dimension Models**

#### **Purpose**

Provide descriptive context on the who, what, where, when, why, and how of business process events and their fact models.

#### **Scope**

Must have a dimension model for each characteristic of one or more fact models that needs to be described in a downstream report model or exposure.

#### **Structure**

##### **Rule: SQL-DIM-01 Directory Syntax**

Saved in './models/marts/{owner}/\*'

##### **Rule: SQL-DIM-02 File Name Syntax**

Phrased like 'dim\_\<noun\>.sql'

##### **Rule: SQL-DIM-03 Noun Word Choice**

Must accurately and succinctly describe the business entity that it represents as a noun. The name should sound like a "head noun" and "attributive noun"; for example, 'dim\_order\_categories' rather than 'dim\_categories'.

##### **Rule: SQL-DIM-04 File Name Underscore Delimitation**

One underscore between the 'dim' prefix and noun; 'dim\_customers'.

#### **Input Restrictions**

##### **Rule: SQL-DIM-05 Consume Integration Models**

Must import data from one or more integration models using the {{ ref() }} macro.

#### **Transformations**

##### **Rule: SQL-DIM-06 Join Multiple Integration Tables**

Must produce a single, wide, flattened dimensional table with all relevant descriptive attribute columns across all data sources for a relevant entity.

##### **Rule: SQL-DIM-07 Dimension Keys**

Must include each key that is needed to join it into all appropriate fact tables.

##### **Rule: SQL-DIM-08 Split or Combine Columns**

Can optimize existing data for downstream consumption, preventing challenging post processing in visualization or spreadsheet tools.

###### **Examples**

Split a full name into first and last names.

Combine multiple address part columns into a full address.

##### **Rule: SQL-DIM-09 Add Enriching Columns**

Can provide intuitive or verbose descriptions of existing data, preventing cumbersome grouping in visualization or spreadsheet tools.

###### **Examples**

Discrete binning of continuous amounts.

Geographic hierarchies.

### **Report Models**

#### **Purpose**

Report models standardize how commonly used combinations of facts and dimensions are served — promoting reusability and reproducibility so that the same business question produces the same answer regardless of who runs it or when.

#### **Scope**

Must create a report model when the same combination of facts and dimensions is consumed by two or more downstream dashboards, exports, or processes, or when the structure of the output is unlikely to change (for example, when the format of a report is specified by a federal regulation or grant agreement). Report models should be extensible — columns displayed to users can be added, removed, and changed without restructuring the model — and maintainable, so a single report can serve multiple use cases or time periods.

#### **Structure**

##### **Rule: SQL-RPT-01 Directory Syntax**

Saved in './models/marts/{owner}/\*'

##### **Rule: SQL-RPT-02 File Name Syntax**

Phrased like 'rpt\_\<subject\>.sql'

##### **Rule: SQL-RPT-03 Subject Word Choice**

Must accurately and succinctly describe the subject or subjects that are being presented in the report.

##### **Rule: SQL-RPT-04 File Name Underscore Delimitation**

One underscore between the 'rpt' prefix and subject; 'rpt\_accomplishments\_by\_activity'.

#### **Input Restrictions**

##### **Rule: SQL-RPT-05 Consume Fact and Dimension Models**

Must import data from one or more fact and dimension models using the {{ ref() }} macro.

#### **Transformations**

##### **Rule: SQL-RPT-06 Join Multiple Fact and Dimension Tables**

Must produce a single, wide, flattened report table with all relevant descriptive attribute columns across all facts and dimensions to present information on business events and their characteristics.

##### **Rule: SQL-RPT-07 Aggregate Facts to Consistent Grains**

Facts may contain data at, or the data in the report may need to be served in, different grains compared to the models that they are being sourced from. Use grouping to present all data in the report at a consistent grain.

### **Macros**

#### **Purpose**

Macros encapsulate reusable SQL logic and Jinja code so that the same pattern does not need to be written — and maintained — in multiple places across the project.

#### **Scope**

A macro is warranted when the same SQL pattern appears in two or more models; when a complex transformation would obscure the business logic of the model it lives in; or when a dbt community package does not already provide the needed functionality.

#### **Structure**

##### **Rule: SQL-MAC-01 Directory Syntax**

Saved in './macros/\*'. Subdirectories may be used to organize macros by function (e.g., './macros/staging/', './macros/testing/').

##### **Rule: SQL-MAC-02 File Name Syntax**

File names must describe the action or output of the macro in snake\_case: 'generate\_surrogate\_key.sql', 'pivot\_columns.sql'. One macro per file unless closely related helper macros are grouped together.

##### **Rule: SQL-MAC-03 Argument Validation**

Macros must validate their arguments with defensive checks (e.g., raising an error if a required argument is missing or an unexpected value is passed) so that misuse produces a clear error message rather than silent incorrect output.

##### **Rule: SQL-MAC-04 Prefer Packages Over Custom Macros**

Before writing a custom macro, check whether a well-maintained community package (such as dbt\_utils, dbt\_expectations, or dbt\_date) already provides the functionality. Custom macros should only be written when no suitable package exists or when the package's implementation does not meet the project's specific needs.

### **Singular Tests**

#### **Purpose**

Singular tests validate complex business logic, data quality expectations, or cross-model assertions that cannot be expressed with generic YAML-based tests — they are custom SQL queries that return failing rows.

#### **Scope**

Use singular tests when a validation requires custom SQL that goes beyond the capabilities of generic tests (unique, not\_null, accepted\_values, relationships) or their community-package extensions.

#### **Structure**

##### **Rule: SQL-TST-01 Directory Syntax**

Saved in './tests/\*'. Subdirectories may be used to organize tests by the layer or model they validate (e.g., './tests/staging/', './tests/marts/').

##### **Rule: SQL-TST-02 File Name Syntax**

File names must describe the assertion being tested: 'assert\_no\_orphan\_awards.sql', 'assert\_revenue\_matches\_ledger.sql'. Use the prefix 'assert\_' to distinguish singular tests from other SQL files.

##### **Rule: SQL-TST-03 Query Must Return Failing Rows**

A singular test query must return the set of rows that violate the assertion. If the query returns zero rows, the test passes; any rows returned constitute a failure.

##### **Rule: SQL-TST-04 Reference Models with ref**

Singular tests must reference models using the {{ ref() }} macro, not direct database table names, so that dbt can track the test's position in the DAG.

### **Seeds**

#### **Purpose**

Provide small, static reference data — such as code-to-label mappings, category lists, or status definitions — that changes infrequently and is version-controlled alongside the project code.

#### **Scope**

Seeds are appropriate for static lookup tables that are small enough to commit to version control (generally fewer than a few hundred rows). Data that changes regularly or is large should be loaded as a source, not a seed.

#### **Structure**

##### **Rule: SQL-SEED-01 Directory Syntax**

Saved in './seeds/\*'. Subdirectories may be used if the number of seeds warrants organization.

##### **Rule: SQL-SEED-02 File Format**

Seeds must be CSV files with a header row. Column names in the header must follow the same snake\_case convention as model columns (ALL-FMT-05).

##### **Rule: SQL-SEED-03 Naming**

Seed file names must describe the reference data they contain in snake\_case: 'country\_codes.csv', 'grant\_status\_mappings.csv'.

##### **Rule: SQL-SEED-04 No Business Logic in Seeds**

Seeds must contain only raw reference data. Any transformation or enrichment of seed data must happen in a model that references the seed using {{ ref() }}.

##### **Rule: SQL-SEED-05 YAML Properties**

Every seed must have a corresponding entry in a \_seeds.yml file within the ./seeds/ directory, including a description and column-level data type overrides where the default string type is not appropriate.

### **Snapshots**

#### **Purpose**

Capture point-in-time changes to mutable source data using SCD Type 2 tracking, preserving a history of how records change over time.

#### **Scope**

Snapshots are not currently in active use in this project. If a use case arises that requires historical change tracking of source data, the following conventions should be applied.

#### **Structure**

##### **Rule: SQL-SNAP-01 Directory Syntax**

Saved in './snapshots/\*'.

##### **Rule: SQL-SNAP-02 File Name Syntax**

File names must describe the source entity being tracked: 'snp\_\<source\>\_\_\<entity\>.sql'.

##### **Rule: SQL-SNAP-03 Strategy Declaration**

Each snapshot must declare its strategy (timestamp or check) and the columns used for change detection in its config block. The timestamp strategy is preferred when a reliable updated\_at column is available in the source.

##### **Rule: SQL-SNAP-04 Source Reference**

Snapshots must reference source tables using the {{ source() }} macro, not the {{ ref() }} macro, since they capture raw source state before transformation.

### **Analyses**

#### **Purpose**

Provide a place for ad-hoc or exploratory SQL queries that compile through dbt (benefiting from {{ ref() }} and Jinja) but do not materialize as tables or views in the warehouse.

#### **Scope**

Analyses are appropriate for audit queries, one-time investigations, data validation scripts, or SQL that supports reporting outside of the standard model pipeline. They should not be used as a substitute for models — if a query is consumed by a downstream process or BI tool, it belongs in the models directory.

#### **Structure**

##### **Rule: SQL-ANL-01 Directory Syntax**

Saved in './analyses/\*'. Subdirectories may be used to organize by purpose or team.

##### **Rule: SQL-ANL-02 File Name Syntax**

File names must describe the query's purpose in snake\_case: 'audit\_missing\_award\_amounts.sql', 'explore\_payment\_timing.sql'.

##### **Rule: SQL-ANL-03 Use ref and source Macros**

Analyses must reference models and sources using {{ ref() }} and {{ source() }} so that dbt can compile them correctly and lineage remains visible.

### **Hooks**

#### **Purpose**

Hooks execute SQL statements at specific points in the dbt run lifecycle — before or after individual models, or at the start or end of a full run — to handle operational tasks that fall outside standard model transformations.

#### **Scope**

Hooks should be used sparingly and only for operational needs that cannot be accomplished through models, tests, or macros — common examples include granting permissions on newly created tables, creating UDFs, logging run metadata, or vacuuming tables after incremental loads. Hooks must not contain business logic or transformations; those belong in models.

#### **Structure**

##### **Rule: SQL-HOOK-01 Declare Hooks in dbt\_project.yml**

on-run-start and on-run-end hooks must be declared in dbt\_project.yml so they are visible and centralized. Per-model pre-hook and post-hook configurations should be set at the project level and only overridden in individual model {{ config() }} blocks when necessary.

##### **Rule: SQL-HOOK-02 Extract Complex Hook Logic into Macros**

If a hook requires more than a single SQL statement, extract the logic into a macro in the ./macros/ directory and call the macro from the hook declaration. Do not embed multi-statement SQL directly in dbt\_project.yml or config blocks.

##### **Rule: SQL-HOOK-03 Document Hook Purpose**

Each hook must have a comment in dbt\_project.yml (or in the macro it calls) explaining what it does and why it is necessary, so that analysts encountering it understand its role in the pipeline.

---

## **YAML & Properties Configuration**

### **Purpose**

YAML property files are where the project defines what is true about each data asset — its tests, its contracts, and its documentation — close to the code that produces it. The purpose of these standards is to ensure that every model's properties are rigorous enough to catch data quality issues before they reach customers and detailed enough that a new analyst can understand the model without reading the SQL first.

### **Scope**

Applies to all Models, Sources, Seeds, Snapshots, and Macros defined in .yml files.

### **YAML/SQL Consistency**

#### **Rule: YML-SYNC-01 Columns Must Match SQL Output**

Every column documented in a `_models.yml` file must exist in the SQL model's output. Conversely, every column in the SQL model's output should be documented in the YAML. A YAML column definition that the SQL does not produce will cause a contract error if contracts are enforced, and is misleading documentation regardless. Before saving a `_models.yml` file, verify column names against the model's final SELECT.

#### **Rule: YML-SYNC-02 No Duplicate Model Entries**

Each model must appear exactly once in its `_models.yml` file. Duplicate entries (e.g., defining `int_cdm_columns` twice in the same YAML) cause unpredictable behavior — dbt may silently use the last definition, masking the first. If a model definition needs to be updated, modify the existing entry rather than adding a second one.

### **Documentation Standards (All Layers)**

These documentation rules apply to every YAML property file across all layers.

#### **Rule: YML-DOC-01 Mandatory Description Field**

Every model, source, seed, exposure, and macro must have a description field.

#### **Rule: YML-DOC-02 Description Content Quality**

Descriptions must explain the business meaning, grain, and potential filters of the data — not just the technical derivation. Include the types of transactions or records in the model; how the model characterizes the records; and any subtle or complex limitations. The description must also include a brief testing rationale — what data quality risks the applied tests protect against and why those tests were chosen for this model (see ALL-TST-02).

### **Structure & Workflow**

#### **Sources**

*Validate expectations about inputs before they enter the transformation pipeline.*

##### **Rule: SRC-YML-01 Directory Location**

Source properties must be defined in the ./models/staging/{source}/ directory.

##### **Rule: SRC-YML-02 Filename Syntax**

Source definitions must be consolidated into a single group-specific YAML file named \_sources.yml. Individual source files (e.g., src\_salesforce.yml) are not permitted.

##### **Rule: SRC-YML-03 Source Database and Schema Configuration**

Must define source systems with both database and schema configurations.

##### **Mandatory Tests**

##### **Rule: SRC-YML-04 Freshness Thresholds (Timeliness)**

Must include freshness blocks for all sources where data latency is a concern, defining warn\_after and error\_after thresholds to ensure pipeline reliability. To determine appropriate thresholds, ask: how frequently does this source update (hourly, daily, weekly)? and how stale can the data be before a downstream report or process produces misleading results? Set warn\_after to the expected update interval plus a reasonable buffer, and error\_after to the point at which the data is too stale to be useful. For example, a source that updates daily might use warn\_after: {count: 36, period: hour} and error\_after: {count: 48, period: hour}.

##### **Rule: SRC-YML-05 Source Key Testing (Uniqueness, Completeness)**

Test Primary Keys (PKs) and Business Keys (BKs) for uniqueness and non-nullability immediately at the source to ensure entities are correctly understood.

##### **Recommended Tests**

##### **Rule: SRC-YML-06 Source Foreign Key Testing (Consistency, Completeness)**

Test Foreign Keys (FKs) in source data to check for orphan records (e.g., a transaction without a valid customer ID) to inform operational teams of data quality issues early. Knowing that orphans exist is useful input for operational teams, but the analyst must work with the data as provided; this test informs rather than blocks.

#### **Staging & Base**

*Standardize data and ensure the foundation is documented and identifiable.*

##### **Rule: STG-YML-01 Directory Location**

Property files must be co-located with models in ./models/staging/{source}/.

##### **Rule: STG-YML-02 Filename Syntax**

Staging model properties must be consolidated into a single group-specific YAML file named \_models.yml. Individual model YAML files or unrelated resource files (e.g., \_macros.yml) are not permitted in this directory.

##### **Mandatory Tests**

##### **Rule: STG-YML-03 Staging Primary Key Testing (Uniqueness, Completeness)**

Every staging model must identify a primary key (natural or surrogate) and must apply unique and not\_null tests to it. This is the foundation for entity integrity throughout the pipeline; if the primary key is not trustworthy here, every downstream model inherits the problem.

##### **Optional Tests**

##### **Rule: STG-YML-04 Hash Collision Testing (Uniqueness, Consistency)**

Verify that Hash Keys (if used) and Hash Diffs do not have collisions. The collision risk is very small for most datasets, but grows with table size; consider running this test at a lower frequency for large tables rather than skipping it entirely.

###### **Staging YAML Example**

```yaml
# models/staging/salesforce/_models.yml
version: 2

models:
  - name: stg_salesforce__accounts
    description: >
      Salesforce account records representing organizations that
      interact with the agency. One row per account. Columns are
      renamed from Salesforce internal conventions to
      CDM-adjacent business names and recast to appropriate types.
    meta:
      testing_rationale: >
        Hash key collision test included because the account table
        exceeds 500k rows, making collision risk non-trivial.
    columns:
      - name: hk_accounts
        description: >
          Surrogate hash key derived from source_system and
          account_id. Used as the primary key for downstream joins.
        tests:
          - unique
          - not_null
      - name: account_id
        description: >
          System-generated identifier assigned by Salesforce when
          the account is created.
        tests:
          - not_null
      - name: account_name
        description: >
          Legal or operating name of the organization as recorded
          in Salesforce.
```

#### **Integration**

*Validate business logic, joins, and complex transformations.*

##### **Rule: INT-YML-01 Directory Location**

Property files must be co-located with models in ./models/integration/.

##### **Rule: INT-YML-02 Filename Syntax**

Integration model properties must be consolidated into a single group-specific YAML file named \_models.yml. Individual model YAML files are not permitted.

##### **Mandatory Tests**

##### **Rule: INT-YML-03 Integration Primary Key Testing (Uniqueness, Completeness)**

Every integration model must identify a primary key and must apply unique and not\_null tests to it. After unioning and deduplicating data across systems, the primary key test confirms that the harmonization logic actually produced one row per entity.

##### **Rule: INT-YML-04 Integration Foreign Key Testing (Consistency)**

Must use the relationships test to validate foreign keys in Integration models against their parent Staging models. This ensures that joins to staging models will not silently drop records or introduce nulls.

##### **Rule: INT-YML-05 Join Cardinality Validation (Uniqueness, Completeness)**

Test the results of joins to ensure no unintended duplication (fan-out) or data loss occurs during enrichment. This is where most silent data quality failures originate; a join that produces duplicates will cascade errors into every downstream fact and dimension. Implement this by comparing the row count of the model to the expected count based on the grain, or by using the dbt\_expectations package's 'expect\_table\_row\_count\_to\_equal\_other\_table' test to compare against the primary source.

##### **Rule: INT-YML-06 Business Logic Constraints (Validity)**

Important business logic (e.g., "start date must be before end date") must be validated using generic tests (like accepted\_values for status columns) or custom singular tests. The analyst should identify which business rules in the model carry the most risk if they fail, and test those first.

##### **Recommended Tests**

##### **Rule: INT-YML-07 Calculated Field Nullability (Completeness)**

Test that calculated fields (e.g., total\_revenue) are not null where mandatory. A null in a calculated field usually indicates an upstream data gap or a logic error in the transformation, and surfacing it here prevents misleading results in marts.

##### **Rule: INT-YML-08 CDM Accepted Values Testing (Validity)**

String fields must be tested against the appropriate Microsoft Common Data Model specification for accepted values. Numeric, decimal, float, and integer fields should be tested against the CDM specification for minimum and maximum values. All field types must be tested against the CDM specification for nullability. These tests may not be possible if CDM documentation for the entity is incomplete; in that case, document the gap in the model description and test what is available.

#### **Marts**

*Ensure reliability, stability, and contract adherence for downstream customers.*

##### **Rule: MRT-YML-01 Directory Location**

Property files must be co-located with models in ./models/marts/{owner}/.

##### **Rule: MRT-YML-02 Filename Syntax**

Mart model properties must be consolidated into a single group-specific YAML file named \_models.yml. Exposures should be defined in \_exposures.yml. Individual model YAML files are not permitted.

##### **Mandatory Tests**

##### **Rule: MRT-YML-03 Mart Primary Key Testing (Uniqueness, Completeness)**

Every fact, dimension, and report model must identify a primary key and must apply unique and not\_null tests to it. This is the last line of defense before data reaches customers; a duplicate or null key here will produce incorrect aggregations in dashboards and reports.

##### **Rule: MRT-YML-04 Public Interface Contracts (Consistency)**

For Mart models (Facts and Dimensions) that serve as public interfaces to BI tools or external customers, use contract: {enforced: true}.

##### **Rule: MRT-YML-05 Contract Data Type Definitions (Validity)**

Must explicitly define data\_type for every column in a contracted model to prevent unexpected schema changes from breaking downstream dependencies.

###### **Mart Contract YAML Example**

```yaml
# models/marts/finance/_models.yml
models:
  - name: fct_award_disbursements
    description: >
      Individual disbursement events against approved grant awards.
      One row per disbursement. Each row captures the dollar amount
      released, the date of release, and the grant it was drawn
      against. Consumed by rpt_grant_performance and the finance
      reconciliation dashboard.
    meta:
      testing_rationale: >
        Volumetric tests confirm row counts stay within historical
        bounds to catch silent pipeline stalls. FK test to
        dim_grants protects against orphaned disbursements.
    config:
      contract:
        enforced: true
    columns:
      - name: disbursement_sk
        data_type: string
        description: >
          Surrogate key uniquely identifying this disbursement
          event across all source systems.
        tests:
          - unique
          - not_null
      - name: grant_sk
        data_type: string
        description: >
          Reference to the grant award this disbursement was
          drawn against. Links to dim_grants.
        tests:
          - not_null
          - relationships:
              to: ref('dim_grants')
              field: grant_sk
      - name: disbursed_amount
        data_type: numeric
        description: >
          Dollar amount released in this disbursement event.
      - name: disbursed_at
        data_type: timestamp
        description: >
          Date and time the disbursement was processed by the
          granting agency.
```

##### **Rule: MRT-YML-06 Downstream Exposure Definitions**

Must define exposures for all external dashboards, ML models, or reverse ETL syncs that rely on dbt models — this preserves lineage visibility and prevents accidental deprecation of critical data feeds.

##### **Recommended Tests**

##### **Rule: MRT-YML-07 Complex Logic Unit Testing (Accuracy)**

Use the unit\_tests: block to validate complex SQL logic (such as regex parsing, complex window functions, or multi-condition case statements) using mock input data. This ensures logic is correct before running against production data volumes. If the model contains only straightforward joins and filters, unit tests may not add value.

##### **Rule: MRT-YML-08 Statistical Volumetric Testing (Completeness, Validity)**

Run statistical tests to ensure data is flowing within reasonable ranges (e.g., row counts are within expected historical bounds) to detect silent failures or stalled pipelines that pass schema tests but fail business needs. These tests complement source freshness checks by validating not just that data arrived, but that a reasonable quantity arrived with reasonable values. The dbt\_expectations package provides tests like 'expect\_table\_row\_count\_to\_be\_between' and 'expect\_column\_values\_to\_be\_between' that are well suited for this purpose.

#### **Global Resources (Macros)**

*Document and standardize reusable logic across the project.*

##### **Rule: MAC-YML-01 Directory Location**

Macro properties must be defined in the ./macros/ directory (or subdirectories if organized by package/function).

##### **Rule: MAC-YML-02 Filename Syntax**

Macro properties must be consolidated into a single group-specific YAML file named \_macros.yml.

##### **Rule: MAC-YML-03 Macro Documentation and Arguments**

Every macro must have a description and should verify its arguments (e.g., using config blocks or defensive coding) to ensure correct usage by other developers.

#### **Doc Blocks**

*Provide reusable, multi-line documentation that can be referenced across YAML property files.*

##### **Rule: DOC-YML-01 When to Use Doc Blocks**

Use {% docs %} blocks when the same column description applies across multiple models (e.g., a shared 'hk\_' or 'created\_at' definition) or when a description requires more detail than a single YAML line can convey clearly. For descriptions that are unique to one model and fit comfortably in a single line, inline YAML descriptions are sufficient.

##### **Rule: DOC-YML-02 Directory and File Location**

Doc block files must use the .md extension and be co-located with the YAML property files they support — in the same directory as the models they document. For project-wide doc blocks that are reused across layers, store them in a top-level ./models/docs/ directory.

##### **Rule: DOC-YML-03 Naming**

Doc block names must match or closely reflect the column or concept they describe: {% docs hk\_entity %}, {% docs grant\_award\_amount %}. Avoid generic names like {% docs description %} or {% docs notes %}.
