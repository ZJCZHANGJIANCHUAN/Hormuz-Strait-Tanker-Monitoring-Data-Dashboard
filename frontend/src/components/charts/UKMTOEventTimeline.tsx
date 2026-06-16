import { useEffect, useState } from 'react';
import { Timeline, Tag, Empty, Spin } from 'antd';
import { fetchUKMTOData } from '@/services/api';
import type { UKMTODataPoint } from '@/types';

const SEVERITY_COLORS: Record<string, string> = {
  critical: '#ff4d4f',
  high: '#ff7a45',
  medium: '#faad14',
  low: '#52c41a',
};

const TYPE_LABELS: Record<string, string> = {
  attack: '袭击',
  suspicious_activity: '可疑活动',
  hijack: '劫持',
  advisory: '航行警告',
  warning: '警告',
};

export default function UKMTOEventTimeline() {
  const [data, setData] = useState<UKMTODataPoint[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchUKMTOData(14).then(d => { setData(d); setLoading(false); }).catch(() => setLoading(false));
  }, []);

  if (loading) return <Spin />;
  if (data.length === 0) return <Empty description="近14日无安全事件记录" />;

  return (
    <div style={{ maxHeight: 320, overflowY: 'auto' }}>
      <Timeline
        items={data.slice(0, 15).map(d => ({
          color: SEVERITY_COLORS[d.severity || ''] || '#d9d9d9',
          children: (
            <div>
              <div style={{ fontWeight: 600, marginBottom: 2 }}>
                <Tag color={SEVERITY_COLORS[d.severity || '']}>
                  {TYPE_LABELS[d.event_type] || d.event_type}
                </Tag>
                {d.area_name && <span style={{ fontSize: 12, color: '#999' }}>{d.area_name}</span>}
              </div>
              {d.description && (
                <div style={{ fontSize: 13, color: '#666', marginBottom: 2 }}>{d.description}</div>
              )}
              <div style={{ fontSize: 11, color: '#999' }}>
                {d.event_date ? new Date(d.event_date).toLocaleString('zh-CN') : ''}
                {d.advisory_number ? ` · ${d.advisory_number}` : ''}
              </div>
            </div>
          ),
        }))}
      />
    </div>
  );
}
