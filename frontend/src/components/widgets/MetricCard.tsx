import { Card } from 'antd';
import { ArrowUpOutlined, ArrowDownOutlined } from '@ant-design/icons';

interface Props {
  title: string;
  value: number | string | null | undefined;
  prefix?: string;
  suffix?: string;
  changePct?: number | null | undefined;
  subtitle?: string;
}

export default function MetricCard({ title, value, prefix, suffix, changePct, subtitle }: Props) {
  const displayValue = value != null ? (typeof value === 'string' ? value : Number(value)) : null;
  const isNumber = typeof displayValue === 'number';

  return (
    <Card
      size="small"
      style={{ borderRadius: 8, boxShadow: '0 1px 4px rgba(0,0,0,0.06)', height: '100%' }}
      styles={{ body: { padding: '14px 16px' } }}
    >
      <div style={{
        fontSize: 12, color: '#999', marginBottom: 6,
        whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
      }}>
        {title}
      </div>
      <div style={{ fontSize: 26, fontWeight: 700, color: '#1a1a2e', lineHeight: 1.2 }}>
        {isNumber
          ? <>{prefix}{displayValue.toLocaleString()}{suffix}</>
          : <>{prefix}{String(displayValue ?? '—')}{suffix}</>
        }
      </div>
      {changePct != null && (
        <div style={{ marginTop: 4, fontSize: 12 }}>
          {changePct > 0 ? (
            <span style={{ color: '#ff4d4f' }}>
              <ArrowUpOutlined /> {Math.abs(changePct).toFixed(1)}%
            </span>
          ) : changePct < 0 ? (
            <span style={{ color: '#52c41a' }}>
              <ArrowDownOutlined /> {Math.abs(changePct).toFixed(1)}%
            </span>
          ) : (
            <span style={{ color: '#999' }}>0%</span>
          )}
        </div>
      )}
      {subtitle && (
        <div style={{
          marginTop: 6, fontSize: 11, color: '#999', lineHeight: 1.4,
          overflow: 'hidden', textOverflow: 'ellipsis',
          display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical',
        }}>
          {subtitle}
        </div>
      )}
    </Card>
  );
}
