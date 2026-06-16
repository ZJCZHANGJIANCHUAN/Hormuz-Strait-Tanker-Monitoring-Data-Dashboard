import ReactECharts from 'echarts-for-react';

const LEVEL_COLORS: Record<number, string> = {
  0: '#d9d9d9',
  1: '#52c41a',
  2: '#faad14',
  3: '#ff7a45',
  4: '#ff4d4f',
};

const LEVEL_LABELS: Record<number, string> = {
  0: '数据不足',
  1: '情绪冲击',
  2: '中度实质影响',
  3: '严重供应冲击',
  4: '极端冲击',
};

interface Props {
  level: number;
  label: string;
  confidence: number;
}

export default function RiskGauge({ level, label, confidence }: Props) {
  const color = LEVEL_COLORS[level] || '#d9d9d9';

  const option = {
    series: [{
      type: 'gauge',
      startAngle: 210,
      endAngle: -30,
      center: ['50%', '55%'],
      radius: '90%',
      min: 0,
      max: 10,
      splitNumber: 10,
      axisLine: {
        show: true,
        lineStyle: {
          width: 20,
          color: [
            [0.25, '#52c41a'],
            [0.50, '#faad14'],
            [0.75, '#ff7a45'],
            [1, '#ff4d4f'],
          ],
        },
      },
      pointer: {
        icon: 'path://M12.8,0.7l12,40.1H0.7L12.8,0.7z',
        length: '60%',
        width: 8,
        offsetCenter: [0, '-10%'],
        itemStyle: { color: 'auto' },
      },
      axisTick: { distance: -20, length: 8, lineStyle: { width: 1 } },
      splitLine: { distance: -24, length: 20, lineStyle: { width: 3 } },
      axisLabel: {
        distance: 30,
        fontSize: 12,
        formatter: (v: number) => (v === 0 ? '0' : v === 10 ? '10' : ''),
      },
      anchor: { show: true, size: 18 },
      title: { show: false },
      detail: {
        valueAnimation: true,
        fontSize: 24,
        offsetCenter: [0, '50%'],
        formatter: () => `{value|Lv.${level}}`,
        rich: { value: { fontSize: 28, fontWeight: 'bold', color } },
      },
      data: [{ value: level * 2.5, name: label }],
    }],
  };

  return (
    <div style={{ textAlign: 'center', flexShrink: 0 }}>
      <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 2, color: '#666' }}>当前风险等级</div>
      <ReactECharts option={option} style={{ height: 180, width: 220 }} />
      <div style={{
        marginTop: 2, padding: '2px 14px', borderRadius: 4,
        background: color, color: '#fff', fontWeight: 700,
        fontSize: 14, display: 'inline-block', lineHeight: '22px',
      }}>
        {label || LEVEL_LABELS[level] || '未知'}
      </div>
      {confidence > 0 && (
        <div style={{ marginTop: 4, fontSize: 12, color: '#999' }}>
          置信度: {(confidence * 100).toFixed(0)}%
        </div>
      )}
    </div>
  );
}
