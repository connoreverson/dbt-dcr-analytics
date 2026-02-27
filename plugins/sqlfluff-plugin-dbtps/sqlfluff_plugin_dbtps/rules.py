from typing import List, Type
from sqlfluff.core.plugin import hookimpl
from sqlfluff.core.rules import BaseRule

@hookimpl
def get_rules() -> List[Type[BaseRule]]:
    from .custom_rules import (
        Rule_DBTPS_L001, Rule_DBTPS_L002, Rule_DBTPS_L003, Rule_DBTPS_L004,
        Rule_DBTPS_L005, Rule_DBTPS_L006, Rule_DBTPS_L007
    )
    return [
        Rule_DBTPS_L001, Rule_DBTPS_L002, Rule_DBTPS_L003, Rule_DBTPS_L004,
        Rule_DBTPS_L005, Rule_DBTPS_L006, Rule_DBTPS_L007
    ]
