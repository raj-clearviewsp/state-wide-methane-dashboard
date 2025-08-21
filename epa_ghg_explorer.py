from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from urllib.parse import urlencode
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from statistics import mean
from time import sleep

USER_AGENT = "Mozilla/5.0 (GHGRP-XML-Scraper/1.0; +https://ghgdata.epa.gov)"
BASE_XML_URL = "https://ghgdata.epa.gov/ghgp/service/xml/{year}?{qs}"

# ---------------------------
# Small utils
# ---------------------------

TRUE_SET  = {"y","yes","true","1","t"}
FALSE_SET = {"n","no","false","0","f"}

def lname(tag: str) -> str:
    """Return local name without XML namespace."""
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag

def as_bool(x):
    if x is None: 
        return None
    s = str(x).strip().lower()
    if s in TRUE_SET: return True
    if s in FALSE_SET: return False
    return None  # leave unknowns as None

def as_float(x):
    if x is None: 
        return None
    try:
        s = str(x).strip()
        if not s:
            return None
        return float(s)
    except Exception:
        return None

def child_text(el, local_name, default=None):
    """Find first descendant with given local_name and return its text."""
    if el is None: 
        return default
    for d in el.iter():
        if lname(d.tag) == local_name:
            return (d.text or default)
    return default

def childs(el, local_name):
    """All descendants with local_name."""
    if el is None: 
        return []
    out = []
    for d in el.iter():
        if lname(d.tag) == local_name:
            out.append(d)
    return out

def find_first(root, local_name):
    for d in root.iter():
        if lname(d.tag) == local_name:
            return d
    return None

def find_all(root, local_name):
    return [d for d in root.iter() if lname(d.tag) == local_name]

def first_of(el, names, cast=None):
    """Try multiple candidate element names, return first non-empty value."""
    for n in names:
        v = child_text(el, n)
        if v is not None and str(v).strip() != "":
            return cast(v) if cast else v
    return None

# Heuristic getter: look for any child whose local-name contains all tokens.
def guess_numeric(el, *tokens):
    tokens = [t.lower() for t in tokens]
    for d in el:
        nm = lname(d.tag).lower()
        if all(t in nm for t in tokens):
            v = as_float(d.text)
            if v is not None:
                return v
    # also scan one level deeper
    for d in el:
        for g in d:
            nm = lname(g.tag).lower()
            if all(t in nm for t in tokens):
                v = as_float(g.text)
                if v is not None:
                    return v
    return None

def guess_flag(el, *tokens):
    tokens = [t.lower() for t in tokens]
    for d in el:
        nm = lname(d.tag).lower()
        if all(t in nm for t in tokens):
            return as_bool(d.text)
    for d in el:
        for g in d:
            nm = lname(g.tag).lower()
            if all(t in nm for t in tokens):
                return as_bool(g.text)
    return None

# ---------------------------
# HTTP fetch
# ---------------------------

def fetch_xml_root(facility_id: int, year: int = 2023, timeout=30, retries=2):
    qs = urlencode({"id": str(facility_id), "et": "undefined"})
    url = BASE_XML_URL.format(year=year, qs=qs)
    req = Request(url, headers={"User-Agent": USER_AGENT})
    last_err = None
    for attempt in range(retries + 1):
        try:
            with urlopen(req, timeout=timeout) as r:
                data = r.read()
            return ET.fromstring(data)
        except (HTTPError, URLError, ET.ParseError) as e:
            last_err = e
            if attempt < retries:
                sleep(0.7 * (attempt + 1))
                continue
            raise RuntimeError(f"Failed to fetch/parse XML for facility {facility_id} {year}: {e}") from e

# ---------------------------
# Section parsers (targeted)
# ---------------------------
from typing import Optional

def parse_pneumatic_device_venting(root):
    sec = find_first(root, "PneumaticDeviceVentingDetails")
    if sec is None:
        return None

    out = {
        "mt_co2": first_of(sec, ["TotalCarbonDioxideEmissions"], as_float),
        "mt_ch4": first_of(sec, [
            "TotalCh4MetricTonsEmissions", "TotalCH4MetricTonsEmissions",
            "TotalMethaneEmissions", "TotalReportedMethaneEmissions",
        ], as_float),
        "has_high_bleed": first_of(sec, [
            "DoesFacilityHaveHighBleedDevices", "DoesFacilityHaveHighBleedDevicesIndicator",
        ], as_bool),
        "has_intermittent": first_of(sec, [
            "DoesFacilityHaveIntermittentBleedDevices", "DoesFacilityHaveIntermittentBleedDevicesIndicator",
        ], as_bool),
        "has_low_bleed": first_of(sec, [
            "DoesFacilityHaveLowBleedDevices", "DoesFacilityHaveLowBleedDevicesIndicator",
        ], as_bool),
        "missing_data_used": first_of(sec, [
            "MissingDataProceduresUsed", "MissingDataProceduresUsedIndicator",
        ], as_bool),
        "device_types": []
    }

    rows = find_all(sec, "PneumaticDeviceTypesRowDetails")

    def normalize_type(s: Optional[str]) -> Optional[str]:
        if not s:
            return None
        t = s.lower()
        if "low" in t and "bleed" in t:
            return "low-bleed"
        if "high" in t and "bleed" in t:
            return "high-bleed"
        if "intermittent" in t and "bleed" in t:
            return "intermittent-bleed"
        return s.strip()

    for row in rows:
        dtype_raw = first_of(row, ["PneumaticDeviceType", "DeviceType"], str)
        rec = {
            "device_type": normalize_type(dtype_raw) or dtype_raw,
            "total_number": first_of(row, ["TotalCount", "TotalNumber", "TotalNumberCount", "Count"], as_float),
            "total_number_estimated": first_of(row, ["IsTotalNumberEstimated", "IsTotalNumberEstimatedIndicator",
                                                     "TotalNumberEstimatedIndicator"], as_bool),
            "total_co2_mt": first_of(row, ["TotalCarbonDioxideEmissions", "TotalCO2Emissions"], as_float),
            "total_ch4_mt": first_of(row, ["TotalCh4Emissions", "TotalCH4Emissions", "TotalMethaneEmissions"], as_float),
            "estimated_hours": first_of(row, ["EstimatedNumberOfHours"], as_float),
        }
        if any(rec.get(k) is not None for k in ("total_number", "total_co2_mt", "total_ch4_mt", "estimated_hours")):
            out["device_types"].append(rec)

    return out

