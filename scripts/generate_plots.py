#!/usr/bin/env python3
"""
Orchestrates the plotting pipeline.
Calls individual plotting scripts refactored in organized/scripts/wb/
"""

import sys
import os


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

















            from inspect import signature
            sig = signature(module.run)
            if 'region_codes' in sig.parameters:
                module.run(region_codes=region_codes)
            else:
                module.run()
        except Exception as e:
            print(f"❌ Error in {name}: {e}")



    print("\n" + "="*80)
    print("PLOTTING COMPLETED")
    print("="*80 + "\n")

if __name__ == "__main__":
    run()
