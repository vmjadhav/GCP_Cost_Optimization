SELECT
  SUM(total_bytes_processed) AS total_bytes_processed,
  DATE_TRUNC(DATE(creation_time), MONTH) AS month
FROM
  `region-<your-region>`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
WHERE
  creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
  AND state = 'DONE'
  AND job_type = 'QUERY'
GROUP BY month
ORDER BY month DESC
LIMIT 1;
