import pandas as pd
import pytest
from pydantic import ValidationError

from altron.ops import (
    Plan,
    apply_plan,
)


def test_fill_mean():
    df = pd.DataFrame({'age': [10.0, None, 30.0]})
    plan = Plan(explanation='x', operations=[{'op': 'fill_na', 'column': 'age', 'strategy': 'mean'}])
    assert apply_plan(df, plan)['age'].tolist() == [10.0, 20.0, 30.0]

def test_fill_constant():
    df = pd.DataFrame({'status': ['active', None, 'inactive']})
    plan = Plan(explanation='x', operations=[{'op': 'fill_na', 'column': 'status', 'strategy': 'constant', 'value': 'unknown'}])
    assert apply_plan(df, plan)['status'].tolist() == ['active', 'unknown', 'inactive']

def test_drop_na():
    df = pd.DataFrame({'a': [1, None, 3]})
    plan = Plan(explanation='x', operations=[{'op': 'drop_na', 'columns': ['a']}])
    assert len(apply_plan(df, plan)) == 2

def test_drop_duplicates():
    df = pd.DataFrame({'a': [1, 1, 2]})
    plan = Plan(explanation='x', operations=[{'op': 'drop_duplicates'}])
    assert len(apply_plan(df, plan)) == 2

def test_rename():
    df = pd.DataFrame({'a': [1]})
    plan = Plan(explanation='x', operations=[{'op': 'rename', 'mapping': {'a': 'b'}}])
    assert 'b' in apply_plan(df, plan).columns

def test_cast_float():
    df = pd.DataFrame({'a': ['1.5', '2.5']})
    plan = Plan(explanation='x', operations=[{'op': 'cast', 'column': 'a', 'dtype': 'float'}])
    assert apply_plan(df, plan)['a'].dtype == 'float64'

def test_text_clean_lower():
    df = pd.DataFrame({'name': [' JOHN ', 'Jane']})
    plan = Plan(explanation='x', operations=[{'op': 'text_clean', 'column': 'name', 'action': 'lower'}])
    assert apply_plan(df, plan)['name'].tolist() == [' john ', 'jane']

def test_filter_equals():
    df = pd.DataFrame({'a': [1, 2, 3]})
    plan = Plan(explanation='x', operations=[{'op': 'filter', 'column': 'a', 'operator': '==', 'value': 2}])
    assert len(apply_plan(df, plan)) == 1

def test_drop_columns():
    df = pd.DataFrame({'a': [1], 'b': [2]})
    plan = Plan(explanation='x', operations=[{'op': 'drop_columns', 'columns': ['b']}])
    assert list(apply_plan(df, plan).columns) == ['a']

def test_unknown_column_rejected():
    df = pd.DataFrame({'a': [1]})
    plan = Plan(explanation='x', operations=[{'op': 'drop_columns', 'columns': ['nope']}])
    with pytest.raises(ValueError):
        apply_plan(df, plan)

def test_injected_operation_rejected():
    with pytest.raises(ValidationError):
        Plan.model_validate({'explanation': 'x', 'operations': [{'op': 'exec', 'code': 'import os'}]})

def test_clip_outliers():
    df = pd.DataFrame({'val': [10, 12, 11, 10, 1000]}) # 1000 is an outlier
    plan = Plan(explanation='x', operations=[{'op': 'clip_outliers', 'column': 'val'}])
    assert apply_plan(df, plan)['val'].max() < 1000

def test_filter_contains():
    df = pd.DataFrame({'city': ['New York', 'Los Angeles', 'Newark']})
    plan = Plan(explanation='x', operations=[{'op': 'filter', 'column': 'city', 'operator': 'contains', 'value': 'New'}])
    assert len(apply_plan(df, plan)) == 2

def test_text_clean_upper():
    df = pd.DataFrame({'name': ['john', 'jane']})
    plan = Plan(explanation='x', operations=[{'op': 'text_clean', 'column': 'name', 'action': 'upper'}])
    assert apply_plan(df, plan)['name'].tolist() == ['JOHN', 'JANE']

def test_fill_mode():
    df = pd.DataFrame({'status': ['active', 'active', None]})
    plan = Plan(explanation='x', operations=[{'op': 'fill_na', 'column': 'status', 'strategy': 'mode'}])
    assert apply_plan(df, plan)['status'].tolist() == ['active', 'active', 'active']