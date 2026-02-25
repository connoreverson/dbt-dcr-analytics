with cdm_geo as (
    select accountnumber
    from {{ ref('int_parks') }}
    where source_system like '%DCR-GEO-01%'
),

cdm_vista as (
    select accountnumber
    from {{ ref('int_parks') }}
    where source_system like '%DCR-REV-01%'
)

select v.accountnumber as orphaned_vista_park
from cdm_vista as v
left join cdm_geo as g
    on v.accountnumber = g.accountnumber
where g.accountnumber is null
