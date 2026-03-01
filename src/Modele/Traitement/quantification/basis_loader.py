import os
import json
import numpy as np
from src.logger import get_logger

logger = get_logger(__name__)

def load_basis(folder_path):
    basis_dict = {}

    for file in os.listdir(folder_path):
        if file.endswith(".json"):
            full_path = os.path.join(folder_path, file)

            with open(full_path, "r") as f:
                content = json.load(f)

            name = content.get("name", file.replace(".json", ""))

            real = np.array(content["basis"]["basis_re"], dtype=np.float64)
            imag = np.array(content["basis"]["basis_im"], dtype=np.float64)

            fid = real + 1j * imag

            # Normalize FID properly
            max_val = np.max(np.abs(fid))
            if max_val > 0:
                fid = fid / max_val

            basis_dict[name] = fid

    if not basis_dict:
        raise RuntimeError("No basis files found.")

    logger.info(f"[BasisLoader] Loaded metabolites: {list(basis_dict.keys())}")
    return basis_dict