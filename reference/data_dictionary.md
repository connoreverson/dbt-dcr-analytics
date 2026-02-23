# DCR Data Inventory Dictionary

Auto-generated data dictionary from DuckDB system schemas.

## dcr_ast_01_infratrak

### Table: `assets`
*Physical assets. Known issue: Missing underground utilities and assets built after 2020.*

| Column | Type | Nullable |
| --- | --- | --- |
| asset_tag | `VARCHAR` | NO |
| park_id | `INTEGER` | NO |
| asset_category | `VARCHAR` | NO |
| description | `VARCHAR` | YES |
| construction_year | `INTEGER` | YES |
| replacement_value | `DECIMAL(12,2)` | YES |
| expected_lifespan_years | `INTEGER` | YES |
| latitude | `DECIMAL(9,6)` | YES |
| longitude | `DECIMAL(9,6)` | YES |
| is_visible_in_survey | `BOOLEAN` | YES |

### Table: `condition_assessments`
*Periodic Facility Condition Index scoring (1-100).*

| Column | Type | Nullable |
| --- | --- | --- |
| assessment_id | `VARCHAR` | NO |
| asset_tag | `VARCHAR` | NO |
| inspector_id | `VARCHAR` | NO |
| inspection_date | `DATE` | NO |
| fci_score | `INTEGER` | NO |
| notes | `VARCHAR` | YES |

### Table: `deferred_maintenance`
*Calculated cost to bring asset to FCI >= 70. Severely under-reports statewide reality due to missing rural regions.*

| Column | Type | Nullable |
| --- | --- | --- |
| backlog_id | `VARCHAR` | NO |
| asset_tag | `VARCHAR` | NO |
| estimated_repair_cost | `DECIMAL(12,2)` | NO |
| calculation_date | `DATE` | NO |
| is_funded | `BOOLEAN` | YES |

### Table: `employees`
*Maintenance staff, inspectors, and facility managers.*

| Column | Type | Nullable |
| --- | --- | --- |
| employee_id | `VARCHAR` | NO |
| first_name | `VARCHAR` | NO |
| last_name | `VARCHAR` | NO |
| title | `VARCHAR` | NO |
| assigned_region | `INTEGER` | NO |

### Table: `parks`
*The 50 park units managed by DCR. Regions 3 and 4 are not fully onboarded.*

| Column | Type | Nullable |
| --- | --- | --- |
| park_id | `INTEGER` | NO |
| park_name | `VARCHAR` | NO |
| region_id | `INTEGER` | NO |
| classification | `VARCHAR` | NO |

### Table: `work_orders`
*Maintenance tasks. Known issue: Low completion discipline in Region 2.*

| Column | Type | Nullable |
| --- | --- | --- |
| wo_id | `VARCHAR` | NO |
| asset_tag | `VARCHAR` | NO |
| park_id | `INTEGER` | NO |
| primary_assignee | `VARCHAR` | YES |
| wo_type | `VARCHAR` | NO |
| status | `VARCHAR` | NO |
| reported_date | `DATE` | NO |
| completed_date | `DATE` | YES |
| labor_hours | `DECIMAL(6,2)` | YES |
| material_cost | `DECIMAL(10,2)` | YES |
| total_cost | `DECIMAL(10,2)` | YES |

## dcr_fin_01_stategov

### Table: `accounts_payable`
*Vendor invoices and payment disbursements.*

| Column | Type | Nullable |
| --- | --- | --- |
| invoice_id | `VARCHAR` | NO |
| vendor_id | `VARCHAR` | NO |
| encumbrance_id | `VARCHAR` | YES |
| account_id | `VARCHAR` | NO |
| invoice_date | `DATE` | NO |
| payment_date | `DATE` | YES |
| amount | `DECIMAL(12,2)` | NO |
| status | `VARCHAR` | NO |

### Table: `chart_of_accounts`
*Hierarchical accounting structure used for statewide reporting.*

