/**
 * Formate le temps de traitement de manière intelligente
 * @param processingTime - Le temps au format "X.XXs" du backend
 * @returns Le temps formaté avec l'unité appropriée (ms ou s)
 */
export function formatProcessingTime(processingTime: string | null): string | null {
  if (!processingTime) return null;
  
  // Extraire la valeur numérique du format "X.XXs"
  const match = processingTime.match(/^(\d+(?:\.\d+)?)s?$/);
  if (!match) return processingTime; // Retourner tel quel si format inattendu
  
  const seconds = parseFloat(match[1]);
  
  // Si moins d'1 seconde, afficher en millisecondes
  if (seconds < 1) {
    const milliseconds = Math.round(seconds * 1000);
    return `${milliseconds}ms`;
  }
  
  // Si moins de 10 secondes, afficher avec 2 décimales
  if (seconds < 10) {
    return `${seconds.toFixed(2)}s`;
  }
  
  // Si moins de 60 secondes, afficher avec 1 décimale
  if (seconds < 60) {
    return `${seconds.toFixed(1)}s`;
  }
  
  // Pour les durées plus longues, afficher en minutes et secondes
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = Math.round(seconds % 60);
  
  if (remainingSeconds === 0) {
    return `${minutes}m`;
  }
  
  return `${minutes}m ${remainingSeconds}s`;
}