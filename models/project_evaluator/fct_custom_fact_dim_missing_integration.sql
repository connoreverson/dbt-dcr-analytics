{{ config(materialized='table') }}

with nodes as (
    select * from {{ ref('stg_nodes') }}
),

relationships as (
    select * from {{ ref('int_all_dag_relationships') }}
    where distance = 1
),

marts as (
    select * from nodes
    where
        resource_type = 'model'
        and (starts_with(name, 'fct_') or starts_with(name, 'dim_'))
),

missing_integration as (
    select
        m.unique_id,
        m.name as resource_name
    from marts as m
    where not exists (
        select 1
        from relationships as r
        where
            r.child = m.unique_id
            and contains(r.parent, 'model.') and contains(r.parent, '.int_')
    )
)

select * from missing_integration
