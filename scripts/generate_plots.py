#!/usr/bin/env python3
"""
Orchestrates the plotting pipeline.
Calls individual plotting scripts refactored in organized/scripts/wb/
"""

import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from organized.scripts.wb import (
    plot_timeseries, 
    plot_seasonal_cycle, 
    deliverable_key_numbers,
    plot_temp_timeseries,
    plot_warming_stripes,
    plot_ai_cdd_timeseries,
    window_bars_p_pet_wb,
    plot_wb_maps_windows,
    plot_monthly_wb_maps
)

from organized.scripts.wb.Deliverables import (
    deliverable_delta_bars,
    deliverable_maps_components,
    deliverable_season_extreme_maps,
    deliverable_timeseries_climatology
)

def run(region_codes=None):
    print("\nSTARTING PLOTTING PIPELINE")
    if region_codes:
        print(f"Targeting regions: {region_codes}")
    print("="*80)
    
    modules_to_run = [
        (plot_timeseries, "Standard Time Series"),
        (plot_temp_timeseries, "Temperature Time Series"),
        (plot_seasonal_cycle, "Seasonal Cycles"),
        (plot_warming_stripes, "Warming Stripes"),
        (plot_ai_cdd_timeseries, "AI & CDD Timeseries"),
        (window_bars_p_pet_wb, "Window Bar Plots"),
        (plot_wb_maps_windows, "Window Maps"),
        (plot_monthly_wb_maps, "Monthly Maps"),
        (deliverable_key_numbers, "Key Numbers Report"),
        (deliverable_delta_bars, "Deliverable: Delta Bars"),
        (deliverable_maps_components, "Deliverable: Map Components"),
        (deliverable_season_extreme_maps, "Deliverable: Season Extreme Maps"),
        (deliverable_timeseries_climatology, "Deliverable: Climatology Timeseries"),
    ]

    for module, name in modules_to_run:
        try:
            print(f"\nRunning: {name}...")
            # Inspect argument count to see if it accepts region_codes (simple duck typing or try/except)
            # Most of these scripts likely just iterate settings.REGIONS internally.
            # We need to verify if they accept arguments. 
            # If they don't, we might need to rely on them reading settings.REGIONS, 
            # OR we can modify settings.REGIONS temporarily?
            # Modifying settings.REGIONS globally is safer if we just want to run for one region.
            
            # Since we are running in the same process as app.py, modifying settings.REGIONS 
            # might be side-effect heavy if not reverted. 
            # BUT, for this run, we ONLY care about the active region.
            # So passing it is better.
            
            # Let's assume we will update the sub-modules to accept 'region_codes'. 
            # For now, let's try calling with kwargs if possible, or just run().
            # If we don't update them, they will run for all regions.
            # CRITICAL: We need to update the sub-modules too.
            # For this step, I will pass the argument. I will proceed to update sub-modules next.
            from inspect import signature
            sig = signature(module.run)
            if 'region_codes' in sig.parameters:
                module.run(region_codes=region_codes)
            else:
                module.run()
        except Exception as e:
            print(f"❌ Error in {name}: {e}")
            # import traceback
            # traceback.print_exc()

    print("\n" + "="*80)
    print("PLOTTING COMPLETED")
    print("="*80 + "\n")

if __name__ == "__main__":
    run()
