-- Add 'team' to permission_scope_enum
ALTER TYPE permission_scope_enum ADD VALUE IF NOT EXISTS 'team';
