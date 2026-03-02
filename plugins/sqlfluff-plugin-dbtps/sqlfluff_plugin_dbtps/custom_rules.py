from typing import Tuple
from sqlfluff.core.rules import BaseRule, LintResult, RuleContext
from sqlfluff.core.rules.crawlers import SegmentSeekerCrawler

class Rule_DBTPS_L001(BaseRule):
    """ALL-PERF-03: No bare union (use 'union all')."""
    name = "dbtps.no_bare_union"
    groups: Tuple[str, ...] = ("all", "dbt_public_sector")
    crawl_behaviour = SegmentSeekerCrawler({"set_operator"})
    
    def _eval(self, context: RuleContext) -> LintResult:
        assert context.segment.is_type("set_operator")
        if "union" in context.segment.raw.lower() and not (
            "all" in context.segment.raw.lower() or "distinct" in context.segment.raw.lower()
        ):
            return LintResult(
                anchor=context.segment,
                description="ALL-PERF-03: bare 'union' found; use 'union all'"
            )
        return LintResult()

class Rule_DBTPS_L002(BaseRule):
    """ALL-PERF-03: No select distinct"""
    name = "dbtps.no_select_distinct"
    groups: Tuple[str, ...] = ("all", "dbt_public_sector")
    crawl_behaviour = SegmentSeekerCrawler({"select_clause_modifier"})
    
    def _eval(self, context: RuleContext) -> LintResult:
        if context.segment.raw.upper() == "DISTINCT":
            return LintResult(
                anchor=context.segment,
                description="ALL-PERF-03: 'select distinct' is not allowed."
            )
        return LintResult()

class Rule_DBTPS_L003(BaseRule):
    """ALL-PERF-04: No subqueries."""
    name = "dbtps.no_subqueries"
    groups: Tuple[str, ...] = ("all", "dbt_public_sector")
    crawl_behaviour = SegmentSeekerCrawler({"select_statement"})
    
    def _eval(self, context: RuleContext) -> LintResult:
        # A subquery is a select_statement inside a bracketed segment.
        if context.parent_stack and context.parent_stack[-1].is_type("bracketed"):
            # CTE bodies are also select_statements inside brackets — do not flag them.
            if any(p.is_type("common_table_expression") for p in context.parent_stack):
                return LintResult()
            return LintResult(
                anchor=context.segment,
                description="ALL-PERF-04: subquery found (use CTEs instead)"
            )
        return LintResult()

class Rule_DBTPS_L004(BaseRule):
    """ALL-CTE-11: Simple final select."""
    name = "dbtps.simple_final_select"
    groups: Tuple[str, ...] = ("all", "dbt_public_sector")
    crawl_behaviour = SegmentSeekerCrawler({"file"})
    
    def _eval(self, context: RuleContext) -> LintResult:
        # Iterate backward to find the last select statement
        last_select = None
        for seg in reversed(list(context.segment.recursive_crawl("select_statement"))):
            last_select = seg
            break
        
        if last_select:
            # Check if it's 'select * from <something>'
            select_clause = next(last_select.recursive_crawl("select_clause"), None)
            from_clause = next(last_select.recursive_crawl("from_clause"), None)
            
            if select_clause and from_clause:
                stars = list(select_clause.recursive_crawl("star"))
                if not stars:
                    return LintResult(
                        anchor=last_select,
                        description="ALL-CTE-11: final select is not 'select * from cte'"
                    )
        return LintResult()

class Rule_DBTPS_L005(BaseRule):
    """ALL-CTE-01: refs/source calls in import CTEs."""
    name = "dbtps.import_ctes_at_top"
    groups: Tuple[str, ...] = ("all", "dbt_public_sector")
    crawl_behaviour = SegmentSeekerCrawler({"join_clause"})
    
    def _eval(self, context: RuleContext) -> LintResult:
        if "{{ ref(" in context.segment.raw or "{{ source(" in context.segment.raw or "{{ref(" in context.segment.raw or "{{source(" in context.segment.raw:
            return LintResult(
                anchor=context.segment,
                description="ALL-CTE-01: ref/source found in join_clause; should be in import CTEs"
            )
        return LintResult()

class Rule_DBTPS_L006(BaseRule):
    """ALL-CFG-02: config block at top of file."""
    name = "dbtps.config_block_at_top"
    groups: Tuple[str, ...] = ("all", "dbt_public_sector")
    crawl_behaviour = SegmentSeekerCrawler({"file"})
    
    def _eval(self, context: RuleContext) -> LintResult:
        # Find the first executable code / templater block
        first_segment = None
        config_segment = None
        for seg in context.segment.segments:
            if getattr(seg, "is_whitespace", False) or getattr(seg, "is_comment", False) or getattr(seg, "is_meta", False):
                continue
            first_segment = first_segment or seg
            if "{{ config(" in getattr(seg, "raw", "") or "{{config(" in getattr(seg, "raw", ""):
                config_segment = seg
        
        if config_segment and config_segment != first_segment:
            return LintResult(
                anchor=config_segment,
                description="ALL-CFG-02: config block must be the first statement"
            )
        return LintResult()

class Rule_DBTPS_L007(BaseRule):
    """ALL-PERF-02: No generate_uuid()"""
    name = "dbtps.no_generate_uuid"
    groups: Tuple[str, ...] = ("all", "dbt_public_sector")
    crawl_behaviour = SegmentSeekerCrawler({"function"})
    
    def _eval(self, context: RuleContext) -> LintResult:
        raw_func = context.segment.raw.lower()
        if "generate_uuid" in raw_func or "uuid()" in raw_func.replace(" ", ""):
            return LintResult(
                anchor=context.segment,
                description="ALL-PERF-02: generate_uuid() is not reproducible"
            )
        return LintResult()
