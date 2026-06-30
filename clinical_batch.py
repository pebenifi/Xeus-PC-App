"""Clinical (Screen02): batched Modbus read — one connection, all registers, no sleep."""
from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from modbus_client import ModbusClient


def _mm():
    import modbus_manager as mm
    return mm


def _build_seop_parameters(client: ModbusClient) -> dict:
    mm = _mm()
    regs = {
        "laser_max_temp": mm._read_input_regs(client, 3011),
        "laser_min_temp": mm._read_input_regs(client, 3021),
        "cell_max_temp": mm._read_input_regs(client, 3031),
        "cell_min_temp": mm._read_input_regs(client, 3041),
        "ramp_temp": mm._read_input_regs(client, 3051),
        "seop_temp": mm._read_input_regs(client, 3061),
        "cell_refill_temp": mm._read_input_regs(client, 3071),
        "loop_time": mm._read_input_regs(client, 3081),
        "process_duration": mm._read_input_regs(client, 3091),
        "laser_max_output_power": mm._read_input_regs(client, 3101),
        "laser_psu_max_current": mm._read_input_regs(client, 3111),
        "water_chiller_max_temp": mm._read_input_regs(client, 3121),
        "water_chiller_min_temp": mm._read_input_regs(client, 3131),
        "xe_concentration": mm._read_input_regs(client, 3141),
        "water_proton_concentration": mm._read_input_regs(client, 3151),
        "cell_number": mm._read_input_regs(client, 3171),
        "refill_cycle": mm._read_input_regs(client, 3181),
    }
    result: dict[str, Any] = {}
    if regs["laser_max_temp"]:
        v = mm._seop_register_to_scaled(regs["laser_max_temp"][0], mm._SEOP_TEMP_SCALE)
        if v is not None:
            result["laser_max_temp"] = v
    if regs["laser_min_temp"]:
        v = mm._seop_register_to_scaled(regs["laser_min_temp"][0], mm._SEOP_TEMP_SCALE)
        if v is not None:
            result["laser_min_temp"] = v
    if regs["cell_max_temp"]:
        v = mm._seop_register_to_scaled(regs["cell_max_temp"][0], mm._SEOP_TEMP_SCALE)
        if v is not None:
            result["cell_max_temp"] = v
    if regs["cell_min_temp"]:
        v = mm._seop_register_to_scaled(regs["cell_min_temp"][0], mm._SEOP_TEMP_SCALE)
        if v is not None:
            result["cell_min_temp"] = v
    if regs["ramp_temp"]:
        v = mm._seop_register_to_scaled(regs["ramp_temp"][0], mm._SEOP_TEMP_SCALE)
        if v is not None:
            result["ramp_temp"] = v
    if regs["seop_temp"]:
        v = mm._seop_register_to_scaled(regs["seop_temp"][0], mm._SEOP_TEMP_SCALE)
        if v is not None:
            result["seop_temp"] = v
    if regs["cell_refill_temp"]:
        v = mm._seop_register_to_scaled(regs["cell_refill_temp"][0], mm._SEOP_TEMP_SCALE)
        if v is not None:
            result["cell_refill_temp"] = v
    if regs["loop_time"]:
        result["loop_time"] = float(int(regs["loop_time"][0]))
    if regs["process_duration"]:
        result["process_duration"] = float(int(regs["process_duration"][0]))
    if regs["laser_max_output_power"]:
        v = mm._seop_register_to_scaled(regs["laser_max_output_power"][0], mm._SEOP_POWER_SCALE)
        if v is not None:
            result["laser_max_output_power"] = v
    if regs["laser_psu_max_current"]:
        v = mm._seop_register_to_scaled(regs["laser_psu_max_current"][0], mm._SEOP_CURRENT_SCALE)
        if v is not None:
            result["laser_psu_max_current"] = v
    if regs["water_chiller_max_temp"]:
        v = mm._seop_register_to_scaled(regs["water_chiller_max_temp"][0], mm._SEOP_TEMP_SCALE)
        if v is not None:
            result["water_chiller_max_temp"] = v
    if regs["water_chiller_min_temp"]:
        v = mm._seop_register_to_scaled(regs["water_chiller_min_temp"][0], mm._SEOP_TEMP_SCALE)
        if v is not None:
            result["water_chiller_min_temp"] = v
    if regs["xe_concentration"]:
        v = mm._seop_register_to_scaled(regs["xe_concentration"][0], mm._SEOP_XE_CONCENTRATION_SCALE)
        if v is not None:
            result["xe_concentration"] = v
    if regs["water_proton_concentration"]:
        v = mm._seop_register_to_scaled(regs["water_proton_concentration"][0], mm._SEOP_WATER_PROTON_SCALE)
        if v is not None:
            result["water_proton_concentration"] = v
    if regs["cell_number"]:
        result["cell_number"] = int(regs["cell_number"][0])
    if regs["refill_cycle"]:
        result["refill_cycle"] = int(regs["refill_cycle"][0])
    return result


