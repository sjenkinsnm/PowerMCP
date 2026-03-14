# -*- coding: utf-8 -*-
"""
LTSpice MCP Server
==================

This script provides a set of tools accessible via the Model-Context Protocol (MCP)
to automate LTSpice simulations. It allows an AI assistant to create netlists,
run simulations, and plot results programmatically.

This server is built using `fastmcp` and is intended to be run from within
an AI-powered editor like Cursor.

Features:
- Dynamically generate SPICE netlists from text descriptions.
- Create and manage unique, timestamped simulation sessions.
- Run LTSpice simulations in headless batch mode.
- Open netlists in the LTSpice GUI for visual inspection.
- List all available signals (traces) from a simulation's raw output.
- Plot specified voltage and current traces using matplotlib.
- Read simulation log files for debugging.

Author: Maanas Goel
Date: 2025-07-10
"""

# --- Core Imports ---
import os
import sys
import datetime
import logging
import shutil
import subprocess
from pathlib import Path

# --- Third-Party Imports ---
# `fastmcp` is for creating the MCP server.
try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    sys.exit("Error: mcp library not found. Please run 'pip install mcp'.")

# `matplotlib` is used for plotting simulation results.
try:
    import matplotlib.pyplot as plt
except ImportError:
    sys.exit("Error: Matplotlib library not found. Please run 'pip install matplotlib'.")

# `PyLTSpice` provides the tools to read LTSpice's binary .raw files.
try:
    from spicelib.raw.raw_read import RawRead as LTSpiceRawRead
except ImportError:
    sys.exit("Error: PyLTSpice/spicelib not found. Please run 'pip install PyLTSpice'.")


# =============================================================================
#  1. Server & Logging Configuration
# =============================================================================

# Initialize the FastMCP server instance. This object will manage all our tools.
mcp = FastMCP()

# Configure logging to provide timestamps and clear status messages in the console.
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(funcName)s] - %(message)s'
)

# =============================================================================
#  2. Environment & Path Configuration
# =============================================================================
# --- IMPORTANT: USER CONFIGURATION REQUIRED ---
# The user must set this path to their LTspice executable.
# Default for Windows:
LTSPICE_EXECUTABLE_PATH = r"C:\Program Files\LTC\LTspiceXVII\XVIIx64.exe"
# For macOS/Linux with Wine, it might look like:
# LTSPICE_EXECUTABLE_PATH = "/Users/username/.wine/drive_c/Users/username/AppData/Local/Programs/ADI/LTspice/LTspice.exe"

# On macOS/Linux, Wine is required to run the Windows version of LTSpice.
WINE_COMMAND = "wine"

# Define the base directory for all simulation outputs.
# This script is in the project root, so we can get the directory directly.
project_root = os.path.dirname(os.path.abspath(__file__))
BASE_OUTPUT_DIR = os.path.join(project_root, "simulation_output")

# Ensure the base output directory exists on startup.
os.makedirs(BASE_OUTPUT_DIR, exist_ok=True)


def check_ltspice_executable():
    """
    Checks if the LTspice executable and its wrapper (Wine) are available.
    This provides a clear error message if the environment is not set up correctly.
    """
    if sys.platform != "win32":
        if not shutil.which(WINE_COMMAND):
            return False, f"'{WINE_COMMAND}' command not found. Wine is required to run LTspice on this OS."

    if not os.path.exists(os.path.expanduser(LTSPICE_EXECUTABLE_PATH)):
        return False, f"LTspice executable not found at '{LTSPICE_EXECUTABLE_PATH}'. Please check the path."
    return True, ""


# =============================================================================
#  3. Core MCP Tools
#
#  Each function decorated with `@mcp.tool()` becomes a command the AI can call.
# =============================================================================

