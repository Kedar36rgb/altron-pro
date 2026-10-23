from typing import Literal
import pandas as pd
from pydantic import BaseModel
from .ops import need

class PivotSpec(BaseModel):
    index: list[str]
    columns: list[str] | None = None
    values: str
    aggfunc: Literal['sum', 'mean', 'count', 'median', 'max', 'min']

def build_pivot(df, spec: PivotSpec):
    # Validate columns
    cols_to_check = spec.index + (spec.columns or []) + [spec.values]
    need(df, cols_to_check)
    
    # Build pivot table
    pivot_df = df.pivot_table(
        index=spec.index,
        columns=spec.columns,
        values=spec.values,
        aggfunc=spec.aggfunc
    ).reset_index()
    
    return pivot_df