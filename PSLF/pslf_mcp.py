import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mcp.server.fastmcp import FastMCP
from common.utils import PowerError, power_mcp_tool
from typing import Dict, List, Optional, Tuple, Any, Union

# Initialize MCP server
mcp = FastMCP("PSLF Positive Sequence Load Flow Program")

from PSLF_PYTHON import *
init_pslf(silent=False)

@power_mcp_tool(mcp)
def open_case(case: str) -> Dict[str, Any]:
    """
    Open a PSLF case file.
    
    Args:
        case: Filename with .sav extension.
    
    Returns:
        Dict with status and case information
    """
    try:
        
        iret = Pslf.load_case(os.getcwd() + "\\" + case)
        cp = CaseParameters()
        
        # Get basic case information
        bus_data = cp.Nbus
        branch_data = cp.Nbrsec
        gen_data = cp.Ngen
        
        if (iret == 0):
            return {
                'status': 'success',
                'case_info': {
                    'path': os.getcwd() + "\\" + case,
                    'num_buses': bus_data if bus_data is not None else 0,
                    'num_branches': branch_data if branch_data is not None else 0,
                    'num_generators': gen_data if gen_data is not None else 0
                }
            }
        else:
            return {
                'status': 'error unknown'
            }
    except Exception as e:
        return PowerError(
            status='error unknown',
            message=str(e)
        )

@power_mcp_tool(mcp)
def solve_case() -> Dict[str, Any]:
    """
    Solves a powerflow case using PSLF.
    
    Returns:
        Dict with status
    """
    try:
        
        iret = Pslf.solve_case()
        if (iret == 0):
            return {
                'status': 'success',
                'case_info': {
                    'result_code': iret
                }
            }
        elif (iret == -1):
            return {
                'status': 'error case diverged',
                'case_info': {
                    'result_code': iret
                }
            }
        elif (iret == -2):
            return {
                'status': 'error exceeded maximum iterations',
                'case_info': {
                    'result_code': iret
                }
            }
        elif (iret < -2):
            return {
                'status': 'error no swing bus or HVDC error',
                'case_info': {
                    'result_code': iret
                }
            }
        else:
            return {
                'status': 'error unknown',
                'case_info': {
                    'result_code': iret
                }
            }
    except Exception as e:
        return PowerError(
            status='error unknown',
            message=str(e)
        )

@power_mcp_tool(mcp)
def add_bus(busnum: int, busname: str, nominalkv: float, type: int) -> Dict[str, Any]:
    """
    Add a new bus to the power system model
    
    Args:
        busnum: A unique identifying integer used as the primary key in the bus database. Is not necessarily consecutive and could be larger than the number of buses in the case.
        busname: A human readable name of the bus no longer than 12 characters in length.
        nominalkv: The nominal voltage of the bus in kilovolts.
        type: An integer flag where 0 = system slack bus, 1 = a load bus, and 2 = a generator bus. (default 1)
    
    Returns:
        Dict with status
    """
    try:
        
        iret = Pslf.add_record(1, 0, busnum, 'type basekv busnam', str(type) + " " + str(nominalkv) + " " + busname)
        cp = CaseParameters()
        
        # Get basic case information
        bus_data = cp.Nbus
        branch_data = cp.Nbrsec
        gen_data = cp.Ngen
        
        if (iret == 0):
            return {
                'status': 'success',
                'case_info': {
                    'num_buses': bus_data if bus_data is not None else 0,
                    'num_branches': branch_data if branch_data is not None else 0,
                    'num_generators': gen_data if gen_data is not None else 0
                }
            }
        elif (iret == 1):
            return {
                'status': 'error insufficient input',
                'case_info': {
                    'num_buses': bus_data if bus_data is not None else 0,
                    'num_branches': branch_data if branch_data is not None else 0,
                    'num_generators': gen_data if gen_data is not None else 0
                }
            }
        elif (iret == 2):
            return {
                'status': 'error bus number not found when using combination of bus name and voltage',
                'case_info': {
                    'num_buses': bus_data if bus_data is not None else 0,
                    'num_branches': branch_data if branch_data is not None else 0,
                    'num_generators': gen_data if gen_data is not None else 0
                }
            }
        elif (iret == 3):
            return {
                'status': 'error bus number must be positive',
                'case_info': {
                    'num_buses': bus_data if bus_data is not None else 0,
                    'num_branches': branch_data if branch_data is not None else 0,
                    'num_generators': gen_data if gen_data is not None else 0
                }
            }
        elif (iret == -2):
            return {
                'status': 'error bus voltage must be positive',
                'case_info': {
                    'num_buses': bus_data if bus_data is not None else 0,
                    'num_branches': branch_data if branch_data is not None else 0,
                    'num_generators': gen_data if gen_data is not None else 0
                }
            }
        else:
            return {
                'status': 'error bus type is out of range',
                'case_info': {
                    'num_buses': bus_data if bus_data is not None else 0,
                    'num_branches': branch_data if branch_data is not None else 0,
                    'num_generators': gen_data if gen_data is not None else 0
                }
            }
    except Exception as e:
        return PowerError(
            status='error unknown',
            message=str(e)
        )

