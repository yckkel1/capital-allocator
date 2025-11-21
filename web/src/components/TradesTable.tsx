/**
 * Trades Table Component
 * Display historical trades with filtering
 */

'use client';

import { useEffect, useState } from 'react';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Trade, ActionType } from '@/types/models';
import { formatCurrency, formatQuantity, formatDateTime } from '@/utils/format';
import { ASSET_NAMES } from '@/lib/constants';
import clsx from 'clsx';

const TIME_FILTERS = [
  { label: '1 Week', days: 7 },
  { label: '2 Weeks', days: 14 },
  { label: '1 Month', days: 30 },
  { label: '3 Months', days: 90 },
];

export function TradesTable() {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedDays, setSelectedDays] = useState(14); // Default: 2 weeks

  useEffect(() => {
    loadTrades(selectedDays);
  }, [selectedDays]);

  const loadTrades = async (days: number) => {
    setLoading(true);
    try {
      const response = await fetch(`/api/trades?days=${days}`);
      const result = await response.json();
      if (result.data) {
        setTrades(result.data.trades);
      }
    } catch (error) {
      console.error('Error loading trades:', error);
    } finally {
      setLoading(false);
    }
  };

  const getActionVariant = (action: ActionType) => {
    switch (action) {
      case ActionType.BUY:
        return 'success';
      case ActionType.SELL:
        return 'danger';
      default:
        return 'neutral';
    }
  };

  return (
    <Card title="Trade History" subtitle="View past trade executions">
      {/* Time Filter */}
      <div className="flex gap-2 mb-6 flex-wrap">
        {TIME_FILTERS.map((filter) => (
          <button
            key={filter.days}
            onClick={() => setSelectedDays(filter.days)}
            disabled={loading}
            className={clsx(
              'px-4 py-2 rounded-lg text-sm font-medium transition-colors',
              selectedDays === filter.days
                ? 'bg-primary-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200',
              loading && 'opacity-50 cursor-not-allowed'
            )}
          >
            {filter.label}
          </button>
        ))}
      </div>

      {/* Table */}
      {loading ? (
        <div className="text-center text-gray-500 py-8">Loading...</div>
      ) : trades.length === 0 ? (
        <div className="text-center text-gray-500 py-8">No trades found</div>
      ) : (
        <>
          <div className="mb-4 text-sm text-gray-600">
            Showing {trades.length} {trades.length === 1 ? 'trade' : 'trades'}
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead>
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Date/Time
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Action
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Symbol
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Quantity
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Price
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Total Amount
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {trades.map((trade) => (
                  <tr key={trade.id} className="hover:bg-gray-50">
                    <td className="px-4 py-4 whitespace-nowrap">
                      <div className="flex flex-col">
                        <span className="text-sm text-gray-900">
                          {formatDateTime(trade.executed_at, 'MMM d, yyyy')}
                        </span>
                        <span className="text-xs text-gray-500">
                          {formatDateTime(trade.executed_at, 'h:mm a')}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-4 whitespace-nowrap">
                      <Badge variant={getActionVariant(trade.action)} size="sm">
                        {trade.action}
                      </Badge>
                    </td>
                    <td className="px-4 py-4 whitespace-nowrap">
                      <div className="flex flex-col">
                        <span className="text-sm font-medium text-gray-900">{trade.symbol}</span>
                        <span className="text-xs text-gray-500">{ASSET_NAMES[trade.symbol]}</span>
                      </div>
                    </td>
                    <td className="px-4 py-4 whitespace-nowrap text-right text-sm text-gray-900">
                      {formatQuantity(trade.quantity)}
                    </td>
                    <td className="px-4 py-4 whitespace-nowrap text-right text-sm text-gray-900">
                      {formatCurrency(trade.price)}
                    </td>
                    <td className="px-4 py-4 whitespace-nowrap text-right text-sm font-medium text-gray-900">
                      {formatCurrency(trade.amount)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </Card>
  );
}
