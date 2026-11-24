import json
import math
import streamlit as st

st.set_page_config(
    page_title="Ionforge · Battery Forge",
    layout="wide",
)

FORGE_DATA = {
    "description": (
        "This educational model uses illustrative single-cell parameters. "
        "Each day starts with a fully charged cell at ambient temperature. "
        "Capacity loss and resistance growth accumulate across days."
    ),
    "defaults": {
        "cathode": "lfp",
        "anode": "graphite",
        "electrolyte": "carbonate",
        "size": 48,
        "thickness": 55,
        "coat": 50,
        "profile": "pulse",
        "ambient": 25,
        "cycles": 300,
    },
    "cathode": [
        {
            "id": "lfp",
            "name": "LFP",
            "formula": "LiFePO4",
            "capacity": 155,
            "density": 3.6,
            "potential": 3.43,
            "transport": 1.15,
            "limit": 64,
            "life": 3200,
            "expansion": 7,
            "cost": 0.8,
            "supply": 0.92,
        },
        {
            "id": "nmc",
            "name": "NMC",
            "formula": "LiNi0.6Mn0.2Co0.2O2",
            "capacity": 186,
            "density": 4.75,
            "potential": 3.8,
            "transport": 1.0,
            "limit": 54,
            "life": 1600,
            "expansion": 6,
            "cost": 1.48,
            "supply": 0.57,
        },
        {
            "id": "lmo",
            "name": "LMO",
            "formula": "LiMn2O4",
            "capacity": 115,
            "density": 4.25,
            "potential": 4.0,
            "transport": 1.65,
            "limit": 59,
            "life": 1250,
            "expansion": 6.5,
            "cost": 0.87,
            "supply": 0.86,
        },
    ],
    "anode": [
        {
            "id": "graphite",
            "name": "Graphite",
            "formula": "C6",
            "capacity": 350,
            "density": 2.25,
            "potential": 0.13,
            "transport": 1.0,
            "limit": 65,
            "lifeFactor": 1.0,
            "expansion": 10,
            "cost": 0.85,
            "supply": 0.8,
        },
        {
            "id": "siox",
            "name": "Silicon-graphite",
            "formula": "SiOx / C",
            "capacity": 650,
            "density": 2.15,
            "potential": 0.24,
            "transport": 0.92,
            "limit": 57,
            "lifeFactor": 0.76,
            "expansion": 56,
            "cost": 1.45,
            "supply": 0.69,
        },
        {
            "id": "lto",
            "name": "Titanate",
            "formula": "Li4Ti5O12",
            "capacity": 165,
            "density": 3.5,
            "potential": 1.55,
            "transport": 2.2,
            "limit": 72,
            "lifeFactor": 1.9,
            "expansion": 1,
            "cost": 1.9,
            "supply": 0.75,
        },
    ],
    "electrolyte": [
        {
            "id": "carbonate",
            "name": "Liquid carbonate",
            "formula": "LiPF6 / EC-DMC",
            "transport": 1.0,
            "limit": 60,
            "lifeFactor": 1.0,
            "oxidation": 4.3,
            "cost": 0.85,
            "supply": 0.9,
        },
        {
            "id": "polymer",
            "name": "Gel polymer",
            "formula": "PVDF-HFP / LiPF6",
            "transport": 0.76,
            "limit": 69,
            "lifeFactor": 1.08,
            "oxidation": 4.4,
            "cost": 1.34,
            "supply": 0.76,
        },
    ],
    "process": {
        "activeMassG": 37,
        "packing": 0.59,
        "overheadMassG": 22,
        "overheadVolumeMl": 11,
        "anodeBalance": 1.12,
        "loadingMin": 0.7,
        "loadingRange": 0.6,
        "coatingMassPenalty": 0.035,
        "baseOhm": 0.059,
        "thicknessPenalty": 0.8,
        "nanoTransport": 0.7,
        "coatTransportPenalty": 0.14,
        "nanoAgePenalty": 0.28,
        "coatLifeGain": 0.65,
        "coldOhm": 0.035,
        "agingOhm": 1.7,
        "coolingWPerK": 0.035,
        "heatCapacityJPerK": 58,
        "cutoffDrop": 0.55,
        "endOfLifeLoss": 0.2,
        "thermalReserve": 8,
        "stepMinutes": 5,
    },
    "profile": [
        {
            "id": "steady",
            "name": "Steady load",
            "description": "Continuous operation at nearly constant power.",
            "ambient": 25,
            "base": 0.41,
            "variation": 0.02,
            "peaks": [],
        },
        {
            "id": "pulse",
            "name": "Pulse load",
            "description": "Low baseline demand with morning and evening power pulses.",
            "ambient": 25,
            "base": 0.24,
            "variation": 0.12,
            "peaks": [
                [6.6, 1.4, 0.31],
                [8.25, 5.5, 0.12],
                [12.6, 2.4, 0.21],
                [17.25, 11.3, 0.09],
                [18.15, 6.2, 0.1],
                [20.5, 1.2, 0.28],
            ],
        },
        {
            "id": "extreme",
            "name": "Extreme heat",
            "description": "A hot ambient environment with repeated midday demand peaks.",
            "ambient": 45,
            "base": 0.34,
            "variation": 0.11,
            "peaks": [
                [8, 2.5, 0.27],
                [11.7, 5.8, 0.18],
                [13.65, 6.5, 0.2],
                [15.1, 4.3, 0.13],
                [19.45, 2.5, 0.24],
            ],
        },
    ],
}


