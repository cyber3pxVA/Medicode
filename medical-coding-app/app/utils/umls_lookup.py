"""Utility for mapping UMLS CUI → SNOMED and ICD-10 codes.

This is designed for *read-only* look-ups at runtime.  The first time it runs
in a fresh container it builds a small SQLite database (~200-300 MB) that holds
only the fields we need (CUI, CODE, SAB) filtered to two vocabularies:
  • SNOMEDCT_US  (SNOMED CT)
  • ICD10CM      (ICD-10-CM)
Subsequent runs simply query this database via parameterized SQL.

Because the DB lives inside the Docker volume (see docker-compose.yml) the
expensive import happens once per host, not per request.
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Dict, List, Tuple

# Which UMLS source abbreviations (SAB) we care about
SOURCES = {
    "SNOMEDCT_US": "snomed_codes",
    "ICD10CM": "icd10_codes",
}

DB_FILENAME = "umls_lookup.db"
TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS codes (
    cui TEXT NOT NULL,
    code TEXT NOT NULL,
    sab  TEXT NOT NULL,
    desc TEXT NOT NULL,
    PRIMARY KEY (cui, code, sab)
);
CREATE INDEX IF NOT EXISTS idx_codes_cui ON codes(cui);
"""


class UMLSLookup:
    """Singleton class managing the SQLite lookup DB."""

    _instance: "UMLSLookup | None" = None

    def __new__(cls, umls_base_path: str):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init(umls_base_path)
        return cls._instance

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _init(self, umls_base_path: str) -> None:
        self.umls_base_path = Path(umls_base_path)
        self.db_path = self.umls_base_path / DB_FILENAME
        self._ensure_db()

    def _ensure_db(self):
        """Create DB & import minimal data if the DB file does not exist."""
        first_time = not self.db_path.exists()
        if first_time:
            # Only use a persistent connection for DB build
            conn = sqlite3.connect(self.db_path)
            self._build_db(conn)
            conn.close()

    def _build_db(self, conn):
        """Parse MRCONSO.RRF and insert rows for SNOMED & ICD-10 only, including descriptions."""
        print("[UMLSLookup] Building SQLite lookup database … this may take a few minutes…")
        cur = conn.cursor()
        cur.executescript(TABLE_SCHEMA)
        # Disable journalling & synchronous for faster bulk insert – safe because we only write once
        cur.execute("PRAGMA journal_mode = OFF;")
        cur.execute("PRAGMA synchronous = OFF;")

        mrconso_path = self.umls_base_path / "META" / "MRCONSO.RRF"
        if not mrconso_path.exists():
            raise FileNotFoundError(f"Cannot find MRCONSO.RRF at {mrconso_path}")

        insert_sql = "INSERT OR IGNORE INTO codes (cui, code, sab, desc) VALUES (?, ?, ?, ?);"
        batch: List[Tuple[str, str, str, str]] = []
        batch_size = 10000
        total_inserted = 0

        with mrconso_path.open("r", encoding="utf-8", errors="ignore") as fh:
            for line_num, line in enumerate(fh, 1):
                parts = line.rstrip("\n\r").split("|")
                if len(parts) < 15:
                    continue  # malformed line
                cui = parts[0]
                sab = parts[11]
                code = parts[13]
                desc = parts[14]

                if sab in SOURCES and code and desc:
                    batch.append((cui, code, sab, desc))

                if len(batch) >= batch_size:
                    cur.executemany(insert_sql, batch)
                    total_inserted += len(batch)
                    batch.clear()
                    if total_inserted % 100000 == 0:
                        print(f"  … {total_inserted:,} codes imported so far…")

        # Insert remaining
        if batch:
            cur.executemany(insert_sql, batch)
            total_inserted += len(batch)

        conn.commit()
        print(f"[UMLSLookup] ✅ Import finished – {total_inserted:,} rows inserted.")
        # Restore safe pragmas
        cur.execute("PRAGMA journal_mode = WAL;")
        cur.execute("PRAGMA synchronous = NORMAL;")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def get_codes(self, cui: str) -> Dict[str, List[dict]]:
        """Return SNOMED & ICD-10 code lists (with descriptions) for the given CUI. Thread-safe."""
        db_path = self.db_path
        conn = sqlite3.connect(db_path)
        try:
            cur = conn.cursor()
            placeholder = ",".join(["?"] * len(SOURCES))
            cur.execute(
                f"SELECT code, sab, desc FROM codes WHERE cui = ? AND sab IN ({placeholder})",
                [cui, *SOURCES.keys()],
            )
            result: Dict[str, List[dict]] = {v: [] for v in SOURCES.values()}
            for code, sab, desc in cur.fetchall():
                result[SOURCES[sab]].append({'code': code, 'desc': desc})
            return result
        finally:
            conn.close()


# Convenience function -----------------------------------------------------
_lookup_instance: UMLSLookup | None = None

def get_codes_for_cui(cui: str, umls_base_path: str) -> Dict[str, List[str]]:
    """Module-level helper so callers don’t need to manage the singleton."""
    global _lookup_instance
    if _lookup_instance is None:
        _lookup_instance = UMLSLookup(umls_base_path)
    return _lookup_instance.get_codes(cui) 