def _build_calculated_parameters(client: ModbusClient) -> dict:
    mm = _mm()
    addrs = (4011, 4021, 4031, 4041, 4051, 4061, 4071, 4081, 4091, 4101)
    keys = (
        "electron_polarization", "xe_polarization", "buildup_rate",
        "electron_polarization_error", "xe_polarization_error", "buildup_rate_error",
        "fitted_xe_polarization_max", "fitted_xe_polarization_max_error",
        "hp_xe_t1", "hp_xe_t1_error",
    )
    result: dict[str, Any] = {}
    for addr, key in zip(addrs, keys):
        r = mm._read_input_regs(client, addr)
        if r:
            result[key] = float(int(r[0])) / 100.0
    return result


def _build_measured_parameters(client: ModbusClient) -> dict:
    mm = _mm()
    result: dict[str, Any] = {}
    current_ir = mm._read_measured_ir_uint32(client, 5011)
    if current_ir is not None:
        result["current_ir_signal"] = current_ir
    cold_ir = mm._read_measured_ir_uint32(client, 5021)
    if cold_ir is not None:
        result["cold_cell_ir_signal"] = cold_ir
    hot_ir = mm._read_measured_ir_uint32(client, 5031)
    if hot_ir is not None:
        result["hot_cell_ir_signal"] = hot_ir
    water_1h = mm._read_input_regs(client, 5041)
    if water_1h:
        v = mm._seop_register_to_scaled(water_1h[0], mm._MEASURED_WATER_1H_NMR_SCALE)
        if v is not None:
            result["water_1h_nmr_reference_signal"] = v
    water_t2 = mm._read_input_regs(client, 5051)
    if water_t2:
        v = mm._seop_register_to_scaled(water_t2[0], mm._MEASURED_T2_MS_SCALE)
        if v is not None:
            result["water_t2"] = v
    hp_nmr = mm._read_measured_ir_uint32(client, 5061)
    if hp_nmr is not None:
        result["hp_129xe_nmr_signal"] = hp_nmr
    hp_t2 = mm._read_input_regs(client, 5071)
    if hp_t2:
        v = mm._seop_register_to_scaled(hp_t2[0], mm._MEASURED_T2_MS_SCALE)
        if v is not None:
            result["hp_129xe_t2"] = v
    t2_corr = mm._read_measured_scalar_register(client, 5081)
    if t2_corr is not None:
        result["t2_correction_factor"] = t2_corr
    return result


