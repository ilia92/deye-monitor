#!/usr/bin/python3
import sys
import argparse
import configparser
from pathlib import Path
from string import Formatter

# Optional dependency (only needed when actually querying the inverter)
try:
    from pysolarmanv5 import PySolarmanV5
except Exception:
    PySolarmanV5 = None

# ---------------- Register map (same semantics as before) ----------------
REGISTER_DEFINITIONS = {
    0x02A0: {'name': 'PV1 Power', 'scale': 10, 'unit': 'W', 'group': 'solar', 'signed': False},
    0x02A1: {'name': 'PV2 Power', 'scale': 10, 'unit': 'W', 'group': 'solar', 'signed': False},
    0x02A2: {'name': 'PV3 Power', 'scale': 10, 'unit': 'W', 'group': 'solar', 'signed': False},
    0x02A3: {'name': 'PV4 Power', 'scale': 10, 'unit': 'W', 'group': 'solar', 'signed': False},
    0x02A4: {'name': 'PV1 Voltage', 'scale': 0.1, 'unit': 'V', 'group': 'solar', 'signed': False},
    0x02A5: {'name': 'PV1 Current', 'scale': 0.1, 'unit': 'A', 'group': 'solar', 'signed': False},
    0x02A6: {'name': 'PV2 Voltage', 'scale': 0.1, 'unit': 'V', 'group': 'solar', 'signed': False},
    0x02A7: {'name': 'PV2 Current', 'scale': 0.1, 'unit': 'A', 'group': 'solar', 'signed': False},
    0x02A8: {'name': 'PV3 Voltage', 'scale': 0.1, 'unit': 'V', 'group': 'solar', 'signed': False},
    0x02A9: {'name': 'PV3 Current', 'scale': 0.1, 'unit': 'A', 'group': 'solar', 'signed': False},
    0x02AA: {'name': 'PV4 Voltage', 'scale': 0.1, 'unit': 'V', 'group': 'solar', 'signed': False},
    0x02AB: {'name': 'PV4 Current', 'scale': 0.1, 'unit': 'A', 'group': 'solar', 'signed': False},
    0x0211: {'name': 'Daily Production', 'scale': 0.1, 'unit': 'kWh', 'group': 'solar', 'signed': False},
    0x0216: {'name': 'Total Production Low', 'scale': 0.1, 'unit': 'kWh', 'group': 'solar', 'signed': False},
    0x0217: {'name': 'Total Production High', 'scale': 0.1, 'unit': 'kWh', 'group': 'solar', 'signed': False},

    0x0063: {'name': 'Battery Equalization V', 'scale': 0.1, 'unit': 'V', 'group': 'battery', 'signed': False},
    0x0064: {'name': 'Battery Absorption V', 'scale': 0.1, 'unit': 'V', 'group': 'battery', 'signed': False},
    0x0065: {'name': 'Battery Float V', 'scale': 0.1, 'unit': 'V', 'group': 'battery', 'signed': False},
    0x0066: {'name': 'Battery Capacity', 'scale': 1, 'unit': 'Ah', 'group': 'battery', 'signed': False},
    0x006C: {'name': 'Battery Max A Charge', 'scale': 1, 'unit': 'A', 'group': 'battery', 'signed': False},
    0x006D: {'name': 'Battery Max A Discharge', 'scale': 1, 'unit': 'A', 'group': 'battery', 'signed': False},
    0x0202: {'name': 'Daily Battery Charge', 'scale': 0.1, 'unit': 'kWh', 'group': 'battery', 'signed': False},
    0x0203: {'name': 'Daily Battery Discharge', 'scale': 0.1, 'unit': 'kWh', 'group': 'battery', 'signed': False},
    0x0204: {'name': 'Total Battery Charge Low', 'scale': 0.1, 'unit': 'kWh', 'group': 'battery', 'signed': False},
    0x0205: {'name': 'Total Battery Charge High', 'scale': 0.1, 'unit': 'kWh', 'group': 'battery', 'signed': False},
    0x0206: {'name': 'Total Battery Discharge Low', 'scale': 0.1, 'unit': 'kWh', 'group': 'battery', 'signed': False},
    0x0207: {'name': 'Total Battery Discharge High', 'scale': 0.1, 'unit': 'kWh', 'group': 'battery', 'signed': False},
    0x024A: {'name': 'Battery Temperature', 'scale': 0.1, 'unit': '°C', 'group': 'battery', 'signed': False, 'offset': 1000},
    0x024B: {'name': 'Battery Voltage', 'scale': 0.1, 'unit': 'V', 'group': 'battery', 'signed': False},
    0x024C: {'name': 'Battery SOC', 'scale': 1, 'unit': '%', 'group': 'battery', 'signed': False},
    0x024E: {'name': 'Battery Power', 'scale': 10, 'unit': 'W', 'group': 'battery', 'signed': True},
    0x024F: {'name': 'Battery Current', 'scale': 0.01, 'unit': 'A', 'group': 'battery', 'signed': True},

    0x0256: {'name': 'Grid Voltage L1', 'scale': 0.1, 'unit': 'V', 'group': 'grid', 'signed': False},
    0x0257: {'name': 'Grid Voltage L2', 'scale': 0.1, 'unit': 'V', 'group': 'grid', 'signed': False},
    0x0258: {'name': 'Grid Voltage L3', 'scale': 0.1, 'unit': 'V', 'group': 'grid', 'signed': False},
    0x025C: {'name': 'Internal CT L1 Power', 'scale': 1, 'unit': 'W', 'group': 'grid', 'signed': True},
    0x025D: {'name': 'Internal CT L2 Power', 'scale': 1, 'unit': 'W', 'group': 'grid', 'signed': True},
    0x025E: {'name': 'Internal CT L3 Power', 'scale': 1, 'unit': 'W', 'group': 'grid', 'signed': True},
    0x0268: {'name': 'External CT L1 Power', 'scale': 1, 'unit': 'W', 'group': 'grid', 'signed': True},
    0x0269: {'name': 'External CT L2 Power', 'scale': 1, 'unit': 'W', 'group': 'grid', 'signed': True},
    0x026A: {'name': 'External CT L3 Power', 'scale': 1, 'unit': 'W', 'group': 'grid', 'signed': True},
    0x0271: {'name': 'Total Grid Power', 'scale': 1, 'unit': 'W', 'group': 'grid', 'signed': True},
    0x0208: {'name': 'Daily Energy Bought', 'scale': 0.1, 'unit': 'kWh', 'group': 'grid', 'signed': False},
    0x020A: {'name': 'Total Energy Bought Low', 'scale': 0.1, 'unit': 'kWh', 'group': 'grid', 'signed': False},
    0x020B: {'name': 'Total Energy Bought High', 'scale': 0.1, 'unit': 'kWh', 'group': 'grid', 'signed': False},
    0x0209: {'name': 'Daily Energy Sold', 'scale': 0.1, 'unit': 'kWh', 'group': 'grid', 'signed': False},
    0x020C: {'name': 'Total Energy Sold Low', 'scale': 0.1, 'unit': 'kWh', 'group': 'grid', 'signed': False},
    0x020D: {'name': 'Total Energy Sold High', 'scale': 0.1, 'unit': 'kWh', 'group': 'grid', 'signed': False},

    0x028A: {'name': 'Load L1 Power', 'scale': 1, 'unit': 'W', 'group': 'load', 'signed': True},
    0x028B: {'name': 'Load L2 Power', 'scale': 1, 'unit': 'W', 'group': 'load', 'signed': True},
    0x028C: {'name': 'Load L3 Power', 'scale': 1, 'unit': 'W', 'group': 'load', 'signed': True},
    0x028D: {'name': 'Total Load Power', 'scale': 1, 'unit': 'W', 'group': 'load', 'signed': True},
    0x0284: {'name': 'Load Voltage L1', 'scale': 0.1, 'unit': 'V', 'group': 'load', 'signed': False},
    0x0285: {'name': 'Load Voltage L2', 'scale': 0.1, 'unit': 'V', 'group': 'load', 'signed': False},
    0x0286: {'name': 'Load Voltage L3', 'scale': 0.1, 'unit': 'V', 'group': 'load', 'signed': False},

    0x020E: {'name': 'Daily Load Consumption', 'scale': 0.1, 'unit': 'kWh', 'group': 'load', 'signed': False},
    0x020F: {'name': 'Total Load Consumption Low', 'scale': 0.1, 'unit': 'kWh', 'group': 'load', 'signed': False},
    0x0210: {'name': 'Total Load Consumption High', 'scale': 0.1, 'unit': 'kWh', 'group': 'load', 'signed': False},

    0x0276: {'name': 'Current L1', 'scale': 0.01, 'unit': 'A', 'group': 'inverter', 'signed': True},
    0x0277: {'name': 'Current L2', 'scale': 0.01, 'unit': 'A', 'group': 'inverter', 'signed': True},
    0x0278: {'name': 'Current L3', 'scale': 0.01, 'unit': 'A', 'group': 'inverter', 'signed': True},
    0x0279: {'name': 'Inverter L1 Power', 'scale': 1, 'unit': 'W', 'group': 'inverter', 'signed': True},
    0x027A: {'name': 'Inverter L2 Power', 'scale': 1, 'unit': 'W', 'group': 'inverter', 'signed': True},
    0x027B: {'name': 'Inverter L3 Power', 'scale': 1, 'unit': 'W', 'group': 'inverter', 'signed': True},

    0x021C: {'name': 'DC Temperature', 'scale': 0.1, 'unit': '°C', 'group': 'inverter', 'signed': True, 'offset': 1000},
    0x021D: {'name': 'AC Temperature', 'scale': 0.1, 'unit': '°C', 'group': 'inverter', 'signed': True, 'offset': 1000},

    130: {'name': 'Grid Charge Enable', 'scale': 1, 'unit': '', 'group': 'tou', 'signed': False},
    145: {'name': 'Solar Sell Enable', 'scale': 1, 'unit': '', 'group': 'tou', 'signed': False},
    166: {'name': 'ToU SOC Slot 1', 'scale': 1, 'unit': '%', 'group': 'tou', 'signed': False},
    167: {'name': 'ToU SOC Slot 2', 'scale': 1, 'unit': '%', 'group': 'tou', 'signed': False},
    168: {'name': 'ToU SOC Slot 3', 'scale': 1, 'unit': '%', 'group': 'tou', 'signed': False},
    169: {'name': 'ToU SOC Slot 4', 'scale': 1, 'unit': '%', 'group': 'tou', 'signed': False},
    170: {'name': 'ToU SOC Slot 5', 'scale': 1, 'unit': '%', 'group': 'tou', 'signed': False},
    171: {'name': 'ToU SOC Slot 6', 'scale': 1, 'unit': '%', 'group': 'tou', 'signed': False},
    172: {'name': 'ToU Charge Enable Slot 1', 'scale': 1, 'unit': '', 'group': 'tou', 'signed': False},
    173: {'name': 'ToU Charge Enable Slot 2', 'scale': 1, 'unit': '', 'group': 'tou', 'signed': False},
    174: {'name': 'ToU Charge Enable Slot 3', 'scale': 1, 'unit': '', 'group': 'tou', 'signed': False},
    175: {'name': 'ToU Charge Enable Slot 4', 'scale': 1, 'unit': '', 'group': 'tou', 'signed': False},
    176: {'name': 'ToU Charge Enable Slot 5', 'scale': 1, 'unit': '', 'group': 'tou', 'signed': False},
    177: {'name': 'ToU Charge Enable Slot 6', 'scale': 1, 'unit': '', 'group': 'tou', 'signed': False},
    178: {'name': 'ToU Sell Slot 1', 'scale': 1, 'unit': '', 'group': 'tou', 'signed': False},
    179: {'name': 'ToU Sell Slot 2', 'scale': 1, 'unit': '', 'group': 'tou', 'signed': False},
    180: {'name': 'ToU Sell Slot 3', 'scale': 1, 'unit': '', 'group': 'tou', 'signed': False},
    181: {'name': 'ToU Sell Slot 4', 'scale': 1, 'unit': '', 'group': 'tou', 'signed': False},
    182: {'name': 'ToU Sell Slot 5', 'scale': 1, 'unit': '', 'group': 'tou', 'signed': False},
    183: {'name': 'ToU Sell Slot 6', 'scale': 1, 'unit': '', 'group': 'tou', 'signed': False},
    184: {'name': 'Alt Sell Slot 1', 'scale': 1, 'unit': '', 'group': 'tou', 'signed': False},
    185: {'name': 'Alt Sell Slot 2', 'scale': 1, 'unit': '', 'group': 'tou', 'signed': False},
    186: {'name': 'Alt Sell Slot 3', 'scale': 1, 'unit': '', 'group': 'tou', 'signed': False},
    187: {'name': 'Alt Sell Slot 4', 'scale': 1, 'unit': '', 'group': 'tou', 'signed': False},
    188: {'name': 'Alt Sell Slot 5', 'scale': 1, 'unit': '', 'group': 'tou', 'signed': False},
    189: {'name': 'Alt Sell Slot 6', 'scale': 1, 'unit': '', 'group': 'tou', 'signed': False},

    0x0094: {'name': 'ToU Time 1', 'scale': 1, 'unit': '', 'group': 'tou', 'signed': False},
    0x0095: {'name': 'ToU Time 2', 'scale': 1, 'unit': '', 'group': 'tou', 'signed': False},
    0x0096: {'name': 'ToU Time 3', 'scale': 1, 'unit': '', 'group': 'tou', 'signed': False},
    0x0097: {'name': 'ToU Time 4', 'scale': 1, 'unit': '', 'group': 'tou', 'signed': False},
    0x0098: {'name': 'ToU Time 5', 'scale': 1, 'unit': '', 'group': 'tou', 'signed': False},
    0x0099: {'name': 'ToU Time 6', 'scale': 1, 'unit': '', 'group': 'tou', 'signed': False},

    0x009A: {'name': 'ToU Power 1', 'scale': 1, 'unit': 'W', 'group': 'tou', 'signed': False},
    0x009B: {'name': 'ToU Power 2', 'scale': 1, 'unit': 'W', 'group': 'tou', 'signed': False},
    0x009C: {'name': 'ToU Power 3', 'scale': 1, 'unit': 'W', 'group': 'tou', 'signed': False},
    0x009D: {'name': 'ToU Power 4', 'scale': 1, 'unit': 'W', 'group': 'tou', 'signed': False},
    0x009E: {'name': 'ToU Power 5', 'scale': 1, 'unit': 'W', 'group': 'tou', 'signed': False},
    0x009F: {'name': 'ToU Power 6', 'scale': 1, 'unit': 'W', 'group': 'tou', 'signed': False},
}

