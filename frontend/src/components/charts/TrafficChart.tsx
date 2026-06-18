import { useEffect, useState } from 'react';
import ReactECharts from 'echarts-for-react';
import { fetchStraitData } from '@/services/api';
import type { StraitDataPoint } from '@/types';

export default function TrafficChart() {
  const [data, setData] = useState<StraitDataPoint[]>([]);

  const load = () => { fetchStraitData(90).then(setData).catch(() => {}); };
  useEffect(() => {
    load();
    window.addEventListener('dashboard-refresh', load);
    return () => window.removeEventListener('dashboard-refresh', load);
  }, []);

  // Separate data by source
  const portwatch = data.filter(d => d.source === 'portwatch' && d.tanker_vessels != null);
  const iea = data.filter(d => d.source === 'iea_baseline' && d.tanker_vessels != null);

  // Build date-indexed maps
  const pwMap = new Map(portwatch.map(d => [d.date, d.tanker_vessels]));
  const ieaMap = new Map(iea.map(d => [d.date, d.tanker_vessels]));

  // Use IEA dates as primary (more complete), merge PortWatch
  const allDates = [...new Set([...iea.map(d => d.date), ...portwatch.map(d => d.date)])].sort();

  const pwValues = allDates.map(d => pwMap.get(d) ?? null);
  const ieaValues = allDates.map(d => ieaMap.get(d) ?? null);

  const option = {
    tooltip: {
      trigger: 'axis',
      formatter: (params: any[]) => {
        let html = `<b>${params[0].axisValue}</b><br/>`;
        params.forEach(p => {
          html += `${p.marker} ${p.seriesName}: ${p.value ?? '-'}<br/>`;
        });
        return html;
      },
    },
    legend: {
      data: ['IEA/EIA 权威估算', 'IMF PortWatch AIS检测'],
      top: 0,
    },
    grid: { left: 55, right: 20, top: 36, bottom: 50 },
    xAxis: {
      type: 'category',
      data: allDates,
      axisLabel: { rotate: 45, fontSize: 10 },
    },
    yAxis: { type: 'value', name: '艘/日' },
    dataZoom: [
      { type: 'inside', start: 50, end: 100 },
      { type: 'slider', start: 50, end: 100, height: 20, bottom: 16 },
    ],
    series: [
      {
        name: 'IEA/EIA 权威估算',
        type: 'line',
        data: ieaValues,
        smooth: true,
        symbol: 'circle',
        symbolSize: 5,
        lineStyle: { width: 2.5, color: '#1677ff' },
        itemStyle: { color: '#1677ff' },
      },
      {
        name: 'IMF PortWatch AIS检测',
        type: 'line',
        data: pwValues,
        smooth: true,
        symbol: 'diamond',
        symbolSize: 6,
        lineStyle: { width: 2, color: '#ff7a45', type: 'dashed' },
        itemStyle: { color: '#ff7a45' },
      },
    ],
  };

  return <ReactECharts option={option} style={{ height: 340 }} />;
}