def clamp(x: float, low: float, high: float) -> float:
    return min(high, max(low, x))


def score_val(x: float) -> int:
    return int(round(clamp(x, 0, 100)))


def run_simulation(cfg: dict, data: dict) -> dict:
    cathode = next(item for item in data["cathode"] if item["id"] == cfg["cathode"])
    anode = next(item for item in data["anode"] if item["id"] == cfg["anode"])
    electrolyte = next(item for item in data["electrolyte"] if item["id"] == cfg["electrolyte"])
    profile = next(item for item in data["profile"] if item["id"] == cfg["profile"])
    p = data["process"]

    nano = clamp(float(cfg["size"]), 0, 100) / 100.0
    thick = clamp(float(cfg["thickness"]), 0, 100) / 100.0
    coat = clamp(float(cfg["coat"]), 0, 100) / 100.0
    ambient = clamp(float(cfg["ambient"]), -40, 70)
    cycles = int(round(clamp(float(cfg["cycles"]), 1, 1000)))

    mass = p["activeMassG"] * (p["loadingMin"] + p["loadingRange"] * thick)
    positive_mass = mass / (1.0 + p["anodeBalance"] * cathode["capacity"] / anode["capacity"])
    voltage = cathode["potential"] - anode["potential"]
    ah = positive_mass * cathode["capacity"] / 1000.0 * (1.0 - p["coatingMassPenalty"] * coat)
    wh = voltage * ah
    whkg = 1000.0 * wh / (mass + p["overheadMassG"])
    whl = 1000.0 * wh / (
        p["overheadVolumeMl"]
        + (positive_mass / cathode["density"] + (mass - positive_mass) / anode["density"]) / p["packing"]
    )

    transport = math.sqrt(cathode["transport"] * anode["transport"]) * electrolyte["transport"]
    ohm = (
        p["baseOhm"]
        * (0.65 + p["thicknessPenalty"] * thick)
        * (1.0 + p["coatTransportPenalty"] * coat)
        / (transport * (0.8 + p["nanoTransport"] * nano))
    )
    discharge_c = 2.9 * transport * (0.75 + nano) / (0.8 + thick)
    charge_c = discharge_c * (0.8 if anode["id"] == "lto" else 0.45)
    thermal_limit = min(cathode["limit"], anode["limit"], electrolyte["limit"])
    life = int(
        round(
            cathode["life"]
            * anode["lifeFactor"]
            * electrolyte["lifeFactor"]
            * (0.82 + p["coatLifeGain"] * coat)
            / (1.0 + p["nanoAgePenalty"] * nano)
        )
    )

    steps = int(round(24 * 60 / p["stepMinutes"]))
    dt = 24.0 / steps
    cooling = 1.0 - math.exp(-p["coolingWPerK"] * dt * 3600.0 / p["heatCapacityJPerK"])

    demand = []
    for i in range(steps):
        h = (i + 0.5) * dt
        watts = profile["base"] + profile["variation"] * (1.0 - math.cos(2.0 * math.pi * h / 24.0)) / 2.0
        for center, amplitude, width in profile["peaks"]:
            watts += amplitude * math.exp(-0.5 * ((h - center) / width) ** 2)
        demand.append(watts)

    required = sum(watts * dt for watts in demand)
    series = []
    health = [{"cycle": 0, "soh": 100.0}]

    remaining_health = 1.0
    delivered = 0.0
    peak_temp = ambient
    max_sag = 0.0
    heat_limited = False
    voltage_limited = False
    current_limited = False
    depleted = False
    cutoff = voltage - p["cutoffDrop"]

    for cycle in range(1, cycles + 1):
        capacity = ah * remaining_health
        base_r = ohm * (1.0 + p["agingOhm"] * (1.0 - remaining_health))
        soc = 1.0
        temp = ambient
        day_peak = temp
        peak_c = 0.0

        for i in range(steps):
            watts = demand[i]
            r = base_r * (1.0 + p["coldOhm"] * max(0.0, 25.0 - temp))
            ocv = voltage + 0.54 * (soc - 0.5)
            target_i = 2.0 * watts / (ocv + math.sqrt(max(0.0, ocv * ocv - 4.0 * r * watts)))
            derate = clamp((thermal_limit - temp) / p["thermalReserve"], 0.0, 1.0)
            rate_i = capacity * discharge_c
            cutoff_i = max(0.0, (ocv - cutoff) / r)
            available_i = soc * capacity / dt
            current = min(target_i, ocv / (2.0 * r), rate_i * derate, cutoff_i, available_i)
            sag = current * r
            terminal = ocv - sag
            watts_out = current * terminal

            if watts_out < watts * 0.995:
                if current == available_i:
                    depleted = True
                if current == cutoff_i or current == ocv / (2.0 * r):
                    voltage_limited = True
                if current == rate_i * derate:
                    if derate < 1.0:
                        heat_limited = True
                    else:
                        current_limited = True

            if cycle == cycles and i == 0:
                series.append({
                    "hour": 0.0,
                    "demand": watts,
                    "output": watts_out,
                    "soc": 100.0,
                    "temp": temp,
                    "voltage": terminal,
                    "sag": sag,
                })

            soc = max(0.0, soc - current * dt / capacity)
            temp += cooling * (ambient + current * current * r / p["coolingWPerK"] - temp)
            day_peak = max(day_peak, temp)
            max_sag = max(max_sag, sag)
            peak_c = max(peak_c, current / capacity)
            delivered += watts_out * dt

            if cycle == cycles:
                series.append({
                    "hour": (i + 1) * dt,
                    "demand": watts,
                    "output": watts_out,
                    "soc": soc * 100.0,
                    "temp": temp,
                    "voltage": terminal,
                    "sag": sag,
                })

        peak_temp = max(peak_temp, day_peak)
        rate_stress = 1.0 + max(0.0, peak_c - 0.5) * (0.15 + anode["expansion"] / 220.0)
        heat_stress = 2.0 ** ((day_peak - 25.0) / 14.0)
        cold_recharge_stress = 1.0 + max(0.0, 10.0 - ambient) / 12.0
        daily_loss = (
            p["endOfLifeLoss"]
            / life
            * (0.1 + 0.9 * (1.0 - soc))
            * rate_stress
            * (0.22 + 0.78 * heat_stress)
            * cold_recharge_stress
        )
        remaining_health = max(0.01, remaining_health - daily_loss)
        health.append({"cycle": cycle, "soh": remaining_health * 100.0})

    fulfillment = clamp(100.0 * delivered / (cycles * required), 0.0, 100.0)
    scores = {
        "energy": score_val(whkg / 2.7),
        "power": score_val(0.68 * fulfillment + 3.3 * discharge_c + 12.0 * (1.0 - max_sag / voltage)),
        "life": score_val(100.0 * (1.0 - math.exp(-life / 1850.0)) * remaining_health),
        "safety": score_val(50.0 + 1.2 * (thermal_limit - peak_temp) - 30.0 * max_sag / voltage),
        "cost": score_val(
            65.0 / ((cathode["cost"] + anode["cost"] + electrolyte["cost"]) / 3.0 + coat * 0.12)
            + 20.0 * (cathode["supply"] + anode["supply"] + electrolyte["supply"]) / 3.0
        ),
    }

    if fulfillment < 90:
        title = "Energy shortfall"
    elif scores["energy"] >= 86:
        title = "High-energy cell"
    elif scores["power"] >= 90:
        title = "Pulse-load buffer"
    elif scores["safety"] >= 83:
        title = "Thermally stable cell"
    else:
        title = "General-purpose cell"

    notes = []
    if depleted:
        notes.append("The cell ran out of charge before the end of the load profile. Increasing active material loading raises usable capacity.")
    if heat_limited:
        notes.append("Discharge current was reduced as cell temperature approached its limit.")
    if voltage_limited:
        notes.append("Voltage sag across the internal resistance limited output during a demand peak.")
    if current_limited:
        notes.append("A load pulse exceeded the discharge current limit of the electrode pair.")
    if not notes:
        notes.append("The cell maintained voltage and supplied the required power throughout the load profile.")

    if anode["expansion"] > 30:
        notes.append("The silicon-containing electrode expands during cycling. Large current pulses accelerate its degradation.")
    elif ambient >= 35 or ambient < 10:
        notes.append(
            "High temperatures accelerate daily capacity loss."
            if ambient >= 35
            else "Cold conditions increase internal resistance and accelerate wear during recharge."
        )
    else:
        notes.append(
            "The coating slows electrode degradation while slightly increasing resistance and cost."
            if coat >= 0.5
            else "A thinner coating reduces inactive mass at the expense of cycle stability."
        )

    return {
        "voltage": voltage,
        "ah": ah,
        "wh": wh,
        "whkg": whkg,
        "whl": whl,
        "resistance": ohm * 1000.0,
        "chargeC": charge_c,
        "dischargeC": discharge_c,
        "thermalLimit": thermal_limit,
        "life": life,
        "fade": 100.0 * (1.0 - remaining_health) / cycles,
        "fulfillment": fulfillment,
        "peakTemp": peak_temp,
        "maxSag": max_sag,
        "soh": remaining_health * 100.0,
        "series": series,
        "health": health,
        "scores": scores,
        "title": title,
        "notes": notes,
    }


