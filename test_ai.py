import pandas as pd
from altron.llm import plan_cleaning

# Create a tiny messy dataset
df = pd.DataFrame({
    'Name': [' john ', 'JANE', 'Bob'],
    'Age': [25, None, 30],
    'Salary': [50000, 60000, None]
})

print("Original Data:")
print(df)

print("\nAsking AI to clean the data...")
try:
    # Ask the AI to fix missing ages and clean names
    plan, cleaned_df = plan_cleaning(
        df, 
        "Fill missing Age with the mean, and strip whitespace and lowercase the Name column.", 
        share_samples=False
    )
    
    print("\nAI Explanation:")
    print(plan.explanation)
    
    print("\nOperations JSON:")
    for op in plan.operations:
        print(op.model_dump_json())
        
    print("\nCleaned Data:")
    print(cleaned_df)

except Exception as e:
    print(f"\nError: {e}")