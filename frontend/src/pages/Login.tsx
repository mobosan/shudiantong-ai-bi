import { useState } from 'react';
import { Alert, Button, Form, Input, Tag } from 'antd';
import { BarChartOutlined, ArrowRightOutlined, SafetyCertificateOutlined } from '@ant-design/icons';
import { api } from '../api/client';
import type { User } from '../types';

export default function Login({onLogin}:{onLogin:(user:User)=>void}) {
  const [busy,setBusy] = useState(false); const [error,setError] = useState(''); const [form] = Form.useForm();
  async function submit(values:{username:string;password:string}) {setBusy(true);setError('');try {const result = await api<{access_token:string;user:User}>('/auth/login',{method:'POST',body:JSON.stringify(values)});sessionStorage.setItem('sdt_token',result.access_token);onLogin(result.user);}catch(e){setError((e as Error).message);}finally{setBusy(false);}}
  return <div className="login-page"><div className="login-story"><div className="brand"><span className="brand-mark"><BarChartOutlined /></span><div>数店通<small>SHUDIANTONG AI</small></div></div><div><Tag color="#d5e9c3">连锁零售 · 经营智能</Tag><h1>好问题，<br/>让经营有答案。</h1><p>从一句中文，到一张清晰的经营图表。<br/>连接门店、商品与会员，把时间留给决策。</p><div className="story-stats"><div><b>7</b><span>核心经营指标</span></div><div><b>6</b><span>示例门店</span></div><div><b>90</b><span>天经营数据</span></div></div></div><span className="login-foot">用数据看见生意的每一种可能</span></div>
    <div className="login-panel"><div className="login-form"><span className="eyebrow">WELCOME TO YOUR WORKSPACE</span><h2>登录经营工作台</h2><p className="muted">选择你的角色，开始第一次经营对话。</p>{error && <Alert showIcon type="error" message={error} />}
      <Form form={form} layout="vertical" onFinish={submit} initialValues={{username:'admin',password:'Demo123!'}}><Form.Item label="账号" name="username" rules={[{required:true,message:'请输入账号'}]}><Input size="large" autoComplete="username" /></Form.Item><Form.Item label="密码" name="password" rules={[{required:true,message:'请输入密码'}]}><Input.Password size="large" autoComplete="current-password" /></Form.Item><Button htmlType="submit" type="primary" size="large" block loading={busy}>进入工作台 <ArrowRightOutlined /></Button></Form>
      <div className="demo-accounts"><span>快速填入演示账号</span><div>{[['admin','管理员'],['east_manager','华东经理'],['store1','上海店长']].map(([name,label])=><Button key={name} size="small" onClick={()=>form.setFieldsValue({username:name,password:'Demo123!'})}>{label}</Button>)}</div><small>默认演示密码 Demo123! · 若初始化时修改密码，请手动输入</small></div><p className="secure-note"><SafetyCertificateOutlined /> 查询范围由你的角色自动限定</p></div></div></div>;
}