def init_state() -> None:
    if "config" not in st.session_state:
        st.session_state.config = dict(FORGE_DATA["defaults"])
    if "journal" not in st.session_state:
        st.session_state.journal = []


def apply_preset(preset_id: str) -> None:
    if preset_id == "default":
        st.session_state.config = dict(FORGE_DATA["defaults"])
    elif preset_id == "high_energy":
        st.session_state.config = {
            "cathode": "nmc",
            "anode": "siox",
            "electrolyte": "carbonate",
            "size": 35,
            "thickness": 85,
            "coat": 65,
            "profile": "steady",
            "ambient": 25,
            "cycles": 300,
        }
    elif preset_id == "high_power":
        st.session_state.config = {
            "cathode": "lmo",
            "anode": "lto",
            "electrolyte": "carbonate",
            "size": 85,
            "thickness": 25,
            "coat": 30,
            "profile": "pulse",
            "ambient": 25,
            "cycles": 300,
        }


init_state()
cfg = st.session_state.config

st.title("Battery Forge")
st.caption("Choose materials, apply a load profile, and see how your cell performs.")

top_c1, top_c2, top_c3, top_c4, top_c5 = st.columns(5)
with top_c1:
    if st.button("Default recipe", use_container_width=True):
        apply_preset("default")
        st.rerun()
