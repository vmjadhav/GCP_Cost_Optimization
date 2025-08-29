SELECT
  table_name,
  SUM(total_logical_bytes) / 1e9 AS logical_gb,
  SUM(total_physical_bytes) / 1e9 AS physical_gb
FROM
  `region-us`.INFORMATION_SCHEMA.TABLE_STORAGE
WHERE
  project_id = 'your-project-id'
GROUP BY
  table_name
  