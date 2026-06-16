import { Tooltip, Tag } from 'antd';
import type { SourceStatus } from '@/types';

const STATUS_CONFIG: Record<string, { color: string; label: string }> = {
  healthy:   { color: '#52c41a', label: '正常' },
  degraded:  { color: '#faad14', label: '稍旧' },
  warning:   { color: '#ff7a45', label: '延迟' },
  stale:     { color: '#ff4d4f', label: '过期' },
  blocked:   { color: '#ff4d4f', label: '被墙' },
  error:     { color: '#ff4d4f', label: '错误' },
  unknown:   { color: '#d9d9d9', label: '未知' },
};

interface Props {
  sources: SourceStatus[];
}

export default function SourceStatusBar({ sources }: Props) {
  return (
    <div>
      <div style={{ fontSize: 13, color: '#666', marginBottom: 8 }}>数据源状态</div>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        {sources.map((s) => {
          const cfg = STATUS_CONFIG[s.status] || STATUS_CONFIG.unknown;
          return (
            <Tooltip
              key={s.key}
              title={
                <div style={{ fontSize: 12 }}>
                  <div style={{ fontWeight: 600, marginBottom: 4 }}>{s.name}</div>
                  <div>{s.description}</div>
                  {s.latest_data && <div>最新数据: {s.latest_data}</div>}
                  {s.days_ago != null && <div>{s.days_ago}天前</div>}
                  {s.collector_error && (
                    <div style={{ color: '#ff4d4f', marginTop: 4 }}>{s.collector_error}</div>
                  )}
                </div>
              }
            >
              <Tag color={cfg.color} style={{ margin: 0, cursor: 'pointer', fontSize: 12 }}>
                <span className={`source-indicator ${s.status}`} style={{ marginRight: 4 }} />
                {s.name}
              </Tag>
            </Tooltip>
          );
        })}
      </div>
    </div>
  );
}