| Column | Type | Nullable |
| --- | --- | --- |
| account_id | `VARCHAR` | NO |
| fund_code | `VARCHAR` | NO |
| fund_description | `VARCHAR` | NO |
| division_code | `VARCHAR` | NO |
| division_description | `VARCHAR` | NO |
| program_code | `VARCHAR` | NO |
| program_description | `VARCHAR` | NO |
| object_code | `VARCHAR` | NO |
| object_description | `VARCHAR` | NO |

### Table: `encumbrances`
*Funds reserved for future payment against contracts or POs.*

| Column | Type | Nullable |
| --- | --- | --- |
| encumbrance_id | `VARCHAR` | NO |
| vendor_id | `VARCHAR` | NO |
| account_id | `VARCHAR` | NO |
| established_date | `DATE` | NO |
| original_amount | `DECIMAL(12,2)` | NO |
| remaining_balance | `DECIMAL(12,2)` | NO |
| status | `VARCHAR` | NO |

### Table: `general_ledger`
*Monthly aggregated financial transactions. Daily detail from subsidiary systems (like VistaReserve) is lost in batch processing.*

| Column | Type | Nullable |
| --- | --- | --- |
| gl_entry_id | `VARCHAR` | NO |
| account_id | `VARCHAR` | NO |
| fiscal_year | `INTEGER` | NO |
| accounting_month | `INTEGER` | NO |
| entry_type | `VARCHAR` | NO |
| amount | `DECIMAL(12,2)` | NO |
| batch_reference | `VARCHAR` | YES |

### Table: `vendors`
*Approved vendors for accounts payable and contracts.*

| Column | Type | Nullable |
| --- | --- | --- |
| vendor_id | `VARCHAR` | NO |
| vendor_name | `VARCHAR` | NO |
| tin_masked | `VARCHAR` | NO |
| vendor_type | `VARCHAR` | NO |
| is_active | `BOOLEAN` | YES |

## dcr_fin_02_granttrack

### Table: `active_awards`
*Grants won. Manual cross-ref to SGF exists but is often slightly off.*

| Column | Type | Nullable |
| --- | --- | --- |
| award_id | `VARCHAR` | NO |
| application_id | `VARCHAR` | YES |
| award_number | `VARCHAR` | YES |
| award_amount | `DECIMAL(12,2)` | NO |
| performance_start | `DATE` | NO |
| performance_end | `DATE` | NO |
| required_match_percentage | `DECIMAL(5,2)` | NO |
| sgf_appropriation_code | `VARCHAR` | YES |

### Table: `compliance_deadlines`
*Tracking deadlines for federal reporting.*

| Column | Type | Nullable |
| --- | --- | --- |
| deadline_id | `VARCHAR` | NO |
| award_id | `VARCHAR` | NO |
| report_type | `VARCHAR` | NO |
| due_date | `DATE` | NO |
| submission_date | `DATE` | YES |
| status | `VARCHAR` | YES |

### Table: `grant_applications`
*Pipeline of funding opportunities.*

| Column | Type | Nullable |
| --- | --- | --- |
| application_id | `VARCHAR` | NO |
| grant_program | `VARCHAR` | NO |
| submission_date | `DATE` | YES |
| requested_amount | `DECIMAL(12,2)` | NO |
| status | `VARCHAR` | NO |
| estimated_award_date | `DATE` | YES |

### Table: `match_fund_tracking`
*Known issue: cross-fiscal year logic is broken causing some aggregated errors in reports.*

| Column | Type | Nullable |
| --- | --- | --- |
| match_id | `VARCHAR` | NO |
| award_id | `VARCHAR` | NO |
| transaction_date | `DATE` | NO |
| match_type | `VARCHAR` | NO |
| amount_value | `DECIMAL(10,2)` | NO |
| description | `VARCHAR` | YES |

### Table: `reimbursement_requests`
*Drawdowns against the grant. Often diverges from SGF by 2-5% due to timing and coding discipline.*

| Column | Type | Nullable |
| --- | --- | --- |
| request_id | `VARCHAR` | NO |
| award_id | `VARCHAR` | NO |
| submission_date | `DATE` | NO |
| requested_amount | `DECIMAL(10,2)` | NO |
| approved_amount | `DECIMAL(10,2)` | YES |
| receipt_date | `DATE` | YES |
| sgf_encumbrance_ref | `VARCHAR` | YES |

