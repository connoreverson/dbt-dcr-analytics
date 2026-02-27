{{ config(materialized='table') }}

with nodes as (
    select * from {{ ref('stg_nodes') }}
),

relationships as (
    select * from {{ ref('int_all_dag_relationships') }}
    where distance = 1
),

staging as (
    select unique_id, name as resource_name
    from nodes
    where resource_type = 'model' and starts_with(name, 'stg_')
),

violating_staging as (
    select distinct s.unique_id, s.resource_name
    from staging s
    inner join relationships r on s.unique_id = r.child
    where not (contains(r.parent, 'source.') or (contains(r.parent, 'model.') and contains(r.parent, '.base_')))
)

select * from violating_staging
