import numpy as np
from src.thermal.temperature_map import temperature_map

def test_temperature_map_scaling():
    # Test linear mapping from [0, 255] to [18.0, 38.0]
    img = np.array([[0, 127, 255]], dtype=np.uint8)
    temp = temperature_map(img)
    
    assert temp.shape == (1, 3)
    assert np.isclose(temp[0, 0], 18.0)
    assert np.isclose(temp[0, 1], 18.0 + (127.0/255.0)*(38.0 - 18.0), atol=0.01)
    assert np.isclose(temp[0, 2], 38.0)
