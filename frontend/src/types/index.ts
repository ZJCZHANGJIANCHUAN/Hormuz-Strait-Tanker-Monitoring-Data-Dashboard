export interface RiskInfo {
  level: number;
  label: string;
  confidence: number;
  date: string | null;
}

export interface StraitInfo {
  tanker_vessels: number | null;
  total_vessels: number | null;
  baseline_30d: number | null;
  change_pct: number | null;
  record_date: string | null;
  source: string | null;
  portwatch: {
    tanker_vessels: number | null;
    total_vessels: number | null;
    record_date: string | null;
    baseline_30d: number | null;
    source: string;
  } | null;
}

export interface PortsInfo {
  avg_loading_ratio: number | null;
  ports_count: number;
}

export interface OilInfo {
  brent: number | null;
  wti: number | null;
  spread: number | null;
  record_date: string | null;
}

export interface ShippingInfo {
  bdti: number | null;
  td3c: number | null;
  record_date: string | null;
}

export interface FiresInfo {
  count_3d: number;
}

export interface UKMTOInfo {
  count_7d: number;
}

export interface SourceStatus {
  name: string;
  key: string;
  status: 'healthy' | 'degraded' | 'warning' | 'stale' | 'blocked' | 'error' | 'unknown';
  description: string;
  latest_data: string | null;
  days_ago: number | null;
  last_collection: string | null;
  collector_error: string | null;
}

export interface DashboardSummary {
  risk: RiskInfo;
  strait: StraitInfo;
  ports: PortsInfo;
  oil: OilInfo;
  shipping: ShippingInfo;
  fires: FiresInfo;
  ukmto: UKMTOInfo;
  source_status: SourceStatus[];
  updated_at: string;
}

export interface StraitDataPoint {
  date: string;
  tanker_vessels: number | null;
  total_vessels: number | null;
  lng_vessels: number | null;
  tanker_capacity_tons: number | null;
  total_capacity_tons: number | null;
  source: string | null;
}

export interface PortDataPoint {
  date: string;
  port_name: string;
  port_code: string;
  loaded_tankers: number | null;
  ballast_tankers: number | null;
  loading_ratio: number | null;
  estimated_exports_7d: number | null;
}

export interface PriceDataPoint {
  date: string;
  brent_close: number | null;
  wti_close: number | null;
  spread: number | null;
}

export interface ShippingDataPoint {
  date: string;
  bdti: number | null;
  td3c: number | null;
  td8: number | null;
  bcti: number | null;
}

export interface FireDataPoint {
  detection_time: string | null;
  latitude: number;
  longitude: number;
  brightness: number | null;
  frp: number | null;
  confidence: string | null;
  facility_name: string;
  facility_type: string;
  country: string;
}

export interface UKMTODataPoint {
  event_date: string | null;
  event_type: string;
  severity: string | null;
  area_name: string | null;
  description: string | null;
  advisory_number: string | null;
}

export interface RiskAssessmentPoint {
  date: string;
  level: number;
  label: string;
  confidence: number;
  evidence: string | null;
}
