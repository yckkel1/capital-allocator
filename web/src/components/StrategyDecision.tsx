/**
 * Strategy Decision Component
 * Display yesterday's (D-1) strategy decision and today's execution
 */

'use client';

import { useEffect, useState } from 'react';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { StrategyDecision as StrategyDecisionType } from '@/types/api';
import { ActionType } from '@/types/models';
import { formatCurrency, formatDate, formatConfidence, formatQuantity } from '@/utils/format';
import { ACTION_COLORS, REGIME_COLORS, RISK_COLORS, ASSET_NAMES } from '@/lib/constants';
import clsx from 'clsx';

export function StrategyDecision() {
  const [decision, setDecision] = useState<StrategyDecisionType | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDecision();
  }, []);

  const loadDecision = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/signals/yesterday');
      const result = await response.json();
      if (result.data) {
        setDecision(result.data);
      }
    } catch (error) {
      console.error('Error loading strategy decision:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Card title="Yesterday's Strategy Decision (D-1)">
        <div className="text-center text-gray-500 py-8">Loading...</div>
      </Card>
    );
  }

  if (!decision) {
    return (
      <Card title="Yesterday's Strategy Decision (D-1)">
        <div className="text-center text-gray-500 py-8">No decision available</div>
      </Card>
    );
  }

  const { signal, trades, is_executed } = decision;
  const allocations = signal.allocations;

  return (
    <Card
      title="Yesterday's Strategy Decision (D-1)"
      subtitle={`Generated on ${formatDate(signal.trade_date)} at ${new Date(signal.generated_at).toLocaleTimeString()}`}
    >
      {/* Action & Status */}
      <div className="flex items-center justify-between mb-6 pb-6 border-b border-gray-200">
        <div className="flex items-center gap-4">
          <div>
            <p className="text-sm text-gray-500 mb-1">Action</p>
            <Badge variant={allocations.action === ActionType.BUY ? 'success' : allocations.action === ActionType.SELL ? 'danger' : 'neutral'} size="lg">
              {allocations.action}
            </Badge>
          </div>
          <div>
            <p className="text-sm text-gray-500 mb-1">Confidence</p>
            <p className="text-2xl font-bold text-gray-900">
              {formatConfidence(signal.confidence_score)}
            </p>
          </div>
        </div>
        <div>
          <Badge variant={is_executed ? 'success' : 'warning'}>
            {is_executed ? 'Executed Today' : 'Pending Execution'}
          </Badge>
        </div>
      </div>

      {/* Market Analysis */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-6">
        <div className="bg-gray-50 rounded-lg p-4">
          <p className="text-sm text-gray-500 mb-1">Market Regime</p>
          <p className={clsx('text-lg font-semibold capitalize', REGIME_COLORS[allocations.regime])}>
            {allocations.regime}
          </p>
          <p className="text-sm text-gray-600 mt-1">
            Score: {allocations.regime_score.toFixed(2)}
          </p>
        </div>
        <div className="bg-gray-50 rounded-lg p-4">
          <p className="text-sm text-gray-500 mb-1">Risk Level</p>
          <p className={clsx('text-lg font-semibold capitalize', RISK_COLORS[allocations.risk_level])}>
            {allocations.risk_level}
          </p>
          <p className="text-sm text-gray-600 mt-1">
            Score: {allocations.risk_score.toFixed(0)}
          </p>
        </div>
        <div className="bg-gray-50 rounded-lg p-4">
          <p className="text-sm text-gray-500 mb-1">Circuit Breaker</p>
          <Badge variant={allocations.circuit_breaker_active ? 'danger' : 'success'}>
            {allocations.circuit_breaker_active ? 'ACTIVE' : 'Inactive'}
          </Badge>
        </div>
      </div>

      {/* Planned Allocations */}
      {allocations.action !== ActionType.HOLD && Object.keys(allocations.assets).length > 0 && (
        <div className="mb-6">
          <h4 className="text-md font-medium text-gray-900 mb-4">
            {allocations.action === ActionType.BUY ? 'Planned Purchases' : 'Planned Sales'}
          </h4>
          <div className="space-y-3">
            {Object.entries(allocations.assets).map(([symbol, data]) => (
              <div key={symbol} className="flex items-center justify-between bg-gray-50 rounded-lg p-4">
                <div className="flex items-center gap-4">
                  <div>
                    <p className="text-lg font-semibold text-gray-900">{symbol}</p>
                    <p className="text-sm text-gray-500">{ASSET_NAMES[symbol]}</p>
                  </div>
                  <div className="text-sm text-gray-600">
                    Score: {data.score.toFixed(2)}
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-lg font-bold text-gray-900">
                    {formatCurrency(data.allocation)}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Executed Trades */}
      {is_executed && trades.length > 0 && (
        <div className="pt-6 border-t border-gray-200">
          <h4 className="text-md font-medium text-gray-900 mb-4">
            Executed Trades (Today)
          </h4>
          <div className="space-y-2">
            {trades.map((trade) => (
              <div key={trade.id} className="flex items-center justify-between bg-green-50 rounded-lg p-3">
                <div className="flex items-center gap-4">
                  <Badge variant={trade.action === ActionType.BUY ? 'success' : 'danger'} size="sm">
                    {trade.action}
                  </Badge>
                  <div>
                    <p className="text-sm font-semibold text-gray-900">{trade.symbol}</p>
                    <p className="text-xs text-gray-500">
                      {formatQuantity(trade.quantity)} shares @ {formatCurrency(trade.price)}
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-sm font-bold text-gray-900">
                    {formatCurrency(trade.amount)}
                  </p>
                  <p className="text-xs text-gray-500">
                    {new Date(trade.executed_at).toLocaleTimeString()}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </Card>
  );
}
