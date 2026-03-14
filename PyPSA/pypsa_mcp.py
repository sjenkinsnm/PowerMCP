import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mcp.server.fastmcp import FastMCP
from pypsa import Network
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Union, Any


def _to_serializable(obj: Any) -> Any:
    """Convert numpy/pandas types to JSON-serializable Python types."""
    if hasattr(obj, 'item'):  # numpy scalar
        return obj.item()
    if hasattr(obj, 'tolist'):  # numpy array
        return obj.tolist()
    if isinstance(obj, dict):
        return {k: _to_serializable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_serializable(x) for x in obj]
    if hasattr(obj, 'strftime'):  # datetime-like
        return str(obj)
    if hasattr(obj, '__str__') and not isinstance(obj, (str, int, float, bool, type(None))):
        return str(obj)
    return obj


# Create an MCP server
mcp = FastMCP("PyPSA-MCP")


# ============= Network Information =============

@mcp.tool()
def get_network_info(network_name: str) -> Dict[str, Any]:
    """Get basic information about the network"""
    network = Network(network_name)
    info = {
        "buses": len(network.buses),
        "generators": len(network.generators),
        "loads": len(network.loads),
        "lines": len(network.lines),
        "transformers": len(network.transformers),
        "storage_units": len(network.storage_units),
        "snapshots": len(network.snapshots),
        "components": list(network.all_components)
    }
    return info

@mcp.tool()
def load_network(file_path: str) -> Dict[str, Any]:
    """Load a PyPSA network from a NetCDF (.nc) file"""
    try:
        network = Network(file_path)
        info = {
            "buses": len(network.buses),
            "generators": len(network.generators),
            "loads": len(network.loads),
            "lines": len(network.lines),
            "transformers": len(network.transformers),
            "snapshots": len(network.snapshots),
        }
        return {
            "status": "success",
            "message": f"Network loaded successfully from {file_path}",
            "info": info
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to load network: {str(e)}"
        }

@mcp.tool()
def run_power_flow(network_name: str, linear: bool = False) -> Dict[str, Any]:
    """Run a non-linear (AC) or linear (DC) power flow on the network"""
    try:
        network = Network(network_name)
        
        if linear:
            network.lpf()
        else:
            network.pf()
            
        # Get basic results
        results = {
            "status": "success",
            "message": f"{'Linear' if linear else 'Non-linear'} power flow completed successfully.",
            "buses": {},
            "lines": {}
        }
        
        for bus in network.buses.index:
            bus_data = {}
            if not network.buses_t.v_mag_pu.empty and bus in network.buses_t.v_mag_pu:
                bus_data["v_mag_pu"] = network.buses_t.v_mag_pu[bus].tolist() if len(network.snapshots) > 1 else float(network.buses_t.v_mag_pu[bus].iloc[0])
            if not network.buses_t.v_ang.empty and bus in network.buses_t.v_ang:
                bus_data["v_ang"] = network.buses_t.v_ang[bus].tolist() if len(network.snapshots) > 1 else float(network.buses_t.v_ang[bus].iloc[0])
            results["buses"][bus] = bus_data
            
        for line in network.lines.index:
            line_data = {}
            if not network.lines_t.p0.empty and line in network.lines_t.p0:
                line_data["p0"] = network.lines_t.p0[line].tolist() if len(network.snapshots) > 1 else float(network.lines_t.p0[line].iloc[0])
            if not network.lines_t.q0.empty and line in network.lines_t.q0:
                line_data["q0"] = network.lines_t.q0[line].tolist() if len(network.snapshots) > 1 else float(network.lines_t.q0[line].iloc[0])
            results["lines"][line] = line_data
            
        return _to_serializable(results)
    except Exception as e:
        return {
            "status": "error",
            "message": f"Power flow failed: {str(e)}"
        }

