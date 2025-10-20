import { ref, type Ref } from "vue";
import { buildWsUrl } from "./apiClient";
import { toast } from "vue-sonner";
import { getMonteCarloJobStatus } from "./monteCarloJobService";

export interface WebSocketMessage {
  status: string;
  progress?: number;
  current_run?: number;
  total_runs?: number;
  eta_seconds?: number;
  estimated_completion_time?: string;
  message?: string;
}

export interface WebSocketMetrics {
  jobSubmissionTime: number | null;
  wsConnectionTime: number | null;
  firstMessageTime: number | null;
  jobStartTime: number | null;
  messageCount: number;
  speed: number | null;
  connectionDelay: number | null;
  processingDelay: number | null;
  totalDuration: number | null;
}

export interface WebSocketState {
  connected: Ref<boolean>;
  connecting: Ref<boolean>;
  status: Ref<string>;
  percent: Ref<number>;
  current: Ref<number>;
  total: Ref<number>;
  etaSeconds: Ref<number | null>;
  metrics: Ref<WebSocketMetrics>;
}

export class MonteCarloWebSocketService {
  private ws: WebSocket | null = null;
  private activeJobId: string | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 3;
  private reconnectDelay = 2000;
  private fallbackTimer: number | null = null;
  private fallbackActive = false;
  private lastRealMessageTime: number | null = null;
  private fallbackIntervalMs = 200;
  private fallbackStartDelayMs = 1000;
  private fallbackGeneration = 0;
  // État réactif
  public state: WebSocketState = {
    connected: ref(false),
    connecting: ref(false),
    status: ref(""),
    percent: ref(0),
    current: ref(0),
    total: ref(0),
    etaSeconds: ref(null),
    metrics: ref({
      jobSubmissionTime: null,
      wsConnectionTime: null,
      firstMessageTime: null,
      jobStartTime: null,
      messageCount: 0,
      speed: null,
      connectionDelay: null,
      processingDelay: null,
      totalDuration: null,
    }),
  };

  // Callbacks pour les événements
  private onMessageCallback?: (message: WebSocketMessage) => void;
  private onStatusChangeCallback?: (status: string) => void;
  private onCompletionCallback?: (status: string) => void;

  constructor() {
    // Bind methods to preserve context
    this.handleOpen = this.handleOpen.bind(this);
    this.handleMessage = this.handleMessage.bind(this);
    this.handleClose = this.handleClose.bind(this);
    this.handleError = this.handleError.bind(this);
  }

  public connect(jobId: string, totalRuns?: number): void {
    // Éviter les connexions multiples pour le même job
    if (this.state.connecting.value) {
      console.log("WebSocket: Connexion déjà en cours, ignorée");
      return;
    }

    if (
      this.ws &&
      (this.ws.readyState === WebSocket.OPEN ||
        this.ws.readyState === WebSocket.CONNECTING) &&
      this.activeJobId === jobId
    ) {
      console.log("WebSocket: Déjà connecté pour ce job, ignoré");
      return;
    }

    // Fermer la connexion précédente si différent job
    if (this.ws && this.activeJobId !== jobId) {
      this.disconnect();
    }

    console.log(`WebSocket: Connexion au job ${jobId}`);

    // Initialiser les métriques
    this.resetMetrics();
    this.state.metrics.value.jobSubmissionTime = Date.now();

    // Réinitialiser l'état
    this.resetState();
    if (totalRuns) {
      this.state.total.value = totalRuns;
    }

    this.state.connecting.value = true;
    this.activeJobId = jobId;
    this.reconnectAttempts = 0;

    try {
      const url = buildWsUrl(`/monte-carlo/jobs/${jobId}/progress`);
      this.ws = new WebSocket(url);

      // Configurer les gestionnaires d'événements
      this.ws.onopen = this.handleOpen;
      this.ws.onmessage = this.handleMessage;
      this.ws.onclose = this.handleClose;
      this.ws.onerror = this.handleError;
    } catch (error) {
      console.error("WebSocket: Erreur lors de la création:", error);
      this.state.connecting.value = false;
      toast.error("Erreur WebSocket", {
        description: "Impossible de créer la connexion WebSocket.",
      });
      this.startFallbackPolling(true);
    }
  }