## dcr_geo_01_geoparks

### Table: `cultural_resources`
*RESTRICTED. Protected archaeological sites, burial grounds. High sensitivity.*

| Column | Type | Nullable |
| --- | --- | --- |
| site_id | `VARCHAR` | NO |
| geo_park_id | `VARCHAR` | NO |
| site_type | `VARCHAR` | NO |
| shpo_reference_number | `VARCHAR` | YES |
| geometry_wkt | `VARCHAR` | NO |
| access_level | `VARCHAR` | NO |
| last_assessed | `DATE` | YES |

### Table: `infrastructure_features`
*Trails, roads, utilities. Known issue: underground utilities have positional errs up to 5+ meters.*

| Column | Type | Nullable |
| --- | --- | --- |
| feature_id | `VARCHAR` | NO |
| geo_park_id | `VARCHAR` | NO |
| feature_class | `VARCHAR` | NO |
| sub_type | `VARCHAR` | YES |
| status | `VARCHAR` | NO |
| installation_year | `INTEGER` | YES |
| geometry_wkt | `VARCHAR` | NO |
| positional_accuracy_meters | `DECIMAL(5,2)` | YES |
| last_updated | `DATE` | NO |

### Table: `legal_boundaries`
*Legal surveyed parcel boundaries (Polygons). Sub-meter accuracy.*

| Column | Type | Nullable |
| --- | --- | --- |
| boundary_id | `VARCHAR` | NO |
| geo_park_id | `VARCHAR` | NO |
| boundary_type | `VARCHAR` | NO |
| last_survey_date | `DATE` | YES |
| geometry_wkt | `VARCHAR` | NO |

### Table: `natural_resources`
*E.g., vegetation polygons derived from 2019 survey. Known issue: sometimes lags 1-3 years.*

| Column | Type | Nullable |
| --- | --- | --- |
| resource_id | `VARCHAR` | NO |
| geo_park_id | `VARCHAR` | NO |
| resource_type | `VARCHAR` | NO |
| classification_code | `VARCHAR` | NO |
| geometry_wkt | `VARCHAR` | NO |
| last_survey_year | `INTEGER` | NO |

### Table: `parks_master`
*The geospatial systems standalone list of parks.*

| Column | Type | Nullable |
| --- | --- | --- |
| geo_park_id | `VARCHAR` | NO |
| park_name | `VARCHAR` | NO |
| total_acres | `DECIMAL(10,2)` | NO |
| gis_steward | `VARCHAR` | NO |

### Table: `recreational_features`
*Points of interest for public maps.*

| Column | Type | Nullable |
| --- | --- | --- |
| poi_id | `VARCHAR` | NO |
| geo_park_id | `VARCHAR` | NO |
| poi_type | `VARCHAR` | NO |
| name | `VARCHAR` | NO |
| is_publicly_visible | `BOOLEAN` | YES |
| geometry_wkt | `VARCHAR` | NO |

## dcr_hcm_01_peoplefirst

### Table: `benefits`
*Health, retirement, and accrued leave balances.*

| Column | Type | Nullable |
| --- | --- | --- |
| employee_id | `VARCHAR` | NO |
| health_plan_type | `VARCHAR` | NO |
| retirement_tier | `VARCHAR` | NO |
| annual_leave_hours | `DECIMAL(6,2)` | YES |
| sick_leave_hours | `DECIMAL(6,2)` | YES |
| comp_time_hours | `DECIMAL(6,2)` | YES |

### Table: `employees`
*Demographics and core HR employment records for permanent staff.*

| Column | Type | Nullable |
| --- | --- | --- |
| employee_id | `VARCHAR` | NO |
| first_name | `VARCHAR` | NO |
| last_name | `VARCHAR` | NO |
| ssn_last4 | `VARCHAR` | NO |
| email | `VARCHAR` | YES |
| phone | `VARCHAR` | YES |
| hire_date | `DATE` | NO |
| separation_date | `DATE` | YES |
| position_id | `VARCHAR` | NO |

