import React from 'react';
import ReactDOM from 'react-dom/client';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import App from './App';
import './styles.css';

ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><ConfigProvider locale={zhCN} theme={{token:{colorPrimary:'#206a57',borderRadius:10,fontFamily:'Inter, "Microsoft YaHei", sans-serif',colorText:'#243b36',colorBgLayout:'#f5f7f5'}}}><App /></ConfigProvider></React.StrictMode>);
