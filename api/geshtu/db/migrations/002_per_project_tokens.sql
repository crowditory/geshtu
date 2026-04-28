-- access_tokens.project_id: NULL means "team-wide" (admin/legacy behaviour).
-- A non-null value scopes the token to one project — any API call that
-- references a different project must reject with 403.

ALTER TABLE access_tokens
    ADD COLUMN IF NOT EXISTS project_id UUID REFERENCES projects(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_access_tokens_project ON access_tokens(project_id) WHERE project_id IS NOT NULL;

INSERT INTO schema_migrations(version) VALUES ('002_per_project_tokens')
ON CONFLICT DO NOTHING;
