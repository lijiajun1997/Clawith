/**
 * Memory system API service
 * Token-based configuration for conversation compression
 */

const API_BASE = '/api';

// Types
export interface MemorySystemConfig {
  id?: string;
  tenant_id?: string;
  context_window_tokens: number;  // Always set: 128k, 200k, 1M
  compress_threshold: number;     // 0.5-0.95, trigger at X% of context window
  preserve_ratio: number;         // 0.1-0.5, keep recent X% during compression
}

export interface AgentMemoryConfig {
  context_window_tokens: number | null;
  compress_threshold: number | null;
  preserve_ratio: number | null;
}

export interface MemoryConfigResponse {
  model_info: {
    provider: string;
    model: string;
    default_context_window: number;
  };
  global_config: Partial<MemorySystemConfig>;
  agent_config: Partial<AgentMemoryConfig>;
  merged_config: {
    context_window_tokens: number;
    compress_threshold: number;
    preserve_ratio: number;
    trigger_tokens: number;
    preserve_tokens: number;
  };
}

export interface MemoryStatusResponse {
  config: {
    context_window_tokens: number;
    compress_threshold: number;
    preserve_ratio: number;
    trigger_tokens: number;
    preserve_tokens: number;
  };
}

// Helper
async function request<T>(url: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem('token');
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };

  const res = await fetch(`${API_BASE}${url}`, { ...options, headers });

  if (!res.ok) {
    const bodyText = await res.text();
    throw new Error(bodyText || `HTTP ${res.status}`);
  }

  return res.json();
}

// Company-level config
export async function getMemorySystemConfig(tenantId?: string): Promise<{
  exists: boolean;
  config: MemorySystemConfig;
}> {
  const params = tenantId ? `?tenant_id=${tenantId}` : '';
  return request(`/memory/system-config${params}`);
}

export async function updateMemorySystemConfig(
  config: Partial<MemorySystemConfig>
): Promise<{ success: boolean; id: string }> {
  return request('/memory/system-config', {
    method: 'PUT',
    body: JSON.stringify(config),
  });
}

// Agent-level config
export async function getAgentMemoryConfig(
  agentId: string
): Promise<MemoryConfigResponse> {
  return request(`/memory/agents/${agentId}/config`);
}

export async function updateAgentMemoryConfig(
  agentId: string,
  config: Partial<AgentMemoryConfig>
): Promise<{ success: boolean }> {
  return request(`/memory/agents/${agentId}/config`, {
    method: 'PUT',
    body: JSON.stringify(config),
  });
}

export async function resetAgentMemoryConfig(
  agentId: string
): Promise<{ success: boolean }> {
  return request(`/memory/agents/${agentId}/config`, {
    method: 'DELETE',
  });
}

// Memory status
export async function getAgentMemoryStatus(
  agentId: string
): Promise<MemoryStatusResponse> {
  return request(`/memory/agents/${agentId}/status`);
}

// Format helpers
export function formatContextWindow(tokens: number): string {
  if (tokens >= 1000000) {
    return `${(tokens / 1000000).toFixed(1)}M`;
  } else if (tokens >= 1000) {
    return `${(tokens / 1000).toFixed(0)}k`;
  }
  return tokens.toString();
}

// Context window preset options
export const CONTEXT_WINDOW_PRESETS = [
  { value: 64000, labelKey: 'enterprise.memory.64k' },
  { value: 128000, labelKey: 'enterprise.memory.128k' },
  { value: 200000, labelKey: 'enterprise.memory.200k' },
  { value: 256000, labelKey: 'enterprise.memory.256k' },
  { value: 1000000, labelKey: 'enterprise.memory.1m' },
];

// Export all
export const memoryApi = {
  getSystemConfig: getMemorySystemConfig,
  updateSystemConfig: updateMemorySystemConfig,
  getAgentConfig: getAgentMemoryConfig,
  updateAgentConfig: updateAgentMemoryConfig,
  resetAgentConfig: resetAgentMemoryConfig,
  getStatus: getAgentMemoryStatus,
  formatContextWindow,
  CONTEXT_WINDOW_PRESETS,
};

export default memoryApi;
