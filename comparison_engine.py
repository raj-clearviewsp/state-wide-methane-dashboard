# compliance_engine.py
import json
from pathlib import Path

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

def run_compliance_check(rule, facility_data):
    """
    Checks a single rule against a facility's data.
    """
    # 1. Verify all required data is present
    for data_key in rule['data_requirements']:
        if data_key not in facility_data:
            return {
                "rule_id": rule.get('rule_id'),
                "component": rule.get('component'),
                "regulation": rule.get('regulation'),
                "status": rule['status_if_data_missing'],
                "details": f"Cannot check rule. Missing data for: '{data_key}'",
                "scope": rule.get('automated_check_scope', 'N/A')
            }

    # 2. Evaluate the logic
    is_compliant = _evaluate_logic_block(rule['logic'], facility_data)

    if is_compliant is None: # This case should be rare due to the check above but is a safeguard
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

# --- This is an example of how to use the engine ---
if __name__ == '__main__':
    print("--- Loading All Compliance Rules ---")
    # Assumes your JSON files are in the same directory as this script
    master_rulebook = load_all_rules()
    print(f"Loaded {len(master_rulebook)} rules.\n")
    
    # --- SIMULATING FACILITY DATA ---
    
    # Scenario 1: A facility that is likely NON-COMPLIANT with EPA compressor rule
    facility_non_compliant = {
        "operating_hours": 30000, # Fails the < 26000 check
        "uncontrolled_mt_CH4": 20, # Fails the tank check
        "count_tanks_no_control": 1,
        "mt_CH4_pneumatics": 1.0, # Fails pneumatics check
        "site_type": "gathering_boosting", # For NM Rule
    }

    # Scenario 2: A facility that appears COMPLIANT on the checked items
    facility_compliant = {
        "operating_hours": 15000, # Passes
        "uncontrolled_mt_CH4": 5,   # Passes
        "count_tanks_no_control": 0,
        "mt_CH4_pneumatics": 0,     # Passes
        "site_type": "well site", # Not covered by the specific NM rule
    }
    
    # Scenario 3: A facility with MISSING DATA for a key check
    facility_missing_data = {
        # Missing "operating_hours" completely
        "uncontrolled_mt_CH4": 5,
        "count_tanks_no_control": 0,
        "mt_CH4_pneumatics": 0,
        "site_type": "well site",
    }

    print("--- Running Compliance Check for NON-COMPLIANT Facility ---")
    results = []
    for rule_id, rule_obj in master_rulebook.items():
        # We only check rules for which the facility has the required data
        if all(key in facility_non_compliant for key in rule_obj.get('data_requirements', {})):
             results.append(run_compliance_check(rule_obj, facility_non_compliant))

    for result in sorted(results, key=lambda x: x['rule_id']):
        print(f"  Rule: {result['rule_id']}\n    Status: {result['status']}\n")

    print("\n--- Running Compliance Check for COMPLIANT Facility ---")
    results = []
    for rule_id, rule_obj in master_rulebook.items():
        if all(key in facility_compliant for key in rule_obj.get('data_requirements', {})):
            results.append(run_compliance_check(rule_obj, facility_compliant))

    for result in sorted(results, key=lambda x: x['rule_id']):
        print(f"  Rule: {result['rule_id']}\n    Status: {result['status']}\n")

    print("\n--- Running Compliance Check for Facility with MISSING DATA ---")
    # We will check just one specific rule to demonstrate the missing data handling
    compressor_rule = master_rulebook['epa_oooob_reciprocating_compressor_packing_v3']
    result = run_compliance_check(compressor_rule, facility_missing_data)
    print(f"  Rule: {result['rule_id']}\n    Status: {result['status']}\n    Details: {result['details']}\n")