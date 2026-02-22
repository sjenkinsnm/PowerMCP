import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mcp.server.fastmcp import FastMCP
from common.utils import PowerError, power_mcp_tool
from typing import Dict, List, Optional, Tuple, Any, Union

# Initialize MCP server
mcp = FastMCP("PSSE 35 Steady State Powerflow Tool")

# Import and initialize PSSE Python library
# If PSSE is not in your path, run "C:\Program Files\PTI\PSSE36\36.0\SET_PSSE_PATH.BAT" from your PSSE install directory
import psse36 # change the version if you run another version
import psspy
psspy.psseinit(50) # If you're running PSSE Xplore (free edition), this is 50 buses. But if you have a commercial license you can use 150000 instead


@power_mcp_tool(mcp)
def open_case(case: str) -> Dict[str, Any]:
    """
    Open a PSSE case file.
    
    Args:
        case: Filename with .sav extension.
    
    Returns:
        Dict with status and case information
    """
    try:
        
        ierr = psspy.case(os.getcwd() + "\\" + case)
        
        # Get basic case information
        err, bus_data = psspy.abuscount(flag=2)
        err, branch_data = psspy.abrncount(flag=4)
        err, gen_data = psspy.amachcount(flag=4)
        
        if (err == 0) :
            return {
                'status': 'success',
                'case_info': {
                    'path': os.getcwd() + "\\" + case,
                    'num_buses': bus_data if bus_data is not None else 0,
                    'num_branches': branch_data if branch_data is not None else 0,
                    'num_generators': gen_data if gen_data is not None else 0
                }
            }
        elif (err == 1) :
            return {
                'status': 'error case is blank',
                'case_info': {
                    'result_code': err
                }
            }
        elif (err == 2) :
            return {
                'status': 'error reading case',
                'case_info': {
                    'result_code': err
                }
            }
        elif (err == 3) :
            return {
                'status': 'error opening case file',
                'case_info': {
                    'result_code': err
                }
            }
        elif (err == 4) :
            return {
                'status': 'error prerequisite for API not met',
                'case_info': {
                    'result_code': err
                }
            }
        else:
            return {
                'status': 'error unknown',
                'case_info': {
                    'result_code': err
                }
            }
    except Exception as e:
        return PowerError(
            status='error',
            message=str(e)
        )

@power_mcp_tool(mcp)
def solve_case() -> Dict[str, Any]:
    """
    Solves a powerflow case using PSSE.
    
    Returns:
        Dict with status and case information
    """
    try:
        
        err = psspy.nsol()
        if (err == 0) :
            return {
                'status': 'success',
                'case_info': {
                    'result_code': err
                }
            }
        elif (err == 1) :
            return {
                'status': 'error invalid OPTIONS value',
                'case_info': {
                    'result_code': err
                }
            }
        elif (err == 2) :
            return {
                'status': 'success with generators converted',
                'case_info': {
                    'result_code': err
                }
            }
        elif (err == 3) :
            return {
                'status': 'error buses in island(s) without a swing bus',
                'case_info': {
                    'result_code': err
                }
            }
        elif (err == 4) :
            return {
                'status': 'error bus type code and series element status inconsistencies',
                'case_info': {
                    'result_code': err
                }
            }
        elif (err == 5) :
            return {
                'status': 'error prerequisitie conditions for API are not met',
                'case_info': {
                    'result_code': err
                }
            }
        else :
            return {
                'status': 'error unknown',
                'case_info': {
                    'result_code': err
                }
            }
    except Exception as e:
        return PowerError(
            status='error',
            message=str(e)
        )



if __name__ == "__main__":
    mcp.run(transport="stdio")