def parse_acid_gas_and_dehydrators(root):
    """Return whatever we can reasonably extract (totals by sub-type)."""
    ag = find_first(root, "AcidGasRemovalUnitsDetails")
    deh = find_first(root, "DehydratorsDetails")
    out = {}

    if ag is not None:
        out["AcidGasRemovalUnitsDetails"] = {
            "mt_co2": first_of(ag, ["TotalCarbonDioxideEmissions"], as_float),
            "mt_ch4": first_of(ag, ["TotalCh4MetricTonsEmissions"], as_float),
            "mt_n2o": first_of(ag, ["TotalNitrousOxideEmissions"], as_float),
        }

    if deh is not None:
        # Small Glycol and Desiccant (absorption/adsorption) may be nested differently across years
        small_glycol = find_first(deh, "SmallGlycolDehydrators")
        desiccant    = find_first(deh, "DessicantDehydrators") or find_first(deh, "DesiccantDehydrators")

        sub = {}
        if small_glycol is not None:
            sub["SmallGlycolDehydrators"] = {
                "mt_co2": first_of(small_glycol, ["TotalCarbonDioxideEmissions"], as_float),
                "mt_ch4": first_of(small_glycol, ["TotalCh4MetricTonsEmissions"], as_float),
                "count":  first_of(small_glycol, ["TotalNumber", "Count"], as_float),
            }
        if desiccant is not None:
            sub["DesiccantDehydrators"] = {
                "mt_co2": first_of(desiccant, ["TotalCarbonDioxideEmissions"], as_float),
                "mt_ch4": first_of(desiccant, ["TotalCh4MetricTonsEmissions"], as_float),
                "count":  first_of(desiccant, ["TotalNumber", "Count"], as_float),
            }
        if sub:
            out["DehydratorsDetails"] = sub

    return out or None

def parse_well_venting(root):
    sec = find_first(root, "WellVentingDetails")
    if sec is None:
        return None
    return {
        "mt_co2": first_of(sec, ["TotalCarbonDioxideEmissions"], as_float),
        "mt_ch4": first_of(sec, ["TotalCh4MetricTonsEmissions"], as_float),
        "has_liquids_unloading": first_of(sec, [
            "DidFacilityHaveWellVenting",
            "DoesFacilityHaveAnyWellVentingForLiquidsUnloadingSubjectToReportingIndicator"
        ], as_bool),
        "calc_method_1_used": first_of(sec, ["WasMethod1UsedforCO2Emissions"], as_bool),
        "calc_method_2_used": first_of(sec, ["WasMethod2UsedforCO2Emissions"], as_bool),
        "calc_method_3_used": first_of(sec, ["WasMethod3UsedforCO2Emissions"], as_bool),
    }


def parse_onshore_production_wells(root):
    """
    Parses onshore production well counts and characteristics, providing totals
    and breakdowns by sub-basin and formation type.
    """
    rows = find_all(root, "OnshoreProductionRequirementsSubBasinRowDetails")
    if not rows:
        return None

    # --- Data structures for aggregation ---
    # For facility-wide totals
    totals = {
        "total_wells_producing_eoy": 0.0,
        "total_wells_acquired": 0.0,
        "total_wells_divested": 0.0,
        "total_wells_completed": 0.0,
        "total_wells_removed": 0.0,
    }
    # To build the detailed "by_sub_basin" list
    by_sb_agg = {}
    # To build the "by_formation_type" summary
    by_formation_agg = {}

    for row in rows:
        # --- Extract data from the current row ---
        sb_id = first_of(row, ["SubBasinIdentifier"], str) or "Unknown"
        county = first_of(row, ["SubBasinCounty"], str)
        formation = first_of(row, ["SubBasinFormationType"], str) or "Unknown"
        
        wells_eoy = first_of(row, ["WellProducingEndOfYear"], as_float) or 0.0
        wells_acq = first_of(row, ["ProducingWellsAcquired"], as_float) or 0.0
        wells_div = first_of(row, ["ProducingWellsDivested"], as_float) or 0.0
        wells_comp = first_of(row, ["WellsCompleted"], as_float) or 0.0
        wells_rem = first_of(row, ["WellRemovedFromProduction"], as_float) or 0.0

        # --- Aggregate facility-wide totals ---
        totals["total_wells_producing_eoy"] += wells_eoy
        totals["total_wells_acquired"] += wells_acq
        totals["total_wells_divested"] += wells_div
        totals["total_wells_completed"] += wells_comp
        totals["total_wells_removed"] += wells_rem

        # --- Aggregate by sub-basin ---
        bucket = by_sb_agg.setdefault(sb_id, {
            "sub_basin_id": sb_id,
            "county": county,
            "formation_type": formation,
            "wells_producing_eoy": 0.0,
            "wells_acquired": 0.0,
            "wells_divested": 0.0,
            "wells_completed": 0.0,
            "wells_removed": 0.0,
        })
        bucket["wells_producing_eoy"] += wells_eoy
        bucket["wells_acquired"] += wells_acq
        bucket["wells_divested"] += wells_div
        bucket["wells_completed"] += wells_comp
        bucket["wells_removed"] += wells_rem

        # --- Aggregate by formation type ---
        formation_bucket = by_formation_agg.setdefault(formation, {
            "formation_type": formation,
            "well_count": 0.0,
        })
        formation_bucket["well_count"] += wells_eoy

    # --- Finalize and format the output ---
    # Convert aggregated dictionaries to sorted lists for consistent output
    by_sub_basin = sorted(by_sb_agg.values(), key=lambda x: x.get("sub_basin_id") or "")
    by_formation_type = sorted(by_formation_agg.values(), key=lambda x: x.get("formation_type") or "")

    return {
        "totals": totals,
        "by_sub_basin": by_sub_basin,
        "by_formation_type": by_formation_type
    }


def parse_wells_with_fracturing(root):
    sec = find_first(root, "WellsWithFracturingDetails")
    if sec is None:
        return None
    return {
        "mt_co2": first_of(sec, ["TotalCarbonDioxideEmissions"], as_float),
        "mt_ch4": first_of(sec, [
            "TotalMethaneEmissions",
            "TotalCh4MetricTonsEmissions",   # your file
            "TotalCH4MetricTonsEmissions"
        ], as_float),
        "mt_n2o": first_of(sec, [
            "TotalNitrousOxideEmissions",
            "TotalN2OMetricTonsEmissions",   # your file
            "TotalN2OEmissions"
        ], as_float),
        "has_fracturing": first_of(sec, [
            "DoesFacilityHaveAnyGasOrOilWellCompletionsOrWorkoversWithHydraulicFracturingIndicator",
            "DidFacilityHaveCompletionsWithHydraulic"   # your file
        ], as_bool),
        "missing_data_used": first_of(sec, [
            "MissingDataProceduresUsedIndicator",
            "MissingDataProceduresUsed"                 # your file
        ], as_bool),
    }