  public disconnect(): void {
    console.log(`[${new Date().toISOString()}] WebSocket: Déconnexion demandée`);
    // S'assurer que le polling REST de fallback s'arrête
    this.stopFallbackPolling();

    if (this.ws) {
      // Supprimer les gestionnaires pour éviter les événements indésirables
      this.ws.onopen = null;
      this.ws.onmessage = null;
      this.ws.onclose = null;
      this.ws.onerror = null;

      if (
        this.ws.readyState === WebSocket.OPEN ||
        this.ws.readyState === WebSocket.CONNECTING
      ) {
        this.ws.close();
      }
      this.ws = null;
    }

    this.activeJobId = null;
    this.state.connected.value = false;
    this.state.connecting.value = false;
    this.reconnectAttempts = 0;
  }

  public setCallbacks(callbacks: {
    onMessage?: (message: WebSocketMessage) => void;
    onStatusChange?: (status: string) => void;
    onCompletion?: (status: string) => void;
  }): void {
    this.onMessageCallback = callbacks.onMessage;
    this.onStatusChangeCallback = callbacks.onStatusChange;
    this.onCompletionCallback = callbacks.onCompletion;
  }

  private handleOpen(): void {
    console.log(`[${new Date().toISOString()}] WebSocket: Connexion établie`);
    this.state.connected.value = true;
    this.state.connecting.value = false;
    this.state.metrics.value.wsConnectionTime = Date.now();

    if (this.state.metrics.value.jobSubmissionTime) {
      this.state.metrics.value.connectionDelay =
        (this.state.metrics.value.wsConnectionTime -
          this.state.metrics.value.jobSubmissionTime) /
        1000;
    }

    this.reconnectAttempts = 0;

    toast.success("Worker Monte Carlo connecté", {
      description: "Streaming de la progression en temps réel.",
    });
    // Armer le fallback après l’ouverture pour éviter les démarrages prématurés
    this.armFallbackTimer();
  }

