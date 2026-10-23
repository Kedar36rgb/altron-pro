
def quality_report(df):
    n = max(len(df), 1)
    # Calculate missing percentage
    missing_pct = float(df.isna().sum().sum()) / (n * max(df.shape[1], 1)) * 100
    # Calculate duplicates
    dupes = int(df.duplicated().sum())
    # Find constant columns (all same value)
    constant = [c for c in df if df[c].nunique(dropna=False) <= 1]
    # Find mostly empty columns (>40% missing)
    sparse = [c for c in df if df[c].isna().mean() > 0.4]
    
    # Calculate score (0-100)
    score = max(0, 100 - missing_pct - (100 * dupes / n) - (5 * len(constant)) - (5 * len(sparse)))
    
    return {
        'score': round(score), 
        'missing_pct': round(missing_pct, 1),
        'duplicate_rows': dupes, 
        'constant_columns': constant,
        'mostly_empty_columns': sparse
    }