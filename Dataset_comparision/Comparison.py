import pandas as pd

# Function to find the 'Title' column by matching possible variations in column names
def find_title_column(columns):
    for col in columns:
        if 'title' in str(col).lower():
            return col
    return None

# Load IEEE Dataset
ieee_data = pd.read_excel("250507_IEEE_Auswertung.xlsx")
ieee_title_col = find_title_column(ieee_data.columns)
if ieee_title_col is None:
    raise ValueError("No 'Title' column found in IEEE dataset.")
ieee_titles = ieee_data[ieee_title_col].dropna().astype(str).str.strip()

# Load Scopus Dataset
scopus_data = pd.read_excel("scopus_data_final_Auswertung.xlsx")
scopus_title_col = find_title_column(scopus_data.columns)
if scopus_title_col is None:
    raise ValueError("No 'Title' column found in Scopus dataset.")
scopus_titles = scopus_data[scopus_title_col].dropna().astype(str).str.strip()

# Load ScienceDirect Dataset (special structure handling)
science_direct_data = pd.read_excel("Lit_rech_ScienceDirect_draft-final_Auswertung.xlsx")
science_direct_titles = science_direct_data['Unnamed: 2'].iloc[2:].dropna().astype(str).str.strip()

# Comparison Operations
ieee_scopus_common = set(ieee_titles).intersection(set(scopus_titles))
ieee_sciencedirect_common = set(ieee_titles).intersection(set(science_direct_titles))
scopus_sciencedirect_common = set(scopus_titles).intersection(set(science_direct_titles))

# Generate Consolidated Report
output_file = "consolidated_similarity_report.txt"
with open(output_file, 'w', encoding='utf-8') as f:
    # IEEE vs Scopus
    f.write(f"IEEE and Scopus similarities: {len(ieee_scopus_common)}\n")
    if ieee_scopus_common:
        for title in sorted(ieee_scopus_common):
            f.write(f"{title}\n")
    f.write("\n")

    # IEEE vs ScienceDirect
    f.write(f"IEEE and ScienceDirect similarities: {len(ieee_sciencedirect_common)}\n")
    if ieee_sciencedirect_common:
        for title in sorted(ieee_sciencedirect_common):
            f.write(f"{title}\n")
    f.write("\n")

    # Scopus vs ScienceDirect
    f.write(f"Scopus and ScienceDirect similarities: {len(scopus_sciencedirect_common)}\n")
    if scopus_sciencedirect_common:
        for title in sorted(scopus_sciencedirect_common):
            f.write(f"{title}\n")

print(f"Consolidated similarity report saved to {output_file}")
