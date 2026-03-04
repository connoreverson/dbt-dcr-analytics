{{ config(materialized='table') }}

with nodes as (
    select * from {{ ref('stg_nodes') }}
),

relationships as (
    select * from {{ ref('int_all_dag_relationships') }}
    where distance = 1
),

marts as (
    select
        unique_id,
        name as resource_name
    from nodes
    where
        resource_type = 'model'
        and (starts_with(name, 'fct_') or starts_with(name, 'dim_'))
),

violating_marts as (
    select
        m.unique_id,
        m.resource_name
    from marts as m
    inner join relationships as r on m.unique_id = r.child
    where contains(r.parent, 'model.') and contains(r.parent, '.stg_')
)

select * from violating_marts
