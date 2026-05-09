from __future__ import annotations

import os
import random


def set_seed(seed: int = 42) -> None:
    """Set reproducibility seed for standard-library randomness."""
    random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
