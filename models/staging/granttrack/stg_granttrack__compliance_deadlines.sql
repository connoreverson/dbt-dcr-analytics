with

source as (
    select * from {{ source('granttrack', 'compliance_deadlines') }}
),

final as (
    select
        --  hash key
        {{ dbt_utils.generate_surrogate_key(['source.deadline_id']) }} as hk_compliance_deadline,
        --  ids
        cast(source.deadline_id as varchar) as deadline_id,
        cast(source.award_id as varchar) as award_id,
        --  attributes
        cast(source.report_type as varchar) as report_type,
        cast(source.status as varchar) as status,
        --  dates: four mixed formats normalised in priority order
        --    1. ISO:           2022-12-25
        --    2. US slash:      12/13/2022
        --    3. Long text:     December 10, 2010
        --    4. Abbreviated:   Mar 08, 2012
        cast(
            coalesce(
                try_strptime(source.due_date, '%Y-%m-%d'),
                try_strptime(source.due_date, '%m/%d/%Y'),
                try_strptime(source.due_date, '%B %d, %Y'),
                try_strptime(source.due_date, '%b %d, %Y')
            ) as date
        ) as due_date,
        cast(
            coalesce(
                try_strptime(source.submission_date, '%Y-%m-%d'),
                try_strptime(source.submission_date, '%m/%d/%Y'),
                try_strptime(source.submission_date, '%B %d, %Y'),
                try_strptime(source.submission_date, '%b %d, %Y')
            ) as date
        ) as submission_date
    from source
)

select * from final