  private handleMessage(event: MessageEvent): void {
    console.log("WebSocket: Raw message received:", event.data);
    try {
      const message: WebSocketMessage = JSON.parse(event.data);

      // Incrémenter le compteur de messages
      this.state.metrics.value.messageCount++;
      const messageTime = Date.now();

      // Marquer toute activité WS pour bloquer le fallback le plus tôt possible
      this.lastRealMessageTime = messageTime;
      if (this.fallbackActive) this.stopFallbackPolling();

      // Marquer le premier message
      if (this.state.metrics.value.firstMessageTime === null) {
        this.state.metrics.value.firstMessageTime = messageTime;
        if (this.state.metrics.value.jobSubmissionTime) {
          const delay =
            (messageTime - this.state.metrics.value.jobSubmissionTime) / 1000;
          console.log(`🎯 PREMIER MESSAGE REÇU! (délai: ${delay.toFixed(3)}s)`);
        }
      }

      // Ignorer les messages de connexion - NE PAS déclencher les callbacks
      if (message.status === "connecting") {
        console.log(
          `🔗 Msg#${this.state.metrics.value.messageCount}: CONNEXION - ${message.message || "Connexion établie"}`,
        );
        return; // IMPORTANT: Return ici pour éviter tous les callbacks
      }

      // Mettre à jour l'état
      this.updateState(message);

      // Détecter le début du traitement
      if (
        this.state.metrics.value.jobStartTime === null &&
        this.state.current.value > 0
      ) {
        this.state.metrics.value.jobStartTime = messageTime;
        if (this.state.metrics.value.jobSubmissionTime) {
          this.state.metrics.value.processingDelay =
            (this.state.metrics.value.jobStartTime -
              this.state.metrics.value.jobSubmissionTime) /
            1000;
          console.log(
            `🏃 DÉBUT DU TRAITEMENT DÉTECTÉ! (délai: ${this.state.metrics.value.processingDelay.toFixed(3)}s)`,
          );
        }
      }

      // Calculer la vitesse
      if (
        this.state.metrics.value.jobStartTime &&
        this.state.current.value > 0
      ) {
        const processingTime =
          (messageTime - this.state.metrics.value.jobStartTime) / 1000;
        this.state.metrics.value.speed =
          this.state.current.value / processingTime;
      }

      // Log de progression
      this.logProgress(message, messageTime);

      // Forcer l'exécution immédiate des callbacks pour éviter le buffering Vue.js
      // Utiliser setTimeout avec délai 0 pour forcer l'exécution dans la prochaine boucle d'événements
      setTimeout(() => {
        // Appeler le callback onMessage pour TOUS les messages (sauf connecting)
        if (this.onMessageCallback) {
          this.onMessageCallback(message);
        }

        // Appeler le callback onStatusChange pour TOUS les messages (sauf connecting)
        if (this.onStatusChangeCallback) {
          this.onStatusChangeCallback(message.status);
        }
      }, 0);

      // Vérifier si le job est terminé - être plus strict sur les statuts de completion
      const status = (message.status || "").toUpperCase();
      if (
        status === "COMPLETED" ||
        status === "FAILED" ||
        status === "CANCELLED" ||
        status === "JOB_COMPLETED" ||
        status === "JOB_FAILED" ||
        status === "JOB_CANCELLED"
      ) {
        this.handleJobCompletion(status, messageTime);
      }
    } catch (error) {
      console.error("WebSocket: Erreur lors du parsing du message:", error);
    }
  }

  private handleClose(event: CloseEvent): void {
    console.log(
      `[${new Date().toISOString()}] WebSocket: Connection closed. Code: ${event.code}, Reason: '${event.reason}', Clean: ${event.wasClean}`
    );
    this.state.connected.value = false;
    this.state.connecting.value = false;

    // Activer fallback REST si un job est en cours
    if (this.activeJobId) {
      this.startFallbackPolling();
    }

    // Ne pas reconnecter si le job est terminé ou si on a atteint le maximum de tentatives
    if (
      !this.activeJobId ||
      this.reconnectAttempts >= this.maxReconnectAttempts
    ) {
      console.log(
        "WebSocket: Pas de reconnexion (job terminé ou max tentatives atteint)",
      );
      return;
    }

    // Tentative de reconnexion
    this.reconnectAttempts++;
    console.log(
      `WebSocket: Tentative de reconnexion ${this.reconnectAttempts}/${this.maxReconnectAttempts}`,
    );

    setTimeout(() => {
      if (
        this.activeJobId &&
        !this.state.connected.value &&
        !this.state.connecting.value
      ) {
        toast.warning("Reconnexion au worker…", {
          description: `Tentative ${this.reconnectAttempts}/${this.maxReconnectAttempts}`,
        });
        this.connect(this.activeJobId, this.state.total.value);
      }
    }, this.reconnectDelay);
  }

  private handleError(error: Event): void {
    console.error("WebSocket: Erreur de connexion:", error);
    this.state.connecting.value = false;

    toast.error("Erreur de connexion WebSocket", {
      description:
        "Impossible de se connecter au serveur. Vérifiez que le backend est démarré.",
    });
  }