def parse_well_completions_hf_tabg(root):
    rows = find_all(root, "WellCompletionsWithHydraulicFracturingTabgRowDetails")
    if not rows:
        return None

    total_rec = 0.0
    total_nonrec = 0.0
    ch4_values = []
    equations = set()

    for row in rows:
        # Prefer explicit numeric fields if present…
        rec_num  = first_of(row, ["NumberOfReducedEmissionsCompletions"], as_float)
        nrec_num = first_of(row, ["NumberOfNonReducedEmissionsCompletions"], as_float)

        if rec_num is not None or nrec_num is not None:
            total_rec    += rec_num  or 0.0
            total_nonrec += nrec_num or 0.0
        else:
            # …otherwise derive from ReducedEmissionCompletions (Yes/No) + TotalCompletions
            rec_flag = first_of(row, ["ReducedEmissionCompletions"], as_bool)  # your file
            tot_comp = first_of(row, ["TotalCompletions"], as_float)           # your file
            if rec_flag is True and tot_comp is not None:
                total_rec += tot_comp
            elif rec_flag is False and tot_comp is not None:
                total_nonrec += tot_comp

        ch4 = first_of(row, [
            "AnnualMethaneEmissions",   # your file
            "AnnualCH4Emissions",
            "TotalMethaneEmissions",
            "TotalCh4Emissions"
        ], as_float)
        if ch4 is not None:
            ch4_values.append(ch4)

        eqn = first_of(row, ["EquationUsed"], str)
        if eqn:
            equations.add(eqn.strip())

    return {
        "total_rec": total_rec or None,
        "total_nonrec": total_nonrec or None,
        "sum_ch4_mt": (sum(ch4_values) if ch4_values else None),
        "equations_used": (sorted(equations) if equations else None),
    }

def parse_well_completions_hf_tabg(root):
    rows = find_all(root, "WellCompletionsWithHydraulicFracturingTabgRowDetails")
    if not rows:
        return None

    def num_rec(row):
        # explicit counts if present
        n = first_of(row, [
            "NumberOfReducedEmissionsCompletions",
            "TotalNumberOfReducedEmissionsCompletions",
            "TotalReducedEmissionsCompletions"
        ], as_float)
        if n is not None:
            return n
        # derive from "ReducedEmissionCompletions" (Yes/No) + total completions
        rec_flag = first_of(row, ["ReducedEmissionCompletions",
                                  "ReducedEmissionCompletionsIndicator"], as_bool)
        tot = first_of(row, ["TotalCompletions", "TotalNumberOfCompletions"], as_float)
        if rec_flag is True and tot is not None:
            return tot
        if rec_flag is False:
            return 0.0
        return None

    def num_nonrec(row):
        n = first_of(row, [
            "NumberOfNonReducedEmissionsCompletions",
            "TotalNumberOfNonReducedEmissionsCompletions",
            "TotalNonReducedEmissionsCompletions"
        ], as_float)
        if n is not None:
            return n
        rec = num_rec(row)
        tot = first_of(row, ["TotalCompletions", "TotalNumberOfCompletions"], as_float)
        if rec is not None and tot is not None:
            return max(tot - rec, 0.0)
        if rec is False and tot is not None:
            return tot
        return None

    by_sb = {}
    totals = {
        "total_rec": 0.0,
        "total_nonrec": 0.0,
        "sum_ch4_mt": 0.0,
        "sum_co2_mt": 0.0,
        "sum_n2o_mt": 0.0,
        "sum_gas_scf": 0.0,
        "equations_used": set(),
    }

    for row in rows:
        sb = first_of(row, ["SubBasinIdentifier", "SubBasinID"], str) or "Unknown"

        rec  = num_rec(row) or 0.0
        nrec = num_nonrec(row) or 0.0

        ch4  = first_of(row, ["AnnualMethaneEmissions", "AnnualCH4Emissions",
                              "TotalMethaneEmissions", "TotalCh4Emissions"], as_float) or 0.0
        co2  = first_of(row, ["AnnualCarbonDioxideEmissions", "AnnualCO2Emissions"], as_float) or 0.0
        n2o  = first_of(row, ["AnnualNitrousOxideEmissions", "AnnualN2OEmissions"], as_float) or 0.0
        gas  = first_of(row, ["AnnualGasEmissions"], as_float) or 0.0
        eqn  = first_of(row, ["EquationUsed"], str)
        flr  = first_of(row, ["IsGasFlared", "GasFlared"], as_bool)
        wtyp = first_of(row, ["WellType"], str)
        og   = first_of(row, ["OilOrGasWell"], str)
        totc = first_of(row, ["TotalCompletions", "TotalNumberOfCompletions"], as_float) or 0.0

        bucket = by_sb.setdefault(sb, {
            "sub_basin_id": sb,
            "total_completions": 0.0,
            "reduced_emissions_completions": 0.0,
            "non_reduced_emissions_completions": 0.0,
            "sum_ch4_mt": 0.0,
            "sum_co2_mt": 0.0,
            "sum_n2o_mt": 0.0,
            "sum_gas_scf": 0.0,
            "equations_used": set(),
            "well_types": set(),
            "oil_or_gas": set(),
            "any_gas_flared": False,
        })

        bucket["total_completions"] += totc
        bucket["reduced_emissions_completions"] += rec
        bucket["non_reduced_emissions_completions"] += nrec
        bucket["sum_ch4_mt"] += ch4
        bucket["sum_co2_mt"] += co2
        bucket["sum_n2o_mt"] += n2o
        bucket["sum_gas_scf"] += gas
        if eqn: bucket["equations_used"].add(eqn.strip())
        if wtyp: bucket["well_types"].add(wtyp)
        if og: bucket["oil_or_gas"].add(og)
        if flr: bucket["any_gas_flared"] = True

        totals["total_rec"] += rec
        totals["total_nonrec"] += nrec
        totals["sum_ch4_mt"] += ch4
        totals["sum_co2_mt"] += co2
        totals["sum_n2o_mt"] += n2o
        totals["sum_gas_scf"] += gas
        if eqn: totals["equations_used"].add(eqn.strip())

    # finalize: convert sets → sorted lists
    by_sub_basin = []
    for sb, d in by_sb.items():
        d["equations_used"] = sorted(d["equations_used"]) if d["equations_used"] else None
        d["well_types"] = sorted(d["well_types"]) if d["well_types"] else None
        d["oil_or_gas"] = sorted(d["oil_or_gas"]) if d["oil_or_gas"] else None
        by_sub_basin.append(d)

    totals["equations_used"] = sorted(totals["equations_used"]) if totals["equations_used"] else None

    # sort for stable output
    by_sub_basin.sort(key=lambda x: x.get("sub_basin_id") or "")

    return {
        "by_sub_basin": by_sub_basin,
        "totals": totals
    }