### Table: `org_units`
*Organizational units (e.g., "Region 2 - Tall Pines District"). Duty stations are only tracked at this level, not park-specific.*

| Column | Type | Nullable |
| --- | --- | --- |
| org_unit_id | `VARCHAR` | NO |
| org_unit_name | `VARCHAR` | NO |
| region_id | `INTEGER` | NO |

### Table: `payroll`
*Per-pay-period earnings disbursements. Flows to DCR-FIN-01.*

| Column | Type | Nullable |
| --- | --- | --- |
| payroll_id | `VARCHAR` | NO |
| employee_id | `VARCHAR` | NO |
| pay_period_start | `DATE` | NO |
| pay_period_end | `DATE` | NO |
| gross_pay | `DECIMAL(10,2)` | NO |
| deductions | `DECIMAL(10,2)` | NO |
| taxes_withheld | `DECIMAL(10,2)` | NO |
| net_pay | `DECIMAL(10,2)` | NO |

### Table: `positions`
*Authorized position inventory for DCR defining the FTE count.*

| Column | Type | Nullable |
| --- | --- | --- |
| position_id | `VARCHAR` | NO |
| job_classification | `VARCHAR` | NO |
| pay_grade | `VARCHAR` | NO |
| org_unit_id | `VARCHAR` | NO |
| funding_source | `VARCHAR` | NO |
| is_active | `BOOLEAN` | YES |

### Table: `seasonal_workforce`
*Temporary seasonal staff. Known issue: system_onboard_date often lags actual_start_date due to HR processing delays.*

| Column | Type | Nullable |
| --- | --- | --- |
| seasonal_emp_id | `VARCHAR` | NO |
| first_name | `VARCHAR` | NO |
| last_name | `VARCHAR` | NO |
| org_unit_id | `VARCHAR` | NO |
| season_year | `INTEGER` | NO |
| actual_start_date | `DATE` | NO |
| system_onboard_date | `DATE` | NO |
| separation_date | `DATE` | YES |
| hourly_rate | `DECIMAL(6,2)` | NO |

## dcr_les_01_rangershield

### Table: `citations`
*Notices to appear, infractions. Includes court dispositions.*

| Column | Type | Nullable |
| --- | --- | --- |
| citation_number | `VARCHAR` | NO |
| incident_number | `VARCHAR` | YES |
| issuing_officer | `VARCHAR` | NO |
| violation_code | `VARCHAR` | NO |
| issue_timestamp | `TIMESTAMP` | NO |
| fine_amount | `DECIMAL(6,2)` | YES |
| court_disposition | `VARCHAR` | YES |

### Table: `dispatch_logs`
*Real-time CAD radio communications and check-ins.*

| Column | Type | Nullable |
| --- | --- | --- |
| log_id | `VARCHAR` | NO |
| incident_number | `VARCHAR` | YES |
| badge_number | `VARCHAR` | NO |
| log_timestamp | `TIMESTAMP` | NO |
| event_type | `VARCHAR` | NO |
| radio_traffic_transcript | `VARCHAR` | YES |

### Table: `incidents`
*Case reports. Location is narrative text, not a spatial coordinate. High internal integrity.*

| Column | Type | Nullable |
| --- | --- | --- |
| incident_number | `VARCHAR` | NO |
| reporting_officer | `VARCHAR` | NO |
| incident_type | `VARCHAR` | NO |
| report_timestamp | `TIMESTAMP` | NO |
| location_narrative | `VARCHAR` | NO |
| narrative_summary | `VARCHAR` | YES |
| review_status | `VARCHAR` | NO |

### Table: `officer_activity`
*Daily patrol logs capturing activity metrics.*

| Column | Type | Nullable |
| --- | --- | --- |
| activity_id | `VARCHAR` | NO |
| badge_number | `VARCHAR` | NO |
| shift_date | `DATE` | NO |
| shift_start_time | `TIMESTAMP` | NO |
| shift_end_time | `TIMESTAMP` | NO |
| patrol_miles | `DECIMAL(5,1)` | YES |
| visitor_contacts | `INTEGER` | YES |
| resource_checks | `INTEGER` | YES |

