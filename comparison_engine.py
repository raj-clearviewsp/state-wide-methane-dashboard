import json
from pathlib import Path

def get_nested(data, path):
    """Helper to access nested dict with dot notation, e.g., 'A.B.C'."""
    keys = path.split('.')
    val = data
    for k in keys:
        if isinstance(val, list):
            # If list, assume we need to aggregate or handle separately
            return None  # Flag for computation needed
        val = val.get(k) if isinstance(val, dict) else None
        if val is None:
            return None
    return val

def pre_process_facility_data(facility_data):
    """
    Flattens and computes values from nested data for rule keys, handling
    the new, structured scraper output gracefully.
    """
    flat_data = {}
    
    # Ensure facility_data itself is a dictionary to prevent top-level errors.
    if not isinstance(facility_data, dict):
        facility_data = {}

    # Pneumatics
    pneum = facility_data.get('PneumaticDeviceVentingDetails') or {}
    flat_data['pneumatic_mt_ch4'] = pneum.get('mt_ch4', 0)
    flat_data['pneumatic_has_high_bleed'] = pneum.get('has_high_bleed', False)
    flat_data['pneumatic_has_intermittent'] = pneum.get('has_intermittent', False)
    flat_data['pneumatic_has_low_bleed'] = pneum.get('has_low_bleed', False)
    
    device_types = pneum.get('device_types') or []
    # FIX: Make string matching more robust to handle 'low-bleed', 'intermittent-bleed', etc.
    if isinstance(device_types, list):
        flat_data['pneumatic_high_bleed_count'] = sum(d.get('total_number', 0) for d in device_types if isinstance(d, dict) and 'high-bleed' in d.get('device_type', ''))
        flat_data['pneumatic_intermittent_count'] = sum(d.get('total_number', 0) for d in device_types if isinstance(d, dict) and 'intermittent' in d.get('device_type', ''))
        flat_data['pneumatic_low_bleed_count'] = sum(d.get('total_number', 0) for d in device_types if isinstance(d, dict) and 'low-bleed' in d.get('device_type', ''))
    else:
        flat_data['pneumatic_high_bleed_count'] = 0
        flat_data['pneumatic_intermittent_count'] = 0
        flat_data['pneumatic_low_bleed_count'] = 0

    tanks_totals = facility_data.get('AtmosphericTanks_Combined_Totals') or {}
    tanks_summary_1_2 = (facility_data.get('AtmosphericTanks_CalcMethod_1_2') or {}).get('totals') or {}

    # Use the most reliable reported total, otherwise use the calculated total.
    flat_data['tank_storage_mt_ch4'] = tanks_totals.get('total_ch4_emissions_mt_reported') or tanks_totals.get('total_ch4_emissions_mt', 0)
    flat_data['tank_count_vented'] = tanks_totals.get('uncontrolled_count', 0)
    
    # These indicators may still be useful, found in the Method 1/2 data if it exists.
    flat_data['tank_any_atmosphere_indicator'] = tanks_summary_1_2.get('any_atmosphere_indicator', False)
    flat_data['tank_any_vru_indicator'] = tanks_summary_1_2.get('any_vru_indicator', False)
    flat_data['tank_any_flares_indicator'] = tanks_summary_1_2.get('any_flares_indicator', False)
    
    # Well Completions/Workovers
    completions = (facility_data.get('WellCompletionsWithHydraulicFracturingTabgSummary') or {}).get('totals') or {}
    flat_data['completion_number_reduced'] = completions.get('total_rec', 0)
    flat_data['completion_number_non_reduced'] = completions.get('total_nonrec', 0)
    flat_data['completion_number_vented'] = flat_data['completion_number_non_reduced']
    
    # Liquids Unloading
    unloading = facility_data.get('WellVentingDetails') or {}
    flat_data['unloading_mt_ch4'] = unloading.get('mt_ch4', 0)
    flat_data['unloading_number_venting_wells'] = 0
    
    # Reciprocating Compressors
    recip = facility_data.get("ReciprocatingCompressorsDetails") or {}
    flat_data['recip_compressor_mt_ch4'] = recip.get('mt_ch4', 0)
    flat_data['recip_compressors_count'] = recip.get('count', 0)
    
    # Centrifugal Compressors
    centrif = facility_data.get('CentrifugalCompressorsDetails') or {}
    flat_data['centrif_mt_ch4'] = centrif.get('mt_ch4', 0)
    flat_data['centrif_present'] = centrif.get('present', False)
    
    # Associated Gas
    assoc = facility_data.get('AssociatedGasVentingFlaringDetails') or {}
    flat_data['associated_gas_mt_ch4'] = assoc.get('mt_ch4', 0)
    
    # Flares
    flares = facility_data.get('UniqueFlareStacks_Summary') or {}
    flat_data['flare_avg_efficiency'] = flares.get('avg_flare_combustion_efficiency', 0)
    flat_data['flare_mt_ch4'] = flares.get('total_ch4_emissions_mt', 0)
    flat_data['flare_count_monitors'] = flares.get('count_with_monitor_or_analyzer', 0)
    
    # Leaks
    leaks = facility_data.get('LeaksCalculatedWithCountsFactors_SummaryBySourceType') or []
    if isinstance(leaks, list):
        flat_data['leaks_mt_ch4'] = sum(l.get('ch4_emissions_mt', 0) for l in leaks if isinstance(l, dict))
    else:
        flat_data['leaks_mt_ch4'] = 0
    
    return flat_data