@power_mcp_tool(mcp)
def add_transmission_line(frombus: int, tobus: int, circuit: int, resistance: float, reactance: float, susceptance: float, rating: float) -> Dict[str, Any]:
    """
    Add a new transmission line to the power system model
    
    Args:
        frombus: Integer identifier of the transmission lines starting terminal Is not necessarily consecutive and could be larger than the number of buses in the case.
        tobus: Integer identifier of the transmission lines ending terminal Is not necessarily consecutive and could be larger than the number of buses in the case.
        circuit: Integer identifer uniquely identifying the circuit in the case there are multiple circuits. (default 1)
        resistance: A float representing the real component of impedance of the transmission line in per unit. (default 0.0)
        reactance: A float representing the imaginary component of impedance of the transmission line in per unit.
        susceptance: A float representing the per unit susceptance of the transmission line. (default 0.0)
        rating: The maximum safe rating of the transmission line in MVA (default 9999.0)
    
    Returns:
        Dict with status
    """
    try:
        
        iret = Pslf.add_record(1, 1, str(frombus) + " " + str(tobus) + " " + str(circuit) + " 1", "st zsecr zsecx bsec rate[0]", "1 " + str(resistance) + " " + str(reactance) + " " + str(susceptance) + " " + str(rating))
        
        cp = CaseParameters()
        
        # Get basic case information
        bus_data = cp.Nbus
        branch_data = cp.Nbrsec
        gen_data = cp.Ngen
        
        if (iret == 0):
            return {
                'status': 'success',
                'case_info': {
                    'num_buses': bus_data if bus_data is not None else 0,
                    'num_branches': branch_data if branch_data is not None else 0,
                    'num_generators': gen_data if gen_data is not None else 0
                }
            }
        elif (iret == 1):
            return {
                'status': 'error insufficient input',
                'case_info': {
                    'num_buses': bus_data if bus_data is not None else 0,
                    'num_branches': branch_data if branch_data is not None else 0,
                    'num_generators': gen_data if gen_data is not None else 0
                }
            }
        elif (iret == 2):
            return {
                'status': 'error branch bus out of range',
                'case_info': {
                    'num_buses': bus_data if bus_data is not None else 0,
                    'num_branches': branch_data if branch_data is not None else 0,
                    'num_generators': gen_data if gen_data is not None else 0
                }
            }
        elif (iret == 3):
            return {
                'status': 'error branch bus does not exist',
                'case_info': {
                    'num_buses': bus_data if bus_data is not None else 0,
                    'num_branches': branch_data if branch_data is not None else 0,
                    'num_generators': gen_data if gen_data is not None else 0
                }
            }
        elif (iret == 4):
            return {
                'status': 'error branch from and to bus are identical',
                'case_info': {
                    'num_buses': bus_data if bus_data is not None else 0,
                    'num_branches': branch_data if branch_data is not None else 0,
                    'num_generators': gen_data if gen_data is not None else 0
                }
            }
        else:
            return {
                'status': 'error unknown',
                'case_info': {
                    'num_buses': bus_data if bus_data is not None else 0,
                    'num_branches': branch_data if branch_data is not None else 0,
                    'num_generators': gen_data if gen_data is not None else 0
                }
            }
    except Exception as e:
        return PowerError(
            status='error unknown',
            message=str(e)
        )

@power_mcp_tool(mcp)
def get_voltage(bus: int) -> Dict[str, Any]:
    """
    Queries the voltage of a bus and reports in per unit
    
    Args:
        bus: Integer identifier of the desired bus to query voltage for.  Is not necessarily consecutive and could be larger than the number of buses in the case.
    
    Returns:
        Dict with status
    """
    try:
        
        index = Pslf.bus_internal_index(bus)
        
        if (index < 0):
            return {
                'status': 'error bus not found'
            }
        else:
            return {
                'status': 'success',
                'case_info': {
                    'bus_id': str(bus),
                    'bus_name': str(Bus[index].Busnam),
                    'base_kv': str(Bus[index].Basekv),
                    'voltage_perunit_kv': str(Bus[index].Vm),
                    'voltage_kv': str(Bus[index].Vm * Bus[index].Basekv),
                    'voltage_angle_degrees': str(Bus[index].Va)
                }
            }
    except Exception as e:
        return PowerError(
            status='error unknown',
            message=str(e)
        )

if __name__ == "__main__":
    mcp.run(transport="stdio")