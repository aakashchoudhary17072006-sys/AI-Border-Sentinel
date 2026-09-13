export interface HealthResponse {
  status: string;
  service: string;
  version: string;
  active_scenario?: string;
}

export interface StatusResponse {
  status: 'ready' | 'degraded' | 'unavailable' | string;
  sequence: string;
  telemetry_available: boolean;
  video_available: boolean;
  processed_frames: number;
  unique_targets: number;
  alerts: number;
  highest_risk_score: number;
  highest_risk_level: 'NORMAL' | 'MONITOR' | 'SUSPICIOUS' | 'HIGH RISK' | string;
}

export interface RiskFactor {
  name: string;
  points: number;
  reason?: string;
}

export interface TargetRisk {
  score: number;
  level: 'NORMAL' | 'MONITOR' | 'SUSPICIOUS' | 'HIGH RISK' | string;
  factors: RiskFactor[];
}

export interface TargetState {
  target_id: number;
  bbox: [number, number, number, number];
  center: [number, number];
  confidence: number;
  direction: string;
  zone_state: 'INSIDE' | 'OUTSIDE' | string;
  risk: TargetRisk;
}

export interface Alert {
  target_id: number;
  frame_index: number;
  timestamp_seconds: number;
  level: 'SUSPICIOUS' | 'HIGH RISK' | string;
  previous_level?: string;
  score: number;
  message: string;
  reasons: string[];
  human_verification_required: boolean;
  disclaimer: string;
}

export interface TargetDetail {
  target_id: number;
  total_observations: number;
  latest_state: TargetState | null;
  zone_states_observed: string[];
  directions_observed: string[];
  highest_risk_score: number;
  highest_risk_level: string;
  triggered_factors: string[];
  alerts: Alert[];
  observations_history: Array<Record<string, any>>;
}

export interface ApiOverview {
  name: string;
  version: string;
  endpoints: string[];
}

export interface TelemetryFrame {
  frame_index: number;
  timestamp_seconds: number;
  frame_filename: string;
  targets: TargetState[];
  alerts: Alert[];
}

export interface TelemetryPayload {
  metadata: {
    project: string;
    sequence: string;
    total_input_frames: number;
    processed_frames: number;
    unreadable_frames: number;
    output_fps: number;
    resolution: { width: number; height: number };
    restricted_zone: { label: string; polygon: Array<[number, number]> };
    risk_model: {
      type: string;
      score_range: [number, number];
      risk_tiers: Record<string, string>;
    };
    disclaimer: string;
  };
  summary: Record<string, any>;
  frames: TelemetryFrame[];
  alerts_summary: Alert[];
}
