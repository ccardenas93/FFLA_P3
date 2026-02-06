#!/usr/bin/env python3
"""
Orchestrates the calculation pipeline:
1. Merge daily files (National level only)
2. Compute PET (Regional level)
3. Calculate Water Balance (Regional level)
"""

import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from organized.config import settings
from organized.scripts.wb import merge_daily, compute_pet, water_balance

def run():
    print("\nSTARTING CALCULATION PIPELINE")
    print("="*80)
    # Read from inputs/, write derived data (PET, WB) to outputs/<Region>/
    region_pairs = [
        (settings.get_region_input_dir(code), settings.get_region_output_dir(code))
        for code in settings.REGIONS
    ]
    for inp, out in region_pairs:
        print(f"  Input: {inp}  ->  Output: {out}")
    # Step 2: PET (read tas* from input, write pet to output)
    compute_pet.run(region_pairs=region_pairs)
    # Step 3: Water Balance (read pr from input, pet from output; write wb to output)
    water_balance.run(region_pairs=region_pairs)
    print("\n" + "="*80)
    print("CALCULATIONS COMPLETED")
    print("="*80 + "\n")

if __name__ == "__main__":
    run()