with top_c2:
    if st.button("High-energy preset", use_container_width=True):
        apply_preset("high_energy")
        st.rerun()
with top_c3:
    if st.button("High-power preset", use_container_width=True):
        apply_preset("high_power")
        st.rerun()
with top_c4:
    recipe_label = st.text_input(
        "Recipe name",
        value=f"{cfg['cathode'].upper()} / {cfg['anode'].upper()}",
        label_visibility="collapsed",
    )
with top_c5:
    if st.button("Save to journal", use_container_width=True):
        st.session_state.journal.insert(0, {"name": recipe_label.strip() or "Saved cell", "config": dict(cfg)})

with st.sidebar:
    st.header("Forge settings")

    st.subheader("Cell materials")
    cathode_ids = [x["id"] for x in FORGE_DATA["cathode"]]
    cathode_names = {x["id"]: f"{x['name']} ({x['formula']})" for x in FORGE_DATA["cathode"]}
    cfg["cathode"] = st.selectbox(
        "Cathode",
        options=cathode_ids,
        index=cathode_ids.index(cfg["cathode"]),
        format_func=lambda k: cathode_names[k],
    )

    anode_ids = [x["id"] for x in FORGE_DATA["anode"]]
    anode_names = {x["id"]: f"{x['name']} ({x['formula']})" for x in FORGE_DATA["anode"]}
    cfg["anode"] = st.selectbox(
        "Anode",
        options=anode_ids,
        index=anode_ids.index(cfg["anode"]),
        format_func=lambda k: anode_names[k],
    )

    elec_ids = [x["id"] for x in FORGE_DATA["electrolyte"]]
    elec_names = {x["id"]: f"{x['name']} ({x['formula']})" for x in FORGE_DATA["electrolyte"]}
    cfg["electrolyte"] = st.selectbox(
        "Electrolyte",
        options=elec_ids,
        index=elec_ids.index(cfg["electrolyte"]),
        format_func=lambda k: elec_names[k],
    )

    st.subheader("Electrode processing")
    cfg["size"] = st.slider("Particle refinement", min_value=0, max_value=100, value=int(cfg["size"]))
    cfg["thickness"] = st.slider("Electrode thickness", min_value=0, max_value=100, value=int(cfg["thickness"]))
    cfg["coat"] = st.slider("Surface coating", min_value=0, max_value=100, value=int(cfg["coat"]))

    st.subheader("Test conditions")
    prof_ids = [x["id"] for x in FORGE_DATA["profile"]]
    prof_names = {x["id"]: x["name"] for x in FORGE_DATA["profile"]}
    prev_profile = cfg["profile"]
    selected_profile = st.selectbox(
        "Load profile",
        options=prof_ids,
        index=prof_ids.index(cfg["profile"]),
        format_func=lambda k: prof_names[k],
    )
    if selected_profile != prev_profile:
        cfg["profile"] = selected_profile
        cfg["ambient"] = next(x["ambient"] for x in FORGE_DATA["profile"] if x["id"] == selected_profile)
    else:
        cfg["profile"] = selected_profile

    cfg["ambient"] = st.number_input("Ambient (°C)", min_value=-20, max_value=60, value=int(cfg["ambient"]), step=1)
    cfg["cycles"] = st.number_input("Cycle count", min_value=1, max_value=1000, value=int(cfg["cycles"]), step=1)

