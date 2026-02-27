select
    r.reservations_sk,
    r._park_sk,
    r.msnvo_visitid
from {{ ref('int_reservations') }} as r
left join {{ ref('int_parks') }} as p
    on r._park_sk = p.parks_sk
where p.parks_sk is null
