select
    r.visits_sk,
    r._park_sk
from {{ ref('int_visits') }} as r
left join {{ ref('int_parks') }} as p
    on r._park_sk = p.parks_sk
where p.parks_sk is null
