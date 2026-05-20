import numpy as np
from src.thermal.anomaly_detection import anomaly_detection

def test_anomaly_detection_cool_spot():
    # Create a 200x200 temperature map (all 30.0 degrees Celsius)
    temp_map = np.full((200, 200), 30.0, dtype=np.float32)
    
    # Insert a cool spot in the center (representing evaporative cooling of seepage)
    temp_map[90:110, 90:110] = 27.0
    
    results = anomaly_detection(temp_map)
    
    assert "delta_t" in results
    assert "anomaly_score" in results
    assert "seepage_probability" in results
    assert "moisture_level" in results
    
    # In the cool spot center, delta_t should be negative (cooler than surroundings)
    center_delta = results["delta_t"][100, 100]
    assert center_delta < -1.5
    
    # Seepage probability at center should be high
    assert results["seepage_probability"][100, 100] > 0.8
    
    # Moisture level at center should be high
    assert results["moisture_level"][100, 100] == "high"
    
    # Background concrete far from cool spot should be normal/stable
    edge_delta = results["delta_t"][10, 10]
    assert abs(edge_delta) < 0.5
    assert results["seepage_probability"][10, 10] < 0.1
    assert results["moisture_level"][10, 10] == "low"
