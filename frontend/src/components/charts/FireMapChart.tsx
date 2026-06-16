import { useEffect, useState, useRef } from 'react';
import { fetchFireData } from '@/services/api';
import type { FireDataPoint } from '@/types';

export default function FireMapChart() {
  const [fireData, setFireData] = useState<FireDataPoint[]>([]);
  const [mapReady, setMapReady] = useState(false);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  useEffect(() => {
    fetchFireData(3).then(setFireData).catch(() => {});
  }, []);

  // Listen for map-ready from iframe
  useEffect(() => {
    const handler = (e: MessageEvent) => {
      if (e.data?.type === 'map-ready') setMapReady(true);
    };
    window.addEventListener('message', handler);
    return () => window.removeEventListener('message', handler);
  }, []);

  // Send fire data once map is ready AND data is loaded
  useEffect(() => {
    if (!mapReady || !fireData.length || !iframeRef.current) return;
    iframeRef.current.contentWindow?.postMessage(
      { type: 'fire-data', data: fireData },
      '*'
    );
  }, [mapReady, fireData]);

  const highConf = fireData.filter(f => f.confidence === 'high');
  const otherConf = fireData.filter(f => f.confidence !== 'high');

  return (
    <div style={{ position: 'relative' }}>
      <iframe
        ref={iframeRef}
        src="/fire-map.html"
        style={{ width: '100%', height: 440, border: 'none', borderRadius: 6 }}
        title="波斯湾火点地图"
      />
      <div style={{
        position: 'absolute', top: 8, right: 16, zIndex: 1,
        background: 'rgba(255,255,255,0.9)', padding: '6px 10px',
        borderRadius: 4, fontSize: 11, color: '#666',
        pointerEvents: 'none',
      }}>
        波斯湾 · {fireData.length} 火点 · {FACILITIES.length} 设施
      </div>
    </div>
  );
}

const FACILITIES = [
  { name: 'Kharg Island', coords: [29.25, 50.30], country: '伊朗' },
  { name: 'Ras Tanura', coords: [26.70, 50.15], country: '沙特' },
  { name: 'Fujairah', coords: [25.12, 56.33], country: '阿联酋' },
  { name: 'Das Island', coords: [25.15, 52.87], country: '阿联酋' },
  { name: 'Ras Laffan', coords: [25.91, 51.58], country: '卡塔尔' },
  { name: 'Ruwais', coords: [24.12, 52.73], country: '阿联酋' },
  { name: 'Jubail', coords: [27.01, 49.66], country: '沙特' },
  { name: 'Mina al-Ahmadi', coords: [29.08, 48.17], country: '科威特' },
  { name: 'Asaluyeh', coords: [27.48, 52.61], country: '伊朗' },
  { name: 'Basrah Terminal', coords: [29.67, 48.83], country: '伊拉克' },
];