def _evaluate_single_condition(condition, facility_data):
    """
    Evaluates a single condition object, e.g., 
    { "data_point": "operating_hours", "operator": "<=", "value": 26000 }
    """
    data_point_key = condition.get('data_point')
    operator = condition.get('operator')
    threshold_value = condition.get('value')

    actual_value = facility_data.get(data_point_key)

    if actual_value is None:
        return None  # Indicates required data is missing

    # Perform the comparison based on the operator
    if operator == '==': return actual_value == threshold_value
    if operator == '!=': return actual_value != threshold_value
    if operator == '>':  return actual_value > threshold_value
    if operator == '<':  return actual_value < threshold_value
    if operator == '>=': return actual_value >= threshold_value
    if operator == '<=': return actual_value <= threshold_value
    if operator == 'IN': return actual_value in threshold_value
    return False

def _evaluate_logic_block(logic_block, facility_data):
    """
    Recursively evaluates a logic block, which can contain other logic blocks.
    This is the core of the recursive engine.
    """
    # Base Case: The block is just a single condition
    if 'operator' in logic_block:
        return _evaluate_single_condition(logic_block, facility_data)

    # Recursive Step: The block has a 'type' and a list of 'conditions'
    logic_type = logic_block.get('type')
    results = []
    for condition in logic_block.get('conditions', []):
        # Recursively call this function for each condition in the list
        result = _evaluate_logic_block(condition, facility_data)
        if result is None:
            return None # Propagate missing data status up
        results.append(result)

    if not results:
        return False # No conditions to evaluate

    # Combine results based on the logic type
    if logic_type == 'ALL' or logic_type == 'SINGLE':
        return all(results)
    if logic_type == 'ANY':
        return any(results)
    
    return False

def run_compliance_check(rule, facility_flat_data):
    """
    Updated to use pre-processed flat data.
    """
    # 1. Verify all required data is present
    for data_key in rule['data_requirements']:
        if data_key not in facility_flat_data:
            return {
                "rule_id": rule.get('rule_id'),
                "component": rule.get('component'),
                "regulation": rule.get('regulation'),
                "status": rule['status_if_data_missing'],
                "details": f"Cannot check rule. Missing data for: '{data_key}'",
                "scope": rule.get('automated_check_scope', 'N/A')
            }

    # 2. Evaluate the logic (using flat data)
    is_compliant = _evaluate_logic_block(rule['logic'], facility_flat_data)

    if is_compliant is None:
        status = rule['status_if_data_missing']
        details = "Could not determine compliance due to missing data during logic evaluation."
    elif is_compliant:
        status = "In Compliance"
        details = rule['output_if_compliant']
    else:
        status = "Out of Compliance"
        details = rule['output_if_noncompliant']

    return {
        "rule_id": rule.get('rule_id'),
        "component": rule.get('component', 'N/A'),
        "regulation": rule.get('regulation', 'N/A'),
        "status": status,
        "details": details,
        "scope": rule.get('automated_check_scope', 'N/A')
    }

def load_all_rules(rules_directory="data"):
    """
    Loads all .json files from a directory and combines them into one dict.
    """
    all_rules = {}
    for path in Path(rules_directory).glob('*.json'):
        with open(path, 'r') as f:
            data = json.load(f)
            all_rules.update(data)
    return all_rules

# Updated main for actual use
if __name__ == '__main__':
    print("--- Loading All Compliance Rules ---")
    master_rulebook = load_all_rules()
    print(f"Loaded {len(master_rulebook)} rules.\n")
    
    # Load actual facility data (replace with your file path)
    with open('facility_data.json', 'r') as f:  # Assume you save the provided data as JSON
        facility_data = json.load(f)
    
    facility_flat = pre_process_facility_data(facility_data)
    
    print("--- Running Compliance Checks ---")
    results = []
    for rule_id, rule_obj in master_rulebook.items():
        result = run_compliance_check(rule_obj, facility_flat)
        results.append(result)
    
    for result in sorted(results, key=lambda x: x['rule_id']):
        print(f"  Rule: {result['rule_id']}")
        print(f"    Component: {result['component']}")
        print(f"    Status: {result['status']}")
        print(f"    Details: {result['details']}")
        print(f"    Scope: {result['scope']}\n")
