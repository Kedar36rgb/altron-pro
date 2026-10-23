from openpyxl.utils import get_column_letter
from pydantic import BaseModel

class FormulaSpec(BaseModel):
    formula: str
    explanation: str

def column_map(df):
    # Creates a string like "A=Name, B=Age, C=Salary"
    return ', '.join(f'{get_column_letter(i + 1)}={c}' for i, c in enumerate(df.columns))