res = run_simulation(cfg, FORGE_DATA)

st.subheader(f"Cell under test: {cfg['cathode'].upper()} / {cfg['anode'].upper()}")
h1, h2, h3, h4 = st.columns(4)
h1.metric("Nominal voltage", f"{res['voltage']:.2f} V")
h2.metric("Capacity", f"{res['ah']:.2f} Ah")
h3.metric("Internal resistance", f"{res['resistance']:.1f} mΩ")
h4.metric("Specific energy", f"{res['whkg']:.0f} Wh/kg")

st.divider()

st.subheader("Test results")
m1, m2, m3 = st.columns(3)
m1.metric("Demand met", f"{res['fulfillment']:.1f} %")
m2.metric("Peak temperature", f"{res['peakTemp']:.1f} °C")
m3.metric("State of health", f"{res['soh']:.1f} %")

st.subheader("Load response")
tab_power, tab_thermal, tab_health = st.tabs(["Power & SoC", "Temperature & voltage", "Capacity fade"])

with tab_power:
    power_rows = {
        row["hour"]: {"Demand (W)": row["demand"], "Output (W)": row["output"], "SoC (%)": row["soc"]}
        for row in res["series"]
    }
    st.line_chart(power_rows, height=280)

with tab_thermal:
    thermal_rows = {
        row["hour"]: {
            "Temperature (°C)": row["temp"],
            "Terminal voltage (V)": row["voltage"],
            "Voltage sag (V)": row["sag"],
        }
        for row in res["series"]
    }
    st.line_chart(thermal_rows, height=280)

