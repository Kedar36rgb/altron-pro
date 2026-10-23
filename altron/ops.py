import operator as pyop
from typing import Annotated, Literal, Union

import pandas as pd
from pydantic import BaseModel, Field


class DropNA(BaseModel):
    op: Literal['drop_na']
    columns: list[str] | None = None

class FillNA(BaseModel):
    op: Literal['fill_na']
    column: str
    strategy: Literal['mean', 'median', 'mode', 'constant']
    value: str | float | None = None

class DropDuplicates(BaseModel):
    op: Literal['drop_duplicates']
    columns: list[str] | None = None

class Rename(BaseModel):
    op: Literal['rename']
    mapping: dict[str, str]

class CastType(BaseModel):
    op: Literal['cast']
    column: str
    dtype: Literal['int', 'float', 'str', 'datetime', 'category']

class TextClean(BaseModel):
    op: Literal['text_clean']
    column: str
    action: Literal['strip', 'lower', 'upper', 'title']

class FilterRows(BaseModel):
    op: Literal['filter']
    column: str
    operator: Literal['==', '!=', '>', '<', '>=', '<=', 'contains']
    value: str | float

class DropColumns(BaseModel):
    op: Literal['drop_columns']
    columns: list[str]

class ClipOutliers(BaseModel):
    op: Literal['clip_outliers']
    column: str


Operation = Annotated[
    Union[DropNA, FillNA, DropDuplicates, Rename, CastType, TextClean, FilterRows, DropColumns, ClipOutliers],
    Field(discriminator='op'),
]

class Plan(BaseModel):
    explanation: str
    operations: list[Operation] = Field(default_factory=list, max_length=10)


def need(df, cols):
    bad = [c for c in cols if c not in df.columns]
    if bad:
        raise ValueError(f'Unknown column(s): {bad}')


COMPARE = {'==': pyop.eq, '!=': pyop.ne, '>': pyop.gt, '<': pyop.lt, '>=': pyop.ge, '<=': pyop.le}


def apply_op(df: pd.DataFrame, o) -> pd.DataFrame:
    df = df.copy()
    match o:
        case DropNA():
            need(df, o.columns or [])
            return df.dropna(subset=o.columns)
        case FillNA():
            need(df, [o.column])
            s = df[o.column]
            if o.strategy == 'constant':
                fill = o.value
            elif o.strategy == 'mode':
                fill = s.mode().iloc[0]
            else:
                fill = getattr(s, o.strategy)()
            df[o.column] = s.fillna(fill)
            return df
        case DropDuplicates():
            need(df, o.columns or [])
            return df.drop_duplicates(subset=o.columns)
        case Rename():
            need(df, list(o.mapping))
            return df.rename(columns=o.mapping)
        case CastType():
            need(df, [o.column])
            c = o.column
            if o.dtype == 'datetime':
                df[c] = pd.to_datetime(df[c], errors='coerce')
            elif o.dtype in ('int', 'float'):
                num = pd.to_numeric(df[c], errors='coerce')
                df[c] = num.astype('Int64') if o.dtype == 'int' else num
            else:
                df[c] = df[c].astype(o.dtype)
            return df
        case TextClean():
            need(df, [o.column])
            text = df[o.column].astype('string').str
            df[o.column] = getattr(text, o.action)()
            return df
        case FilterRows():
            need(df, [o.column])
            if o.operator == 'contains':
                mask = df[o.column].astype(str).str.contains(str(o.value), case=False, regex=False)
            else:
                mask = COMPARE[o.operator](df[o.column], o.value)
            return df[mask]
        case DropColumns():
            need(df, o.columns)
            return df.drop(columns=o.columns)
        case ClipOutliers():
            need(df, [o.column])
            q1, q3 = df[o.column].quantile([0.25, 0.75])
            iqr = q3 - q1
            df[o.column] = df[o.column].clip(q1 - 1.5 * iqr, q3 + 1.5 * iqr)
            return df
    raise ValueError('Unsupported operation')


def apply_plan(df: pd.DataFrame, plan: Plan) -> pd.DataFrame:
    for o in plan.operations:
        try:
            df = apply_op(df, o)
        except Exception as e:
            raise ValueError(f'{o.op} failed: {e}') from e
    return df