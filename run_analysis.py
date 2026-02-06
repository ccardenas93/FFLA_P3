#!/usr/bin/env python3
"""
Main entry point for the Climate Data analysis pipeline.
Use this script to run analysis, organize outputs, and generate reports.
"""

import sys
import os
import argparse

# Ensure 'organized' is in python path
# Add parent directory to path so we can import 'organized' as a package
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from organized.config import settings
from organized.scripts import generate_report, perform_analysis, generate_plots, generate_dashboard

def run_calculations():
    """Run data processing and calculations."""
    print("\nStarting calculations...")
    try:
        perform_analysis.run()
    except Exception as e:
        print(f"❌ Error during calculations: {e}")
        raise

def run_plotting():
    """Generate figures from computed data."""
    print("\nStarting figure generation...")
    try:
        generate_plots.run()
    except Exception as e:
        print(f"❌ Error during plotting: {e}")
        raise

def run_organize():
    """Generate dashboard (figures already in outputs/ by default)."""
    print("\nGenerating dashboard...")
    try:
        generate_dashboard.run()
    except Exception as e:
        print(f"❌ Error generating dashboard: {e}")
        raise

def run_report():
    """Generate Word document report from figures."""
    print("\nStarting report generation...")
    try:
        generate_report.create_document()
    except Exception as e:
        print(f"❌ Error during report generation: {e}")
        raise

def main():
    parser = argparse.ArgumentParser(description="Climate Data Analysis Pipeline")
    
    parser.add_argument("--compute", action="store_true", help="Run data processing and calculations (Merge -> PET -> WB)")
    parser.add_argument("--plot", action="store_true", help="Generate figures from the computed data")
    parser.add_argument("--organize", action="store_true", help="Generate dashboard (figures are already in outputs/)")
    parser.add_argument("--report", action="store_true", help="Generate Word document report from figures")
    parser.add_argument("--all", action="store_true", help="Run ALL steps: Compute -> Plot -> Organize -> Report")
    
    args = parser.parse_args()
    
    if not any(vars(args).values()):
        parser.print_help()
        return

    if args.compute or args.all:
        run_calculations()
        
    if args.plot or args.all:
        run_plotting()

    if args.organize or args.all:
        run_organize()
    
    if args.report or args.all:
        run_report()

if __name__ == "__main__":
    main()