with tab_health:
    health_rows = {row["cycle"]: {"State of health (%)": row["soh"]} for row in res["health"]}
    st.line_chart(health_rows, height=280)

st.subheader(f"Recipe evaluation — {res['title']}")
score_labels = [
    ("Energy density", res["scores"]["energy"]),
    ("Power response", res["scores"]["power"]),
    ("Cycle stability", res["scores"]["life"]),
    ("Safety margin", res["scores"]["safety"]),
    ("Cost and scalability", res["scores"]["cost"]),
]
for label, val in score_labels:
    st.write(f"**{label}**: {val} / 100")
    st.progress(val)

for note in res["notes"]:
    st.write(f"- {note}")

with st.expander("Cell specifications & model notes"):
    spec_table = [
        {"Parameter": "Usable energy", "Value": f"{res['wh']:.1f} Wh"},
        {"Parameter": "Energy density", "Value": f"{res['whkg']:.0f} Wh/kg · {res['whl']:.0f} Wh/L"},
        {"Parameter": "Charge / Discharge C-rate", "Value": f"{res['chargeC']:.1f} C / {res['dischargeC']:.1f} C"},
        {"Parameter": "Temperature limit", "Value": f"{res['thermalLimit']} °C"},
        {"Parameter": "Baseline cycle life", "Value": f"{res['life']} cycles"},
        {"Parameter": "Maximum voltage sag", "Value": f"{res['maxSag']:.2f} V"},
        {"Parameter": "Capacity loss per cycle", "Value": f"{res['fade']:.3f} percentage points"},
    ]
    st.dataframe(spec_table, use_container_width=True, hide_index=True)
    st.caption(FORGE_DATA["description"])

    export_payload = json.dumps({"version": 1, "config": cfg}, indent=2)
    st.download_button(
        label="Export configuration (JSON)",
        data=export_payload,
        file_name=f"ion-forge-{cfg['cathode']}-{cfg['profile']}.json",
        mime="application/json",
    )

if st.session_state.journal:
    with st.expander(f"Recipe journal ({len(st.session_state.journal)} saved)"):
        for idx, item in enumerate(st.session_state.journal):
            c_left, c_right = st.columns([4, 1])
            with c_left:
                ic = item["config"]
                st.write(f"**{item['name']}** — {ic['cathode'].upper()} / {ic['anode'].upper()} ({ic['profile']}, {ic['ambient']} °C, {ic['cycles']} cycles)")
            with c_right:
                if st.button("Load", key=f"load_{idx}", use_container_width=True):
                    st.session_state.config = dict(item["config"])
                    st.rerun()