  private updateState(message: WebSocketMessage): void {
    this.state.status.value = message.status || "";

    if (message.progress !== undefined) {
      this.state.percent.value = Math.max(
        0,
        Math.min(100, Math.round(message.progress * 100)),
      );
    }

    if (message.current_run !== undefined) {
      this.state.current.value = message.current_run;
    }

    if (message.total_runs !== undefined) {
      this.state.total.value = message.total_runs;
    }

    // Gestion de l'ETA
    if (typeof message.eta_seconds === "number") {
      this.state.etaSeconds.value = message.eta_seconds;
    } else if (message.estimated_completion_time) {
      const etaMs = Date.parse(message.estimated_completion_time);
      if (!Number.isNaN(etaMs)) {
        this.state.etaSeconds.value = Math.max(
          0,
          Math.round((etaMs - Date.now()) / 1000),
        );
      }
    }

    // Callback de changement de statut
    if (this.onStatusChangeCallback) {
      this.onStatusChangeCallback(this.state.status.value);
    }
  }

  private logProgress(message: WebSocketMessage, messageTime: number): void {
    if (!this.state.metrics.value.jobSubmissionTime) return;

    const msgDelay =
      (messageTime - this.state.metrics.value.jobSubmissionTime) / 1000;
    const progressPercent = Math.round((message.progress || 0) * 100 * 10) / 10;

    if (this.state.current.value > 0 && this.state.total.value > 0) {
      const speedStr = this.state.metrics.value.speed
        ? ` (${this.state.metrics.value.speed.toFixed(1)} runs/s)`
        : "";
      const etaStr = message.eta_seconds
        ? ` (ETA: ${message.eta_seconds}s)`
        : "";
      console.log(
        `📊 Msg#${this.state.metrics.value.messageCount} (+${msgDelay.toFixed(3)}s): ${message.status} - ${this.state.current.value}/${this.state.total.value} runs (${progressPercent}%)${speedStr}${etaStr}`,
      );
    } else {
      console.log(
        `📊 Msg#${this.state.metrics.value.messageCount} (+${msgDelay.toFixed(3)}s): ${message.status} - ${progressPercent}%`,
      );
    }
  }

  private handleJobCompletion(status: string, messageTime: number): void {
    this.stopFallbackPolling();
    // Calculer la durée totale
    if (this.state.metrics.value.jobSubmissionTime) {
      this.state.metrics.value.totalDuration =
        (messageTime - this.state.metrics.value.jobSubmissionTime) / 1000;
      console.log(
        `🏁 Job terminé avec le statut: ${status} (durée totale: ${this.state.metrics.value.totalDuration.toFixed(3)}s)`,
      );
    }

    // Fermer la connexion
    this.disconnect();

    // Callback de completion
    if (this.onCompletionCallback) {
      this.onCompletionCallback(status);
    }

    // Afficher les toasts appropriés
    if (status.includes("COMPLETED")) {
      toast.success("Monte Carlo terminé", {
        description: `${this.state.total.value} runs terminés en ${this.state.metrics.value.totalDuration?.toFixed(1)}s`,
      });
    } else if (status.includes("FAILED")) {
      toast.error("Monte Carlo échoué", {
        description: "Consultez les logs du worker pour plus de détails.",
      });
    } else if (status.includes("CANCELLED")) {
      toast.warning("Monte Carlo annulé", {
        description: "Le job a été interrompu.",
      });
    }
  }

  private resetState(): void {
    this.state.status.value = "";
    this.state.percent.value = 0;
    this.state.current.value = 0;
    this.state.etaSeconds.value = null;
  }

  private resetMetrics(): void {
    this.state.metrics.value = {
      jobSubmissionTime: null,
      wsConnectionTime: null,
      firstMessageTime: null,
      jobStartTime: null,
      messageCount: 0,
      speed: null,
      connectionDelay: null,
      processingDelay: null,
      totalDuration: null,
    };
  }

