# In a new file, e.g., data_aggregator.py

# We assume you can import the necessary functions from your other modules
from epa_ghg_explorer import scrape_many
from comparison_engine import (
    pre_process_facility_data,
    run_compliance_check,
    load_all_rules,
)



def calculate_total_methane(ghg_data):
    """
    Calculate total methane emissions from all sources, handling missing
    or None data structures gracefully.
    """
    # Ensure ghg_data is a dictionary to prevent top-level errors.
    if not isinstance(ghg_data, dict):
        ghg_data = {}

    total = 0

    # Add emissions from all major sources
    sources = [
        ("PneumaticDeviceVentingDetails", "mt_ch4"),
        ("WellVentingDetails", "mt_ch4"),
        ("AssociatedGasVentingFlaringDetails", "mt_ch4"),
        ("CentrifugalCompressorsDetails", "mt_ch4"),
        ("ReciprocatingCompressorsDetails", "mt_ch4"),
        ("UniqueFlareStacks_Summary", "total_ch4_emissions_mt"),
        ("WellsWithFracturingDetails", "mt_ch4"),
        ("WellsWithoutFracturingDetails", "mt_ch4"),
        ("AtmosphericTanks_Summary", "mt_ch4")
    ]

    for source, field in sources:
        # Safely access nested data, defaulting to 0 if missing
        if source == "AtmosphericTanks_Summary":
            print(ghg_data.get(source))
        total += (ghg_data.get(source) or {}).get(field, 0) or 0

    # Add leak emissions
    leaks = ghg_data.get("LeaksCalculatedWithCountsFactors_SummaryBySourceType") or []
    if isinstance(leaks, list):
        for leak in leaks:
            if isinstance(leak, dict):
                total += leak.get("ch4_emissions_mt", 0) or 0

    return round(total, 2)


def generate_real_county_data(facility_ids):
    """
    Fetches, processes, and aggregates data for a list of facility IDs
    to produce a county-level summary.
    """
    print(f"--- Starting data generation for {len(facility_ids)} facilities... ---")

    # 1. Fetch all facility data in parallel
    print("Fetching raw XML data...")
    all_facility_data = scrape_many(facility_ids, year=2023)
    print("Data fetching complete.")

    # 2. Load the compliance rulebook once
    master_rulebook = load_all_rules()

    # 3. Initialize variables for aggregation
    total_methane_emissions = 0
    total_rules_checked = 0
    total_compliant_rules = 0
    facilities_with_any_non_compliance = 0
    processed_facility_count = 0

    # 4. Process each facility one by one
    print("Processing and running compliance checks...")
    for fid, ghg_data in all_facility_data.items():
        if "error" in ghg_data:
            print(f"Skipping facility {fid} due to fetch error: {ghg_data['error']}")
            continue

        processed_facility_count += 1
        
        # Aggregate total methane emissions
        total_methane_emissions += calculate_total_methane(ghg_data)

        # Run compliance checks
        is_facility_critical = False
        facility_flat_data = pre_process_facility_data(ghg_data)
        for rule_obj in master_rulebook.values():
            result = run_compliance_check(rule_obj, facility_flat_data)
            
            # Don't count "N/A" or "Data Missing" statuses in compliance rate
            if result['status'] in ["In Compliance", "Out of Compliance"]:
                total_rules_checked += 1
                if result['status'] == "In Compliance":
                    total_compliant_rules += 1
                else:
                    # If even one rule is "Out of Compliance", flag the facility
                    is_facility_critical = True
        
        if is_facility_critical:
            facilities_with_any_non_compliance += 1

    print("Aggregation complete.")

    # 5. Calculate final summary metrics
    avg_compliance_rate = (total_compliant_rules / total_rules_checked) if total_rules_checked > 0 else 0
    
    # NOTE: fix economic impact
    economic_impact_placeholder = round(total_methane_emissions * 0.0002, 1) # Example calc

    # 6. Return the data in the exact format the Dash layout expects
    county_summary = {
        'facilities': processed_facility_count,
        'methane_emissions': round(total_methane_emissions),
        'avg_compliance': avg_compliance_rate,
        'critical_facilities': facilities_with_any_non_compliance,
        'economic_impact': economic_impact_placeholder
    }

    return county_summary