/**
 * Portfolio Holdings Component
 * Display current holdings with P&L and pending changes
 */

'use client';

import { useEffect, useState } from 'react';
import { Card } from '@/components/ui/Card';
import { ASSET_NAMES } from '@/lib/constants';
import {
  formatCurrency,
  formatQuantity,
  formatPercent,
  formatChange,
  getValueColorClass,
} from '@/utils/format';
import { PortfolioSummary } from '@/types/api';
import clsx from 'clsx';

export function PortfolioHoldings() {
  const [portfolio, setPortfolio] = useState<PortfolioSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadPortfolio();
  }, []);

  const loadPortfolio = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/portfolio');
      const result = await response.json();
      if (result.data) {
        setPortfolio(result.data);
      }
    } catch (error) {
      console.error('Error loading portfolio:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Card title="Portfolio Holdings">
        <div className="text-center text-gray-500 py-8">Loading...</div>
      </Card>
    );
  }

  if (!portfolio || portfolio.positions.length === 0) {
    return (
      <Card title="Portfolio Holdings">
        <div className="text-center text-gray-500 py-8">No positions</div>
      </Card>
    );
  }

  return (
    <Card
      title="Portfolio Holdings"
      subtitle={`Last updated: ${new Date(portfolio.last_updated).toLocaleString()}`}
    >
      {/* Summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6 pb-6 border-b border-gray-200">
        <div>
          <p className="text-sm text-gray-500">Total Value</p>
          <p className="text-2xl font-bold text-gray-900">
            {formatCurrency(portfolio.total_value)}
          </p>
        </div>
        <div>
          <p className="text-sm text-gray-500">Total P&L</p>
          <p className={clsx('text-2xl font-bold', getValueColorClass(portfolio.total_pnl))}>
            {formatCurrency(portfolio.total_pnl)}
          </p>
          <p className={clsx('text-sm font-medium', getValueColorClass(portfolio.total_pnl_pct))}>
            {formatPercent(portfolio.total_pnl_pct, 2)}
          </p>
        </div>
        <div>
          <p className="text-sm text-gray-500">Cash Balance</p>
          <p className="text-2xl font-bold text-gray-900">
            {formatCurrency(portfolio.cash_balance)}
          </p>
        </div>
        <div>
          <p className="text-sm text-gray-500">Positions</p>
          <p className="text-2xl font-bold text-gray-900">{portfolio.positions.length}</p>
        </div>
      </div>

      {/* Holdings Table */}
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead>
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Symbol
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Quantity
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Avg Cost
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Current Price
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Market Value
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                P&L
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Pending
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {portfolio.positions.map((position) => (
              <tr key={position.symbol} className="hover:bg-gray-50">
                <td className="px-4 py-4 whitespace-nowrap">
                  <div className="flex flex-col">
                    <span className="text-sm font-medium text-gray-900">{position.symbol}</span>
                    <span className="text-xs text-gray-500">{ASSET_NAMES[position.symbol]}</span>
                  </div>
                </td>
                <td className="px-4 py-4 whitespace-nowrap text-right text-sm text-gray-900">
                  {formatQuantity(position.quantity)}
                </td>
                <td className="px-4 py-4 whitespace-nowrap text-right text-sm text-gray-900">
                  {formatCurrency(position.avg_cost)}
                </td>
                <td className="px-4 py-4 whitespace-nowrap text-right text-sm text-gray-900">
                  {formatCurrency(position.current_price)}
                </td>
                <td className="px-4 py-4 whitespace-nowrap text-right text-sm font-medium text-gray-900">
                  {formatCurrency(position.market_value)}
                </td>
                <td className="px-4 py-4 whitespace-nowrap text-right">
                  <div className="flex flex-col items-end">
                    <span
                      className={clsx(
                        'text-sm font-medium',
                        getValueColorClass(position.unrealized_pnl)
                      )}
                    >
                      {formatCurrency(position.unrealized_pnl)}
                    </span>
                    <span
                      className={clsx(
                        'text-xs',
                        getValueColorClass(position.unrealized_pnl_pct)
                      )}
                    >
                      {formatPercent(position.unrealized_pnl_pct, 2)}
                    </span>
                  </div>
                </td>
                <td className="px-4 py-4 whitespace-nowrap text-right text-sm">
                  {position.pending_quantity_change !== undefined &&
                  Math.abs(position.pending_quantity_change) > 0.01 ? (
                    <span
                      className={clsx(
                        'font-medium',
                        getValueColorClass(position.pending_quantity_change)
                      )}
                    >
                      {formatChange(position.pending_quantity_change, 2)}
                    </span>
                  ) : (
                    <span className="text-gray-400">-</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
