/**
 * P&L Chart Component
 * Time-series chart showing portfolio value over time
 */

'use client';

import { useState, useEffect } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { Card } from '@/components/ui/Card';
import { TIME_RANGES } from '@/lib/constants';
import { formatCurrency, formatDate, formatPercent, getValueColorClass } from '@/utils/format';
import { PnLChartData } from '@/types/api';
import clsx from 'clsx';

interface PnLChartProps {
  initialData?: PnLChartData;
}

export function PnLChart({ initialData }: PnLChartProps) {
  const [data, setData] = useState<PnLChartData | null>(initialData || null);
  const [selectedRange, setSelectedRange] = useState('1Y');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadData(selectedRange);
  }, [selectedRange]);

  const loadData = async (timeRange: string) => {
    setLoading(true);
    try {
      const response = await fetch(`/api/pnl?timeRange=${timeRange}`);
      const result = await response.json();
      if (result.data) {
        setData(result.data);
      }
    } catch (error) {
      console.error('Error loading P&L data:', error);
    } finally {
      setLoading(false);
    }
  };

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const point = payload[0].payload;
      return (
        <div className="bg-white p-4 border border-gray-200 rounded-lg shadow-lg">
          <p className="text-sm text-gray-600 mb-2">{formatDate(point.date)}</p>
          <p className="text-lg font-semibold text-gray-900">
            {formatCurrency(point.value)}
          </p>
          <p className={clsx('text-sm font-medium mt-1', getValueColorClass(point.daily_return))}>
            Daily: {point.daily_return >= 0 ? '+' : ''}
            {formatPercent(point.daily_return, 2)}
          </p>
          <p className={clsx('text-sm font-medium', getValueColorClass(point.cumulative_return))}>
            Total: {point.cumulative_return >= 0 ? '+' : ''}
            {formatPercent(point.cumulative_return, 2)}
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <Card title="Portfolio Performance" subtitle="Track your P&L over time">
      {/* Time Range Selector */}
      <div className="flex gap-2 mb-6 flex-wrap">
        {TIME_RANGES.map((range) => (
          <button
            key={range.value}
            onClick={() => setSelectedRange(range.value)}
            disabled={loading}
            className={clsx(
              'px-4 py-2 rounded-lg text-sm font-medium transition-colors',
              selectedRange === range.value
                ? 'bg-primary-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200',
              loading && 'opacity-50 cursor-not-allowed'
            )}
          >
            {range.label}
          </button>
        ))}
      </div>

      {/* Summary Stats */}
      {data && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div>
            <p className="text-sm text-gray-500">Total Return</p>
            <p className={clsx('text-2xl font-bold', getValueColorClass(data.total_return))}>
              {formatCurrency(data.total_return)}
            </p>
            <p className={clsx('text-sm font-medium', getValueColorClass(data.total_return_pct))}>
              {data.total_return_pct >= 0 ? '+' : ''}
              {formatPercent(data.total_return_pct, 2)}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Max Drawdown</p>
            <p className="text-2xl font-bold text-danger-600">
              {formatPercent(data.max_drawdown, 2)}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Sharpe Ratio</p>
            <p className="text-2xl font-bold text-gray-900">
              {data.sharpe_ratio !== null ? data.sharpe_ratio.toFixed(2) : 'N/A'}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Data Points</p>
            <p className="text-2xl font-bold text-gray-900">{data.data.length}</p>
          </div>
        </div>
      )}

      {/* Chart */}
      <div className="h-96">
        {loading ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-gray-500">Loading...</div>
          </div>
        ) : data && data.data.length > 0 ? (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data.data} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis
                dataKey="date"
                tickFormatter={(value) => formatDate(value, 'MMM d')}
                stroke="#6b7280"
                style={{ fontSize: '12px' }}
              />
              <YAxis
                tickFormatter={(value) => formatCurrency(value, 0)}
                stroke="#6b7280"
                style={{ fontSize: '12px' }}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend />
              <Line
                type="monotone"
                dataKey="value"
                name="Portfolio Value"
                stroke="#0ea5e9"
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 6 }}
              />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex items-center justify-center h-full">
            <div className="text-gray-500">No data available</div>
          </div>
        )}
      </div>
    </Card>
  );
}
