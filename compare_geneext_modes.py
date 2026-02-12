#!/usr/bin/env python3

import argparse
import subprocess
import os
import sys
import shutil

def run_command(cmd, verbose=False):
    cmd_str = ' '.join(cmd) if isinstance(cmd, list) else cmd
    if verbose:
        print(f"Running: {cmd_str}")

    # Use shell=False for list of args
    result = subprocess.run(cmd, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    if result.returncode != 0:
        print(f"Error running command: {cmd_str}")
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
        sys.exit(1)
    return result.stdout

def compare_files(file1, file2):
    # Reads files line by line and compares them
    # This allows for potentially ignoring specific lines if needed in future
    # For now, strict comparison
    if not os.path.exists(file1):
        print(f"File not found: {file1}")
        return False
    if not os.path.exists(file2):
        print(f"File not found: {file2}")
        return False

    with open(file1, 'r') as f1, open(file2, 'r') as f2:
        lines1 = f1.readlines()
        lines2 = f2.readlines()

    if len(lines1) != len(lines2):
        print(f"Files have different number of lines: {len(lines1)} vs {len(lines2)}")
        return False

    diffs = 0
    for i, (l1, l2) in enumerate(zip(lines1, lines2)):
        if l1 != l2:
            print(f"Difference at line {i+1}:")
            print(f"Ref:  {l1.strip()}")
            print(f"Test: {l2.strip()}")
            diffs += 1
            if diffs >= 5:
                print("... and more differences.")
                return False
    return diffs == 0

def cleanup(paths):
    for p in paths:
        if os.path.exists(p):
            if os.path.isdir(p):
                shutil.rmtree(p)
            else:
                os.remove(p)

def main():
    parser = argparse.ArgumentParser(description="Compare GeneExt runs with BAM vs Peaks.")
    parser.add_argument('-g', '--genome', default='test_data/annotation.gtf', help='Genome annotation file')
    parser.add_argument('-b', '--bam', default='test_data/alignments.bam', help='BAM alignment file')
    parser.add_argument('--keep', action='store_true', help='Keep temporary files and outputs even on success')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')

    args = parser.parse_args()

    gtf_file = args.genome
    bam_file = args.bam

    # Check inputs
    if not os.path.exists(gtf_file):
        print(f"Error: Genome file not found: {gtf_file}")
        sys.exit(1)
    if not os.path.exists(bam_file):
        print(f"Error: BAM file not found: {bam_file}")
        sys.exit(1)

    out_ref = "output_ref.gtf"
    out_test = "output_test.gtf"

    tmp_ref = "tmp_ref"
    tmp_test = "tmp_test"

    # Cleanup beforehand to ensure clean state
    cleanup([tmp_ref, tmp_test, out_ref, out_test, "GeneExt.log", out_ref + ".GeneExt.log", out_test + ".GeneExt.log"])

    success = False
    try:
        # Run 1: Reference (with BAM, peak filtering disabled)
        print("--- Running Mode 1: Reference (BAM input, --peak_perc 0) ---")
        cmd_ref = ["python3", "geneext.py", "-g", gtf_file, "-b", bam_file, "-o", out_ref, "-t", tmp_ref, "--peak_perc", "0"]
        run_command(cmd_ref, args.verbose)

        # Identify peaks file
        # geneext.py saves MACS2 peaks to 'allpeaks.bed' in temp dir
        peaks_file = os.path.join(tmp_ref, "allpeaks.bed")
        if not os.path.exists(peaks_file):
            print(f"Error: Peaks file not found at {peaks_file}")
            sys.exit(1)

        print(f"Peaks file generated at: {peaks_file}")

        # Run 2: Test (with Peaks, skipping BAM)
        print("--- Running Mode 2: Test (Peaks input, skipping BAM) ---")
        cmd_test = ["python3", "geneext.py", "-g", gtf_file, "-p", peaks_file, "-o", out_test, "-t", tmp_test]
        run_command(cmd_test, args.verbose)

        # Compare
        print("--- Comparing Outputs ---")
        if compare_files(out_ref, out_test):
            print("SUCCESS: The outputs are identical.")
            success = True
        else:
            print("FAILURE: The outputs differ.")
            success = False

    except SystemExit:
        success = False
        raise
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        success = False
        raise

    finally:
        files_to_clean = [tmp_ref, tmp_test, out_ref, out_test]
        # Clean logs too if successful
        log_files = ["GeneExt.log", out_ref + ".GeneExt.log", out_test + ".GeneExt.log"]

        if success and not args.keep:
            print("Cleaning up...")
            cleanup(files_to_clean + log_files)
        else:
            if not success:
                print("\nComparison failed or script error. Artifacts preserved for inspection:")
            else:
                print("\n--keep flag set. Artifacts preserved:")

            print(f"  Reference Output: {out_ref}")
            print(f"  Test Output:      {out_test}")
            print(f"  Reference Temp:   {tmp_ref}")
            print(f"  Test Temp:        {tmp_test}")
            # Check for logs
            for log in log_files:
                if os.path.exists(log):
                    print(f"  Log File:         {log}")

if __name__ == "__main__":
    main()
