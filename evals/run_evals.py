import io
import json
import os
import sys

# Tell Python to look in the root directory for the 'altron' module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from altron.llm import plan_cleaning


def run_evals():
    # Load cases relative to this script's directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    cases_path = os.path.join(current_dir, 'cases.json')
    
    with open(cases_path, 'r') as f:
        cases = json.load(f)
        
    passed = 0
    total = len(cases)
    
    print(f"Running {total} evaluation cases...\n")
    
    for case in cases:
        df = pd.read_csv(io.StringIO(case['csv']))
        print(f"Testing: '{case['request']}'")
        
        try:
            # Ask the AI to plan and apply
            _plan, result_df = plan_cleaning(df, case['request'])
            
            # Check 1: Row count
            if len(result_df) != case['expect_rows']:
                print(f"  ❌ Failed: Expected {case['expect_rows']} rows, got {len(result_df)}")
                continue
                
            # Check 2: Columns
            if set(result_df.columns) != set(case['expect_cols']):
                print(f"  ❌ Failed: Expected columns {case['expect_cols']}, got {list(result_df.columns)}")
                continue
                
            # Check 3: No nulls in specific column
            if 'expect_no_nulls_in' in case:
                col = case['expect_no_nulls_in']
                if result_df[col].isna().any():
                    print(f"  ❌ Failed: Column '{col}' still has missing values")
                    continue
                    
            # Check 4: Specific value
            if 'expect_value_in_col' in case:
                col = case['expect_value_in_col']['col']
                row = case['expect_value_in_col']['row']
                expected_val = case['expect_value_in_col']['expected']
                actual_val = result_df.iloc[row][col]
                if str(actual_val) != str(expected_val):
                    print(f"  ❌ Failed: Expected '{expected_val}' in row {row}, got '{actual_val}'")
                    continue
                    
            print("  ✅ Passed")
            passed += 1
            
        except Exception as err:
            print(f"  ❌ Failed with Error: {err}")
            
    print("\n==================================")
    print(f"FINAL SCORE: {passed} / {total} ({(passed/total)*100:.1f}%)")
    print("==================================")

if __name__ == "__main__":
    run_evals()