def _minutes_to_time(val: int) -> str:
    if val == 0 or val >= 2400:  # Deye encodes as HHMM, 0 and >=2400 wrap to 00:00
        return "00:00"
    h = val // 100
    m = val % 100
    return f"{h:02d}:{m:02d}"

def _signed_adjust(reg: int, value: int) -> int:
    meta = REGISTER_DEFINITIONS.get(reg, {})
    if meta.get('signed') and value is not None:
        if value > 32767:
            value -= 65536
    return value

def _scaled_value(reg: int, raw: int) -> float:
    if raw is None:
        return 0.0
    meta = REGISTER_DEFINITIONS.get(reg, {})
    value = _signed_adjust(reg, raw)
    if meta.get('offset', 0):
        value = abs(value - meta['offset'])
    return float(value) * float(meta.get('scale', 1))

def _log(verbose: bool, *args, **kwargs):
    if verbose:
        print(*args, **kwargs)

def _bulk_read(ip: str, sn: int, verbose: bool = False):
    ranges = [
        {'start': 0x0094, 'count': 84},  # ToU + Battery + Grid
        {'start': 0x0202, 'count': 32},  # Energy Stats
        {'start': 0x024A, 'count': 68},  # Live Status
        {'start': 0x02A0, 'count': 12},  # PV Strings
    ]
    inv = PySolarmanV5(ip, sn)
    data = {}
    for r in ranges:
        _log(verbose, f"Reading 0x{r['start']:04X}..+{r['count']}")
        arr = inv.read_holding_registers(r['start'], r['count'])
        for i, v in enumerate(arr):
            data[r['start'] + i] = v
    inv.disconnect()
    return data

