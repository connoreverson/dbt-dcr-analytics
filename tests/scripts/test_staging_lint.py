# tests/scripts/test_staging_lint.py
from scripts.grain.staging_lint import check_staging_purity


def test_clean_staging_passes():
    sql = """
    with source as (
        select * from {{ source('vistareserve', 'reservations') }}
    )
    select
        cast(id as integer) as reservation_id,
        trim(guest_name) as guest_name,
        cast(created_at as timestamp) as created_at
    from source
    """
    findings = check_staging_purity(sql)
    violations = [f for f in findings if f["severity"] == "error"]
    assert len(violations) == 0


def test_forbidden_join():
    sql = """
    select a.id, b.name
    from source_a a
    left join source_b b on a.id = b.id
    """
    findings = check_staging_purity(sql)
    assert any(f["check"] == "forbidden_join" for f in findings)


def test_forbidden_group_by():
    sql = """
    select category, count(*) as cnt
    from source
    group by category
    """
    findings = check_staging_purity(sql)
    assert any(f["check"] == "forbidden_group_by" for f in findings)


def test_forbidden_where():
    sql = """
    select id, name
    from source
    where status != 'deleted'
    """
    findings = check_staging_purity(sql)
    assert any(f["check"] == "forbidden_where" for f in findings)


def test_case_statement_flagged():
    sql = """
    select
        id,
        case when type = 'A' then 'Active' else 'Inactive' end as status
    from source
    """
    findings = check_staging_purity(sql)
    assert any(f["check"] == "logic_beyond_cast_rename" for f in findings)


def test_allowed_functions_pass():
    """CAST, TRIM, LOWER, UPPER, COALESCE are allowed in staging."""
    sql = """
    select
        cast(id as integer) as id,
        lower(trim(name)) as name,
        coalesce(email, '') as email,
        upper(code) as code
    from source
    """
    findings = check_staging_purity(sql)
    violations = [f for f in findings if f["severity"] == "error"]
    assert len(violations) == 0
