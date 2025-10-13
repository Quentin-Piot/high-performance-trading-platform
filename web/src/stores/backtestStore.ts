import { defineStore } from "pinia";
import {
  BacktestValidationError,
  runBacktest as runBacktestSvc,
  runBacktestUnified as runBacktestUnifiedSvc,
  isMultipleBacktestResponse,
  isMonteCarloResponse,
  type BacktestRequest,
  type BacktestResponse,
  type BacktestApiResponse,
  type BacktestResult,
  type AggregatedMetrics,
  type MonteCarloResult,
  type MetricsDistribution,
  type EquityEnvelope,
} from "@/services/backtestService";
import { useErrorStore } from "@/stores/errorStore";
import { buildEquityPoints, toLineData } from "@/composables/useEquitySeries";

export type BacktestStatus = "idle" | "loading" | "success" | "error";

export const useBacktestStore = defineStore("backtest", {
  state: () => ({
    status: "idle" as BacktestStatus,
    timestamps: [] as string[],
    equityCurve: [] as number[],
    pnl: null as number | null,
    drawdown: null as number | null,
    sharpe: null as number | null,
    errorCode: null as string | null,
    errorMessage: null as string | null,
    lastFile: null as File | null,
    lastFiles: [] as File[],
    lastRequest: null as BacktestRequest | null,
    // Multiple backtest results
    results: [] as BacktestResult[],
    aggregatedMetrics: null as AggregatedMetrics | null,
    isMultipleResults: false,
    // Monte Carlo specific state
    isMonteCarloResults: false,
    monteCarloResults: [] as MonteCarloResult[],
    metricsDistribution: null as {
      pnl: MetricsDistribution;
      sharpe: MetricsDistribution;
      drawdown: MetricsDistribution;
    } | null,
    equityEnvelope: null as EquityEnvelope | null,
  }),
  getters: {
    equitySeries(state) {
      const points = buildEquityPoints(state.timestamps, state.equityCurve);
      return toLineData(points);
    },
  },
  actions: {
    reset() {
      this.status = "idle";
      this.timestamps = [];
      this.equityCurve = [];
      this.pnl = null;
      this.drawdown = null;
      this.sharpe = null;
      this.errorCode = null;
      this.errorMessage = null;
      this.lastFile = null;
      this.lastFiles = [];
      this.lastRequest = null;
      this.results = [];
      this.aggregatedMetrics = null;
      this.isMultipleResults = false;
      // Reset Monte Carlo state
      this.isMonteCarloResults = false;
      this.monteCarloResults = [];
      this.metricsDistribution = null;
      this.equityEnvelope = null;
    },
    async runBacktest(file: File, req: BacktestRequest) {
      this.status = "loading";
      this.errorCode = null;
      this.errorMessage = null;
      try {
        const resp: BacktestResponse = await runBacktestSvc(file, req);

        const curve = resp.equity_curve || [];
        const base = curve.length ? curve[0] : 1;
        const normalized = base ? curve.map((v) => v / base) : curve;

        this.timestamps = resp.timestamps || [];
        this.equityCurve = normalized;
        this.pnl = resp.pnl;
        this.drawdown = resp.drawdown;
        this.sharpe = resp.sharpe;
        this.lastFile = file;
        this.lastRequest = req;
        this.status = "success";
      } catch (e: unknown) {
        const msg = e instanceof Error ? e.message : String(e);
        let code: string = "error.backtest_failed";
        if (e instanceof BacktestValidationError) {
          code = e.code;
        }
        this.errorCode = code;
        this.errorMessage = msg;
        useErrorStore().log(code, msg, req);
        this.status = "error";
      }
    },
    async runBacktestUnified(files: File[], req: BacktestRequest) {
      this.status = "loading";
      this.errorCode = null;
      this.errorMessage = null;
      try {
        const resp: BacktestApiResponse = await runBacktestUnifiedSvc(
          files,
          req,
        );

        if (isMultipleBacktestResponse(resp)) {
          // Handle multiple results
          this.results = resp.results;
          this.aggregatedMetrics = resp.aggregated_metrics;
          this.isMultipleResults = true;
          this.isMonteCarloResults = false;

          // For backward compatibility, set the first result as the main result
          if (resp.results.length > 0) {
            const firstResult = resp.results[0]!;
            const curve = firstResult.equity_curve || [];
            const base = curve.length ? curve[0] : 1;
            const normalized = base
              ? curve.map((v: number) => v / base)
              : curve;

            this.timestamps = firstResult.timestamps || [];
            this.equityCurve = normalized;
            this.pnl = firstResult.pnl;
            this.drawdown = firstResult.drawdown;
            this.sharpe = firstResult.sharpe;
          }
        } else if (isMonteCarloResponse(resp)) {
          // Handle Monte Carlo results
          this.monteCarloResults = resp.results;
          this.aggregatedMetrics = resp.aggregated_metrics;
          this.isMonteCarloResults = true;
          this.isMultipleResults = false;

          // Set distribution data from first result
          if (resp.results.length > 0) {
            const firstResult = resp.results[0]!;
            this.metricsDistribution = firstResult.metrics_distribution;
            this.equityEnvelope = firstResult.equity_envelope;

            // Set median values as main metrics for display
            this.pnl = firstResult.metrics_distribution.pnl.median;
            this.drawdown = firstResult.metrics_distribution.drawdown.median;
            this.sharpe = firstResult.metrics_distribution.sharpe.median;

            // Use median equity curve for main display
            this.timestamps = firstResult.equity_envelope.timestamps;
            this.equityCurve = firstResult.equity_envelope.median;
          }
        } else {
          // Handle single result (backward compatible)
          const curve = resp.equity_curve || [];
          const base = curve.length ? curve[0] : 1;
          const normalized = base ? curve.map((v: number) => v / base) : curve;

          this.timestamps = resp.timestamps || [];
          this.equityCurve = normalized;
          this.pnl = resp.pnl;
          this.drawdown = resp.drawdown;
          this.sharpe = resp.sharpe;
          this.isMultipleResults = false;
          this.isMonteCarloResults = false;
          this.results = [];
          this.aggregatedMetrics = null;
        }

        this.lastFiles = files;
        this.lastFile = files.length === 1 ? files[0] || null : null;
        this.lastRequest = req;
        this.status = "success";
      } catch (e: unknown) {
        const msg = e instanceof Error ? e.message : String(e);
        let code: string = "error.backtest_failed";
        if (e instanceof BacktestValidationError) {
          code = e.code;
        }
        this.errorCode = code;
        this.errorMessage = msg;
        useErrorStore().log(code, msg, req);
        this.status = "error";
      }
    },
    async retryLast() {
      if (this.lastRequest) {
        if (this.lastFiles.length > 1) {
          await this.runBacktestUnified(this.lastFiles, this.lastRequest);
        } else if (this.lastFile) {
          await this.runBacktest(this.lastFile, this.lastRequest);
        }
      }
    },
  },
});
