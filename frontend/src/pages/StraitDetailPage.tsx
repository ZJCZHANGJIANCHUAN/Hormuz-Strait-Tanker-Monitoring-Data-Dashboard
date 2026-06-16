import { useEffect, useState } from 'react';
import { Row, Col, Card, Statistic, Spin } from 'antd';
import ReactECharts from 'echarts-for-react';
import { fetchStraitData, fetchDashboardSummary } from '@/services/api';
import type { StraitDataPoint, DashboardSummary } from '@/types';

export default function StraitDetailPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [data, setData] = useState<StraitDataPoint[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetchDashboardSummary(),
      fetchStraitData(90),
    ]).then(([s, d]) => {
      setSummary(s);
      setData(d);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  if (loading) return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />;

  // Separate data by source
  const portwatch = data.filter(d => d.source === 'portwatch');
  const iea = data.filter(d => d.source === 'iea_baseline');

  // Build date-indexed maps for tankers
  const pwTankerMap = new Map(portwatch.map(d => [d.date, d.tanker_vessels]));
  const ieaTankerMap = new Map(iea.map(d => [d.date, d.tanker_vessels]));
  const pwTotalMap = new Map(portwatch.map(d => [d.date, d.total_vessels]));
  const ieaTotalMap = new Map(iea.map(d => [d.date, d.total_vessels]));
  const pwCapMap = new Map(portwatch.map(d => [d.date, d.tanker_capacity_tons]));
  const ieaCapMap = new Map(iea.map(d => [d.date, d.tanker_capacity_tons]));

  const allDates = [...new Set([...iea.map(d => d.date), ...portwatch.map(d => d.date)])].sort();

  const pwTankerVals = allDates.map(d => pwTankerMap.get(d) ?? null);
  const ieaTankerVals = allDates.map(d => ieaTankerMap.get(d) ?? null);
  const pwTotalVals = allDates.map(d => pwTotalMap.get(d) ?? null);
  const ieaTotalVals = allDates.map(d => ieaTotalMap.get(d) ?? null);
  const pwCapVals = allDates.map(d => pwCapMap.get(d) ?? null);
  const ieaCapVals = allDates.map(d => ieaCapMap.get(d) ?? null);

  const trafficOption = {
    tooltip: { trigger: 'axis' },
    legend: {
      data: ['IEA油轮估算', 'PortWatch油轮检测', 'IEA总船舶', 'PortWatch总船舶'],
      top: 0,
    },
    grid: { left: 55, right: 20, top: 36, bottom: 50 },
    xAxis: { type: 'category', data: allDates, axisLabel: { rotate: 45, fontSize: 10 } },
    yAxis: { type: 'value', name: '艘/日' },
    dataZoom: [
      { type: 'inside', start: 50, end: 100 },
      { type: 'slider', height: 20, bottom: 16 },
    ],
    series: [
      {
        name: 'IEA油轮估算', type: 'line', data: ieaTankerVals,
        smooth: true, symbol: 'circle', symbolSize: 4,
        lineStyle: { width: 2.5, color: '#1677ff' },
        itemStyle: { color: '#1677ff' },
      },
      {
        name: 'PortWatch油轮检测', type: 'line', data: pwTankerVals,
        smooth: true, symbol: 'diamond', symbolSize: 5,
        lineStyle: { width: 2, color: '#ff7a45', type: 'dashed' },
        itemStyle: { color: '#ff7a45' },
      },
      {
        name: 'IEA总船舶', type: 'line', data: ieaTotalVals,
        smooth: true, symbol: 'none',
        lineStyle: { width: 1.5, color: '#52c41a' },
      },
      {
        name: 'PortWatch总船舶', type: 'line', data: pwTotalVals,
        smooth: true, symbol: 'none',
        lineStyle: { width: 1.5, color: '#722ed1', type: 'dashed' },
      },
    ],
  };

  const capacityOption = {
    tooltip: { trigger: 'axis' },
    legend: {
      data: ['IEA油轮吨位估算', 'PortWatch油轮吨位检测'],
      top: 0,
    },
    grid: { left: 60, right: 20, top: 36, bottom: 50 },
    xAxis: { type: 'category', data: allDates, axisLabel: { rotate: 45, fontSize: 10 } },
    yAxis: { type: 'value', name: '吨' },
    dataZoom: [
      { type: 'inside' },
      { type: 'slider', height: 20, bottom: 16 },
    ],
    series: [
      {
        name: 'IEA油轮吨位估算', type: 'bar', data: ieaCapVals,
        itemStyle: { color: '#1677ff' },
      },
      {
        name: 'PortWatch油轮吨位检测', type: 'bar', data: pwCapVals,
        itemStyle: { color: '#722ed1' },
      },
    ],
  };

  return (
    <div>
      <h2 style={{ marginBottom: 20 }}>🛳️ 霍尔木兹海峡通行量详情</h2>

      {/* IEA Stats */}
      <Row gutter={12} style={{ marginBottom: 12 }}>
        <Col span={6}>
          <Card size="small">
            <Statistic title="IEA油轮估算" value={summary?.strait.tanker_vessels ?? '-'} suffix="艘/日" />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic title="IEA 30日均值" value={summary?.strait.baseline_30d ? Number(summary.strait.baseline_30d).toFixed(1) : '-'} suffix="艘" />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic title="IEA总通行量" value={summary?.strait.total_vessels ?? '-'} suffix="艘/日" />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="变化率"
              value={summary?.strait.change_pct ? Math.abs(summary.strait.change_pct).toFixed(1) : '-'}
              suffix="%"
              valueStyle={{ color: (summary?.strait.change_pct ?? 0) < 0 ? '#52c41a' : '#ff4d4f' }}
            />
          </Card>
        </Col>
      </Row>

      {/* PortWatch Stats */}
      <Row gutter={12} style={{ marginBottom: 20 }}>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="PortWatch AIS检测"
              value={summary?.strait.portwatch?.tanker_vessels ?? '-'}
              suffix="艘/日"
              valueStyle={{ fontSize: 18, color: '#ff7a45' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="PortWatch 30日均值"
              value={summary?.strait.portwatch?.baseline_30d ? Number(summary.strait.portwatch.baseline_30d).toFixed(1) : '-'}
              suffix="艘"
              valueStyle={{ fontSize: 18, color: '#ff7a45' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="PortWatch检测日期"
              value={summary?.strait.portwatch?.record_date ?? '-'}
              valueStyle={{ fontSize: 16, color: '#ff7a45' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="PortWatch总通行"
              value={summary?.strait.portwatch?.total_vessels ?? '-'}
              suffix="艘/日"
              valueStyle={{ fontSize: 18, color: '#ff7a45' }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col span={24}>
          <Card title="船舶通行量趋势（90日）— IEA估算 + PortWatch AIS检测">
            <ReactECharts option={trafficOption} style={{ height: 400 }} />
          </Card>
        </Col>
        <Col span={24}>
          <Card title="油轮吨位趋势（90日）— IEA估算 + PortWatch AIS检测">
            <ReactECharts option={capacityOption} style={{ height: 350 }} />
          </Card>
        </Col>
      </Row>
    </div>
  );
}
