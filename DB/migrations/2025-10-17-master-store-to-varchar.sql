-- Migration: Convert master_user_id and store_id to VARCHAR in MySQL tables
-- Note: Review index/constraint names in your DB before applying. Run in maintenance window.

START TRANSACTION;

-- jobs: BIGINT -> VARCHAR
ALTER TABLE `jobs`
  MODIFY `master_user_id` VARCHAR(255) NOT NULL,
  MODIFY `store_id` VARCHAR(100) NOT NULL;

-- templates: BIGINT -> VARCHAR
ALTER TABLE `templates`
  MODIFY `master_user_id` VARCHAR(255) NOT NULL,
  MODIFY `store_id` VARCHAR(100) NOT NULL;

-- assets: ensure tenant columns are VARCHAR
-- If your assets table exists with numeric columns, convert them:
-- ALTER TABLE `assets`
--   MODIFY `master_user_id` VARCHAR(255) NOT NULL,
--   MODIFY `store_id` VARCHAR(100) NOT NULL;

-- sender_accounts: ensure tenant columns are VARCHAR
-- ALTER TABLE `sender_accounts`
--   MODIFY `master_user_id` VARCHAR(255) NOT NULL,
--   MODIFY `store_id` VARCHAR(100) NOT NULL;

COMMIT;