### Table: `officers`
*Sworn State Park Peace Officers (SPPOs).*

| Column | Type | Nullable |
| --- | --- | --- |
| badge_number | `VARCHAR` | NO |
| first_name | `VARCHAR` | NO |
| last_name | `VARCHAR` | NO |
| rank | `VARCHAR` | NO |
| certification_status | `VARCHAR` | NO |
| assigned_region | `INTEGER` | NO |

### Table: `use_of_force`
*Mandatory tracking of force incidents. Highly sensitive.*

| Column | Type | Nullable |
| --- | --- | --- |
| uof_id | `VARCHAR` | NO |
| incident_number | `VARCHAR` | NO |
| involved_officer | `VARCHAR` | NO |
| force_level | `VARCHAR` | NO |
| subject_injury | `BOOLEAN` | YES |
| officer_injury | `BOOLEAN` | YES |
| internal_review_status | `VARCHAR` | NO |

## dcr_nrm_01_biosurvey

### Table: `endangered_species_monitoring`
*Annual counts for ESA-listed species.*

| Column | Type | Nullable |
| --- | --- | --- |
| monitoring_id | `VARCHAR` | NO |
| site_id | `VARCHAR` | NO |
| species_code | `VARCHAR` | NO |
| monitoring_year | `INTEGER` | NO |
| population_count | `INTEGER` | YES |
| nesting_pairs | `INTEGER` | YES |
| reproductive_success_rate | `DECIMAL(5,2)` | YES |
| compliance_reported | `BOOLEAN` | YES |

### Table: `flora_fauna_surveys`
*Observation records. Known issue: latitude/longitude are NULL for records before 2011.*

| Column | Type | Nullable |
| --- | --- | --- |
| survey_id | `VARCHAR` | NO |
| site_id | `VARCHAR` | NO |
| species_code | `VARCHAR` | NO |
| survey_date | `DATE` | NO |
| observer_name | `VARCHAR` | NO |
| count_estimate | `INTEGER` | YES |
| density_estimate_per_hectare | `DECIMAL(8,2)` | YES |
| latitude | `DECIMAL(9,6)` | YES |
| longitude | `DECIMAL(9,6)` | YES |

### Table: `invasive_species_observations`
*Invasive species tracking and treatment history.*

| Column | Type | Nullable |
| --- | --- | --- |
| observation_id | `VARCHAR` | NO |
| site_id | `VARCHAR` | NO |
| species_code | `VARCHAR` | NO |
| observation_date | `DATE` | NO |
| extent_square_meters | `DECIMAL(10,2)` | YES |
| treatment_applied | `VARCHAR` | YES |
| treatment_date | `DATE` | YES |
| latitude | `DECIMAL(9,6)` | YES |
| longitude | `DECIMAL(9,6)` | YES |

### Table: `species_codes`
*Custom alphanumeric scheme developed in 1993 by the Chief Biologist.*

| Column | Type | Nullable |
| --- | --- | --- |
| species_code | `VARCHAR` | NO |
| common_name | `VARCHAR` | NO |
| scientific_name | `VARCHAR` | YES |
| category | `VARCHAR` | NO |
| is_endangered | `BOOLEAN` | YES |
| is_invasive | `BOOLEAN` | YES |

### Table: `survey_sites`
*Sites where surveys and tests are conducted. Linked to parks, but historically only by name/ID.*

| Column | Type | Nullable |
| --- | --- | --- |
| site_id | `VARCHAR` | NO |
| park_id | `INTEGER` | NO |
| site_name | `VARCHAR` | NO |
| site_description | `VARCHAR` | YES |

### Table: `water_quality_tests`
*Water sampling. Longitudinal analysis requires manual methodology-aware adjustments due to protocol eras.*

