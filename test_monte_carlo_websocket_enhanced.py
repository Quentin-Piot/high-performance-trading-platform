#!/usr/bin/env python3
"""
Script de test amélioré pour diagnostiquer le problème de timing des messages WebSocket Monte Carlo
"""

import asyncio
import json
import time
import requests
import websockets
from datetime import datetime
from typing import Optional, Dict, Any
import signal
import sys
import uuid
import random

# Configuration
API_BASE_URL = "http://localhost:8000/api/v1"
WS_BASE_URL = "ws://localhost:8000/api/v1"

# Données de test avec plus de runs pour voir la progression
TEST_PAYLOAD = {
    "end_date": "2022-03-23",
    "gaussian_scale": 1,
    "initial_capital": 10000,
    "method": "bootstrap",
    "num_runs": 100,  # Plus de runs pour mieux observer le timing
    "priority": 2,
    "sample_fraction": 1,
    "start_date": "2016-01-21",
    "strategy_params": {
        "sma_long": 30,
        "sma_short": 10
    },
    "symbol": "amzn"
}

class TimingDiagnosticTester:
    def __init__(self):
        self.job_id: Optional[str] = None
        self.ws_connection: Optional[websockets.WebSocketServerProtocol] = None
        self.progress_data = {
            "status": "",
            "progress": 0.0,
            "current_run": 0,
            "total_runs": 0,
            "eta_seconds": None
        }
        self.completed = False
        self.failed = False
        self.ws_task: Optional[asyncio.Task] = None
        self.progress_messages = []
        self.start_time = None
        self.job_submission_time = None
        self.ws_connection_time = None
        self.first_message_time = None
        self.job_start_time = None
        
    def log(self, message: str, level: str = "INFO"):
        """Log avec timestamp précis"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        elapsed = ""
        if self.start_time:
            elapsed_sec = time.time() - self.start_time
            elapsed = f" (+{elapsed_sec:.3f}s)"
        print(f"[{timestamp}{elapsed}] [{level}] {message}")
        
    def submit_monte_carlo_job(self) -> bool:
        """Soumet un job Monte Carlo via l'API REST"""
        try:
            # Créer un payload unique
            test_payload = TEST_PAYLOAD.copy()
            unique_id = str(uuid.uuid4())[:8]
            timestamp_ms = int(time.time() * 1000)
            
            # Modifier plusieurs paramètres pour garantir l'unicité
            test_payload["initial_capital"] = TEST_PAYLOAD["initial_capital"] + random.randint(1000, 9999)
            test_payload["gaussian_scale"] = round(random.uniform(0.5, 2.0), 3)
            test_payload["num_runs"] = TEST_PAYLOAD["num_runs"] + random.randint(1, 50)
            test_payload["sample_fraction"] = round(random.uniform(0.8, 1.0), 3)
            
            # Ajouter l'ID unique dans les paramètres de stratégie
            test_payload["strategy_params"]["unique_id"] = unique_id
            
            self.log("🚀 Soumission du job Monte Carlo...")
            self.log(f"Payload: num_runs={test_payload['num_runs']}, unique_id={unique_id}")
            
            self.job_submission_time = time.time()
            
            response = requests.post(
                f"{API_BASE_URL}/monte-carlo/jobs",
                json=test_payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                self.job_id = data.get("job_id")
                submission_duration = time.time() - self.job_submission_time
                self.log(f"✅ Job créé avec succès! ID: {self.job_id} (durée: {submission_duration:.3f}s)")
                self.log(f"Status initial: {data.get('status', 'unknown')}")
                return True
            else:
                self.log(f"❌ Erreur lors de la création du job: {response.status_code}", "ERROR")
                self.log(f"Response: {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Exception lors de la soumission: {str(e)}", "ERROR")
            return False
    
    async def check_job_status_immediately(self):
        """Vérifie le statut du job immédiatement après soumission"""
        if not self.job_id:
            return
            
        try:
            response = requests.get(
                f"{API_BASE_URL}/monte-carlo/jobs/{self.job_id}",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                check_time = time.time() - self.job_submission_time
                self.log(f"📊 Statut immédiat (+{check_time:.3f}s): {data.get('status', 'unknown')}")
                self.log(f"   Progress: {data.get('progress', 0) * 100:.1f}%")
                self.log(f"   Current/Total runs: {data.get('current_run', 0)}/{data.get('total_runs', 0)}")
                return data
            else:
                self.log(f"❌ Erreur statut immédiat: {response.status_code}", "ERROR")
                
        except Exception as e:
            self.log(f"❌ Exception statut immédiat: {e}", "ERROR")
    
    async def connect_websocket_with_timing(self):
        """Se connecte au WebSocket avec diagnostic de timing détaillé"""
        if not self.job_id:
            self.log("❌ Pas de job_id pour la connexion WebSocket", "ERROR")
            return
            
        ws_url = f"{WS_BASE_URL}/monte-carlo/jobs/{self.job_id}/progress"
        self.log(f"🔌 Tentative de connexion WebSocket: {ws_url}")
        
        connection_start = time.time()
        
        try:
            async with websockets.connect(
                ws_url,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10
            ) as websocket:
                self.ws_connection = websocket
                self.ws_connection_time = time.time()
                connection_duration = self.ws_connection_time - connection_start
                ws_delay = self.ws_connection_time - self.job_submission_time
                
                self.log(f"✅ WebSocket connecté! (durée connexion: {connection_duration:.3f}s, délai depuis soumission: {ws_delay:.3f}s)")
                
                message_count = 0
                
                # Écouter les messages avec timing détaillé
                async for message in websocket:
                    try:
                        message_received_time = time.time()
                        data = json.loads(message)
                        message_count += 1
                        
                        # Marquer le premier message
                        if self.first_message_time is None:
                            self.first_message_time = message_received_time
                            first_msg_delay = self.first_message_time - self.job_submission_time
                            ws_to_first_msg = self.first_message_time - self.ws_connection_time
                            self.log(f"🎯 PREMIER MESSAGE REÇU! (délai depuis soumission: {first_msg_delay:.3f}s, depuis connexion WS: {ws_to_first_msg:.3f}s)")
                        
                        await self.handle_progress_message_with_timing(data, message_count, message_received_time)
                        
                        # Vérifier si le job est terminé
                        status = str(data.get("status", "")).upper()
                        if any(term in status for term in ["COMPLETED", "FAILED", "CANCELLED"]):
                            completion_time = time.time()
                            total_duration = completion_time - self.job_submission_time
                            self.log(f"🏁 Job terminé avec le statut: {status} (durée totale: {total_duration:.3f}s)")
                            
                            if "COMPLETED" in status:
                                self.completed = True
                                self.log("🎉 Monte Carlo terminé avec succès!")
                            else:
                                self.failed = True
                                self.log("💥 Monte Carlo a échoué!")
                            break
                            
                    except json.JSONDecodeError as e:
                        self.log(f"❌ Erreur de parsing JSON: {e}", "ERROR")
                    except Exception as e:
                        self.log(f"❌ Erreur lors du traitement du message: {e}", "ERROR")
                        
        except websockets.exceptions.ConnectionClosed:
            self.log("🔌 Connexion WebSocket fermée")
        except websockets.exceptions.InvalidURI:
            self.log(f"❌ URI WebSocket invalide: {ws_url}", "ERROR")
        except Exception as e:
            self.log(f"❌ Erreur WebSocket: {e}", "ERROR")
            self.failed = True
    
    async def handle_progress_message_with_timing(self, data: Dict[str, Any], message_count: int, received_time: float):
        """Traite un message de progression avec analyse de timing"""
        # Stocker le message avec timing
        self.progress_messages.append({
            "timestamp": received_time,
            "message_count": message_count,
            "data": data.copy()
        })
        
        # Détecter le message d'accusé de réception immédiat
        if data.get("status") == "connecting":
            msg_delay = received_time - self.job_submission_time
            self.log(f"🔗 Msg#{message_count} (+{msg_delay:.3f}s): CONNEXION - {data.get('message', 'Connexion établie')}")
            return
        
        # Mettre à jour les données de progression
        self.progress_data.update({
            "status": str(data.get("status", "")),
            "progress": float(data.get("progress", 0.0)),
            "current_run": int(data.get("current_run", 0)),
            "total_runs": int(data.get("total_runs", 0)),
            "eta_seconds": data.get("eta_seconds")
        })
        
        # Calculer les timings
        msg_delay = received_time - self.job_submission_time
        progress_percent = round(self.progress_data["progress"] * 100, 1)
        
        # Détecter le début du traitement (quand current_run > 0 pour la première fois)
        if self.job_start_time is None and self.progress_data["current_run"] > 0:
            self.job_start_time = received_time
            job_start_delay = self.job_start_time - self.job_submission_time
            self.log(f"🏃 DÉBUT DU TRAITEMENT DÉTECTÉ! (délai: {job_start_delay:.3f}s)")
        
        # Log de progression avec timing
        status = self.progress_data["status"]
        current = self.progress_data["current_run"]
        total = self.progress_data["total_runs"]
        
        # Formater l'ETA
        eta_str = ""
        if self.progress_data["eta_seconds"] is not None:
            eta_sec = int(self.progress_data["eta_seconds"])
            if eta_sec < 60:
                eta_str = f" (ETA: {eta_sec}s)"
            else:
                eta_min = eta_sec // 60
                eta_sec_rem = eta_sec % 60
                eta_str = f" (ETA: {eta_min}m {eta_sec_rem}s)"
        
        if current > 0 and total > 0:
            # Calculer la vitesse si le traitement a commencé
            if self.job_start_time:
                processing_time = received_time - self.job_start_time
                speed = current / processing_time if processing_time > 0 else 0
                speed_str = f" ({speed:.1f} runs/s)" if speed > 0 else ""
            else:
                speed_str = ""
            
            self.log(f"📊 Msg#{message_count} (+{msg_delay:.3f}s): {status} - {current}/{total} runs ({progress_percent}%){speed_str}{eta_str}")
        else:
            self.log(f"📊 Msg#{message_count} (+{msg_delay:.3f}s): {status} - {progress_percent}%{eta_str}")
            
        # Log spécial pour les messages problématiques
        if current == 0 and total == 0 and message_count > 1:
            self.log(f"⚠️  Message avec 0/0 runs détecté! Contenu: {data}", "WARNING")
    
    async def monitor_job_status_parallel(self):
        """Surveille le statut du job en parallèle via l'API REST"""
        if not self.job_id:
            return
            
        self.log("🔍 Démarrage de la surveillance parallèle via API REST...")
        
        last_status = None
        check_count = 0
        
        while not self.completed and not self.failed:
            try:
                check_count += 1
                check_time = time.time()
                
                response = requests.get(
                    f"{API_BASE_URL}/monte-carlo/jobs/{self.job_id}",
                    timeout=5
                )
                
                if response.status_code == 200:
                    data = response.json()
                    current_status = data.get("status", "unknown")
                    
                    # Log seulement si le statut change
                    if current_status != last_status:
                        check_delay = check_time - self.job_submission_time
                        self.log(f"🔄 API Check#{check_count} (+{check_delay:.3f}s): Status changé vers '{current_status}'")
                        self.log(f"   Progress: {data.get('progress', 0) * 100:.1f}%")
                        self.log(f"   Runs: {data.get('current_run', 0)}/{data.get('total_runs', 0)}")
                        last_status = current_status
                    
                    # Arrêter si terminé
                    if current_status in ["completed", "failed", "cancelled"]:
                        break
                        
                await asyncio.sleep(2)  # Vérifier toutes les 2 secondes
                
            except Exception as e:
                self.log(f"❌ Erreur surveillance API: {e}", "ERROR")
                await asyncio.sleep(2)
    
    def analyze_timing_issues(self):
        """Analyse les problèmes de timing détectés"""
        self.log("🔬 ANALYSE DES PROBLÈMES DE TIMING:")
        self.log("=" * 60)
        
        if not self.progress_messages:
            self.log("⚠️  PROBLÈME MAJEUR: Aucun message WebSocket reçu!", "ERROR")
            return
            
        # Analyser les délais
        if self.first_message_time:
            first_msg_delay = self.first_message_time - self.job_submission_time
            self.log(f"📊 Délai premier message WebSocket: {first_msg_delay:.3f}s")
            
            if first_msg_delay > 5.0:
                self.log("⚠️  PROBLÈME: Délai > 5s pour le premier message!", "WARNING")
        
        if self.job_start_time:
            job_start_delay = self.job_start_time - self.job_submission_time
            self.log(f"📊 Délai début traitement: {job_start_delay:.3f}s")
            
            if job_start_delay > 10.0:
                self.log("⚠️  PROBLÈME: Délai > 10s pour démarrer le traitement!", "WARNING")
        
        # Analyser les messages
        first_msg = self.progress_messages[0]["data"]
        self.log(f"📊 Premier message: {first_msg}")
        
        if first_msg.get("current_run", 0) == 0 and first_msg.get("total_runs", 0) == 0:
            self.log("⚠️  PROBLÈME: Premier message avec 0/0 runs!", "WARNING")
        
        # Compter les messages avec 0/0 runs
        zero_messages = [msg for msg in self.progress_messages if msg["data"].get("current_run", 0) == 0 and msg["data"].get("total_runs", 0) == 0]
        if zero_messages:
            self.log(f"⚠️  PROBLÈME: {len(zero_messages)} messages avec 0/0 runs détectés!", "WARNING")
        
        self.log(f"📊 Total messages reçus: {len(self.progress_messages)}")
        
        if len(self.progress_messages) > 1:
            duration = self.progress_messages[-1]["timestamp"] - self.progress_messages[0]["timestamp"]
            self.log(f"📊 Durée de progression WebSocket: {duration:.3f}s")
    
    async def run_diagnostic_test(self):
        """Exécute le test de diagnostic complet"""
        self.log("🎯 DÉMARRAGE DU TEST DE DIAGNOSTIC TIMING")
        self.log("=" * 70)
        
        self.start_time = time.time()
        
        # 1. Soumettre le job
        if not self.submit_monte_carlo_job():
            self.log("❌ Échec de la soumission du job", "ERROR")
            return False
        
        # 2. Vérifier le statut immédiatement
        await self.check_job_status_immediately()
        
        # 3. Démarrer la surveillance parallèle
        monitor_task = asyncio.create_task(self.monitor_job_status_parallel())
        
        # 4. Attendre un court délai puis se connecter au WebSocket
        self.log("⏳ Attente de 1 seconde avant connexion WebSocket...")
        await asyncio.sleep(1)
        
        # 5. Se connecter au WebSocket
        await self.connect_websocket_with_timing()
        
        # 6. Arrêter la surveillance
        monitor_task.cancel()
        
        # 7. Analyser les problèmes de timing
        self.analyze_timing_issues()
        
        # 8. Résumé
        self.log("=" * 70)
        total_time = time.time() - self.start_time
        self.log(f"⏱️  Temps total du test: {total_time:.3f}s")
        
        if self.completed:
            self.log("✅ TEST RÉUSSI: Job complété avec succès!")
            return True
        elif self.failed:
            self.log("❌ TEST ÉCHOUÉ: Job a échoué!")
            return False
        else:
            self.log("⚠️  TEST INCOMPLET: Statut final incertain")
            return False

def signal_handler(signum, frame):
    """Gestionnaire de signal pour arrêt propre"""
    print("\n🛑 Arrêt du test demandé...")
    sys.exit(0)

async def main():
    """Fonction principale"""
    signal.signal(signal.SIGINT, signal_handler)
    
    tester = TimingDiagnosticTester()
    
    try:
        success = await tester.run_diagnostic_test()
        if success:
            print("\n🎉 Test de diagnostic terminé avec succès!")
            sys.exit(0)
        else:
            print("\n💥 Test de diagnostic échoué!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Test interrompu par l'utilisateur")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Erreur inattendue: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    print("🧪 Test de diagnostic timing WebSocket Monte Carlo")
    print("Ce test analyse précisément les délais de réception des messages")
    print("Appuyez sur Ctrl+C pour arrêter")
    print()
    
    # Vérifier que les dépendances sont disponibles
    try:
        import websockets
        import requests
    except ImportError as e:
        print(f"❌ Dépendance manquante: {e}")
        print("Installez avec: pip install websockets requests")
        sys.exit(1)
    
    # Lancer le test
    asyncio.run(main())