def parse_wells_without_fracturing(root):
    sec = find_first(root, "WellsWithoutFracturingDetails")
    if sec is None:
        return None
    return {
        "mt_co2": first_of(sec, ["TotalCarbonDioxideEmissions"], as_float),
        "mt_ch4": first_of(sec, [
            "TotalMethaneEmissions",
            "TotalCh4MetricTonsEmissions",
            "TotalCH4MetricTonsEmissions"
        ], as_float),
        "mt_n2o": first_of(sec, [
            "TotalNitrousOxideEmissions",
            "TotalN2OMetricTonsEmissions",
            "TotalN2OEmissions"
        ], as_float),
        "has_without_fracturing": first_of(sec, [
            "DoesFacilityHaveAnyGasOrOilWellCompletionsOrWorkoversWithoutHydraulicFracturingIndicator",
            "DidFacilityHaveCompletionsWithoutHydraulic"
        ], as_bool),
    }


def parse_atmospheric_tanks(root):
    """
    Orchestrates parsing of all AtmosphericTanksDetails sections, combining
    results from different calculation methods into a unified summary.
    """
    sec = find_first(root, "AtmosphericTanksDetails")
    if sec is None:
        return {} # Return empty dict if the whole section is missing

    # 1. Parse top-level summary information from the main section
    summary = {
        "mt_co2": first_of(sec, ["TotalCarbonDioxideEmissions"], as_float),
        "mt_ch4": first_of(sec, ["TotalCh4MetricTonsEmissions"], as_float),
        "mt_n2o": first_of(sec, ["TotalN2OMetricTonsEmissions"], as_float),
        "calc_method_1_used": first_of(sec, ["CalcMethod1Used"], as_bool),
        "calc_method_2_used": first_of(sec, ["CalcMethod2Used"], as_bool),
        "calc_method_3_used": first_of(sec, ["CalcMethod3Used"], as_bool),
        "has_malfunctioning_dump_valves": first_of(sec, ["MalfunctioningDumpValves"], as_bool),
        "missing_data_used": first_of(sec, ["MissingDataProceduresUsed"], as_bool),
    }

    # 2. Call individual parsers for each calculation method
    data_1_2 = parse_atmos_tanks_calc_1_2(root)
    data_3_flaring = parse_atmos_tanks_calc_3_with_flaring(root)
    data_3_no_flaring = parse_atmos_tanks_calc_3_no_flaring(root)

    # 3. Combine totals from all available methods into a single summary
    combined_totals = {
        "total_tank_count": 0.0,
        "total_ch4_emissions_mt": 0.0,
        "flaring_ch4_mt": 0.0,
        "recovered_ch4_mt": 0.0,
        "uncontrolled_ch4_mt": 0.0,
        "vru_control_count": 0.0,
        "flare_control_count": 0.0,
        "uncontrolled_count": 0.0,
    }

    # Add totals from Method 1/2
    if data_1_2 and data_1_2.get("totals"):
        t = data_1_2["totals"]
        combined_totals["total_tank_count"] += t.get("tank_count", 0)
        combined_totals["flaring_ch4_mt"] += t.get("flaring_ch4_mt", 0)
        combined_totals["recovered_ch4_mt"] += t.get("annual_ch4_recovered_mt", 0)
        combined_totals["vru_control_count"] += t.get("count_vru_control", 0)
        combined_totals["flare_control_count"] += t.get("count_flaring_control", 0)
        # Assume tanks vented to atmosphere are "uncontrolled" in this context
        if t.get("any_atmosphere_indicator"):
            combined_totals["uncontrolled_count"] += t.get("tank_count", 0) - (t.get("count_vru_control", 0) + t.get("count_flaring_control", 0))


    # Add totals from Method 3 (With Flaring)
    if data_3_flaring and data_3_flaring.get("totals"):
        t = data_3_flaring["totals"]
        combined_totals["flare_control_count"] += t.get("count_flare_control", 0)
        combined_totals["flaring_ch4_mt"] += t.get("annual_ch4_from_flaring_mt", 0)
        # Add tank counts from the overview section if available
        if data_3_flaring.get("method3_overview"):
            combined_totals["total_tank_count"] += data_3_flaring["method3_overview"].get("atmospheric_tank_count", 0)


    # Add totals from Method 3 (No Flaring)
    if data_3_no_flaring and data_3_no_flaring.get("totals"):
        t = data_3_no_flaring["totals"]
        combined_totals["uncontrolled_count"] += t.get("count_uncontrolled", 0)
        combined_totals["uncontrolled_ch4_mt"] += t.get("annual_ch4_uncontrolled_mt", 0)

    # Calculate final CH4 total from components
    combined_totals["total_ch4_emissions_mt"] = (
        combined_totals["flaring_ch4_mt"] +
        combined_totals["recovered_ch4_mt"] + # Note: recovered is not an emission but is part of the balance
        combined_totals["uncontrolled_ch4_mt"]
    )
    # Often the top-level reported CH4 is the most reliable figure
    if summary.get("mt_ch4") is not None:
        combined_totals["total_ch4_emissions_mt_reported"] = summary["mt_ch4"]


    # 4. Return a dictionary containing all parsed data, separated by source
    return {
        "AtmosphericTanks_Summary": summary,
        "AtmosphericTanks_CalcMethod_1_2": data_1_2,
        "AtmosphericTanks_CalcMethod_3_WithFlaring": data_3_flaring,
        "AtmosphericTanks_CalcMethod_3_NoFlaring": data_3_no_flaring,
        "AtmosphericTanks_Combined_Totals": combined_totals,
    }


