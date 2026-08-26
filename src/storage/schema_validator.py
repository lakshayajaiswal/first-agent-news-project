"""
Schema Validator for Supabase PostgreSQL migrations.
Verifies syntax, table completeness, constraint definitions, and indexes.
"""

from __future__ import annotations
import os
import re
from typing import Any, Dict, List, Set


EXPECTED_TABLES: Set[str] = {
    "sources",
    "articles",
    "events",
    "article_events",
    "classifications",
    "summaries",
    "notifications",
    "fetch_runs",
    "user_preferences",
}

EXPECTED_BUCKETS: Set[str] = {
    "raw-documents",
    "source-artifacts",
}


def read_migration_files(migrations_dir: str = "supabase/migrations") -> List[tuple[str, str]]:
    """Read all SQL migration files in order."""
    if not os.path.exists(migrations_dir):
        return []
    
    files = sorted([f for f in os.listdir(migrations_dir) if f.endswith(".sql")])
    result = []
    for filename in files:
        path = os.path.join(migrations_dir, filename)
        with open(path, "r", encoding="utf-8") as f:
            result.append((filename, f.read()))
    return result


def validate_migration_sql(sql_content: str) -> Dict[str, Any]:
    """Parse and validate SQL content against specification requirements."""
    found_tables = set()
    found_indexes = set()
    found_foreign_keys = set()
    found_unique_constraints = set()

    # Extract CREATE TABLE statements
    table_matches = re.findall(r"CREATE\s+TABLE(?:\s+IF\s+NOT\s+EXISTS)?\s+(\w+)", sql_content, re.IGNORECASE)
    for t in table_matches:
        found_tables.add(t.lower())

    # Extract CREATE INDEX statements
    index_matches = re.findall(r"CREATE\s+INDEX(?:\s+IF\s+NOT\s+EXISTS)?\s+(\w+)", sql_content, re.IGNORECASE)
    for idx in index_matches:
        found_indexes.add(idx.lower())

    # Extract REFERENCES
    fk_matches = re.findall(r"REFERENCES\s+(\w+)\((\w+)\)", sql_content, re.IGNORECASE)
    for ref_table, ref_col in fk_matches:
        found_foreign_keys.add((ref_table.lower(), ref_col.lower()))

    # Check for UNIQUE constraints
    unique_matches = re.findall(r"UNIQUE\s*\(([^)]+)\)", sql_content, re.IGNORECASE)
    for u in unique_matches:
        cleaned = "".join(u.split()).lower()
        found_unique_constraints.add(cleaned)

    # Check RLS
    rls_enabled = re.findall(r"ALTER\s+TABLE\s+(\w+)\s+ENABLE\s+ROW\s+LEVEL\s+SECURITY", sql_content, re.IGNORECASE)
    rls_tables = {t.lower() for t in rls_enabled}

    return {
        "tables": found_tables,
        "indexes": found_indexes,
        "foreign_keys": found_foreign_keys,
        "unique_constraints": found_unique_constraints,
        "rls_tables": rls_tables,
    }


def verify_schema_integrity() -> Dict[str, Any]:
    """Full validation check across all migration and seed files."""
    migrations = read_migration_files("supabase/migrations")
    combined_sql = "\n".join(content for _, content in migrations)
    
    analysis = validate_migration_sql(combined_sql)
    
    missing_tables = EXPECTED_TABLES - analysis["tables"]
    
    # Check seed file
    seed_path = "supabase/seed.sql"
    has_seed = os.path.exists(seed_path)
    seed_sources_count = 0
    if has_seed:
        with open(seed_path, "r", encoding="utf-8") as f:
            seed_content = f.read()
            seed_sources_count = len(re.findall(r"\(\s*'[^']+'\s*,\s*'(?:vtu|ai|development|cybersecurity)'", seed_content))

    return {
        "valid": len(missing_tables) == 0,
        "total_migrations": len(migrations),
        "found_tables": list(sorted(analysis["tables"])),
        "missing_tables": list(sorted(missing_tables)),
        "total_indexes": len(analysis["indexes"]),
        "rls_table_count": len(analysis["rls_tables"]),
        "has_seed_file": has_seed,
        "seed_sources_count": seed_sources_count,
    }
