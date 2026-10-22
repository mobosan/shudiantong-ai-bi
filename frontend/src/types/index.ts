export interface User { id: number; username: string; role: 'admin' | 'regional_manager' | 'store_manager'; store_id: number | null; region: string | null }
export interface Column { key: string; label: string; unit: string }
export interface QueryResult {
  answer_text: string; chart_type: 'line' | 'bar' | 'table'; chart_data: Record<string, string | number | null>[];
  columns: Column[]; sql: string; metric_definition: string; data_updated_at: string | null; permission_scope: string;
  warnings: string[]; parser_mode: string; latency_ms: number; truncated: boolean; total_groups: number;
  period: { start: string; end_exclusive: string }; queries: { metric: string; sql: string; parameters: Record<string, unknown> }[];
}
export interface HistoryItem { id: number; question: string; status: string; created_at: string; response: QueryResult | null }
export interface Metric { label: string; synonyms: string[]; expression: string; unit: string; default_aggregation: string; source: string; definition: string }
export interface Catalog { metrics: Record<string, Metric>; dimensions: Record<string, {label: string; synonyms: string[]; field: string}>; examples: {question: string}[] }
export interface Audit { id: number; user_id: number; username: string; question: string; generated_sql: string; status: string; latency_ms: number; created_at: string }