def parse_atmos_tanks_calc_1_2(root):
    rows = find_all(root, "AtmosphericTanksCalculationMethodOneOrTwoSubBasinRowDetails")
    if not rows:
        return None

    by_sb = {}
    totals = {
        "num_wellhead_separators": 0.0,
        "count_vru_control": 0.0,
        "count_flaring_control": 0.0,
        "tank_count": 0.0,
        "not_on_well_pad_tank_count": 0.0,
        "flaring_co2_mt": 0.0,
        "flaring_ch4_mt": 0.0,
        "flaring_n2o_mt": 0.0,
        "annual_co2_recovered_mt": 0.0,
        "annual_ch4_recovered_mt": 0.0,
        "vapor_recovery_co2_emissions_mt": 0.0,
        "vapor_recovery_ch4_emissions_mt": 0.0,
        "total_volume_oil_bbl": 0.0,
        "any_vru_indicator": False,
        "any_atmosphere_indicator": False,
        "any_flares_indicator": False,
        "two_year_delay_any": False,
        "calc_methodologies": set(),
        "software_used": set(),
        # facility-wide ranges across all rows (if present)
        "min_flash_ch4_frac": None,
        "max_flash_ch4_frac": None,
        "min_flash_co2_frac": None,
        "max_flash_co2_frac": None,
    }

    for row in rows:
        sb = first_of(row, ["SubBasinIdentifier", "SubBasinID", "SubBasinId"], str) or "Unknown"

        method   = first_of(row, ["CalculationMethodology", "CalculationMethod", "EquationMethod"], str)
        software = first_of(row, ["SoftwarePackageUsed", "CalculationSoftware", "CalcSoftware"], str)

        n_sep    = first_of(row, ["NumberOfWellHeadSeparators"], as_float) or 0.0
        avg_temp = first_of(row, ["AverageSeparatorTemperature"], as_float)
        avg_psig = first_of(row, ["AveragePressure"], as_float)
        avg_api  = first_of(row, ["AverageAPIGravity"], as_float)

        cnt_vru  = first_of(row, [
            "TanksWithVaporRecovery",
            "CountOfTanksControlledWithVaporRecoverySystems",
            "CountOfTanksThatControlEmissionsWithVaporRecoverySystems"
        ], as_float) or 0.0

        cnt_flr  = first_of(row, [
            "TanksWithFlaring",
            "CountOfTanksWithFlaringEmissionControlMeasures",
            "CountOfTanksVentedToFlares"
        ], as_float) or 0.0

        min_ch4  = first_of(row, ["MinimumFlashMethaneConcentration"], as_float)
        max_ch4  = first_of(row, ["MaximumFlashMethaneConcentration"], as_float)
        min_co2  = first_of(row, ["MinimumFlashGasCarbonDioxideConcentration"], as_float)
        max_co2  = first_of(row, ["MaximumFlashGasCarbonDioxideConcentration"], as_float)

        flr_co2  = first_of(row, ["FlaringCarbonDioxideEmissions", "AnnualCarbonDioxideEmissionsFromFlaring"], as_float) or 0.0
        flr_ch4  = first_of(row, ["FlaringCh4Emissions", "AnnualMethaneEmissionsFromFlaring"], as_float) or 0.0
        flr_n2o  = first_of(row, ["FlaringN2OEmissions", "AnnualNitrousOxideEmissionsFromFlaring"], as_float) or 0.0

        vol_oil  = first_of(row, ["TotalVolumeOfOil"], as_float) or 0.0
        reco2    = first_of(row, ["AnnualCarbonDioxideRecovered"], as_float) or 0.0
        rech4    = first_of(row, ["AnnualMethaneRecovered"], as_float) or 0.0
        vr_co2   = first_of(row, ["VaporRecoveryCO2Emissions"], as_float) or 0.0
        vr_ch4   = first_of(row, ["VaporRecoveryCH4Emissions"], as_float) or 0.0

        any_vru  = first_of(row, ["WereEmissionsVaporRecovery"], as_bool)
        any_atm  = first_of(row, ["WereEmissionsAtmosphere"], as_bool)
        any_flr  = first_of(row, ["WereEmissionsFlares"], as_bool)

        tank_cnt = first_of(row, ["AtmosphericTankCount", "CountOfAtmosphericTanks"], as_float) or 0.0
        not_pad  = first_of(row, ["NotOnWellPadTankCount"], as_float) or 0.0
        delay    = first_of(row, ["TwoYearDelayIndicator"], as_bool)

        bucket = by_sb.setdefault(sb, {
            "sub_basin_id": sb,
            "calc_methodologies": set(),
            "software_used": set(),
            "num_wellhead_separators": 0.0,
            "avg_separator_temp_F": [],
            "avg_separator_pressure_psig": [],
            "avg_api_gravity": [],
            "count_vru_control": 0.0,
            "count_flaring_control": 0.0,
            "min_flash_ch4_frac": [],
            "max_flash_ch4_frac": [],
            "min_flash_co2_frac": [],
            "max_flash_co2_frac": [],
            "flaring_co2_mt": 0.0,
            "flaring_ch4_mt": 0.0,
            "flaring_n2o_mt": 0.0,
            "total_volume_oil_bbl": 0.0,
            "annual_co2_recovered_mt": 0.0,
            "annual_ch4_recovered_mt": 0.0,
            "vapor_recovery_co2_emissions_mt": 0.0,
            "vapor_recovery_ch4_emissions_mt": 0.0,
            "tank_count": 0.0,
            "not_on_well_pad_tank_count": 0.0,
            "any_vru_indicator": False,
            "any_atmosphere_indicator": False,
            "any_flares_indicator": False,
            "two_year_delay_any": False,
        })

        if method:   bucket["calc_methodologies"].add(method)
        if software: bucket["software_used"].add(software)
        bucket["num_wellhead_separators"] += n_sep
        if avg_temp is not None: bucket["avg_separator_temp_F"].append(avg_temp)
        if avg_psig is not None: bucket["avg_separator_pressure_psig"].append(avg_psig)
        if avg_api  is not None: bucket["avg_api_gravity"].append(avg_api)

        bucket["count_vru_control"] += cnt_vru
        bucket["count_flaring_control"] += cnt_flr

        if min_ch4 is not None: bucket["min_flash_ch4_frac"].append(min_ch4)
        if max_ch4 is not None: bucket["max_flash_ch4_frac"].append(max_ch4)
        if min_co2 is not None: bucket["min_flash_co2_frac"].append(min_co2)
        if max_co2 is not None: bucket["max_flash_co2_frac"].append(max_co2)

        bucket["flaring_co2_mt"] += flr_co2
        bucket["flaring_ch4_mt"] += flr_ch4
        bucket["flaring_n2o_mt"] += flr_n2o

        bucket["total_volume_oil_bbl"] += vol_oil
        bucket["annual_co2_recovered_mt"] += reco2
        bucket["annual_ch4_recovered_mt"] += rech4
        bucket["vapor_recovery_co2_emissions_mt"] += vr_co2
        bucket["vapor_recovery_ch4_emissions_mt"] += vr_ch4

        bucket["tank_count"] += tank_cnt
        bucket["not_on_well_pad_tank_count"] += not_pad

        bucket["any_vru_indicator"] = bucket["any_vru_indicator"] or (any_vru is True)
        bucket["any_atmosphere_indicator"] = bucket["any_atmosphere_indicator"] or (any_atm is True)
        bucket["any_flares_indicator"] = bucket["any_flares_indicator"] or (any_flr is True)
        bucket["two_year_delay_any"] = bucket["two_year_delay_any"] or (delay is True)

        # facility totals
        totals["num_wellhead_separators"] += n_sep
        totals["count_vru_control"] += cnt_vru
        totals["count_flaring_control"] += cnt_flr
        totals["tank_count"] += tank_cnt
        totals["not_on_well_pad_tank_count"] += not_pad
        totals["flaring_co2_mt"] += flr_co2
        totals["flaring_ch4_mt"] += flr_ch4
        totals["flaring_n2o_mt"] += flr_n2o
        totals["annual_co2_recovered_mt"] += reco2
        totals["annual_ch4_recovered_mt"] += rech4
        totals["vapor_recovery_co2_emissions_mt"] += vr_co2
        totals["vapor_recovery_ch4_emissions_mt"] += vr_ch4
        totals["total_volume_oil_bbl"] += vol_oil

        totals["any_vru_indicator"] = totals["any_vru_indicator"] or (any_vru is True)
        totals["any_atmosphere_indicator"] = totals["any_atmosphere_indicator"] or (any_atm is True)
        totals["any_flares_indicator"] = totals["any_flares_indicator"] or (any_flr is True)
        totals["two_year_delay_any"] = totals["two_year_delay_any"] or (delay is True)
        if method:   totals["calc_methodologies"].add(method)
        if software: totals["software_used"].add(software)

        # facility-wide ranges
        for k, v in [
            ("min_flash_ch4_frac", min_ch4),
            ("max_flash_ch4_frac", max_ch4),
            ("min_flash_co2_frac", min_co2),
            ("max_flash_co2_frac", max_co2),
        ]:
            if v is None:
                continue
            if totals[k] is None:
                totals[k] = v
            else:
                if "min_" in k:
                    totals[k] = min(totals[k], v)
                else:
                    totals[k] = max(totals[k], v)

    # finalize per-sub-basin stats
    out_rows = []
    for sb, d in by_sb.items():
        d["calc_methodologies"] = sorted(d["calc_methodologies"]) if d["calc_methodologies"] else None
        d["software_used"] = sorted(d["software_used"]) if d["software_used"] else None
        d["avg_separator_temp_F"] = (mean(d["avg_separator_temp_F"]) if d["avg_separator_temp_F"] else None)
        d["avg_separator_pressure_psig"] = (mean(d["avg_separator_pressure_psig"]) if d["avg_separator_pressure_psig"] else None)
        d["avg_api_gravity"] = (mean(d["avg_api_gravity"]) if d["avg_api_gravity"] else None)
        d["min_flash_ch4_frac"] = (min(d["min_flash_ch4_frac"]) if d["min_flash_ch4_frac"] else None)
        d["max_flash_ch4_frac"] = (max(d["max_flash_ch4_frac"]) if d["max_flash_ch4_frac"] else None)
        d["min_flash_co2_frac"] = (min(d["min_flash_co2_frac"]) if d["min_flash_co2_frac"] else None)
        d["max_flash_co2_frac"] = (max(d["max_flash_co2_frac"]) if d["max_flash_co2_frac"] else None)
        out_rows.append(d)

    out_rows.sort(key=lambda x: x.get("sub_basin_id") or "")
    totals["calc_methodologies"] = sorted(totals["calc_methodologies"]) if totals["calc_methodologies"] else None
    totals["software_used"] = sorted(totals["software_used"]) if totals["software_used"] else None

    return {"by_sub_basin": out_rows, "totals": totals}