@mcp.tool()
def get_component_details(
    network_name: str,
    component_type: str,
    component_id: Optional[str] = None
) -> Dict[str, Any]:
    """Get detailed information about a specific component or all components of a type"""
    network = Network(network_name)
    
    if not hasattr(network, component_type):
        return {
            "status": "error",
            "message": f"Component type '{component_type}' not found"
        }
    
    component_df = getattr(network, component_type)
    
    if component_id:
        if component_id not in component_df.index:
            return {
                "status": "error",
                "message": f"Component '{component_id}' not found in {component_type}"
            }
        result = component_df.loc[component_id].to_dict()
    else:
        result = component_df.to_dict('index')

    return _to_serializable(result)

# ============= Network Construction =============

@mcp.tool()
def create_network(
    name: str = "network",
    snapshots: Optional[List[str]] = None,
    crs: str = "EPSG:4326"
) -> Dict[str, Any]:
    """Create a new PyPSA network"""
    if snapshots:
        snapshots = pd.DatetimeIndex(snapshots)
    network = Network(name=name, snapshots=snapshots, crs=crs)
    network.export_to_netcdf(f"{name}.nc")
    return {
        "status": "success",
        "message": f"Network '{name}' created and saved to {name}.nc"
    }

@mcp.tool()
def add_bus(
    network_name: str,
    bus_id: str,
    v_nom: float = 380.0,
    x: Optional[float] = None,
    y: Optional[float] = None,
    carrier: str = "AC"
) -> Dict[str, Any]:
    """Add a bus to the network"""
    network = Network(network_name)
    network.add("Bus", bus_id, v_nom=v_nom, x=x, y=y, carrier=carrier)
    network.export_to_netcdf(network_name)
    return {
        "status": "success",
        "message": f"Bus '{bus_id}' added to network"
    }

@mcp.tool()
def add_generator(
    network_name: str,
    gen_id: str,
    bus: str,
    p_nom: float,
    marginal_cost: float = 0.0,
    carrier: str = "generator",
    p_min_pu: float = 0.0,
    p_max_pu: float = 1.0
) -> Dict[str, Any]:
    """Add a generator to the network"""
    network = Network(network_name)
    network.add(
        "Generator",
        gen_id,
        bus=bus,
        p_nom=p_nom,
        marginal_cost=marginal_cost,
        carrier=carrier,
        p_min_pu=p_min_pu,
        p_max_pu=p_max_pu
    )
    network.export_to_netcdf(network_name)
    return {
        "status": "success",
        "message": f"Generator '{gen_id}' added to network"
    }

@mcp.tool()
def add_load(
    network_name: str,
    load_id: str,
    bus: str,
    p_set: float
) -> Dict[str, Any]:
    """Add a load to the network"""
    network = Network(network_name)
    network.add("Load", load_id, bus=bus, p_set=p_set)
    network.export_to_netcdf(network_name)
    return {
        "status": "success",
        "message": f"Load '{load_id}' added to network"
    }

@mcp.tool()
def add_line(
    network_name: str,
    line_id: str,
    bus0: str,
    bus1: str,
    x: float,
    r: float = 0.0,
    s_nom: float = 1000.0,
    length: float = 1.0
) -> Dict[str, Any]:
    """Add a transmission line to the network"""
    network = Network(network_name)
    network.add(
        "Line",
        line_id,
        bus0=bus0,
        bus1=bus1,
        x=x,
        r=r,
        s_nom=s_nom,
        length=length
    )
    network.export_to_netcdf(network_name)
    return {
        "status": "success",
        "message": f"Line '{line_id}' added to network"
    }

@mcp.tool()
def add_storage_unit(
    network_name: str,
    storage_id: str,
    bus: str,
    p_nom: float,
    max_hours: float = 6.0,
    efficiency_store: float = 0.9,
    efficiency_dispatch: float = 0.9,
    cyclic_state_of_charge: bool = True
) -> Dict[str, Any]:
    """Add a storage unit to the network"""
    network = Network(network_name)
    network.add(
        "StorageUnit",
        storage_id,
        bus=bus,
        p_nom=p_nom,
        max_hours=max_hours,
        efficiency_store=efficiency_store,
        efficiency_dispatch=efficiency_dispatch,
        cyclic_state_of_charge=cyclic_state_of_charge
    )
    network.export_to_netcdf(network_name)
    return {
        "status": "success",
        "message": f"Storage unit '{storage_id}' added to network"
    }

