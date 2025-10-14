-- Multi-tenant schema for Email Assistant (PostgreSQL)

CREATE TABLE IF NOT EXISTS tenants (
  id BIGSERIAL PRIMARY KEY,
  master_user_id BIGINT NOT NULL,
  store_id BIGINT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(master_user_id, store_id)
);

CREATE TABLE IF NOT EXISTS sender_accounts (
  id BIGSERIAL PRIMARY KEY,
  tenant_id BIGINT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  email TEXT NOT NULL,
  provider TEXT NOT NULL DEFAULT 'gmail',
  token_json TEXT NOT NULL, -- stores refresh/access tokens JSON (consider encryption)
  status TEXT NOT NULL DEFAULT 'active',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(tenant_id, email)
);

CREATE TABLE IF NOT EXISTS templates (
  id BIGSERIAL PRIMARY KEY,
  tenant_id BIGINT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  language TEXT NOT NULL,
  subject TEXT NOT NULL,
  html_content TEXT NOT NULL,
  text_content TEXT,
  version INT NOT NULL DEFAULT 1,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Unify images and attachments as assets with a type
CREATE TABLE IF NOT EXISTS assets (
  id BIGSERIAL PRIMARY KEY,
  tenant_id BIGINT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  asset_type TEXT NOT NULL CHECK (asset_type IN ('image','attachment')),
  file_id TEXT NOT NULL,          -- logical id for referencing in templates
  filename TEXT NOT NULL,
  mime_type TEXT NOT NULL,
  size_bytes BIGINT NOT NULL,
  storage_path TEXT NOT NULL,     -- e.g., /app/files/tenant_<id>/...
  checksum TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(tenant_id, asset_type, file_id)
);

CREATE TABLE IF NOT EXISTS jobs (
  id UUID PRIMARY KEY,
  tenant_id BIGINT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  type TEXT NOT NULL CHECK (type IN ('template','custom')),
  sender_email TEXT NOT NULL,
  template_id BIGINT REFERENCES templates(id) ON DELETE SET NULL,
  subject TEXT,                    -- for custom mode
  content TEXT,                    -- for custom mode
  html_content TEXT,               -- for custom mode
  min_interval INT NOT NULL DEFAULT 20,
  max_interval INT NOT NULL DEFAULT 90,
  total INT NOT NULL DEFAULT 0,
  success_count INT NOT NULL DEFAULT 0,
  failure_count INT NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'queued',
  webhook_url TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS job_recipients (
  id BIGSERIAL PRIMARY KEY,
  job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  to_email TEXT NOT NULL,
  language TEXT,
  variables JSONB,
  status TEXT NOT NULL DEFAULT 'pending',  -- pending|success|failed|skipped
  error TEXT,
  attempts INT NOT NULL DEFAULT 0,
  provider_message_id TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS job_events (
  id BIGSERIAL PRIMARY KEY,
  job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  event_type TEXT NOT NULL,  -- started|progress|completed|failed|paused|resumed
  payload JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
