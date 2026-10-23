from typing import Literal

import plotly.express as px
from pydantic import BaseModel, Field

from .ops import need


class ChartSpec(BaseModel):
    kind: Literal['bar', 'line', 'scatter', 'histogram', 'box', 'pie']
    x: str
    y: str | None = None
    color: str | None = None
    agg: Literal['sum', 'mean', 'median', 'count'] | None = None
    top_n: int | None = Field(None, ge=1, le=50)
    title: str = ''

def render(df, s: ChartSpec):
    # Check if the columns exist in the dataframe
    need(df, [c for c in (s.x, s.y, s.color) if c])
    
    d = df
    if s.agg and s.y:
        keys = [s.x] + ([s.color] if s.color else [])
        d = df.groupby(keys, as_index=False)[s.y].agg(s.agg)
        if s.top_n:
            d = d.nlargest(s.top_n, s.y)
            
    if s.kind == 'pie':
        return px.pie(d, names=s.x, values=s.y, title=s.title)
    if s.kind == 'histogram':
        return px.histogram(d, x=s.x, color=s.color, title=s.title)
        
    fn = {
        'bar': px.bar, 
        'line': px.line, 
        'scatter': px.scatter, 
        'box': px.box
    }[s.kind]
    
    return fn(d, x=s.x, y=s.y, color=s.color, title=s.title)