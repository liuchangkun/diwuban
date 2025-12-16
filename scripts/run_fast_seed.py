from pathlib import Path
import json
import time

from app.core.config.loader_new import load_settings
from app.core.logging.setup import init_logging
from app.services.rules.seed_from_data import batch_seed_from_existing_data


def main():
    s = load_settings(Path("configs"))
    try:
        init_logging("configs", s.system.timezone.default)
    except Exception:
        pass
    t = time.perf_counter()
    res = batch_seed_from_existing_data(s, fast_mode=True)
    res["elapsed_ms"] = int((time.perf_counter() - t) * 1000)
    print(json.dumps(res, ensure_ascii=False))


if __name__ == "__main__":
    main()

