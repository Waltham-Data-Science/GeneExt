#!/usr/bin/env python3

import argparse
import sys
import os
import pandas as pd
import numpy as np

# Add the project root to sys.path to allow importing geneext
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

try:
    from geneext.helper import parse_gtf, parse_gff, Region
except ImportError as e:
    # Try adding the current directory if run from root
    if os.getcwd() not in sys.path:
        sys.path.append(os.getcwd())
    try:
        from geneext.helper import parse_gtf, parse_gff, Region
    except ImportError as e:
        print(f"Error importing geneext.helper: {e}")
        sys.exit(1)

def load_genes(filepath):
    ext = os.path.splitext(filepath)[1].lower()
    if ext == '.gtf':
        return parse_gtf(filepath, featuretype='gene')
    elif ext == '.gff' or ext == '.gff3':
        return parse_gff(filepath, featuretype='gene')
    else:
        print(f"Unknown file extension: {ext}. Assuming GTF.")
        return parse_gtf(filepath, featuretype='gene')

def main():
    parser = argparse.ArgumentParser(description="Compare GeneExt results with original annotation.")
    parser.add_argument("reference_file", help="Path to the original GTF/GFF file")
    parser.add_argument("extended_file", help="Path to the extended GTF/GFF file")

    args = parser.parse_args()

    ref_file = args.reference_file
    ext_file = args.extended_file

    if not os.path.exists(ref_file):
        print(f"Error: Reference file not found: {ref_file}")
        sys.exit(1)
    if not os.path.exists(ext_file):
        print(f"Error: Extended file not found: {ext_file}")
        sys.exit(1)

    print(f"Loading genes from {ref_file}...")
    try:
        ref_genes = load_genes(ref_file)
        print(f"Loaded {len(ref_genes)} genes from reference.")
    except Exception as e:
        print(f"Error loading genes from {ref_file}: {e}")
        sys.exit(1)

    print(f"Loading genes from {ext_file}...")
    try:
        ext_genes = load_genes(ext_file)
        print(f"Loaded {len(ext_genes)} genes from extended file.")
    except Exception as e:
        print(f"Error loading genes from {ext_file}: {e}")
        sys.exit(1)

    # Create dictionaries
    ref_dict = {g.id: g for g in ref_genes}
    ext_dict = {g.id: g for g in ext_genes}

    # Find common genes
    common_ids = set(ref_dict.keys()) & set(ext_dict.keys())
    print(f"Found {len(common_ids)} common genes.")

    comparison_results = []

    for gene_id in common_ids:
        ref_gene = ref_dict[gene_id]
        ext_gene = ext_dict[gene_id]

        extension_len = 0
        if ref_gene.strand == '+':
            extension_len = ext_gene.end - ref_gene.end
        elif ref_gene.strand == '-':
            extension_len = ref_gene.start - ext_gene.start

        # Only include if there is a change or if we want all
        # Let's include all common genes to show what happened

        comparison_results.append({
            'GeneID': gene_id,
            'OldStart': ref_gene.start,
            'OldEnd': ref_gene.end,
            'NewStart': ext_gene.start,
            'NewEnd': ext_gene.end,
            'ExtensionLength': extension_len,
            'Strand': ref_gene.strand
        })

    if not comparison_results:
        print("No common genes found or no comparison results generated.")
        return

    df = pd.DataFrame(comparison_results)

    # Calculate stats
    total_genes = len(comparison_results)
    extended_genes = df[df['ExtensionLength'] > 0]
    num_extended = len(extended_genes)
    if num_extended > 0:
        median_ext = extended_genes['ExtensionLength'].median()
        max_ext = extended_genes['ExtensionLength'].max()
        min_ext = extended_genes['ExtensionLength'].min()
    else:
        median_ext = 0
        max_ext = 0
        min_ext = 0

    summary = (
        f"Total genes compared: {total_genes}\n"
        f"Number of extended genes: {num_extended}\n"
        f"Median extension length: {median_ext}\n"
        f"Max extension length: {max_ext}\n"
        f"Min extension length: {min_ext}\n"
    )

    output_dir = os.path.dirname(os.path.abspath(ext_file))
    summary_file = os.path.join(output_dir, "ComparisonSummary.txt")
    table_file = os.path.join(output_dir, "ComparisonTable.csv")

    with open(summary_file, "w") as f:
        f.write(summary)

    df.to_csv(table_file, index=False)

    print(f"Comparison complete.")
    print(f"Summary written to: {summary_file}")
    print(f"Table written to: {table_file}")

if __name__ == "__main__":
    main()
