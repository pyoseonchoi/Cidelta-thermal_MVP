import os
import numpy as np
from src.thermal.ogs_integration import OgsIntegration

def test_ogs_integration_python_solver():
    # Instantiate OgsIntegration
    sim = OgsIntegration(config_path="configs/thermal_config.yaml", dam_type="earthfill")
    
    # Run simulation with standard parameters
    results = sim.run_simulation(seepage_anomalies=None)
    
    # Assert result structure
    assert "h_field" in results
    assert "T_field" in results
    assert "slope_temperatures" in results
    assert "v_y" in results
    assert "v_z" in results
    
    h_field = results["h_field"]
    T_field = results["T_field"]
    slope_temps = results["slope_temperatures"]
    
    # Assert shapes match
    ny = int(sim.base_width) + 1
    nz = int(sim.height) + 1
    assert h_field.shape == (ny, nz)
    assert T_field.shape == (ny, nz)
    assert len(slope_temps) == nz
    
    # Water head at bottom-left (upstream base) should be close to reservoir water level
    # Find a node inside the dam on the upstream face at the bottom
    assert h_field[15, 0] > 18.0
    
    # Temperature should be cooler at the upstream wet boundary and warmer at downstream (solar heating)
    # The reservoir is at 15.0C, downstream air/solar is at 25 + 5 = 30C.
    # Therefore, mean temperature close to upstream should be cooler than near downstream.
    upstream_temp = np.mean(T_field[15:20, 5:10])
    downstream_temp = np.mean(T_field[45:50, 5:10])
    assert upstream_temp < downstream_temp
    
    # Verify VTU output is generated
    vtu_path = "outputs/thermal_json/ogs_simulation.vtu"
    assert os.path.exists(vtu_path)
    assert os.path.getsize(vtu_path) > 0
    
def test_ogs_integration_with_anomaly():
    sim = OgsIntegration(config_path="configs/thermal_config.yaml", dam_type="earthfill")
    
    # Define a high permeability seepage channel (piping channel) in the middle of the dam
    anomalies = [
        {
            'y': [25.0, 35.0],
            'z': [5.0, 10.0],
            'k': 1e-3  # 100 times more permeable than base soil
        }
    ]
    
    results = sim.run_simulation(seepage_anomalies=anomalies)
    
    # The anomaly should increase flow and local heat convection, altering the slope temperatures
    assert "slope_temperatures" in results
    assert len(results["slope_temperatures"]) > 0
