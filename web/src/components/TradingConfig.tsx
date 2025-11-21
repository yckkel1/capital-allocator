/**
 * Trading Config Component
 * Display current and previous trading configurations with changes
 */

'use client';

import { useEffect, useState } from 'react';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { ConfigComparison } from '@/types/api';
import { formatDate, formatPercent, getValueColorClass } from '@/utils/format';
import clsx from 'clsx';

export function TradingConfig() {
  const [config, setConfig] = useState<ConfigComparison | null>(null);
  const [showAll, setShowAll] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/config');
      const result = await response.json();
      if (result.data) {
        setConfig(result.data);
      }
    } catch (error) {
      console.error('Error loading config:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Card title="Trading Configuration">
        <div className="text-center text-gray-500 py-8">Loading...</div>
      </Card>
    );
  }

  if (!config) {
    return (
      <Card title="Trading Configuration">
        <div className="text-center text-gray-500 py-8">No configuration found</div>
      </Card>
    );
  }

  const keyParams = [
    { key: 'daily_capital', label: 'Daily Capital', format: (v: number) => `$${v}` },
    { key: 'regime_bullish_threshold', label: 'Bullish Threshold', format: (v: number) => v },
    { key: 'regime_bearish_threshold', label: 'Bearish Threshold', format: (v: number) => v },
    { key: 'allocation_low_risk', label: 'Low Risk Allocation', format: (v: number) => formatPercent(v * 100, 0) },
    { key: 'allocation_medium_risk', label: 'Medium Risk Allocation', format: (v: number) => formatPercent(v * 100, 0) },
    { key: 'allocation_high_risk', label: 'High Risk Allocation', format: (v: number) => formatPercent(v * 100, 0) },
    { key: 'min_confidence_threshold', label: 'Min Confidence', format: (v: number) => formatPercent(v * 100, 0) },
    { key: 'circuit_breaker_reduction', label: 'Circuit Breaker', format: (v: number) => formatPercent(v * 100, 0) },
  ];

  const allParams = Object.keys(config.current)
    .filter(key => !['id', 'start_date', 'end_date', 'created_at', 'created_by', 'notes', 'assets'].includes(key))
    .map(key => ({
      key,
      label: key.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' '),
      format: (v: any) => typeof v === 'number' ? (v < 1 && v > 0 ? formatPercent(v * 100, 1) : v.toString()) : v,
    }));

  const displayParams = showAll ? allParams : keyParams;

  return (
    <Card title="Trading Configuration">
      {/* Active Config Info */}
      <div className="mb-6 pb-6 border-b border-gray-200">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-medium text-gray-900">Current Configuration</h3>
            <p className="text-sm text-gray-500">
              Active since {formatDate(config.current.start_date)}
            </p>
          </div>
          {config.previous && (
            <Badge variant="info">
              {config.changes.length} {config.changes.length === 1 ? 'change' : 'changes'} from previous
            </Badge>
          )}
        </div>

        {/* Assets */}
        <div className="mb-4">
          <p className="text-sm font-medium text-gray-700 mb-2">Trading Assets</p>
          <div className="flex gap-2">
            {config.current.assets.map((asset) => (
              <Badge key={asset} variant="neutral">
                {asset}
              </Badge>
            ))}
          </div>
        </div>
      </div>

      {/* Parameters Comparison */}
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <h4 className="text-md font-medium text-gray-900">Parameters</h4>
          <button
            onClick={() => setShowAll(!showAll)}
            className="text-sm text-primary-600 hover:text-primary-700 font-medium"
          >
            {showAll ? 'Show Key Parameters' : 'Show All Parameters'}
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {displayParams.map((param) => {
            const currentValue = config.current[param.key as keyof typeof config.current];
            const previousValue = config.previous?.[param.key as keyof typeof config.previous];
            const change = config.changes.find(c => c.field === param.key);

            return (
              <div key={param.key} className="bg-gray-50 rounded-lg p-4">
                <div className="flex justify-between items-start mb-2">
                  <p className="text-sm font-medium text-gray-700">{param.label}</p>
                  {change && (
                    <Badge
                      variant={change.change_pct && Math.abs(change.change_pct) > 10 ? 'warning' : 'info'}
                      size="sm"
                    >
                      {change.change_pct !== undefined
                        ? `${change.change_pct >= 0 ? '+' : ''}${change.change_pct.toFixed(1)}%`
                        : 'Changed'}
                    </Badge>
                  )}
                </div>
                <p className="text-lg font-semibold text-gray-900">
                  {param.format(currentValue)}
                </p>
                {previousValue !== undefined && previousValue !== currentValue && (
                  <p className="text-sm text-gray-500 mt-1">
                    Previous: {param.format(previousValue)}
                  </p>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Previous Config */}
      {config.previous && (
        <div className="mt-6 pt-6 border-t border-gray-200">
          <h4 className="text-md font-medium text-gray-700 mb-2">Previous Configuration</h4>
          <p className="text-sm text-gray-500">
            Active from {formatDate(config.previous.start_date)} to{' '}
            {config.previous.end_date ? formatDate(config.previous.end_date) : 'present'}
          </p>
          {config.previous.notes && (
            <p className="text-sm text-gray-600 mt-2 italic">{config.previous.notes}</p>
          )}
        </div>
      )}
    </Card>
  );
}
