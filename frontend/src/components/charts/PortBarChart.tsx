import { useEffect, useState } from 'react';
import ReactECharts from 'echarts-for-react';
import { fetchPortData } from '@/services/api';
import type { PortDataPoint } from '@/types';

export default function PortBarChart() {
  const [data, setData] = useState<PortDataPoint[]>([]);

  useEffect(() => {
    fetchPortData(7).then(setData).catch(() => {});
  }, []);

  // Aggregate by port name
  const portMap = new Map<string, { loaded: number; ballast: number }>();
  data.forEach(d => {
    const existing = portMap.get(d.port_name) || { loaded: 0, ballast: 0 };
    if (d.loaded_tankers) existing.loaded += d.loaded_tankers;
    if (d.ballast_tankers) existing.ballast += d.ballast_tankers;
    portMap.set(d.port_name, existing);
  });

  const ports = Array.from(portMap.entries()).filter(([_, v]) => v.loaded + v.ballast > 0);
  const portNames = ports.map(([n]) => n);
  const loadedValues = ports.map(([_, v]) => v.loaded);
  const ballastValues = ports.map(([_, v]) => v.ballast);

  const option = {
    tooltip: { trigger: 'axis' },
    legend: { data: ['装载', '空载/压载'], top: 0 },
    grid: { left: 50, right: 20, top: 40, bottom: 60 },
    xAxis: { type: 'category', data: portNames, axisLabel: { rotate: 30, fontSize: 10 } },
    yAxis: { type: 'value', name: '艘' },
    series: [
      {
        name: '装载', type: 'bar', stack: 'total',
        data: loadedValues, itemStyle: { color: '#1677ff' },
        label: { show: true, position: 'inside', fontSize: 10, color: '#fff' },
      },
      {
        name: '空载/压载', type: 'bar', stack: 'total',
        data: ballastValues, itemStyle: { color: '#faad14' },
        label: { show: true, position: 'inside', fontSize: 10, color: '#333' },
      },
    ],
  };

  return <ReactECharts option={option} style={{ height: 320 }} />;
}
