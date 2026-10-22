import { useEffect, useState } from 'react';
import { Button, Spin, Tag } from 'antd';
import { BarChartOutlined, MessageOutlined, BookOutlined, SafetyCertificateOutlined, LogoutOutlined, ShopOutlined } from '@ant-design/icons';
import { api } from './api/client';
import type { User } from './types';
import Login from './pages/Login';
import Chat from './pages/Chat';
import Metrics from './pages/Metrics';
import AuditPage from './pages/Audit';

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);
  const [page, setPage] = useState('chat');
  useEffect(() => {
    if (sessionStorage.getItem('sdt_token')) api<User>('/auth/me').then(setUser).catch(() => sessionStorage.removeItem('sdt_token')).finally(() => setReady(true)); else setReady(true);
    const expire = () => setUser(null); window.addEventListener('auth-expired', expire); return () => window.removeEventListener('auth-expired', expire);
  }, []);
  if (!ready) return <div className="loading"><Spin size="large" /></div>;
  if (!user) return <Login onLogin={u => { setUser(u); setPage('chat'); }} />;
  const role = {admin:'管理员',regional_manager:'区域经理',store_manager:'店长'}[user.role];
  const scope = user.role === 'admin' ? '全部门店' : user.region || `门店 #${user.store_id}`;
  const nav = [{key:'chat',label:'智能问数',icon:<MessageOutlined />},{key:'metrics',label:'指标说明',icon:<BookOutlined />},...(user.role === 'admin' ? [{key:'audit',label:'查询审计',icon:<SafetyCertificateOutlined />}] : [])];
  return <div className="app-shell">
    <aside className="sidebar"><div className="brand"><span className="brand-mark"><BarChartOutlined /></span><div>数店通<small>SHUDIANTONG AI</small></div></div><div className="workspace-label">零售经营工作台</div>
      <nav>{nav.map(n => <button key={n.key} className={page === n.key ? 'nav-item active' : 'nav-item'} onClick={() => setPage(n.key)}>{n.icon}<span>{n.label}</span>{page === n.key && <span className="nav-dot" />}</button>)}</nav>
      <div className="sidebar-note"><ShopOutlined /><strong>让每一份数据<br/>成为经营的答案。</strong><span>7 个核心指标 · 7 个分析维度</span></div>
      <div className="profile"><div className="avatar">{role[0]}</div><div><strong>{user.username}</strong><small>{role} · {scope}</small></div><Button type="text" aria-label="退出登录" icon={<LogoutOutlined />} onClick={() => {sessionStorage.removeItem('sdt_token'); setUser(null);}} /></div>
    </aside>
    <section className="workspace"><header className="topbar"><span>工作空间 <span className="slash">/</span> <strong>{nav.find(n => n.key === page)?.label}</strong></span><div><Tag bordered={false} color="green">演示数据</Tag><span className="scope"><SafetyCertificateOutlined /> {scope}</span><Button className="mobile-logout" type="text" size="small" aria-label="移动端退出登录" icon={<LogoutOutlined />} onClick={() => {sessionStorage.removeItem('sdt_token');setUser(null);}} /></div></header>
      <main>{page === 'chat' ? <Chat user={user} /> : page === 'metrics' ? <Metrics /> : <AuditPage />}</main>
    </section>
  </div>;
}