def _build_additional_parameters(client: ModbusClient) -> dict:
    mm = _mm()
    specs = (
        (6011, "magnet_psu_current_proton_nmr", mm._ADDITIONAL_MAGNET_CURRENT_SCALE),
        (6021, "magnet_psu_current_129xe_nmr", mm._ADDITIONAL_MAGNET_CURRENT_SCALE),
        (6031, "operational_laser_psu_current", mm._ADDITIONAL_LASER_CURRENT_SCALE),
        (6041, "rf_pulse_duration", None),
        (6051, "resonance_frequency", mm._ADDITIONAL_SCALE_10),
        (6061, "proton_rf_pulse_power", mm._ADDITIONAL_SCALE_10),
        (6071, "hp_129xe_rf_pulse_power", mm._ADDITIONAL_SCALE_10),
        (6081, "step_size_b0_sweep_hp_129xe", mm._ADDITIONAL_STEP_SCALE),
        (6091, "step_size_b0_sweep_protons", mm._ADDITIONAL_STEP_SCALE),
        (6101, "xe_alicats_pressure", mm._ADDITIONAL_ALICATS_PRESSURE_SCALE),
        (6111, "nitrogen_alicats_pressure", mm._ADDITIONAL_ALICATS_PRESSURE_SCALE),
        (6121, "chiller_temp_setpoint", mm._ADDITIONAL_SCALE_10),
        (6131, "seop_resonance_frequency", mm._ADDITIONAL_NM_SCALE),
        (6141, "seop_resonance_frequency_tolerance", mm._ADDITIONAL_TOLERANCE_SCALE),
        (6151, "ir_spectrometer_number_of_scans", None),
        (6161, "ir_spectrometer_exposure_duration", mm._ADDITIONAL_EXPOSURE_SCALE),
        (6171, "h1_reference_n_scans", None),
        (6181, "h1_current_sweep_n_scans", None),
        (6191, "baseline_correction_min_frequency", mm._ADDITIONAL_SCALE_10),
        (6201, "baseline_correction_max_frequency", mm._ADDITIONAL_SCALE_10),
    )
    result: dict[str, Any] = {}
    for addr, key, scale in specs:
        r = mm._read_input_regs(client, addr)
        if not r:
            continue
        if scale is None:
            result[key] = float(int(r[0]))
        else:
            v = mm._seop_register_to_scaled(r[0], scale)
            if v is not None:
                result[key] = v
    return result


def _build_manual_mode_settings(client: ModbusClient) -> dict:
    mm = _mm()
    result: dict[str, Any] = {}
    rf_freq = mm._read_input_regs(client, 6301)
    if rf_freq:
        v = mm._seop_register_to_scaled(rf_freq[0], mm._MANUAL_MODE_FREQ_SCALE)
        if v is not None:
            result["rf_pulse_frequency"] = v
    rf_pwr = mm._read_input_regs(client, 6311)
    if rf_pwr:
        v = mm._seop_register_to_scaled(rf_pwr[0], mm._MANUAL_MODE_POWER_SCALE)
        if v is not None:
            result["rf_pulse_power"] = v
    for addr, key in ((6321, "rf_pulse_duration"), (6331, "pre_acquisition"),
                      (6351, "nmr_number_of_scans"), (6361, "nmr_recovery")):
        r = mm._read_input_regs(client, addr)
        if r:
            result[key] = float(int(r[0]))
    nmr_gain = mm._read_input_regs(client, 6341)
    if nmr_gain:
        result["nmr_gain"] = float(int(nmr_gain[0]))
    center = mm._read_input_regs(client, 6371)
    if center:
        v = mm._seop_register_to_scaled(center[0], mm._MANUAL_MODE_FREQ_SCALE)
        if v is not None:
            result["center_frequency"] = v
    span = mm._read_input_regs(client, 6381)
    if span:
        v = mm._seop_register_to_scaled(span[0], mm._MANUAL_MODE_FREQ_SCALE)
        if v is not None:
            result["frequency_span"] = v
    return result


def clinical_batch_read(client: ModbusClient) -> dict:
    """Screen02: Screen01 IO + SEOP/Calculated/Measured/Additional/Manual в одном проходе."""
    mm = _mm()
    result = mm._screen01_batch_read(client)
    ok = int(result.get("_ok", 0))

    for key, builder in (
        ("seop_parameters", _build_seop_parameters),
        ("calculated_parameters", _build_calculated_parameters),
        ("measured_parameters", _build_measured_parameters),
        ("additional_parameters", _build_additional_parameters),
        ("manual_mode_settings", _build_manual_mode_settings),
    ):
        section = builder(client)
        if section:
            result[key] = section
            ok += 1

    result["_ok"] = ok
    result["_conn"] = client.client is not None and client.client.is_socket_open()
    return result


# Список регистров Clinical для standalone-скана (FC04 input, шаг 10)
CLINICAL_PARAM_REGISTERS = [
    *range(3011, 3191, 10),
    *range(4011, 4111, 10),
    5010, 5011, 5020, 5021, 5030, 5031, 5041, 5051, 5060, 5061, 5071, 5081,
    *range(6011, 6211, 10),
    *range(6301, 6391, 10),
]