def parse_atmos_tanks_calc_3_with_flaring(root):
    rows = find_all(root, "AtmosphericTanksCalcMethodThreeWithFlaringRowDetails")
    over = find_all(root, "AtmosphericTanksCalculationMethodThreeRowDetails")

    if not rows and not over:
        return None

    # ---- per-sub-basin + totals (flaring) ----
    by_sb = {}
    totals = {
        "count_flare_control": 0.0,
        "annual_co2_from_flaring_mt": 0.0,
        "annual_ch4_from_flaring_mt": 0.0,
        "annual_n2o_from_flaring_mt": 0.0,
    }

    for row in rows:
        sb = first_of(row, ["SubBasinId", "SubBasinID", "SubBasinIdentifier"], str) or "Unknown"

        cnt = first_of(row, [
            "EmissionsControlWithFlareCount",
            "CountOfTanksWithFlaringEmissionControlMeasures",
            "CountOfTanksVentedToFlares"
        ], as_float) or 0.0

        co2 = first_of(row, ["Co2Emissions", "AnnualCarbonDioxideEmissions", "AnnualCO2Emissions"], as_float) or 0.0
        ch4 = first_of(row, ["Ch4Emissions", "AnnualMethaneEmissions", "AnnualCH4Emissions"], as_float) or 0.0
        n2o = first_of(row, ["N2OEmissions", "AnnualNitrousOxideEmissions", "AnnualN2OEmissions"], as_float) or 0.0

        b = by_sb.setdefault(sb, {
            "sub_basin_id": sb,
            "count_flare_control": 0.0,
            "annual_co2_from_flaring_mt": 0.0,
            "annual_ch4_from_flaring_mt": 0.0,
            "annual_n2o_from_flaring_mt": 0.0,
        })

        b["count_flare_control"] += cnt
        b["annual_co2_from_flaring_mt"] += co2
        b["annual_ch4_from_flaring_mt"] += ch4
        b["annual_n2o_from_flaring_mt"] += n2o

        totals["count_flare_control"] += cnt
        totals["annual_co2_from_flaring_mt"] += co2
        totals["annual_ch4_from_flaring_mt"] += ch4
        totals["annual_n2o_from_flaring_mt"] += n2o

    by_sub_basin = sorted(by_sb.values(), key=lambda x: x.get("sub_basin_id") or "")

    # ---- method-3 overview block (non-flaring per-facility metadata) ----
    overview = None
    if over:
        # handle 1+ rows: sum counts/throughput, avg fractions, OR for delay
        fr_flr = []
        fr_vru = []
        tank_cnt = 0.0
        gas_wells = 0.0
        wells_wo_gas = 0.0
        oil_bbl = 0.0
        any_delay = False

        for r in over:
            f1 = first_of(r, ["FractionOfOilThroughputWithFlaring"], as_float)
            f2 = first_of(r, ["FractionOfOilThroughputWithVapor"], as_float)
            if f1 is not None: fr_flr.append(f1)
            if f2 is not None: fr_vru.append(f2)

            tank_cnt     += first_of(r, ["AtmosphericTankCount"], as_float) or 0.0
            gas_wells    += first_of(r, ["GasWellsCount"], as_float) or 0.0
            wells_wo_gas += first_of(r, ["WellsWithoutGasCount"], as_float) or 0.0
            oil_bbl      += first_of(r, ["AnnualOilThroughput"], as_float) or 0.0
            any_delay     = any_delay or (first_of(r, ["TwoYearDelayIndicator"], as_bool) is True)

        overview = {
            "fraction_of_oil_with_flaring": (mean(fr_flr) if fr_flr else None),
            "fraction_of_oil_with_vapor": (mean(fr_vru) if fr_vru else None),
            "atmospheric_tank_count": tank_cnt,
            "gas_wells_count": gas_wells,
            "wells_without_gas_count": wells_wo_gas,
            "annual_oil_throughput_bbl": oil_bbl,
            "two_year_delay_any": any_delay,
        }

    return {
        "by_sub_basin": by_sub_basin if by_sub_basin else None,
        "totals": totals if rows else None,
        "method3_overview": overview
    }