def _calc_32bit(low, high):
    low = int(low or 0) & 0xFFFF
    high = int(high or 0) & 0xFFFF
    return ((high << 16) | low) * 0.1


def _battery_direction(power: float) -> str:
    if power > 1:
        return " (Discharging)"
    elif power < -1:
        return " (Charging)"
    else:
        return " (Idle)"
def _safe_div(a, b):
    return (a / b) if b else 0.0

def _pv_strings_section(get):
    rows = []
    active = 0
    total = 0.0
    spec = [
        ('PV1', 0x02A4, 0x02A5, 0x02A0),
        ('PV2', 0x02A6, 0x02A7, 0x02A1),
        ('PV3', 0x02A8, 0x02A9, 0x02A2),
        ('PV4', 0x02AA, 0x02AB, 0x02A3),
    ]
    for name, v_reg, c_reg, p_reg in spec:
        v = get(v_reg)
        c = get(c_reg)
        pwr = get(p_reg)
        rows.append({'name': name, 'voltage': v, 'current': c, 'power': pwr})
        if pwr > 0:
            active += 1
            total += pwr
    return rows, active, total

def _build_context(values: dict):
    def get(reg: int) -> float:
        return _scaled_value(reg, values.get(reg))

    # System section
    soc = get(0x024C)
    pv_total = get(0x02A0) + get(0x02A1) + get(0x02A2) + get(0x02A3)
    if pv_total > 10:
        status = "GridConnected"
    elif soc > 20:
        status = "Battery"
    else:
        status = "Standby"

    # PV
    pv_rows, active_strings, pv_total_power = _pv_strings_section(get)

    # Inverter
    inv = {
        'l1': {'voltage': get(0x0256), 'current': get(0x0276), 'power': get(0x0279)},
        'l2': {'voltage': get(0x0257), 'current': get(0x0277), 'power': get(0x027A)},
        'l3': {'voltage': get(0x0258), 'current': get(0x0278), 'power': get(0x027B)},
    }
    inverter_total = inv['l1']['power'] + inv['l2']['power'] + inv['l3']['power']

    # Grid (external CT)
    grid_l = [
        {'v': get(0x0256), 'p': get(0x0268)},
        {'v': get(0x0257), 'p': get(0x0269)},
        {'v': get(0x0258), 'p': get(0x026A)},
    ]
    grid = {
        'l1': {'voltage': grid_l[0]['v'], 'current': _safe_div(grid_l[0]['p'], grid_l[0]['v']), 'power': grid_l[0]['p']},
        'l2': {'voltage': grid_l[1]['v'], 'current': _safe_div(grid_l[1]['p'], grid_l[1]['v']), 'power': grid_l[1]['p']},
        'l3': {'voltage': grid_l[2]['v'], 'current': _safe_div(grid_l[2]['p'], grid_l[2]['v']), 'power': grid_l[2]['p']},
    }
    grid_total = get(0x0271)
    grid_dir = "Importing" if grid_total > 0 else "Exporting" if grid_total < 0 else "Balanced"

    # Load
    load = {
        'l1': {'voltage': get(0x0284), 'power': get(0x028A)},
        'l2': {'voltage': get(0x0285), 'power': get(0x028B)},
        'l3': {'voltage': get(0x0286), 'power': get(0x028C)},
    }
    for phase in ('l1','l2','l3'):
        v = load[phase]['voltage']
        p = load[phase]['power']
        load[phase]['current'] = _safe_div(p, v) if v else 0.0
    load_total = get(0x028D)

    # Battery
    battery1 = {
        'voltage': get(0x024B),
        'current': get(0x024F),
        'power':   get(0x024E),
        'temperature': get(0x024A),
        'soc': soc,
        'capacity_percent': 100.0,
        'status': 1,
    }
    battery2 = {
        'voltage': 0.0, 'current': 0.0, 'power': 0.0,
        'temperature': 0.0, 'soc': 0.0, 'capacity_percent': 0.0, 'status': 0,
    }

    # Direction strings for batteries
    battery1['direction'] = _battery_direction(battery1['power'])
    battery2['direction'] = _battery_direction(battery2['power'])

    # Daily

    daily = {
        'pv_generation': get(0x0211),
        'load_consumption': get(0x020E),
        'grid_import': get(0x0208),
        'grid_export': get(0x0209),
        'battery_charge': get(0x0202),
        'battery_discharge': get(0x0203),
    }

    # Totals
    totals = {
        'pv_generation': _calc_32bit(values.get(0x0216), values.get(0x0217)),
        'load_consumption': _calc_32bit(values.get(0x020F), values.get(0x0210)),
        'grid_import': _calc_32bit(values.get(0x020A), values.get(0x020B)),
        'grid_export': _calc_32bit(values.get(0x020C), values.get(0x020D)),
        'battery_charge': _calc_32bit(values.get(0x0204), values.get(0x0205)),
        'battery_discharge': _calc_32bit(values.get(0x0206), values.get(0x0207)),
    }

    # ToU table rows
    grid_charge_enable = int(get(130)) != 0
    solar_sell_enable  = int(get(145)) != 0

    tou_rows = []
    slots = [
        {'start': 0x0094, 'end': 0x0095, 'p': 0x009A, 'soc': 166, 'ctrl': 172},
        {'start': 0x0095, 'end': 0x0096, 'p': 0x009B, 'soc': 167, 'ctrl': 173},
        {'start': 0x0096, 'end': 0x0097, 'p': 0x009C, 'soc': 168, 'ctrl': 174},
        {'start': 0x0097, 'end': 0x0098, 'p': 0x009D, 'soc': 169, 'ctrl': 175},
        {'start': 0x0098, 'end': 0x0099, 'p': 0x009E, 'soc': 170, 'ctrl': 176},
        {'start': 0x0099, 'end': 0x0094, 'p': 0x009F, 'soc': 171, 'ctrl': 177},
    ]
    for sl in slots:
        start_t = _minutes_to_time(int(get(sl['start'])))
        end_t   = _minutes_to_time(int(get(sl['end'])))
        power   = int(get(sl['p'])) * 10
        soc_v   = int(get(sl['soc']))
        ctrl    = int(get(sl['ctrl']))
        grid_mark = "✓" if (ctrl & 1) else " "
        gen_mark  = "✓" if (ctrl & 2) else " "
        sell_mark = "✓" if (ctrl & 32) else " "
        tou_rows.append({
            'grid': '✓' if (ctrl & 1) else ' ',
            'gen': '✓' if (ctrl & 2) else ' ',
            'sell': '✓' if (ctrl & 32) else ' ',
            'grid_flag': 1 if (ctrl & 1) else 0,
            'gen_flag': 1 if (ctrl & 2) else 0,
            'sell_flag': 1 if (ctrl & 32) else 0,
            'start': start_t,
            'end': end_t,
            'power': int(power),
            'soc': int(soc_v),
        })

    context = {
        # top-level strings for multi-line pieces used by the template
        'pv_rows': pv_rows,
        'tou_rows': tou_rows,
        'tou': tou_rows,

        # nested dicts mirroring the template keys
        'system': {
            'status': status,
            'dc_temperature': get(0x021C),
            'ac_temperature': get(0x021D),
            'battery_temperature': get(0x024A),
        },
        'pv': {
            'active_strings': active_strings,
            'total_power': pv_total_power,
        },
        'inverter': {
            'total_power': inverter_total,
            'l1': inv['l1'],
            'l2': inv['l2'],
            'l3': inv['l3'],
        },
        'grid': {
            'total_power': grid_total,
            'importing_flag': 1 if grid_total >= 0 else 0,
            'direction': grid_dir,
            'l1': grid['l1'],
            'l2': grid['l2'],
            'l3': grid['l3'],
        },
        'load': {
            'total_power': load_total,
            'l1': load['l1'],
            'l2': load['l2'],
            'l3': load['l3'],
        },
        'battery': {
            'battery1': battery1,
            'battery2': battery2,
        },
        'daily_energy': daily,
        'total_energy': totals,
        'grid_charge_enable': "Yes" if grid_charge_enable else "No",
        'solar_sell_enable': "Yes" if solar_sell_enable else "No",
        'grid_charge_enable_num': 1 if grid_charge_enable else 0,
        'solar_sell_enable_num': 1 if solar_sell_enable else 0,
        'time_of_use': {
            'grid_charge_enable': bool(grid_charge_enable),
            'solar_sell_enable': bool(solar_sell_enable),
            'rows': tou_rows,
        },
    }
    return context

