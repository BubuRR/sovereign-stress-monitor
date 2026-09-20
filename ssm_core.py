"""Entry point: run one full monitoring cycle and write report + DB logs."""
import asyncio
from core.quant_engine import run_all

if __name__ == "__main__":
    asyncio.run(run_all())