def parse_atmos_tanks_calc_3_no_flaring(root):
    """
    Parses atmospheric tank emissions calculated using Method 3 for tanks
    without flaring controls.
    """
    rows = find_all(root, "AtmosphericTanksCalcMethodThreeNoFlaringRowDetails")
    if not rows:
        return None

    by_sb = {}
    totals = {
        "count_uncontrolled": 0.0,
        "annual_co2_uncontrolled_mt": 0.0,
        "annual_ch4_uncontrolled_mt": 0.0,
    }

    for row in rows:
        sb = first_of(row, ["SubBasinId", "SubBasinID", "SubBasinIdentifier"], str) or "Unknown"

        # This count represents tanks whose emissions are not controlled by a flare.
        count = first_of(row, ["EmissionsNotControlledWithFlareCount"], as_float) or 0.0
        co2 = first_of(row, ["Co2Emissions"], as_float) or 0.0
        ch4 = first_of(row, ["Ch4Emissions"], as_float) or 0.0

        bucket = by_sb.setdefault(sb, {
            "sub_basin_id": sb,
            "count_uncontrolled": 0.0,
            "annual_co2_uncontrolled_mt": 0.0,
            "annual_ch4_uncontrolled_mt": 0.0,
        })

        bucket["count_uncontrolled"] += count
        bucket["annual_co2_uncontrolled_mt"] += co2
        bucket["annual_ch4_uncontrolled_mt"] += ch4

        totals["count_uncontrolled"] += count
        totals["annual_co2_uncontrolled_mt"] += co2
        totals["annual_ch4_uncontrolled_mt"] += ch4

    by_sub_basin = sorted(by_sb.values(), key=lambda x: x.get("sub_basin_id") or "")

    return {"by_sub_basin": by_sub_basin, "totals": totals}

def parse_associated_gas(root):
    sec = find_first(root, "AssociatedGasVentingFlaringDetails")
    if sec is None:
        return None
    return {
        "mt_co2": first_of(sec, ["TotalCarbonDioxideEmissions"], as_float),
        "mt_ch4": first_of(sec, ["TotalCh4MetricTonsEmissions"], as_float),
        "present": first_of(sec, [
            "DidFacilityHaveGasVenting"
        ], as_bool),
    }

def parse_unique_flare_stacks(root):
    rows = find_all(root, "UniqueFlareStacksRowDetails")
    if not rows:
        return None

    # Compute requested summaries
    n_stacks = len(rows)
    n_with_flow_monitor = 0
    n_with_gas_analyzer = 0
    vols = []
    effs = []
    ch4_mf = []
    ch4_emm = []

    for row in rows:
        # Flow monitor & gas analyzer – tag names vary; use heuristics:
        fm = guess_flag(row, "flow", "monitor") or \
             guess_flag(row, "continuous", "flow") or \
             ("continuous" in (first_of(row, ["FlowMeasurementMethod"], str) or "").lower())
        ga = guess_flag(row, "gas", "analyzer") or \
             ("analyzer" in (first_of(row, ["CompositionMeasurementMethod", "GasCompositionMethod"], str) or "").lower())

        if fm: n_with_flow_monitor += 1
        if ga: n_with_gas_analyzer += 1

        vol = (first_of(row, ["GasSentToFlare"], as_float) \
               or guess_numeric(row, "average", "gas", "flare"))
        if vol is not None:
            vols.append(vol)

        eff = first_of(row, ["FlareCombustionEfficiency"], as_float) \
              or guess_numeric(row, "efficiency")
        if eff is not None:
            effs.append(eff)

        mf = first_of(row, ["FlareFeedGasCH4MoleFraction"], as_float) \
             or guess_numeric(row, "mole", "fraction", "methane")
        if mf is not None:
            ch4_mf.append(mf)

        ch4 = first_of(row, ["Ch4Emissions"], as_float) \
              or guess_numeric(row, "methane", "emissions")
        if ch4 is not None:
            ch4_emm.append(ch4)

    n_either = sum(1 for _ in rows)  # we’ll recompute below with flags for “either”
    # recompute “either” properly:
    n_either = 0
    for row in rows:
        fm = guess_flag(row, "flow", "monitor") or \
             guess_flag(row, "continuous", "flow") or \
             ("continuous" in (first_of(row, ["FlowMeasurementMethod"], str) or "").lower())
        ga = guess_flag(row, "gas", "analyzer") or \
             ("analyzer" in (first_of(row, ["CompositionMeasurementMethod", "GasCompositionMethod"], str) or "").lower())
        if fm or ga:
            n_either += 1

    return {
        "num_stacks": n_stacks,
        "count_with_continuous_flow_monitor": n_with_flow_monitor,
        "count_with_continuous_gas_analyzer": n_with_gas_analyzer,
        "count_with_monitor_or_analyzer": n_either,
        "avg_volume_gas_to_flare": (mean(vols) if vols else None),
        "avg_flare_combustion_efficiency": (mean(effs) if effs else None),
        "avg_methane_mole_fraction_feed_gas": (mean(ch4_mf) if ch4_mf else None),
        "avg_ch4_emissions_per_stack": (mean(ch4_emm) if ch4_emm else None),
        "total_ch4_emissions_mt": (sum(ch4_emm) if ch4_emm else None),
    }


def parse_reciprocating_compressors(root):
    sec = find_first(root, "ReciprocatingCompressorsDetails")
    if sec is None:
        return None
    return {
        "mt_co2": first_of(sec, ["TotalCarbonDioxideEmissions"], as_float),
        "mt_ch4": first_of(sec, ["TotalCh4MetricTonsEmissions"], as_float),
        "count": first_of(sec, ["Count"],as_float),
        "present": first_of(sec, [
            "DoesFacilityHaveAnyReciprocatingCompressors"
        ], as_bool),

    }

def parse_centrifugal_compressors(root):
    sec = find_first(root, "CentrifugalCompressorsDetails")
    if sec is None:
        return None
    return {
        "mt_co2": first_of(sec, ["TotalCarbonDioxideEmissions"], as_float),
        "mt_ch4": first_of(sec, ["TotalCh4MetricTonsEmissions"], as_float),
        "present": first_of(sec, [
            "DoesFacilityHaveAnyCentrifugalCompressors"
        ], as_bool),
    }

