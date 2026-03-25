import sys
import os
from mcp.server.fastmcp import FastMCP
import py_dss_interface
from typing import List, Dict, Union, Optional

# Create global DSS instance
dss = py_dss_interface.DSS()

# Create an MCP server
mcp = FastMCP("PyDSS-MCP")

@mcp.tool()
def compile_and_solve(dss_file: str) -> Dict[str, bool]:
    """
    Compile an OpenDSS file and solve the circuit
    
    Args:
        dss_file: Path to the OpenDSS file (.dss)
    
    Returns:
        Dict indicating success status
    """
    try:
        dss.text(f"compile [{dss_file}]")
        dss.text("solve")
        return {"success": True}
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@mcp.tool()
def get_total_power() -> Dict[str, Union[List[float], str, bool]]:
    """
    Get the total power from the current circuit
    
    Returns:
        Dict containing total power values [P, Q] in kW and kVAr
    """
    try:
        total_power = dss.circuit.total_power
        return {
            "success": True,
            "power": total_power,
            "units": "kW, kVAr"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@mcp.tool()
def set_load_multiplier(load_mult: float) -> Dict[str, Union[float, str]]:
    """
    Set the load multiplier and solve the circuit
    
    Args:
        load_mult: Load multiplier value
    
    Returns:
        Dict indicating success status and the minimum per-unit voltage
    """
    try:
        dss.text(f"set loadmult={load_mult}")
        dss.text("solve")
        min_v = min(dss.circuit.buses_vmag_pu)
        return {"success": True, "min_v_pu": min_v}
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@mcp.tool()
def get_bus_voltages() -> Dict[str, Union[bool, list, str]]:
    """
    Get per-unit voltages for all nodes in the circuit
    
    Returns:
        Dict with node names and their per-unit voltages
    """
    try:
        nodes = dss.circuit.nodes_names
        voltages = dss.circuit.buses_vmag_pu
        return {"success": True, "nodes": nodes, "voltages_pu": voltages}
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@mcp.tool()
def run_daily_energy_meter(meter_name: str = "Feeder", hours: int = 24) -> Dict[str, Union[list, str]]:
    """
    Run a daily simulation and return total energy (kWh) from the specified energy meter for each hour
    
    Args:
        meter_name: Name of the energy meter (default: 'Feeder')
        hours: Number of hours to simulate (default: 24)
    
    Returns:
        Dict with hourly energy values
    """
    try:
        dss.text("set mode=daily")
        dss.text("set stepsize=1h")
        dss.text("set number=1")
        dss.meters.name = meter_name
        energy = []
        for hour in range(hours):
            dss.text(f"set hour={hour}")
            dss.text("solve")
            energy.append(dss.meters.register_values[0])
        return {"success": True, "energy_kwh": energy}
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@mcp.tool()
def get_harmonic_results(load_name: str, harmonic: int) -> Dict[str, Union[float, str]]:
    """
    Get the magnitude and angle of current and voltage for a specific load and harmonic order
    
    Args:
        load_name: Name of the load (e.g., 'load.s48')
        harmonic: Harmonic order (e.g., 3, 5, 7, ...)
    
    Returns:
        Dict with current and voltage magnitude and angle for the specified harmonic
    """
    try:
        dss.circuit.set_active_element(load_name)
        dss.text("set mode=harmonic")
        dss.text(f"set harmonics=[{harmonic}]")
        dss.text("solve")
        dss.circuit.set_active_element(load_name)
        current_mag_ang = dss.cktelement.currents_mag_ang[0]
        voltage_mag_ang = dss.cktelement.voltages_mag_ang[0]
        return {
            "success": True,
            "current_mag_ang": current_mag_ang,
            "voltage_mag_ang": voltage_mag_ang,
            "harmonic": harmonic
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

if __name__ == "__main__":
    mcp.run(transport="stdio") 