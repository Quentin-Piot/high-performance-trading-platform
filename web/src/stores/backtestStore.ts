import { defineStore } from "pinia";
import {
  BacktestValidationError,
  runBacktest as runBacktestSvc,
  runBacktestUnified as runBacktestUnifiedSvc,
  submitMonteCarloAsync,
  getMonteCarloAsyncStatus,
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
import { connectMonteCarloProgress, type MonteCarloWsMessage, type MonteCarloJobStatus } from "@/services/monteCarloWsService";
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
    results: [] as BacktestResult[],
    aggregatedMetrics: null as AggregatedMetrics | null,
    isMultipleResults: false,
    isMonteCarloResults: false,
    monteCarloResults: [] as MonteCarloResult[],
    metricsDistribution: null as {
      pnl: MetricsDistribution;
      sharpe: MetricsDistribution;
      drawdown: MetricsDistribution;
    } | null,
    equityEnvelope: null as EquityEnvelope | null,
    processingTime: null as string | null,
    mcJobId: null as string | null,
    mcProgress: null as number | null, 
    mcStatus: "idle" as MonteCarloJobStatus | "idle",
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
      this.results = [];
      this.aggregatedMetrics = null;
      this.isMultipleResults = false;
      this.isMonteCarloResults = false;
      this.monteCarloResults = [];
      this.metricsDistribution = null;
      this.equityEnvelope = null;
      this.processingTime = null;
      this.mcJobId = null;
      this.mcProgress = null;
      this.mcStatus = "idle";
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
        this.processingTime = resp.processing_time || null;
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
    async runBacktestUnified(files: File[], req: BacktestRequest, selectedDatasets?: string[]) {
      this.status = "loading";
      this.errorCode = null;
      this.errorMessage = null;
      try {
        const resp: BacktestApiResponse = await runBacktestUnifiedSvc(
          files,
          req,
          selectedDatasets,
        );
        if (isMultipleBacktestResponse(resp)) {
          this.results = resp.results;
          this.aggregatedMetrics = resp.aggregated_metrics;
          this.isMultipleResults = true;
          this.isMonteCarloResults = false;
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
            this.processingTime = firstResult.processing_time || null;
          }
        } else if (isMonteCarloResponse(resp)) {
          this.monteCarloResults = resp.results;
          this.aggregatedMetrics = resp.aggregated_metrics;
          this.isMonteCarloResults = true;
          this.isMultipleResults = false;
          this.processingTime = resp.processing_time || null;
          if (resp.results.length > 0) {
            const firstResult = resp.results[0]!;
            this.metricsDistribution = firstResult.metrics_distribution;
            this.equityEnvelope = firstResult.equity_envelope;
            this.pnl = firstResult.metrics_distribution.pnl.median;
            this.drawdown = firstResult.metrics_distribution.drawdown.median;
            this.sharpe = firstResult.metrics_distribution.sharpe.median;
            this.timestamps = firstResult.equity_envelope.timestamps;
            this.equityCurve = firstResult.equity_envelope.median;
          }
        } else {
          const curve = resp.equity_curve || [];
          const base = curve.length ? curve[0] : 1;
          const normalized = base ? curve.map((v: number) => v / base) : curve;
          this.timestamps = resp.timestamps || [];
          this.equityCurve = normalized;
          this.pnl = resp.pnl;
          this.drawdown = resp.drawdown;
          this.sharpe = resp.sharpe;
          this.processingTime = resp.processing_time || null;
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
    async runMonteCarloAsync(files: File[], req: BacktestRequest, selectedDatasets?: string[]) {
      this.status = "loading";
      this.errorCode = null;
      this.errorMessage = null;
      this.isMultipleResults = false;
      this.isMonteCarloResults = false;
      this.mcProgress = 0;
      this.mcStatus = "submitted";
      this.monteCarloResults = [];
      this.metricsDistribution = null;
      this.equityEnvelope = null;
      try {
        const submission = await submitMonteCarloAsync(files, req, selectedDatasets);
        this.mcJobId = submission.job_id;
        this.mcStatus = submission.status as MonteCarloJobStatus;
        let disconnect: (() => void) | null = null;
        if (this.mcJobId) {
          const conn = connectMonteCarloProgress(this.mcJobId, {
            onUpdate: (msg: MonteCarloWsMessage) => {
              this.mcStatus = msg.status;
              if (typeof msg.progress === "number") {
                this.mcProgress = Math.max(0, Math.min(100, msg.progress * 100));
              }
            },
            onError: () => {
              this.mcStatus = "failed";
            },
            onClose: () => {
            },
          });
          disconnect = conn.disconnect;
        }
        let final: Awaited<ReturnType<typeof getMonteCarloAsyncStatus>> | null = null;
        for (let i = 0; i < 120; i++) { 
          if (!this.mcJobId) break;
          const status = await getMonteCarloAsyncStatus(this.mcJobId);
          this.mcStatus = status.status as MonteCarloJobStatus;
          if (typeof status.progress === "number") {
            this.mcProgress = Math.max(0, Math.min(100, status.progress * 100));
          }
          if (["completed", "failed", "cancelled", "not_found"].includes(status.status)) {
            final = status;
            break;
          }
          await new Promise(res => setTimeout(res, 1000));
        }
        if (disconnect) disconnect();
        if (!final || final.status !== "completed" || !final.result) {
          throw new Error("Monte Carlo job did not complete successfully");
        }
        const raw: any = final.result;
        const isSingleMonteCarloResult = (x: any): boolean => {
          if (!x || typeof x !== "object") return false;
          const md = x.metrics_distribution;
          const env = x.equity_envelope;
          return !!(
            md && env &&
            md.pnl && md.sharpe && md.drawdown &&
            Array.isArray(env.timestamps) && Array.isArray(env.median)
          );
        };
        const toResponse = (x: any): any => {
          const startedAt = (final as any).started_at ? new Date((final as any).started_at) : null;
          const completedAt = (final as any).completed_at ? new Date((final as any).completed_at) : null;
          const processingSeconds = (startedAt && completedAt)
            ? Math.max(0, (completedAt.getTime() - startedAt.getTime()) / 1000)
            : null;
          const processing_time = processingSeconds != null ? `${processingSeconds.toFixed(2)}s` : undefined;
          return {
            results: [
              {
                filename: x.filename ?? "monte_carlo",
                method: x.method ?? "bootstrap",
                runs: x.runs ?? (this.lastRequest?.monte_carlo_runs ?? 0),
                successful_runs: x.successful_runs ?? x.runs ?? 0,
                metrics_distribution: x.metrics_distribution,
                equity_envelope: x.equity_envelope,
                processing_time,
              },
            ],
            aggregated_metrics: {
              average_pnl: x.metrics_distribution?.pnl?.mean ?? 0,
              average_sharpe: x.metrics_distribution?.sharpe?.mean ?? 0,
              average_drawdown: x.metrics_distribution?.drawdown?.mean ?? 0,
              total_files_processed: 1,
            },
            processing_time,
          };
        };
        const resp: any = isMonteCarloResponse(raw)
          ? raw
          : (isSingleMonteCarloResult(raw) ? toResponse(raw) : null);
        if (!resp || !isMonteCarloResponse(resp)) {
          throw new Error("Unexpected result format for Monte Carlo async job");
        }
        this.monteCarloResults = resp.results;
        this.aggregatedMetrics = resp.aggregated_metrics;
        this.isMonteCarloResults = true;
        this.isMultipleResults = false;
        this.processingTime = resp.processing_time || null;
        if (resp.results.length > 0) {
          const firstResult = resp.results[0]!;
          this.metricsDistribution = firstResult.metrics_distribution;
          this.equityEnvelope = firstResult.equity_envelope;
          this.pnl = firstResult.metrics_distribution.pnl.median;
          this.drawdown = firstResult.metrics_distribution.drawdown.median;
          this.sharpe = firstResult.metrics_distribution.sharpe.median;
          this.timestamps = firstResult.equity_envelope.timestamps;
          this.equityCurve = firstResult.equity_envelope.median;
        }
        this.mcProgress = 100;
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