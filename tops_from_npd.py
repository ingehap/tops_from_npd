#!/usr/bin/env python3
"""
tops_from_npd.py

Create tops CSV files (one per stratigraphic level: GROUP, FORMATION, MEMBER)
from an NPD `strat_litho_wellbore.csv` export plus a well-list file.

Terminal port of the Colab notebook
"Create_tops_files_from_NPD_file.ipynb".

Usage examples
--------------
    # Defaults: ./strat_litho_wellbore.csv, ./my.well_list, output to .
    python tops_from_npd.py

    # Explicit paths
    python tops_from_npd.py -s data/strat_litho_wellbore.csv \\
                            -w data/my.well_list \\
                            -o output/

    # Only process FORMATION level
    python tops_from_npd.py -u FORMATION
"""

from __future__ import annotations

import argparse
import csv
import os
import sys

import pandas as pd


# ---------------------------------------------------------------------------
# Input loading
# ---------------------------------------------------------------------------
def load_well_list(path: str) -> list[str]:
    """Read a whitespace-separated well-list file and return the list of wells.

    The original notebook splits the file on spaces and drops the first five
    tokens (a header). That behaviour is preserved here.
    """
    with open(path, "r") as f:
        content = f.read()

    tokens = content.split(" ")
    return tokens[5:]  # drop the 5-token header, matching the notebook


def load_strat_dataframe(path: str) -> pd.DataFrame:
    """Load the NPD strat_litho_wellbore CSV and normalise well names.

    The notebook prefixes wellbore names with ``NO_`` and replaces spaces
    with underscores so that they match the names used in the well list.
    """
    df = pd.read_csv(path)

    df["wlbName"] = df["wlbName"].str.replace(" ", "_")
    df["wlbName"] = "NO_" + df["wlbName"]

    df = df[["wlbName", "lsuTopDepth", "lsuBottomDepth", "lsuName", "lsuLevel"]]
    return df


# ---------------------------------------------------------------------------
# Output writing
# ---------------------------------------------------------------------------
def write_tops_to_file(
    df: pd.DataFrame,
    selected_wells: list[str],
    unit: str,
    output_file: str,
) -> bool:
    """Write a tops CSV for one stratigraphic level (e.g. GROUP/FORMATION/MEMBER).

    Returns True if a file was written, False if no rows matched the unit.
    """
    df_unit = df[df["lsuLevel"] == unit]
    df_unit = df_unit[df_unit["wlbName"].isin(selected_wells)]

    if df_unit.empty:
        print(f"No data found for unit: {unit}", file=sys.stderr)
        return False

    df_unit = df_unit.sort_values(by=["wlbName", "lsuTopDepth"])
    rows = df_unit.values.tolist()

    with open(output_file, "w", newline="", encoding="utf-8") as outfile:
        writer = csv.writer(outfile)

        # Headers
        writer.writerow(["WELL", "DEPTH", unit])
        writer.writerow(["", "METRES", ""])

        previous = rows[0]

        for current in rows[1:]:
            # Same well and current top == previous bottom -> continuous interval
            if current[0] == previous[0] and current[1] == previous[2]:
                writer.writerow([previous[0], previous[1], previous[3]])
            else:
                writer.writerow([previous[0], previous[1], previous[3]])
                writer.writerow([previous[0], previous[2]])

            previous = current

        # Flush the last interval
        writer.writerow([previous[0], previous[1], previous[3]])
        writer.writerow([previous[0], previous[2]])

    print(f"Created: {output_file}")
    return True


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create tops CSV files from an NPD strat_litho_wellbore export "
            "and a well-list file."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-s", "--strat",
        default="strat_litho_wellbore.csv",
        help="Path to the NPD strat_litho_wellbore CSV file.",
    )
    parser.add_argument(
        "-w", "--wells",
        default="my.well_list",
        help="Path to the well-list file.",
    )
    parser.add_argument(
        "-o", "--outdir",
        default=".",
        help="Directory to write the output tops CSV files into.",
    )
    parser.add_argument(
        "-u", "--units",
        nargs="+",
        default=["GROUP", "FORMATION", "MEMBER"],
        help="Stratigraphic unit levels to process.",
    )
    parser.add_argument(
        "--preview-rows",
        type=int,
        default=5,
        help="Number of rows from the loaded dataframe to preview (0 to skip).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    # Validate inputs
    if not os.path.isfile(args.strat):
        print(f"Error: strat file not found: {args.strat}", file=sys.stderr)
        return 1
    if not os.path.isfile(args.wells):
        print(f"Error: well list file not found: {args.wells}", file=sys.stderr)
        return 1

    os.makedirs(args.outdir, exist_ok=True)

    # Load
    print(f"Reading strat data from: {args.strat}")
    df = load_strat_dataframe(args.strat)

    print(f"Reading well list from: {args.wells}")
    selected_wells = load_well_list(args.wells)
    print(f"Selected wells: {len(selected_wells)}")

    if args.preview_rows > 0:
        print("\nData loaded (preview):")
        print(df.head(args.preview_rows).to_string(index=False))
        print()

    # Process each requested level
    any_written = False
    for unit in args.units:
        out_path = os.path.join(args.outdir, f"npd_{unit.lower()}_tops.csv")
        if write_tops_to_file(df, selected_wells, unit, out_path):
            any_written = True

    return 0 if any_written else 2


if __name__ == "__main__":
    sys.exit(main())
