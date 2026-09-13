import {
  HealthResponse,
  TargetState,
  Alert,
  TargetDetail,
  TelemetryPayload
} from '../types/api';

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://ai-border-sentinel.onrender.com';

async function fetchWithTimeout<T>(endpoint: string, timeoutMs = 3000): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const url = `${API_BASE_URL}${endpoint}`;
    const response = await fetch(url, { signal: controller.signal });
    clearTimeout(timer);
    if (!response.ok) {
      throw new Error(`API Error [${response.status}]: ${response.statusText} (${endpoint})`);
    }
    return await response.json();
  } catch (err) {
    clearTimeout(timer);
    throw err;
  }
}

let cachedFallbackJson: any = null;

async function fetchLocalFallbackJson(): Promise<any> {
  if (cachedFallbackJson) return cachedFallbackJson;
  try {
    const response = await fetch('/patrol1_final.json');
    if (response.ok) {
      cachedFallbackJson = await response.json();
      return cachedFallbackJson;
    }
  } catch (e) {
    console.warn('Local fallback scenario fetch failed:', e);
  }
  return null;
}

export const apiService = {
  getBaseUrl: (): string => API_BASE_URL,

  getHealth: async (): Promise<HealthResponse> => {
    try {
      return await fetchWithTimeout<HealthResponse>('/api/health', 3000);
    } catch {
      return {
        status: 'healthy',
        service: 'AI Border Sentinel API (Demo Fallback)',
        version: '1.0.0',
        active_scenario: 'patrol1_final'
      };
    }
  },

  getTelemetry: async (): Promise<TelemetryPayload> => {
    try {
      const data = await fetchWithTimeout<TelemetryPayload>('/api/telemetry', 3000);
      if (data && (data.metadata || data.summary)) {
        return data;
      }
    } catch (err) {
      console.warn('Render /api/telemetry endpoint unavailable or timed out (>3s). Using local demo fallback dataset (/patrol1_final.json).');
    }
    const fallback = await fetchLocalFallbackJson();
    if (fallback) {
      return fallback as TelemetryPayload;
    }
    throw new Error('Telemetry data unavailable');
  },

  getTargets: async (): Promise<{ targets: TargetState[] }> => {
    try {
      const data = await fetchWithTimeout<any>('/api/targets', 3000);
      if (Array.isArray(data) && data.length > 0) {
        return { targets: data };
      }
      if (data && Array.isArray(data.targets) && data.targets.length > 0) {
        return { targets: data.targets };
      }
    } catch (err) {
      console.warn('Render /api/targets endpoint unavailable or timed out (>3s). Using local demo fallback dataset (/patrol1_final.json).');
    }
    const fallback = await fetchLocalFallbackJson();
    if (fallback && Array.isArray(fallback.targets)) {
      return { targets: fallback.targets };
    }
    return { targets: [] };
  },

  getAlerts: async (): Promise<{ alerts: Alert[] }> => {
    try {
      const data = await fetchWithTimeout<any>('/api/alerts', 3000);
      if (Array.isArray(data) && data.length > 0) {
        return { alerts: data };
      }
      if (data && Array.isArray(data.alerts) && data.alerts.length > 0) {
        return { alerts: data.alerts };
      }
    } catch (err) {
      console.warn('Render /api/alerts endpoint unavailable or timed out (>3s). Using local demo fallback dataset (/patrol1_final.json).');
    }
    const fallback = await fetchLocalFallbackJson();
    if (fallback && Array.isArray(fallback.alerts)) {
      return { alerts: fallback.alerts };
    }
    return { alerts: [] };
  },

  getTarget: (targetId: number): Promise<TargetDetail> => fetchWithTimeout<TargetDetail>(`/api/targets/${targetId}`, 3000),

  getVideoUrl: (): string => `${API_BASE_URL}/api/video`
};

export default apiService;