| Column | Type | Nullable |
| --- | --- | --- |
| test_id | `VARCHAR` | NO |
| site_id | `VARCHAR` | NO |
| sample_date | `DATE` | NO |
| dissolved_oxygen_mgl | `DECIMAL(6,2)` | YES |
| ph_level | `DECIMAL(4,2)` | YES |
| ecoli_cfu_100ml | `INTEGER` | YES |
| turbidity_ntu | `DECIMAL(6,2)` | YES |
| temperature_celsius | `DECIMAL(5,2)` | YES |
| nitrogen_mgl | `DECIMAL(6,2)` | YES |
| phosphorus_mgl | `DECIMAL(6,2)` | YES |
| protocol_era | `VARCHAR` | NO |

## dcr_rev_01_vistareserve

### Table: `asset_crosswalk`
*Nominally links VistaReserve inventory IDs to GeoParks and InfraTrak. Known issue: stale and incomplete for assets added after 2022.*

| Column | Type | Nullable |
| --- | --- | --- |
| vista_asset_id | `VARCHAR` | NO |
| geoparks_feature_id | `VARCHAR` | YES |
| infratrak_asset_tag | `VARCHAR` | YES |
| last_verified_date | `DATE` | YES |

### Table: `customer_profiles`
*Guest accounts. Known issue: ~20% duplicate rate due to self-service creation without deduplication.*

| Column | Type | Nullable |
| --- | --- | --- |
| customer_id | `VARCHAR` | NO |
| first_name | `VARCHAR` | NO |
| last_name | `VARCHAR` | NO |
| email | `VARCHAR` | YES |
| phone | `VARCHAR` | YES |
| address_state | `VARCHAR` | YES |
| is_veteran | `BOOLEAN` | YES |
| is_senior | `BOOLEAN` | YES |
| has_annual_pass | `BOOLEAN` | YES |
| created_at | `TIMESTAMP` | NO |
| merged_into_customer_id | `VARCHAR` | YES |

### Table: `inventory_assets`
*Registry of bookable assets (campsites, cabins, day-use areas)*

| Column | Type | Nullable |
| --- | --- | --- |
| asset_id | `VARCHAR` | NO |
| park_id | `INTEGER` | NO |
| asset_type | `VARCHAR` | NO |
| max_occupancy | `INTEGER` | NO |
| ada_accessible | `BOOLEAN` | NO |
| pet_policy | `VARCHAR` | YES |
| utility_hookup | `VARCHAR` | YES |

### Table: `parks`
*The 50 park units managed by DCR*

| Column | Type | Nullable |
| --- | --- | --- |
| park_id | `INTEGER` | NO |
| park_name | `VARCHAR` | NO |
| region_id | `INTEGER` | NO |
| classification | `VARCHAR` | NO |
| has_unstaffed_kiosk | `BOOLEAN` | YES |

### Table: `pos_transactions`
*Point-of-sale transactions for retail goods, day-use entry fees, and equipment rentals. Note: 12 remote parks have unstaffed kiosks with manual delayed entry.*

| Column | Type | Nullable |
| --- | --- | --- |
| transaction_id | `VARCHAR` | NO |
| park_id | `INTEGER` | NO |
| customer_id | `VARCHAR` | YES |
| transaction_date | `TIMESTAMP` | NO |
| revenue_category | `VARCHAR` | NO |
| amount | `DECIMAL(10,2)` | NO |
| is_kiosk_entry | `BOOLEAN` | YES |

### Table: `reservations`
*The full reservation lifecycle (search, hold, booking, modification, cancellation, no-show)*

| Column | Type | Nullable |
| --- | --- | --- |
| reservation_id | `VARCHAR` | NO |
| customer_id | `VARCHAR` | NO |
| asset_id | `VARCHAR` | NO |
| booking_date | `TIMESTAMP` | NO |
| arrival_date | `DATE` | NO |
| departure_date | `DATE` | NO |
| status | `VARCHAR` | NO |
| total_amount | `DECIMAL(10,2)` | NO |

### Table: `revenue_batch`
*Daily batch files summarizing gross revenue by park unit and category, generated for DCR-FIN-01 reconciliation.*

