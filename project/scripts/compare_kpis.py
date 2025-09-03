import pandas as pd
import argparse

def load_csv(path):
    try:
        return pd.read_csv(path)
    except FileNotFoundError:
        print(f"❌ File not found: {path}")
        exit(1)

def main(base_csv, var_csv, output_csv):
    # Load baseline and variant data
    base_df = load_csv(base_csv)
    var_df = load_csv(var_csv)

    # Ensure same sorting for clean comparison
    base_df = base_df.sort_values(by=base_df.columns[0])
    var_df = var_df.sort_values(by=var_df.columns[0])

    # Merge on road/edge identifier
    key_col = base_df.columns[0]  # first column (usually 'edge_id' or 'road')
    merged = base_df.merge(var_df, on=key_col, suffixes=('_baseline', '_ramped'))

    # Calculate deltas
    for col in base_df.columns[1:]:
        merged[f"{col}_delta"] = merged[f"{col}_ramped"] - merged[f"{col}_baseline"]

    # Save to output
    merged.to_csv(output_csv, index=False)
    print(f"✅ Comparison saved to {output_csv}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compare Baseline and Ramped KPI CSVs")
    parser.add_argument("--base", required=True, help="Path to baseline CSV")
    parser.add_argument("--var", required=True, help="Path to ramped CSV")
    parser.add_argument("--out", required=True, help="Path to save comparison CSV")
    args = parser.parse_args()

    main(args.base, args.var, args.out)
