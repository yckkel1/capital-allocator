/**
 * Main Dashboard Page
 * Single-page dashboard showing all trading information
 */

import { PnLChart } from '@/components/PnLChart';
import { PortfolioHoldings } from '@/components/PortfolioHoldings';
import { StrategyDecision } from '@/components/StrategyDecision';
import { TradingConfig } from '@/components/TradingConfig';
import { TradesTable } from '@/components/TradesTable';

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      {/* Top Section: P&L Chart */}
      <section>
        <PnLChart />
      </section>

      {/* Middle Section: Portfolio & Strategy Decision */}
      <section className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <PortfolioHoldings />
        <StrategyDecision />
      </section>

      {/* Bottom Section: Trading Config & Trade History */}
      <section className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <TradingConfig />
        <TradesTable />
      </section>
    </div>
  );
}
