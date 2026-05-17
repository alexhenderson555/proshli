import argparse
import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal
from app.services.scheduler import run_once


def main() -> None:
    parser = argparse.ArgumentParser(description="JobSkout worker loop")
    parser.add_argument("--frequency", choices=["daily", "weekly"], default="daily")
    parser.add_argument("--interval-seconds", type=int, default=300)
    parser.add_argument("--iterations", type=int, default=1)
    args = parser.parse_args()

    for index in range(args.iterations):
        db = SessionLocal()
        try:
            result = run_once(db, digest_frequency=args.frequency)
            print(
                f"[{index + 1}/{args.iterations}] ingestion_runs={result.ingestion_runs} "
                f"inserted={result.ingestion_inserted} deduped={result.ingestion_deduped} "
                f"digests_sent={result.digests_sent} digests_skipped={result.digests_skipped}"
            )
        finally:
            db.close()
        if index < args.iterations - 1:
            time.sleep(max(1, args.interval_seconds))


if __name__ == "__main__":
    main()