@mcp.tool()
async def create_simulation_session(netlist_text: str) -> dict:
    """
    Creates a new session for a simulation, including a timestamped directory
    and the netlist file. This is the primary tool for starting any new simulation.
    It returns the netlist content so the AI can display it for user confirmation.
    """
    try:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        session_dir = os.path.join(BASE_OUTPUT_DIR, timestamp)
        os.makedirs(session_dir, exist_ok=True)

        netlist_path = os.path.join(session_dir, "circuit.net")
        with open(netlist_path, "w") as f:
            f.write(netlist_text)

        session_name = os.path.basename(session_dir)
        logging.info(f"Created simulation session: {session_name}")
        return {
            "status": "success",
            "session_dir": session_dir,
            "session_name": session_name,
            "netlist_path": netlist_path,
            "netlist_content": netlist_text,  # Return content for AI to display
            "message": f"📁 New session '{session_name}' created at: {session_dir}"
        }
    except Exception as e:
        logging.error(f"Failed to create session: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


@mcp.tool()
async def run_simulation(netlist_path: str, session_dir: str) -> dict:
    """
    Runs the LTSpice simulation in batch mode (-b flag) using a .net file.
    The output .raw and .log files are saved in the specified session directory.
    """
    is_valid, message = check_ltspice_executable()
    if not is_valid:
        return {"status": "error", "message": message}

    if not os.path.exists(netlist_path):
        return {"status": "error", "message": f"Netlist file not found at '{netlist_path}'"}

    try:
        netlist_filename = os.path.basename(netlist_path)
        if sys.platform == "win32":
            cmd = [LTSPICE_EXECUTABLE_PATH, "-b", netlist_filename]
        else:
            cmd = [WINE_COMMAND, LTSPICE_EXECUTABLE_PATH, "-b", netlist_filename]

        process = subprocess.run(
            cmd, cwd=session_dir, capture_output=True, text=True, check=False
        )

        log_file_path = os.path.join(session_dir, "circuit.log")
        raw_file_path = os.path.join(session_dir, "circuit.raw")

        if process.returncode != 0 or not os.path.exists(raw_file_path):
            log_content = "Log file not found."
            if os.path.exists(log_file_path):
                with open(log_file_path, 'r') as f:
                    log_content = f.read()
            message = (f"Simulation failed. See details below.\n\n"
                       f"--- Log File ---\n{log_content}\n\n"
                       f"--- Stderr ---\n{process.stderr}")
            logging.error(message)
            return {"status": "error", "message": message}

        session_name = os.path.basename(session_dir)
        message = (f"✅ Simulation successful in session '{session_name}'!\n"
                   f"📍 Full Path: {session_dir}\n"
                   f"📊 Raw Data: {os.path.basename(raw_file_path)}\n"
                   f"📝 Log File: {os.path.basename(log_file_path)}")
        return {
            "status": "success",
            "raw_file_path": raw_file_path,
            "log_file_path": log_file_path,
            "session_dir": session_dir,
            "session_name": session_name,
            "message": message,
        }
    except Exception as e:
        logging.error(f"Exception during simulation: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


@mcp.tool()
async def list_available_traces(raw_file_path: str) -> dict:
    """
    Reads the .raw output file and lists all available signals (traces)
    that can be plotted, such as 'V(node)' or 'I(R1)'.
    """
    if not os.path.exists(raw_file_path):
        return {"status": "error", "message": f"RAW file not found: '{raw_file_path}'"}
    try:
        raw_reader = LTSpiceRawRead(raw_file_path)
        traces = raw_reader.get_trace_names()
        return {"status": "success", "traces": traces}
    except Exception as e:
        logging.error(f"Failed to read traces: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


@mcp.tool()
async def plot_specific_traces(raw_file_path: str, session_dir: str, trace_names: list[str]) -> dict:
    """
    Generates and saves a .png plot of the specified traces from a .raw file.
    """
    if not os.path.exists(raw_file_path):
        return {"status": "error", "message": f"RAW file not found: '{raw_file_path}'"}

    try:
        raw_reader = LTSpiceRawRead(raw_file_path)
        plt.style.use('seaborn-v0_8-whitegrid')
        plt.figure(figsize=(12, 7))
        plt.title("LTSpice Simulation Results")
        plt.xlabel("Time (s)")
        plt.ylabel("Value (V or A)")

        time_trace = raw_reader.get_trace('time')
        x_axis = time_trace.get_wave()

        for trace_name in trace_names:
            trace = raw_reader.get_trace(trace_name)
            if not trace:
                logging.warning(f"Trace '{trace_name}' not found. Skipping.")
                continue
            
            y_axis = trace.get_wave()
            
            if len(x_axis) != len(y_axis):
                logging.warning(f"Length mismatch for '{trace_name}'. Skipping.")
                continue

            # Filter out potential negative time values from LTSpice
            x_filtered, y_filtered = zip(*[(t, v) for t, v in zip(x_axis, y_axis) if t >= 0])
            plt.plot(x_filtered, y_filtered, label=trace_name)

        plt.legend()
        plt.tight_layout()

        # Generate a safe and descriptive filename.
        safe_traces = ''.join(c for c in '_'.join(trace_names) if c.isalnum() or c in ('_', '-'))
        plot_filename = f"plot_{safe_traces}.png"
        plot_path = os.path.join(session_dir, plot_filename)
        
        plt.savefig(plot_path)
        plt.close()

        message = (f"📈 Plot generated for traces: {', '.join(trace_names)}\n"
                   f"💾 Saved as: {plot_filename}\n"
                   f"📍 Location: {plot_path}")
        return {"status": "success", "plot_path": plot_path, "message": message}
    except Exception as e:
        logging.error(f"Failed to plot traces: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}

@mcp.tool()
async def read_simulation_log(log_file_path: str) -> dict:
    """Reads the content of a simulation .log file, useful for debugging."""
    if not os.path.exists(log_file_path):
        return {"status": "error", "message": f"Log file not found: '{log_file_path}'"}
    try:
        with open(log_file_path, 'r') as f:
            log_content = f.read()
        return {"status": "success", "log_content": log_content}
    except Exception as e:
        logging.error(f"Failed to read log file: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


# =============================================================================
#  4. Helper Tools & Deprecated Functions
#
#  These are convenience functions that chain other tools together or are kept
#  for backward compatibility.
# =============================================================================

@mcp.tool()
async def create_rc_transient_netlist(
    resistance: str, capacitance: str, pulse_v_on: str, pulse_width: str, sim_duration: str
) -> dict:
    """
    [Helper Tool] Creates a netlist for a standard RC circuit.
    This is a convenience wrapper around `create_simulation_session`.
    """
    pulse_params = f"PULSE(0 {pulse_v_on} 0 1n 1n {pulse_width} {sim_duration})"
    netlist_content = (
        f"* Simple RC Circuit - Generated by MCP\n"
        f"V1 Vin 0 {pulse_params}\n"
        f"R1 Vin Vout {resistance}\n"
        f"C1 Vout 0 {capacitance}\n"
        f".tran {sim_duration}\n"
        f".end\n"
    )
    # Re-use the main session creation tool
    return await create_simulation_session(netlist_content)


@mcp.tool()
async def view_netlist_in_ltspice(netlist_path: str) -> dict:
    """
    [Helper Tool] Opens the specified .net file in the LTspice GUI.
    """
    is_valid, message = check_ltspice_executable()
    if not is_valid:
        return {"status": "error", "message": message}

    if not os.path.exists(netlist_path):
        return {"status": "error", "message": f"Netlist file not found: '{netlist_path}'"}

    try:
        if sys.platform == "win32":
            cmd = [LTSPICE_EXECUTABLE_PATH, os.path.abspath(netlist_path)]
        else:
            cmd = [WINE_COMMAND, LTSPICE_EXECUTABLE_PATH, os.path.abspath(netlist_path)]
        subprocess.Popen(cmd)
        message = (f"🚀 LTspice launched successfully with {os.path.basename(netlist_path)}.\n"
                   f"💡 Note: The circuit is a text netlist, so no visual schematic will appear.")
        return {"status": "success", "message": message}
    except Exception as e:
        logging.error(f"Failed to open LTspice: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


# NOTE: view_results_in_ltspice tool has been removed due to Wine compatibility issues.
# Users should use the plot_specific_traces tool for visualization instead.


# =============================================================================
#  5. Server Execution
# =============================================================================

if __name__ == "__main__":
    # Perform a self-check on startup to ensure the environment is configured.
    is_valid, message = check_ltspice_executable()
    if not is_valid:
        logging.warning(f"LTSpice executable not found: {message}")
        logging.warning("Simulation tools will return errors, but other tools will still work.")

    # Start the server.
    # The server will announce its tools to the connected MCP client (e.g., Cursor).
    logging.info("LTspice MCP server starting...")
    mcp.run()
