import os
import json

def export_json(data, path):
    """
    Saves the analyzed dam thermal results to a JSON file.
    
    Args:
        data (dict): The output dictionary containing metadata and updated cell results.
        path (str): Target output file path.
    """
    if path is None:
        raise ValueError("Export path cannot be None")
        
    # Create containing folder if it does not exist
    dir_name = os.path.dirname(path)
    if dir_name and not os.path.exists(dir_name):
        os.makedirs(dir_name, exist_ok=True)
        
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
