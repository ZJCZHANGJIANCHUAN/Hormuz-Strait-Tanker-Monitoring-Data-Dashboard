import { useEffect, useState } from 'react';
import { Card, Table, Tag, Button, Spin, message, Input, Timeline } from 'antd';
import { fetchRiskHistory, triggerRiskAssessment, scrapeUKMTO, fetchUKMTOData } from '@/services/api';
import type { RiskAssessmentPoint, UKMTODataPoint } from '@/types';
import ReactECharts from 'echarts-for-react';

const LEVEL_COLORS: Record<number, string> = {
  1: '#52c41a',
  2: '#faad14',
  3: '#ff7a45',
  4: '#ff4d4f',
};

const SEVERITY_TAG: Record<string, { color: string; label: string }> = {
  critical: { color: '#ff4d4f', label: '严重' },
  high: { color: '#ff7a45', label: '高' },
  medium: { color: '#faad14', label: '中' },
  low: { color: '#52c41a', label: '低' },
};

const EVENT_TYPE_LABEL: Record<string, string> = {
  attack: '袭击',
  hijack: '劫持',
  suspicious_activity: '可疑活动',
  advisory: '航行警告',
  other: '其他',
};

export default function RiskPage() {
  const [data, setData] = useState<RiskAssessmentPoint[]>([]);
  const [ukmtoEvents, setUkmtoEvents] = useState<UKMTODataPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [assessing, setAssessing] = useState(false);
  const [scraping, setScraping] = useState(false);
  const [ukmtoHtml, setUkmtoHtml] = useState('');
  const [showPaste, setShowPaste] = useState(false);

  const loadData = () => {
    Promise.all([
      fetchRiskHistory(30),
      fetchUKMTOData(90),
    ]).then(([riskData, ukmtoData]) => {
      setData(riskData);
      setUkmtoEvents(ukmtoData);
      setLoading(false);
    }).catch(() => setLoading(false));
  };

  useEffect(() => { loadData(); }, []);

  const handleScrape = async () => {
    setScraping(true);
    try {
      const result = await scrapeUKMTO();
      if (result.message.includes('CORS')) {
        setShowPaste(true);
      } else if (result.events.length > 0) {
        message.success(result.message);
        loadData();
      } else {
        message.info(result.message);
      }
    } catch {
      setShowPaste(true);
      message.info('直接抓取失败，请粘贴 UKMTO 页面内容');
    } finally {
      setScraping(false);
    }
  };

  const handlePasteSubmit = async () => {
    if (!ukmtoHtml.trim()) return;
    setScraping(true);
    try {
      const result = await scrapeUKMTO(ukmtoHtml);
      message.success(result.message);
      setUkmtoHtml('');
      setShowPaste(false);
      await loadData();
      // Notify overview page to refresh
      window.dispatchEvent(new CustomEvent('ukmto-updated'));
    } catch {
      message.error('解析失败，请确认粘贴的是 UKMTO 页面完整内容');
    } finally {
      setScraping(false);
    }
  };

  const handleAssess = async () => {
    setAssessing(true);
    try {
      const result = await triggerRiskAssessment();
      message.success(`评估完成：${result.label}（置信度 ${(result.confidence * 100).toFixed(0)}%）`);
      loadData();
    } catch {
      message.error('评估失败');
    } finally {
      setAssessing(false);
    }
  };

  // Trend chart
  const dates = data.map(d => d.date).reverse();
  const levels = data.map(d => d.level).reverse();
  const confidences = data.map(d => d.confidence).reverse();

  const trendOption = {
    tooltip: { trigger: 'axis' },
    legend: { data: ['风险等级', '置信度'], top: 0 },
    grid: { left: 50, right: 50, top: 36, bottom: 40 },
    xAxis: { type: 'category', data: dates, axisLabel: { rotate: 45, fontSize: 10 } },
    yAxis: [
      { type: 'value', name: '风险等级', min: 0, max: 4, interval: 1,
        axisLabel: { formatter: (v: number) => ['', '情绪', '中度', '严重', '极端'][v] || '' } },
      { type: 'value', name: '置信度', min: 0, max: 1 },
    ],
    series: [
      {
        name: '风险等级', type: 'line', yAxisIndex: 0, data: levels,
        step: 'end', lineStyle: { width: 3, color: '#ff4d4f' },
        areaStyle: { color: 'rgba(255,77,79,0.15)' },
      },
      {
        name: '置信度', type: 'line', yAxisIndex: 1, data: confidences,
        lineStyle: { width: 1.5, color: '#1677ff', type: 'dashed' },
      },
    ],
  };

  const columns = [
    { title: '日期', dataIndex: 'date', key: 'date', width: 120 },
    {
      title: '风险等级', dataIndex: 'level', key: 'level', width: 180,
      render: (level: number, record: RiskAssessmentPoint) => (
        <Tag color={LEVEL_COLORS[level]} style={{ fontSize: 14, padding: '2px 12px' }}>
          Lv.{level} {record.label}
        </Tag>
      ),
    },
    {
      title: '置信度', dataIndex: 'confidence', key: 'confidence', width: 100,
      render: (v: number) => `${(v * 100).toFixed(0)}%`,
    },
    { title: '判定依据', dataIndex: 'evidence', key: 'evidence', ellipsis: true },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h2>🎯 风险评估记录</h2>
        <div style={{ display: 'flex', gap: 8 }}>
          <Button onClick={handleScrape} loading={scraping}>
            ⚠️ 抓取 UKMTO 事件
          </Button>
          <Button type="primary" onClick={handleAssess} loading={assessing}>
            立即评估
          </Button>
        </div>
      </div>

      {showPaste && (
        <Card style={{ marginBottom: 16, background: '#fffbe6', border: '1px solid #ffe58f' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
            <span style={{ fontSize: 14, fontWeight: 600 }}>
              📋 粘贴 UKMTO 页面源码
            </span>
            <a href="view-source:https://www.ukmto.org/recent-incidents" target="_blank" style={{ fontSize: 12 }}>
              打开 UKMTO 源码 →
            </a>
          </div>
          <div style={{ fontSize: 12, color: '#999', marginBottom: 8 }}>
            在 Chrome/IGG 中打开 UKMTO → <b>Ctrl+U</b> 查看源码 → Ctrl+A/Ctrl+C → 粘贴到下方 → 提交
          </div>
          <Input.TextArea
            value={ukmtoHtml}
            onChange={e => setUkmtoHtml(e.target.value)}
            placeholder="粘贴 UKMTO 页面完整内容..."
            rows={4}
            style={{ marginBottom: 8 }}
          />
          <div style={{ display: 'flex', gap: 8 }}>
            <Button type="primary" onClick={handlePasteSubmit} loading={scraping}>
              提交解析
            </Button>
            <Button onClick={() => setShowPaste(false)}>取消</Button>
          </div>
        </Card>
      )}

      {loading ? <Spin size="large" style={{ display: 'block', margin: '100px auto' }} /> : (
        <>
          <Card style={{ marginBottom: 20 }}>
            <ReactECharts option={trendOption} style={{ height: 300 }} />
          </Card>

          {/* UKMTO Security Events Timeline */}
          <Card
            title={
              <span>
                ⚠️ UKMTO 安全事件时间线
                <span style={{ fontSize: 13, fontWeight: 400, color: '#999', marginLeft: 12 }}>
                  {ukmtoEvents.length} 起事件
                </span>
              </span>
            }
            style={{ marginBottom: 20 }}
          >
            {ukmtoEvents.length === 0 ? (
              <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>
                暂无安全事件。点击「抓取 UKMTO 事件」获取最新数据。
              </div>
            ) : (
              <Timeline
                items={ukmtoEvents
                  .sort((a, b) => (b.event_date || '').localeCompare(a.event_date || ''))
                  .slice(0, 30)
                  .map(e => {
                    const sev = SEVERITY_TAG[e.severity || ''] || SEVERITY_TAG.low;
                    const typeLabel = EVENT_TYPE_LABEL[e.event_type] || e.event_type;
                    return {
                      color: sev.color,
                      children: (
                        <div style={{ marginBottom: 4 }}>
                          <div style={{ marginBottom: 2 }}>
                            <Tag color={sev.color} style={{ fontSize: 11, lineHeight: '18px' }}>
                              {typeLabel}
                            </Tag>
                            <Tag style={{ fontSize: 11 }}>{sev.label}</Tag>
                            {e.area_name && (
                              <span style={{ fontSize: 11, color: '#999', marginLeft: 4 }}>{e.area_name}</span>
                            )}
                          </div>
                          <div style={{ fontSize: 13, color: '#333', lineHeight: 1.5, marginBottom: 2 }}>
                            {e.description}
                          </div>
                          <div style={{ fontSize: 11, color: '#999' }}>
                            {e.event_date ? new Date(e.event_date).toLocaleString('zh-CN', {
                              year: 'numeric', month: '2-digit', day: '2-digit',
                            }) : ''}
                            {e.advisory_number ? ` · ${e.advisory_number}` : ''}
                          </div>
                        </div>
                      ),
                    };
                  })}
              />
            )}
          </Card>

          <Card title="评估历史记录">
            <Table
              dataSource={data}
              columns={columns}
              rowKey="date"
              size="small"
              pagination={{ pageSize: 10 }}
            />
          </Card>
        </>
      )}
    </div>
  );
}