  private async pollOnce(expectedGen?: number): Promise<void> {
    const jobId = this.activeJobId;
    if (!jobId) return;
    const reqStart = Date.now();
    try {
      const resp = await getMonteCarloJobStatus(jobId);
      // Si le fallback n'est plus actif ou le job a changé, ignorer la réponse
      if (
        !this.fallbackActive ||
        this.activeJobId !== jobId ||
        (expectedGen !== undefined && expectedGen !== this.fallbackGeneration)
      ) {
        return;
      }
      const message: WebSocketMessage = {
        status: resp.status,
        progress: resp.progress,
        current_run: resp.current_run,
        total_runs: resp.total_runs,
        eta_seconds: resp.eta_seconds ?? undefined,
      };
      const now = Date.now();
      console.log(
        `[${new Date(now).toISOString()}] REST: Progress reçu (+${((now - reqStart) / 1000).toFixed(3)}s)`,
      );
      this.updateState(message);
      
      // Forcer l'exécution immédiate des callbacks pour le fallback polling aussi
      setTimeout(() => {
        if (this.onMessageCallback) this.onMessageCallback(message);
        if (this.onStatusChangeCallback) this.onStatusChangeCallback(message.status);
      }, 0);
      
      const status = (message.status || "").toUpperCase();
      if (status === "COMPLETED" || status === "FAILED" || status === "CANCELLED") {
        this.handleJobCompletion(status, now);
      }
    } catch {
      // silencieux
    }
  }

  private startFallbackPolling(immediate = false): void {
    if (!this.activeJobId) return;
    if (this.fallbackActive) return;
    console.log(`[${new Date().toISOString()}] WebSocket: Starting fallback polling.`);
    this.fallbackActive = true;
    this.fallbackGeneration += 1;
    const gen = this.fallbackGeneration;
    const start = () => {
      if (this.fallbackTimer !== null) clearInterval(this.fallbackTimer);
      this.fallbackTimer = setInterval(() => {
        if (
          !this.fallbackActive ||
          gen !== this.fallbackGeneration ||
          (this.lastRealMessageTime && Date.now() - this.lastRealMessageTime < 1000)
        ) {
          this.stopFallbackPolling();
          return;
        }
        void this.pollOnce(gen);
      }, this.fallbackIntervalMs) as unknown as number;
      console.log(
        `[${new Date().toISOString()}] WebSocket: Fallback polling REST activé (interval=${this.fallbackIntervalMs}ms, gen=${gen})`,
      );
    };
    if (immediate) start();
    else setTimeout(start, this.fallbackStartDelayMs);
  }

  private armFallbackTimer(): void {
    console.log(
      `[${new Date().toISOString()}] WebSocket: Fallback timer armé (delay=${this.fallbackStartDelayMs}ms)`,
    );
    setTimeout(() => {
      if (!this.lastRealMessageTime && this.activeJobId) {
        this.startFallbackPolling();
      }
    }, this.fallbackStartDelayMs);
  }

  private stopFallbackPolling(): void {
    if (this.fallbackTimer !== null) {
      clearInterval(this.fallbackTimer);
      this.fallbackTimer = null;
    }
    if (this.fallbackActive) {
      this.fallbackActive = false;
      console.log(`[${new Date().toISOString()}] WebSocket: Fallback polling REST désactivé`);
    }
  }

  public getStatusLabel(): string {
    const s = (this.state.status.value || "").toUpperCase();
    if (s.includes("PROCESSING")) return "En cours";
    if (s.includes("QUEUED") || s.includes("PENDING")) return "En file";
    if (s.includes("COMPLETED")) return "Terminé";
    if (s.includes("FAILED")) return "Échec";
    if (s.includes("CANCELLED")) return "Annulé";
    return this.state.status.value || "";
  }

  // Getter pour l'ID du job actif (accessible publiquement)
  get currentJobId(): string | null {
    return this.activeJobId;
  }

  public formatEta(): string {
    const sec = this.state.etaSeconds.value;
    if (sec == null) return "";
    const s = Math.max(0, Math.round(sec));
    if (s < 60) return `${s}s`;
    const m = Math.floor(s / 60);
    const rem = s % 60;
    return `${m}m ${rem}s`;
  }
}

// Instance singleton pour l'utilisation dans l'application
export const monteCarloWebSocketService = new MonteCarloWebSocketService();