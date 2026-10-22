import { useEffect, useRef, useState } from 'react';
import { Alert, Collapse, Empty, Segmented, Table, Tag } from 'antd';
import { CheckCircleFilled, BarChartOutlined } from '@ant-design/icons';
import * as echarts from 'echarts/core';
import { BarChart, LineChart } from 'echarts/charts';
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import type { QueryResult } from '../types';
echarts.use([BarChart, LineChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer]);

function Chart({result}:{result:QueryResult}) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(()=>{
    const chart = echarts.init(ref.current!);
    const cols = result.columns.filter(c=>c.key!=='dimension' && !c.key.endsWith('_change_pct') && c.key!=='stock_days');
    const units = [...new Set(cols.map(c=>c.unit))];
    chart.setOption({color:['#26745e','#a1b96d','#e2ad64','#718eac','#b8b1ce'],tooltip:{trigger:'axis',renderMode:'richText'},legend:{bottom:0,textStyle:{color:'#63716b'}},grid:{left:60,right:units.length>1?65:25,top:45,bottom:85},xAxis:{type:'category',data:result.chart_data.map(r=>r.dimension),axisLabel:{color:'#6d7d75',rotate:result.chart_data.length>7?30:0},axisLine:{lineStyle:{color:'#e4e9e5'}},axisTick:{show:false}},yAxis:units.map((unit,index)=>({type:'value',name:unit,position:index===0?'left':'right',offset:index>1?(index-1)*50:0,splitLine:{lineStyle:{color:'#edf0ed',type:'dashed'}},axisLabel:{color:'#78877f'}})),series:cols.map(col=>({name:col.label,type:result.chart_type==='line'?'line':'bar',yAxisIndex:units.indexOf(col.unit),data:result.chart_data.map(row=>row[col.key] ?? null),barMaxWidth:44,itemStyle:{borderRadius:[5,5,0,0]},smooth:false}))});
    const observer = new ResizeObserver(()=>chart.resize());observer.observe(ref.current!);return ()=>{observer.disconnect();chart.dispose();};
  },[result]);
  return <div ref={ref} className="result-chart" role="img" aria-label="查询结果图表；可切换数据表查看精确值" />;
}

export default function ResultCard({result}:{result:QueryResult}) {
  const [view,setView] = useState('图表');
  return <div className="result-card"><div className="result-heading"><span className="answer-avatar"><BarChartOutlined /></span><strong>数店通</strong><Tag bordered={false}>{result.parser_mode==='llm'?'AI 意图解析':result.parser_mode==='rules_fallback'?'规则回退':'本地规则解析'}</Tag><span className="result-time">{result.latency_ms} ms</span></div>
    <div className="answer"><CheckCircleFilled /><p>{result.answer_text}</p></div>{result.warnings.map(w=><Alert key={w} type="warning" message={w} showIcon className="result-warning" />)}
    <div className="chart-toolbar"><span>{result.period.start} — {result.period.end_exclusive} <small>（结束日不含）</small></span>{result.chart_type!=='table' && <Segmented size="small" options={['图表','数据表']} value={view} onChange={v=>setView(String(v))} />}</div>
    {!result.chart_data.length ? <Empty description="没有匹配的数据" /> : view==='图表' && result.chart_type!=='table' ? <Chart result={result} /> : <Table size="small" rowKey="dimension" scroll={{x:'max-content'}} pagination={{pageSize:10,hideOnSinglePage:true}} dataSource={result.chart_data} columns={result.columns.map(c=>({key:c.key,title:c.label+(c.unit?` (${c.unit})`:''),dataIndex:c.key,render:v=>v===null || v===undefined?'—':typeof v==='number'?v.toLocaleString('zh-CN',{maximumFractionDigits:2}):v}))} />}
    {result.truncated && <p className="muted">共 {result.total_groups} 组，本次展示前 {result.chart_data.length} 组。</p>}
    <Collapse ghost size="small" items={[{key:'definition',label:'指标口径与查询说明',children:<div className="definition">{result.metric_definition}</div>},{key:'sql',label:'查看只读 SQL 与参数',children:result.queries.map((q,i)=><div key={i}><Tag>{q.metric}</Tag><pre>{q.sql}</pre><pre>{JSON.stringify(q.parameters,null,2)}</pre></div>)}]} />
    <div className="result-footer"><span>数据截至 {result.data_updated_at || '暂无数据'} · Asia/Shanghai</span><span>权限范围：{result.permission_scope}</span></div>
  </div>;
}