| Column | Type | Nullable |
| --- | --- | --- |
| batch_id | `VARCHAR` | NO |
| batch_date | `DATE` | NO |
| park_id | `INTEGER` | NO |
| revenue_category | `VARCHAR` | NO |
| gross_revenue | `DECIMAL(12,2)` | NO |
| transaction_count | `INTEGER` | NO |

## dcr_rev_02_legacyres

### Table: `legacy_customers`
*Historical customer records (PII). Card masks present in some older records.*

| Column | Type | Nullable |
| --- | --- | --- |
| legacy_cust_id | `VARCHAR` | NO |
| first_name | `VARCHAR` | YES |
| last_name | `VARCHAR` | YES |
| email | `VARCHAR` | YES |
| phone_number | `VARCHAR` | YES |
| partial_card_mask | `VARCHAR` | YES |

### Table: `legacy_park_crosswalk`
*Only 15 out of 50 parks have a mapped current_park_id. The rest are NULL.*

| Column | Type | Nullable |
| --- | --- | --- |
| legacy_park_id | `VARCHAR` | NO |
| legacy_park_name | `VARCHAR` | NO |
| current_park_id | `INTEGER` | YES |

### Table: `legacy_reservations`
*Historical reservations showing three distinct data formats/eras.*

| Column | Type | Nullable |
| --- | --- | --- |
| res_id | `VARCHAR` | NO |
| legacy_cust_id | `VARCHAR` | NO |
| legacy_park_id | `VARCHAR` | NO |
| arrival_date | `DATE` | NO |
| departure_date | `DATE` | NO |
| total_paid | `DECIMAL(8,2)` | YES |
| data_format_source | `VARCHAR` | NO |

### Table: `legacy_revenue_summaries`
*Monthly aggregated revenue prior to VistaReserve.*

| Column | Type | Nullable |
| --- | --- | --- |
| summary_id | `VARCHAR` | NO |
| legacy_park_id | `VARCHAR` | NO |
| report_month | `DATE` | NO |
| revenue_category | `VARCHAR` | NO |
| total_revenue | `DECIMAL(10,2)` | NO |

## dcr_vum_01_trafficcount

### Table: `derived_visitor_metrics`
*Daily metrics. Relies on the unvalidated 2.7 persons-per-vehicle multiplier from 2019.*

| Column | Type | Nullable |
| --- | --- | --- |
| metric_id | `VARCHAR` | NO |
| sensor_id | `VARCHAR` | NO |
| target_date | `DATE` | NO |
| estimated_total_visitors | `INTEGER` | NO |
| vehicle_multiplier_used | `DECIMAL(3,2)` | NO |
| calculation_timestamp | `TIMESTAMP` | NO |

### Table: `pedestrian_cyclist_counts`
*Hourly aggregated trail users.*

| Column | Type | Nullable |
| --- | --- | --- |
| count_id | `VARCHAR` | NO |
| sensor_id | `VARCHAR` | NO |
| timestamp_hour | `TIMESTAMP` | NO |
| raw_pedestrian_count | `INTEGER` | NO |
| raw_cyclist_count | `INTEGER` | NO |
| is_anomaly | `BOOLEAN` | YES |

### Table: `sensor_locations`
*Only 20 sensors deployed statewide (8 entrances, 12 trailheads). 85% of parks have no data here.*

| Column | Type | Nullable |
| --- | --- | --- |
| sensor_id | `VARCHAR` | NO |
| park_id | `INTEGER` | NO |
| installation_date | `DATE` | NO |
| sensor_type | `VARCHAR` | NO |
| location_description | `VARCHAR` | NO |
| status | `VARCHAR` | YES |

### Table: `vehicle_counts`
*Hourly aggregated vehicle counts. Includes staff and contractor vehicles erroneously.*

| Column | Type | Nullable |
| --- | --- | --- |
| count_id | `VARCHAR` | NO |
| sensor_id | `VARCHAR` | NO |
| timestamp_hour | `TIMESTAMP` | NO |
| raw_vehicle_count | `INTEGER` | NO |
| is_anomaly | `BOOLEAN` | YES |