class SafeDict(dict):
    """dict subclass that returns {key} literally when missing (for robust format_map)."""
    def __missing__(self, key):
        return '{' + key + '}'

def render_with_template(template_path: str, context: dict) -> str:
    class DeepSafe(dict):
        """Nested-safe dict for str.format_map: missing keys render literally like {key}."""
        def __missing__(self, key):
            return '{' + key + '}'
        def __getitem__(self, key):
            val = dict.get(self, key)
            if isinstance(val, dict) and not isinstance(val, DeepSafe):
                return DeepSafe(val)
            if isinstance(val, list):
                # Wrap any dicts inside list so {list[0][key]} also safe
                wrapped = []
                for item in val:
                    if isinstance(item, dict) and not isinstance(item, DeepSafe):
                        wrapped.append(DeepSafe(item))
                    else:
                        wrapped.append(item)
                return wrapped
            return val

    with open(template_path, 'r', encoding='utf-8') as f:
        tpl = f.read()
    return tpl.format_map(DeepSafe(context))

def read_deye_values(ip: str, sn: int, verbose: bool = False) -> dict:
    if PySolarmanV5 is None:
        print("ERROR: pysolarmanv5 not installed. Install with: pip install pysolarmanv5", file=sys.stderr)
        sys.exit(1)
    raw = _bulk_read(ip, sn, verbose=verbose)
    return raw
