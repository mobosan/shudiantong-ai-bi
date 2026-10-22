import { useEffect,useState } from 'react';
import { Alert, Card, Input, Spin, Tag } from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import { api } from '../api/client';
import type { Catalog } from '../types';

export default function Metrics(){const [catalog,setCatalog]=useState<Catalog>();const [search,setSearch]=useState('');const [error,setError]=useState('');useEffect(()=>{api<Catalog>('/metadata/metrics').then(setCatalog).catch(e=>setError(e.message));},[]);
return <div className="content-page"><div className="page-heading"><div><span className="eyebrow">METRIC DICTIONARY</span><h1>统一口径，读懂每个数字。</h1><p>问数使用的业务语义定义，和计算过程一起公开。</p></div></div>{error?<Alert type="error" message={error}/>:!catalog?<Spin/>:<><Input prefix={<SearchOutlined/>} placeholder="搜索指标或同义词" value={search} onChange={e=>setSearch(e.target.value)} allowClear className="metric-search"/><div className="metric-grid">{Object.entries(catalog.metrics).filter(([key,m])=>(key+m.label+m.synonyms.join('')).toLowerCase().includes(search.toLowerCase())).map(([key,m])=><Card key={key} title={m.label} extra={<Tag color="green">{m.unit}</Tag>}><p>{m.definition}</p><div className="synonyms">{m.synonyms.map(s=><Tag key={s}>{s}</Tag>)}</div><pre>{m.expression}</pre><span className="muted">{key} · {m.default_aggregation}</span></Card>)}</div><h2 className="dimension-title">支持的分析维度</h2><div className="dimension-list">{Object.entries(catalog.dimensions).map(([key,d])=><div key={key}><strong>{d.label}</strong><span>{d.synonyms.join(' / ')}</span><code>{d.field}</code></div>)}</div></>}</div>;
}