def parse_equipment_leaks_by_survey(root):
    """
    Parses equipment leak emissions data determined via surveys. This function
    captures both the summary/overview data and the detailed breakdown by
    leaking component type.
    """
    # Find the main parent element for all equipment leak data
    sec = find_first(root, "OtherEmissionsFromEquipmentLeaksDetails")
    if sec is None:
        return None

    # --- 1. Parse the Summary/Overview Data ---
    summary = {
        "mt_co2": first_of(sec, ["TotalCarbonDioxideEmissions"], as_float),
        "mt_ch4": first_of(sec, ["TotalCh4MetricTonsEmissions"], as_float),
        "calculated_via_surveys": first_of(sec, ["EquipmentLeaksViaSurveys"], as_bool),
        "calculated_via_population_counts": first_of(sec, ["EquipmentLeaksViaPopulationCounts"], as_bool),
        "total_leaks_found_in_year": first_of(sec, ["TotalEquipmentLeaksDuringYear"], as_float),
        "missing_data_used": first_of(sec, ["MissingDataProceduresUsed"], as_bool),
        "elected_to_comply_with_98236q": first_of(sec, ["DidFacilityElectToComplyWith98236Q"], as_bool),
        "detection_methods_used": {
            "optical_gas_imaging_6018": first_of(sec, ["OpticalGasImagingInstrument6018"], as_bool),
            "method_21": first_of(sec, ["Method21"], as_bool),
            "infrared_laser_beam": first_of(sec, ["InfraredLaserBeamIlluminatedInstrument"], as_bool),
            "acoustic_detection": first_of(sec, ["AcousticLeakDetectionDevice"], as_bool),
            "optical_gas_imaging_605397a": first_of(sec, ["OpticalGasImagingInstrument605397A"], as_bool),
            "method_21_605397a": first_of(sec, ["Method21605397A"], as_bool),
        }
    }

    # --- 2. Parse the Detailed Component Breakdown ---
    component_rows = find_all(sec, "OnshorePetroleumAndNaturalGasProductionAndGatheringAndBoostingRowDetails")
    leaking_components = []

    for row in component_rows:
        ch4_emissions = first_of(row, ["Ch4Emissions"], as_float)

        # Per your request, only process components with actual methane emissions
        if ch4_emissions and ch4_emissions > 0:
            component_data = {
                "component_type": first_of(row, ["ComponentType"], str),
                "leaking_count": first_of(row, ["TotalLeakingComponentTypes"], as_float),
                "avg_time_leaking_hours": first_of(row, ["AverageTimeComponentsSurveyed"], as_float),
                "ch4_emissions_mt": ch4_emissions,
                "co2_emissions_mt": first_of(row, ["Co2Emissions"], as_float),
            }
            leaking_components.append(component_data)
    
    # Sort components by emissions descending for easier analysis later
    leaking_components.sort(key=lambda x: x.get('ch4_emissions_mt', 0), reverse=True)

    # --- 3. Combine and Return the Full Structured Data ---
    return {
        "summary": summary,
        "components": leaking_components if leaking_components else None
    }


def parse_facility_site_details(root):
    """
    Parses facility site information including location, parent company, and 
    basic facility characteristics.
    """
    sec = find_first(root, "FacilitySiteDetails")
    if sec is None:
        return None

    # Parse facility site name
    facility_site = find_first(sec, "FacilitySite")
    facility_name = child_text(facility_site, "FacilitySiteName") if facility_site else None

    # Parse location address
    location_address = find_first(sec, "LocationAddress")
    address_data = {}
    if location_address:
        address_data = {
            "street_address": child_text(location_address, "LocationAddressText"),
            "city": child_text(location_address, "LocalityName"),
            "state_code": None,
            "zip_code": child_text(location_address, "AddressPostalCode"),
        }
        
        # Handle nested StateIdentity structure
        state_identity = find_first(location_address, "StateIdentity")
        if state_identity:
            address_data["state_code"] = child_text(state_identity, "StateCode")

    # Parse parent company details
    parent_company_details = find_first(sec, "ParentCompanyDetails")
    parent_company_data = {}
    if parent_company_details:
        parent_company = find_first(parent_company_details, "ParentCompany")
        if parent_company:
            parent_company_data = {
                "legal_name": child_text(parent_company, "ParentCompanyLegalName"),
                "street_address": child_text(parent_company, "StreetAddress"),
                "city": child_text(parent_company, "City"),
                "state": child_text(parent_company, "State"),
                "zip_code": child_text(parent_company, "Zip"),
            }

    return {
        "facility_name": facility_name,
        "location_address": address_data if any(address_data.values()) else None,
        "cogeneration_unit_emissions_indicator": as_bool(child_text(sec, "CogenerationUnitEmissionsIndicator")),
        "primary_naics_code": child_text(sec, "PrimaryNAICSCode"),
        "parent_company": parent_company_data if any(parent_company_data.values()) else None,
    }
# ---------------------------
# Orchestrator
# ---------------------------

def parse_facility(root, facility_id, year):
    # The main dictionary to hold all parsed data for the facility
    facility_data = {
        "facility_id": facility_id,
        "year": year,
        "FacilitySiteDetails": parse_facility_site_details(root),
        "PneumaticDeviceVentingDetails": parse_pneumatic_device_venting(root),
        "AcidGasRemovalUnits_and_Dehydrators": parse_acid_gas_and_dehydrators(root),
        "WellVentingDetails": parse_well_venting(root),
        "WellsWithFracturingDetails": parse_wells_with_fracturing(root),
        "WellsWithoutFracturingDetails": parse_wells_without_fracturing(root),
        "WellCompletionsWithHydraulicFracturingTabgSummary": parse_well_completions_hf_tabg(root),
        "AssociatedGasVentingFlaringDetails": parse_associated_gas(root),
        "UniqueFlareStacks_Summary": parse_unique_flare_stacks(root),
        "CentrifugalCompressorsDetails": parse_centrifugal_compressors(root),
        "ReciprocatingCompressorsDetails": parse_reciprocating_compressors(root),
        "EquipmentLeakDetails": parse_equipment_leaks_by_survey(root),
        "OnshoreProductionWellDetails": parse_onshore_production_wells(root), 
    }

    tanks_data = parse_atmospheric_tanks(root)
    if tanks_data:
        facility_data.update(tanks_data)

    return facility_data

def get_facility_data(facility_id: int, year: int = 2023, timeout=30, retries=2):
    root = fetch_xml_root(facility_id, year, timeout=timeout, retries=retries)
    return parse_facility(root, facility_id, year)

# ---------------------------
# Batch helper (fast for many facilities)
# ---------------------------

def scrape_many(facility_ids, year=2023, max_workers=8, timeout=30):
    results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = {ex.submit(get_facility_data, fid, year, timeout): fid for fid in facility_ids}
        for fut in as_completed(futs):
            fid = futs[fut]
            try:
                results[fid] = fut.result()
            except Exception as e:
                results[fid] = {"facility_id": fid, "year": year, "error": str(e)}
    return results

# ---------------------------
# Example: run single facility
# ---------------------------

if __name__ == "__main__":
    import json, sys
    fid = int(sys.argv[1]) if len(sys.argv) > 1 else 1008052
    yr  = int(sys.argv[2]) if len(sys.argv) > 2 else 2023
    data = get_facility_data(fid, yr)
    print(json.dumps(data, indent=2))