# ============= Optimization =============

@mcp.tool()
def optimize_network(
    network_name: str,
    solver_name: str = "highs",
    formulation: str = "kirchhoff",
    pyomo: bool = False,
    solver_options: Optional[Dict] = None
) -> Dict[str, Any]:
    """Run a linear optimal power flow (LOPF) on the network"""
    network = Network(network_name)
    
    try:
        status = network.lopf(
                    solver_name=solver_name,
                    pyomo=pyomo,
                    solver_options=solver_options or {}
                )
        
        # Get optimization results
        results = {
            "status": status,
            "objective": float(network.objective),
            "solver": solver_name,
            "generators": {
                gen: {
                    "p": network.generators_t.p[gen].tolist() if len(network.snapshots) > 1 
                         else float(network.generators_t.p[gen].iloc[0]),
                    "marginal_cost": float(network.generators.loc[gen, "marginal_cost"])
                }
                for gen in network.generators.index
            },
            "loads": {
                load: network.loads_t.p[load].tolist() if len(network.snapshots) > 1
                      else float(network.loads_t.p[load].iloc[0])
                for load in network.loads.index
            },
            "buses": {
                bus: {
                    "marginal_price": network.buses_t.marginal_price[bus].tolist() 
                                     if len(network.snapshots) > 1
                                     else float(network.buses_t.marginal_price[bus].iloc[0])
                }
                for bus in network.buses.index
            }
        }
        return results
    except Exception as e:
        return {
            "status": "error",
            "message": f"Optimization failed: {str(e)}"
        }

@mcp.tool()
def optimize_investment(
    network_name: str,
    solver_name: str = "highs",
    carriers: Optional[List[str]] = None,
    multi_investment_periods: bool = False
) -> Dict[str, Any]:
    """Run investment optimization to determine optimal capacity expansion"""
    network = Network(network_name)
    
    try:
        # Set components as extendable if carriers specified
        if carriers:
            network.generators.loc[
                network.generators.carrier.isin(carriers), "p_nom_extendable"
            ] = True
        
        status = network.lopf(
                    solver_name=solver_name
                )
        
        # Extract investment results
        results = {
            "status": status,
            "objective": float(network.objective),
            "investments": {
                "generators": {
                    gen: {
                        "p_nom_opt": float(network.generators.loc[gen, "p_nom_opt"]),
                        "capital_cost": float(network.generators.loc[gen, "capital_cost"])
                    }
                    for gen in network.generators[network.generators.p_nom_extendable].index
                },
                "lines": {
                    line: {
                        "s_nom_opt": float(network.lines.loc[line, "s_nom_opt"]),
                        "capital_cost": float(network.lines.loc[line, "capital_cost"])
                    }
                    for line in network.lines[network.lines.s_nom_extendable].index
                },
                "storage_units": {
                    storage: {
                        "p_nom_opt": float(network.storage_units.loc[storage, "p_nom_opt"]),
                        "capital_cost": float(network.storage_units.loc[storage, "capital_cost"])
                    }
                    for storage in network.storage_units[network.storage_units.p_nom_extendable].index
                }
            }
        }
        return results
    except Exception as e:
        return {
            "status": "error",
            "message": f"Investment optimization failed: {str(e)}"
        }

@mcp.tool()
def import_from_csv_folder(folder_path: str) -> Dict[str, Any]:
    """Import network from CSV files"""
    try:
        network = Network()
        network.import_from_csv_folder(folder_path)
        network_name = os.path.basename(folder_path) + ".nc"
        network.export_to_netcdf(network_name)
        return {
            "status": "success",
            "message": f"Network imported from {folder_path} and saved to {network_name}"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Import failed: {str(e)}"
        }

@mcp.tool()
def export_to_csv_folder(network_name: str, folder_path: str) -> Dict[str, Any]:
    """Export network to CSV files"""
    try:
        network = Network(network_name)
        network.export_to_csv_folder(folder_path)
        return {
            "status": "success",
            "message": f"Network exported to {folder_path}"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Export failed: {str(e)}"
        }


if __name__ == "__main__":
    mcp.run(transport="stdio")