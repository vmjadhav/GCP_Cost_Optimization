SELECT
  service.description,
  sku.description,
  usage.amount,
  usage.unit,
  cost
FROM `your-billing-dataset.gcp_billing_export_v1_XXXXXX_XXXXXX_XXXXXX`
WHERE
  service.description = "Cloud Storage"
  AND project.id = "your-project-id"
  AND usage_start_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY);
  