def flatten_context(ctx: dict) -> dict:
    """Return a lightly-flattened dict for JSON (not deeply nested)."""
    flat = {}

    # helpers
    def put(prefix, key, value):
        flat[f"{prefix}_{key}"] = value

    # serial
    if 'serial' in ctx:
        flat['serial'] = ctx['serial']

    # system
    sys = ctx.get('system', {})
    for k in ('status', 'dc_temperature', 'ac_temperature', 'battery_temperature'):
        if k in sys: put('system', k, sys[k])

    # PV
    pv = ctx.get('pv', {})
    for k in ('active_strings', 'total_power'):
        if k in pv: put('pv', k, pv[k])

    pv_rows = ctx.get('pv_rows', [])
    names = ['pv1','pv2','pv3','pv4']
    for idx, name in enumerate(names):
        if idx < len(pv_rows):
            row = pv_rows[idx] or {}
            for k in ('voltage','current','power'):
                if k in row: put(name, k, row[k])

    # Inverter
    inv = ctx.get('inverter', {})
    if 'total_power' in inv: put('inverter', 'total_power', inv['total_power'])
    for phase in ('l1','l2','l3'):
        p = inv.get(phase, {})
        for k in ('voltage','current','power'):
            if k in p: put(f'inverter_{phase}', k, p[k])

    # Grid
    gr = ctx.get('grid', {})
    for k in ('total_power','importing_flag'):
        if k in gr: put('grid', k, gr[k])
    # optional direction string if exists
    if 'direction' in gr: put('grid', 'direction', gr['direction'])
    for phase in ('l1','l2','l3'):
        p = gr.get(phase, {})
        for k in ('voltage','current','power'):
            if k in p: put(f'grid_{phase}', k, p[k])

    # Load
    ld = ctx.get('load', {})
    if 'total_power' in ld: put('load', 'total_power', ld['total_power'])
    for phase in ('l1','l2','l3'):
        p = ld.get(phase, {})
        for k in ('voltage','current','power','current'):
            if k in p: put(f'load_{phase}', k, p[k])

    # Battery
    bat = ctx.get('battery', {})
    for bid in ('battery1','battery2'):
        b = bat.get(bid, {})
        short = 'battery1' if bid=='battery1' else 'battery2'
        for k in ('voltage','current','power','temperature','soc','capacity_percent','status','direction'):
            if k in b: put(short, k, b[k])

    # Daily energy (kWh)
    de = ctx.get('daily_energy', {})
    mapping = {
        'pv_generation':'daily_pv_kwh',
        'load_consumption':'daily_load_kwh',
        'grid_import':'daily_grid_import_kwh',
        'grid_export':'daily_grid_export_kwh',
        'battery_charge':'daily_battery_charge_kwh',
        'battery_discharge':'daily_battery_discharge_kwh',
    }
    for src, dst in mapping.items():
        if src in de: flat[dst] = de[src]

    # Totals (kWh)
    te = ctx.get('total_energy', {})
    mapping2 = {
        'pv_generation':'total_pv_kwh',
        'load_consumption':'total_load_kwh',
        'grid_import':'total_grid_import_kwh',
        'grid_export':'total_grid_export_kwh',
        'battery_charge':'total_battery_charge_kwh',
        'battery_discharge':'total_battery_discharge_kwh',
    }
    for src, dst in mapping2.items():
        if src in te: flat[dst] = te[src]

    # Flags
    if 'grid_charge_enable_num' in ctx:
        flat['grid_charge_enable'] = ctx['grid_charge_enable_num']
    if 'solar_sell_enable_num' in ctx:
        flat['solar_sell_enable'] = ctx['solar_sell_enable_num']

    return flat


