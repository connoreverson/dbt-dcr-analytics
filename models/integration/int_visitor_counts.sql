with

source_visitor_metrics as (
    select * from {{ ref('stg_trafficcount__derived_visitor_metrics') }}
    where is_deleted = false
),

source_sensor_locations as (
    select * from {{ ref('stg_trafficcount__sensor_locations') }}
    where is_deleted = false
),

/*
    int_parks is the authoritative park dimension. TrafficCount sensor
    locations carry integer park_ids (1–50 as varchar) that correspond
    to InfraTrak park_ids, resolved via infratrak_park_id in int_parks.
*/
source_parks as (
    select
        parks_sk,
        infratrak_park_id
    from {{ ref('int_parks') }}
),

/*
    Join daily visitor estimates to sensor metadata and the parks
    dimension. The vehicle occupancy multiplier (2.7) converts raw
    vehicle counts to estimated person-visits and is documented per
    estimate record so downstream models can apply sensitivity analysis.
    Only active, non-deleted records are included.
*/
final as (
    select
        {{ dbt_utils.generate_surrogate_key(['vm.metric_id']) }} as visitor_counts_sk,
        vm.metric_id,
        vm.sensor_id,
        parks.parks_sk,
        vm.target_date,
        vm.estimated_total_visitors,
        vm.vehicle_multiplier_used,
        vm.calculation_timestamp,
        sl.sensor_type,
        sl.location_description
    from source_visitor_metrics as vm
    left join source_sensor_locations as sl
        on vm.sensor_id = sl.sensor_id
    left join source_parks as parks
        on cast(sl.park_id as integer) = parks.infratrak_park_id
)

select * from final
