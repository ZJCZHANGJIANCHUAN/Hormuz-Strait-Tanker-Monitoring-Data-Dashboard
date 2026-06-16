import { useEffect, useState } from 'react';
import ReactECharts from 'echarts-for-react';
import { fetchStraitData, fetchPriceData } from '@/services/api';
import type { StraitDataPoint, PriceDataPoint } from '@/types';

export default function CrossValidationChart() {
  const [straitData, setStraitData] = useState<StraitDataPoint[]>([]);
  const [priceData, setPriceData] = useState<PriceDataPoint[]>([]);

  useEffect(() => {
    fetchStraitData(90).then(setStraitData).catch(() => {});
    fetchPriceData(90).then(setPriceData).catch(() => {});
  }, []);

  const iea = straitData.filter(d => d.source === 'iea_baseline' && d.tanker_vessels != null);
  const portwatch = straitData.filter(d => d.source === 'portwatch' && d.tanker_vessels != null);

  const allDates = [...new Set([
    ...iea.map(d => d.date),
    ...portwatch.map(d => d.date),
    ...priceData.filter(p => p.brent_close != null).map(p => p.date),
  ])].sort();

  const ieaMap = new Map(iea.map(d => [d.date, d.tanker_vessels]));
  const pwMap = new Map(portwatch.map(d => [d.date, d.tanker_vessels]));
  const priceMap = new Map(priceData.filter(p => p.brent_close != null).map(p => [p.date, p.brent_close]));

  const ieaVals = allDates.map(d => ieaMap.get(d) ?? null);
  const pwVals = allDates.map(d => pwMap.get(d) ?? null);
  const brentVals = allDates.map(d => priceMap.get(d) ?? null);

  const option = {
    tooltip: {
      trigger: 'axis',
      formatter: (params: any[]) => {
        let html = `<b>${params[0].axisValue}</b><br/>`;
        params.forEach((p: any) => {
          if (p.value == null) return;
          if (p.seriesName === '布伦特油价') {
            html += `${p.marker} ${p.seriesName}: $${p.value}<br/>`;
          } else {
            html += `${p.marker} ${p.seriesName}: ${p.value} 艘/日<br/>`;
          }
        });
        return html;
      },
    },
    legend: {
      data: ['IEA油轮估算', 'PortWatch AIS检测', '布伦特油价'],
      top: 0,
    },
    grid: { left: 65, right: 60, top: 36, bottom: 50 },
    xAxis: {
      type: 'category', data: allDates,
      axisLabel: { rotate: 45, fontSize: 10 },
    },
    yAxis: [
      { type: 'value', name: '艘/日', min: 0,
        splitLine: { lineStyle: { color: '#f0f0f0', type: 'dashed' } }
      },
      { type: 'value', name: 'USD/桶', min: 60,
        splitLine: { show: false }
      },
    ],
    dataZoom: [
      { type: 'inside', start: 30, end: 100 },
      { type: 'slider', height: 20, bottom: 16, start: 30, end: 100 },
    ],
    series: [
      {
        name: 'IEA油轮估算', type: 'line', yAxisIndex: 0,
        data: ieaVals, smooth: true, connectNulls: false,
        symbol: 'circle', symbolSize: 5,
        lineStyle: { width: 2.5, color: '#1677ff' },
        areaStyle: { color: 'rgba(22,119,255,0.08)' },
        markLine: {
          silent: true, symbol: 'none',
          data: [{ type: 'average', name: '油轮均值' }],
          lineStyle: { color: '#1677ff', type: 'dashed', width: 1 },
        },
      },
      {
        name: 'PortWatch AIS检测', type: 'line', yAxisIndex: 0,
        data: pwVals, smooth: true,
        symbol: 'diamond', symbolSize: 6,
        lineStyle: { width: 2, color: '#ff7a45', type: 'dashed' },
        itemStyle: { color: '#ff7a45' },
      },
      {
        name: '布伦特油价', type: 'line', yAxisIndex: 1,
        data: brentVals, smooth: true, connectNulls: true,
        symbol: 'triangle', symbolSize: 6,
        lineStyle: { width: 2.5, color: '#ff4d4f' },
        itemStyle: { color: '#ff4d4f' },
        markLine: {
          silent: true, symbol: 'none',
          data: [{ type: 'average', name: '均价' }],
          lineStyle: { color: '#ff4d4f', type: 'dashed', width: 1 },
        },
        markPoint: {
          data: [
            { type: 'max', name: '最高' },
            { type: 'min', name: '最低' },
          ],
          symbolSize: 40,
          label: { fontSize: 10 },
        },
      },
    ],
  };

  return <ReactECharts option={option} style={{ height: 360 }} />;
}
