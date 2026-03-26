import andes
import logging
import os
import io
import sys
import shutil
import json
from pathlib import Path
from contextlib import redirect_stdout, redirect_stderr
from mcp.server.fastmcp import FastMCP
from typing import Dict, Any

# Set up storage directory (relative to this script)
STORE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".andes_runs")
os.makedirs(STORE_DIR, exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(STORE_DIR, 'mcp_server.log')),
        logging.StreamHandler()
    ]
)

# Configure ANDES logging
andes.config_logger(stream_level=50)  # 50 is CRITICAL level
logging.getLogger('andes').setLevel(logging.WARNING)
logging.getLogger('numpy').setLevel(logging.WARNING)
logging.getLogger('scipy').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# Initialize MCP server
mcp = FastMCP("ANDES MCP Server")

# Initialize system state
system_state: Dict[str, Any] = {}

@mcp.tool()
def run_power_flow(file_path: str) -> Dict[str, Any]:
    """Run power flow analysis on a power system case
    
    Args:
        file_path: Path to the case file
    
    Returns:
        Dict containing power flow results and output information
    """
    try:
        # Convert to absolute path if not already
        abs_file_path = os.path.abspath(file_path)
        if not os.path.exists(abs_file_path):
            return {
                "status": "error",
                "message": f"Input file not found: {abs_file_path}"
            }

        # Create a unique directory for this run
        run_dir = os.path.join(STORE_DIR, f"pf_{Path(abs_file_path).stem}")
        os.makedirs(run_dir, exist_ok=True)
        
        # Copy input file to run directory
        input_file = os.path.join(run_dir, os.path.basename(abs_file_path))
        shutil.copy2(abs_file_path, input_file)
        
        # Save current directory and change to run directory
        original_dir = os.getcwd()
        os.chdir(run_dir)
        
        try:
            # Capture stdout/stderr
            f_out = io.StringIO()
            f_err = io.StringIO()
            
            with redirect_stdout(f_out), redirect_stderr(f_err):
                # Run power flow with minimal output
                ss = andes.run(input_file, no_output=True, verbose=50)
                
                # Store system state for other tools
                system_state['current_system'] = ss
                
                # Extract key power flow results
                pflow_results = {
                    "converged": ss.PFlow.converged,
                    "iterations": ss.PFlow.niter if hasattr(ss.PFlow, 'niter') else 0,
                    "max_mis": float(ss.PFlow.mis[-1]) if hasattr(ss.PFlow, 'mis') and len(ss.PFlow.mis) > 0 else 0.0,
                    "time": float(ss.PFlow.t) if hasattr(ss.PFlow, 't') else 0.0
                }
                
                # Get list of output files
                output_files = [f for f in os.listdir(run_dir) if os.path.isfile(os.path.join(run_dir, f))]
                
                result = {
                    "status": "success",
                    "message": "Power flow completed successfully" if ss.PFlow.converged else "Power flow did not converge",
                    "power_flow": pflow_results,
                    "output_dir": run_dir,
                    "output_files": output_files,
                    "stdout": f_out.getvalue(),
                    "stderr": f_err.getvalue()
                }
                
                return result
                
        finally:
            # Always change back to original directory
            os.chdir(original_dir)
            
    except Exception as e:
        logger.error(f"Error in power flow analysis: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }

@mcp.tool()
def run_time_domain_simulation(step_size: float = 0.01, t_end: float = 10.0) -> Dict[str, Any]:
    """Run time domain simulation on the currently loaded power system
    
    Args:
        step_size: Time step size in seconds
        t_end: End time in seconds
    
    Returns:
        Dict containing simulation results and output information
    """
    try:
        if 'current_system' not in system_state:
            return {
                "status": "error",
                "message": "No power system currently loaded. Run power flow first."
            }
            
        ss = system_state['current_system']
        
        # Create a unique directory for this run
        run_dir = os.path.join(STORE_DIR, f"tds_{int(t_end)}s")
        os.makedirs(run_dir, exist_ok=True)
        
        # Save current directory and change to run directory
        original_dir = os.getcwd()
        os.chdir(run_dir)
        
        try:
            # Capture stdout/stderr
            f_out = io.StringIO()
            f_err = io.StringIO()
            
            with redirect_stdout(f_out), redirect_stderr(f_err):
                # Configure time domain simulation parameters
                ss.TDS.config.tf = t_end
                ss.TDS.config.tstep = step_size
                
                # Run time domain simulation
                ss.TDS.init()
                success = ss.TDS.run()
                
                # Extract key simulation results
                tds_results = {
                    "t_array": ss.dae.t.tolist() if hasattr(ss.dae, 't') else [],
                    "step_size": float(ss.TDS.config.tstep),
                    "t_end": float(ss.TDS.config.tf),
                    "success": success,
                    "status": "completed" if success else "failed"
                }
                
                # Get list of output files
                output_files = [f for f in os.listdir(run_dir) if os.path.isfile(os.path.join(run_dir, f))]
                
                result = {
                    "status": "success",
                    "message": "Time domain simulation completed successfully" if success else "Time domain simulation failed",
                    "simulation": tds_results,
                    "output_dir": run_dir,
                    "output_files": output_files,
                    "stdout": f_out.getvalue(),
                    "stderr": f_err.getvalue()
                }
                
                return result
                
        finally:
            # Always change back to original directory
            os.chdir(original_dir)
            
    except Exception as e:
        logger.error(f"Error in time domain simulation: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }

@mcp.tool()
def run_eigenvalue_analysis(file_path: str) -> Dict[str, Any]:
    """Run eigenvalue analysis on a power system case
    
    Args:
        file_path: Path to the case file
    
    Returns:
        Dict containing the eigenvalue analysis results
    """
    try:
        # Convert to absolute path if relative
        abs_file_path = os.path.abspath(file_path)
        
        if not os.path.exists(abs_file_path):
            return {
                "status": "error",
                "message": f"File not found: {file_path}"
            }
            
        # Create a unique directory for this run
        run_dir = os.path.join(STORE_DIR, f"eig_{Path(abs_file_path).stem}")
        os.makedirs(run_dir, exist_ok=True)
        
        # Save current directory and change to run directory
        original_dir = os.getcwd()
        os.chdir(run_dir)
        
        try:
            # Capture stdout/stderr
            f_out = io.StringIO()
            f_err = io.StringIO()
            
            with redirect_stdout(f_out), redirect_stderr(f_err):
                # Load the system
                ss = andes.run(abs_file_path, no_output=True)
                system_state['current_system'] = ss
                
                # Run eigenvalue analysis
                success = ss.EIG.run()
                
                # Extract eigenvalue results
                eig_results = {
                    "n_eigenvalues": len(ss.EIG.mu) if hasattr(ss.EIG, 'mu') else 0,
                    "eigenvalues": ss.EIG.mu.tolist() if hasattr(ss.EIG, 'mu') else [],
                    "eigenvectors": ss.EIG.vectors.tolist() if hasattr(ss.EIG, 'vectors') else [],
                    "participation_factors": ss.EIG.pfactors.tolist() if hasattr(ss.EIG, 'pfactors') else [],
                    "state_variables": ss.EIG.state_desc if hasattr(ss.EIG, 'state_desc') else [],
                    "success": success
                }
                
                # Get list of output files
                output_files = [f for f in os.listdir(run_dir) if os.path.isfile(os.path.join(run_dir, f))]
                
                result = {
                    "status": "success",
                    "message": "Eigenvalue analysis completed successfully" if success else "Eigenvalue analysis failed",
                    "analysis": eig_results,
                    "output_dir": run_dir,
                    "output_files": output_files,
                    "stdout": f_out.getvalue(),
                    "stderr": f_err.getvalue()
                }
                
                return result
                
        finally:
            # Always change back to original directory
            os.chdir(original_dir)
            
    except Exception as e:
        logger.error(f"Error in eigenvalue analysis: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }

@mcp.tool()
def get_system_info() -> Dict[str, Any]:
    """
    Get information about the currently loaded power system
    
    Returns:
        Dict containing system information
    """
    if 'current_system' not in system_state:
        return {
            "status": "error",
            "message": "No power system currently loaded"
        }
    
    try:
        # Capture stdout/stderr
        f_out = io.StringIO()
        f_err = io.StringIO()
        
        with redirect_stdout(f_out), redirect_stderr(f_err):
            ss = system_state['current_system']
            info = {
                "status": "success",
                "num_buses": len(ss.Bus.idx.v) if hasattr(ss.Bus, 'idx') else 0,
                "num_generators": (len(ss.PV.idx.v) if hasattr(ss.PV, 'idx') else 0) + 
                                (len(ss.GENROU.idx.v) if hasattr(ss.GENROU, 'idx') else 0),
                "system_name": ss.name if hasattr(ss, 'name') else "Unknown",
                "base_mva": float(ss.config.mva) if hasattr(ss.config, 'mva') else 100.0,
                "stdout": f_out.getvalue(),
                "stderr": f_err.getvalue()
            }
        
        return info
    except Exception as e:
        logger.error(f"Error getting system info: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }


if __name__ == "__main__":
    print(f"Starting ANDES MCP Server")
    print(f"Using storage directory: {STORE_DIR}")
    mcp.run(transport="stdio") 