def main():
    # CLI
    parser = argparse.ArgumentParser(description="Deye monitor with templated output")
    parser.add_argument("--config", default="config.cfg", help="Path to config file (INI)")
    parser.add_argument("--format", default="human", choices=["human", "json", "prometheus"], help="Output format")
    args = parser.parse_args()

    # Paths
    script_dir = Path(__file__).resolve().parent
    cfg_path = (script_dir / args.config) if not Path(args.config).is_absolute() else Path(args.config)
    templates_dir = script_dir / "templates"
    human_template = templates_dir / "human.txt"

    # Read config
    cfg = configparser.ConfigParser()
    if not cfg_path.exists():
        print(f"ERROR: config file not found: {cfg_path}", file=sys.stderr)
        sys.exit(1)
    cfg.read(cfg_path, encoding="utf-8")
    try:
        ip = cfg.get("DeyeInverter", "inverter_ip")
        sn = cfg.getint("DeyeInverter", "inverter_sn")
        verbose = cfg.getboolean("DeyeInverter", "verbose", fallback=False)
    except Exception as e:
        print(f"ERROR: invalid config: {e}", file=sys.stderr)
        sys.exit(1)

    # Fetch values
    values = read_deye_values(ip, sn, verbose=verbose)
    ctx = _build_context(values)

    # Render
    if args.format == "human":
        tpl_path = human_template
        if not tpl_path.exists():
            print(f"ERROR: missing template: {tpl_path}", file=sys.stderr)
            sys.exit(1)
        out = render_with_template(str(tpl_path), ctx)
        print(out)
    elif args.format == "json":
        tpl_path = human_template.parent / "json.txt"
        if not tpl_path.exists():
            print(f"ERROR: missing template: {tpl_path}", file=sys.stderr)
            sys.exit(1)
        out = render_with_template(str(tpl_path), ctx)
        print(out)
    elif args.format == "prometheus":
        ctx["serial"] = str(sn)
        tpl_path = human_template.parent / "prometheus.txt"
        if not tpl_path.exists():
            print(f"ERROR: missing template: {tpl_path}", file=sys.stderr)
            sys.exit(1)
        out = render_with_template(str(tpl_path), ctx)
        print(out)
#        print("# TODO: prometheus exposition not implemented yet", file=sys.stderr)
        sys.exit(0)

if __name__ == "__main__":
    main()
