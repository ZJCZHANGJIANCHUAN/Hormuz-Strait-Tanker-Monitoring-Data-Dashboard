import axios from 'axios';
import type {
  DashboardSummary,
  StraitDataPoint,
  PortDataPoint,
  PriceDataPoint,
  ShippingDataPoint,
  FireDataPoint,
  UKMTODataPoint,
  RiskAssessmentPoint,
} from '@/types';

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
});

export async function fetchDashboardSummary(): Promise<DashboardSummary> {
  const res = await api.get('/dashboard/summary');
  return res.data;
}

export async function fetchStraitData(days: number = 30): Promise<StraitDataPoint[]> {
  const res = await api.get('/data/strait', { params: { days } });
  return res.data.data;
}

export async function fetchPortData(days: number = 7): Promise<PortDataPoint[]> {
  const res = await api.get('/data/ports', { params: { days } });
  return res.data.data;
}

export async function fetchPriceData(days: number = 30): Promise<PriceDataPoint[]> {
  const res = await api.get('/data/prices', { params: { days } });
  return res.data.data;
}

export async function fetchShippingData(days: number = 30): Promise<ShippingDataPoint[]> {
  const res = await api.get('/data/shipping', { params: { days } });
  return res.data.data;
}

export async function fetchFireData(days: number = 7): Promise<FireDataPoint[]> {
  const res = await api.get('/data/fires', { params: { days } });
  return res.data.data;
}

export async function fetchUKMTOData(days: number = 30): Promise<UKMTODataPoint[]> {
  const res = await api.get('/data/ukmto', { params: { days } });
  return res.data.data;
}

export async function fetchRiskHistory(days: number = 30): Promise<RiskAssessmentPoint[]> {
  const res = await api.get('/risk/assessment', { params: { days } });
  return res.data.data;
}

export async function triggerRiskAssessment() {
  const res = await api.post('/risk/assess');
  return res.data;
}

export async function triggerCollection(collectorName?: string) {
  const res = await api.post('/admin/collect', { collector_name: collectorName || null });
  return res.data;
}

export async function scrapeUKMTO(html?: string): Promise<{ message: string; events: string[] }> {
  if (html) {
    const res = await api.post('/admin/ukmto/scrape', { html });
    return res.data;
  }

  // Try direct fetch (works only if IGG overrides CORS)
  try {
    const res = await fetch('https://www.ukmto.org/recent-incidents');
    if (res.ok) {
      const text = await res.text();
      const apiRes = await api.post('/admin/ukmto/scrape', { html: text });
      return apiRes.data;
    }
  } catch {
    // CORS blocked
  }

  // Fallback: tell user to paste content
  return { message: 'CORS 阻止直接抓取。请用 Chrome/IGG 打开 ukmto.org，Ctrl+A/Ctrl+C 复制页面内容，粘贴到输入框提交。', events: [] };
}
