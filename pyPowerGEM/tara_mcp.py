import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mcp.server.fastmcp import FastMCP
from common.utils import PowerError, power_mcp_tool
from typing import Dict, List, Optional, Tuple, Any, Union

# Initialize MCP server
mcp = FastMCP("PowerGEM TARA Steady State Powerflow Tool")

# Import pyPowerGEM TARA Python library
import pyPowerGEM.pyTARA as pt
tara = pt.taraAPI()

@power_mcp_tool(mcp)
def open_PSSEcase(case: str) -> Dict[str, Any]:
    """
    Open a PSSE35 format case file.
    
    Args:
        case: Filename with .raw extension.
    
    Returns:
        Dict with status and case information
    """
    try:
        
        ierr = tara.loadRawCase(caseFilePath=(os.getcwd() + "\\" + case), rawVer=35)
        return {
            'status': 'success',
            'case_info': {
                'path': os.getcwd() + "\\" + case
            }
        }
        
    except Exception as e:
        return PowerError(
            status='error',
            message=str(e)
        )



if __name__ == "__main__":
    mcp.run(transport="stdio")