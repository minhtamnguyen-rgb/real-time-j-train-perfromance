import duckdb

con = duckdb.connect()

result = con.execute("""
SELECT
    route_id,
    COUNT(*)
FROM read_parquet('project/data/processed/delays/*.parquet')
GROUP BY route_id;
""").fetchdf()

print(result)