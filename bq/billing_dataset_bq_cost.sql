SELECT
  service.description,
  SUM(cost) AS total_cost
FROM
  `your-billing-project.billing_dataset.gcp_billing_export_v1_XXXXXX_XXXXXX_XXXXXX`
WHERE
  service.description = 'BigQuery'
  AND project.id = 'your-project-id'
  AND usage_start_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
GROUP BY
  service.description

  