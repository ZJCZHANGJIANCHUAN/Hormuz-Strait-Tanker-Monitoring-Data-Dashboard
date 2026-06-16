import { useState } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu, Button } from 'antd';
import {
  DashboardOutlined,
  RadarChartOutlined,
  AlertOutlined,
  ReloadOutlined,
} from '@ant-design/icons';

const { Header, Sider, Content } = Layout;

const menuItems = [
  { key: '/', icon: <DashboardOutlined />, label: '总览看板' },
  { key: '/strait', icon: <RadarChartOutlined />, label: '海峡通行量' },
  { key: '/risk', icon: <AlertOutlined />, label: '风险评估' },
];

export default function DashboardLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        theme="dark"
        style={{ background: 'linear-gradient(180deg, #0d1b2a 0%, #1b2838 100%)' }}
      >
        <div style={{
          height: 64,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#fff',
          fontSize: collapsed ? 18 : 16,
          fontWeight: 700,
          letterSpacing: 1,
          borderBottom: '1px solid rgba(255,255,255,0.1)',
        }}>
          {collapsed ? '🛢️' : '🛢️ 海峡监测'}
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
          style={{ background: 'transparent' }}
        />
      </Sider>

      <Layout>
        <Header style={{
          background: 'linear-gradient(135deg, #0d1b2a 0%, #1b2838 50%, #1a3a4a 100%)',
          color: '#fff',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 24px',
          height: 56,
        }}>
          <h1 style={{ fontSize: 18, fontWeight: 600, margin: 0, letterSpacing: 1 }}>
            霍尔木兹海峡油轮监测数据看板
          </h1>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <span style={{ fontSize: 13, opacity: 0.8 }}>
              最后更新: {new Date().toLocaleTimeString('zh-CN')}
            </span>
            <Button
              type="text"
              icon={<ReloadOutlined />}
              style={{ color: '#fff' }}
              onClick={() => window.location.reload()}
            />
          </div>
        </Header>

        <Content style={{ padding: 20, background: '#f0f2f5', minHeight: 'calc(100vh - 56px)', overflow: 'auto' }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
