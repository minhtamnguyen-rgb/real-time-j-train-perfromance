import duckdb

con = duckdb.connect()

print(
    con.execute("""
    SELECT
        window_start,
        COUNT(*)
    FROM read_parquet('project/data/processed/delays/delays_20260623_155433.parquet')
    GROUP BY window_start
    """).fetchdf()
)
