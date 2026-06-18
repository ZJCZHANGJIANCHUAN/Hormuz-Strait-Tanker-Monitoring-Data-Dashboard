import { useEffect, useState, useCallback } from 'react';
import { Spin, message } from 'antd';
import { fetchDashboardSummary } from '@/services/api';
import type { DashboardSummary } from '@/types';
import RiskGauge from '@/components/widgets/RiskGauge';
import MetricCard from '@/components/widgets/MetricCard';
import TrafficChart from '@/components/charts/TrafficChart';
import FireMapChart from '@/components/charts/FireMapChart';
import PortBarChart from '@/components/charts/PortBarChart';
import UKMTOEventTimeline from '@/components/charts/UKMTOEventTimeline';
import CrossValidationChart from '@/components/charts/CrossValidationChart';
import SourceStatusBar from '@/components/widgets/SourceStatusBar';

export default function OverviewPage() {
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);

  const loadData = useCallback(async () => {
    try {
      const summary = await fetchDashboardSummary();
      setData(summary);
    } catch (err) {
      message.error('数据加载失败，请检查后端服务是否运行');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    const handleRefresh = () => loadData();
    window.addEventListener('dashboard-refresh', handleRefresh);
    window.addEventListener('ukmto-updated', handleRefresh);
    return () => {
      window.removeEventListener('dashboard-refresh', handleRefresh);
      window.removeEventListener('ukmto-updated', handleRefresh);
    };
  }, [loadData]);

  if (loading) {
    return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />;
  }

  return (
    <div>
      {/* Risk Level & Source Status */}
      <div style={{
        background: '#fff', borderRadius: 8, padding: '16px 24px',
        boxShadow: '0 1px 4px rgba(0,0,0,0.06)', marginBottom: 16,
        display: 'flex', alignItems: 'center', gap: 32, flexWrap: 'wrap',
      }}>
        <RiskGauge level={data?.risk.level ?? 0} label={data?.risk.label ?? '未知'} confidence={data?.risk.confidence ?? 0} />
        <div style={{ flex: 1, minWidth: 280 }}>
          <SourceStatusBar sources={data?.source_status ?? []} />
        </div>
      </div>

      {/* Metric Cards */}
      <div className="metrics-row">
        <MetricCard
          title="🛳️ 海峡油轮 (IEA估算)"
          value={data?.strait.tanker_vessels}
          suffix="艘/日"
          changePct={data?.strait.change_pct}
          subtitle={`30日均值 ${data?.strait.baseline_30d ?? '-'} 艘 | AIS检测: ${data?.strait.portwatch?.tanker_vessels ?? '-'} 艘`}
        />
        <MetricCard
          title="⚓ 港口装载比"
          value={data?.ports.avg_loading_ratio != null ? (data.ports.avg_loading_ratio * 100).toFixed(0) : null}
          suffix="%"
          subtitle={`近7日 ${data?.ports.ports_count} 条记录`}
        />
        <MetricCard
          title="🛢️ 布伦特原油"
          value={data?.oil.brent}
          prefix="$"
          subtitle={`WTI $${data?.oil.wti ?? '-'} | 价差 $${data?.oil.spread ?? '-'}`}
        />
        <MetricCard
          title="📊 BDTI 运价指数"
          value={data?.shipping.bdti}
          subtitle={data?.shipping.td3c ? `TD3C: ${data.shipping.td3c}` : '暂无运价数据'}
        />
        <MetricCard
          title="🔥 卫星火点"
          value={data?.fires.count_3d}
          suffix="个"
          subtitle="近3日波斯湾火点"
        />
        <MetricCard
          title="⚠️ 安全事件"
          value={data?.ukmto.count_7d}
          suffix="起"
          subtitle="近7日 UKMTO 事件"
        />
      </div>

      {/* Charts Row 1 */}
      <div className="charts-row">
        <div className="chart-panel">
          <h3>📈 霍尔木兹海峡通行量趋势（30日）</h3>
          <TrafficChart />
        </div>
        <div className="chart-panel">
          <h3>🗺️ 波斯湾关键设施火点监测</h3>
          <FireMapChart />
        </div>
      </div>

      {/* Charts Row 2 */}
      <div className="charts-row">
        <div className="chart-panel">
          <h3>⚓ 主要港口装船量对比（近7日）</h3>
          <PortBarChart />
        </div>
        <div className="chart-panel">
          <h3>⚠️ UKMTO 安全事件时间线</h3>
          <UKMTOEventTimeline />
        </div>
      </div>

      {/* Charts Row 3 - Full Width Cross Validation */}
      <div className="charts-row" style={{ marginTop: 0 }}>
        <div className="chart-panel full-width">
          <h3>🔍 交叉验证：通行量 / 装船量 vs 油价</h3>
          <CrossValidationChart />
        </div>
      </div>
    </div>
  );
}
