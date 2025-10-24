/**
 * Formate le temps de traitement de manière intelligente
 * @param processingTime - Le temps au format "X.XXs" du backend
 * @returns Le temps formaté avec l'unité appropriée (ms ou s)
 */
export function formatProcessingTime(
  processingTime: string | null,
): string | null {
  if (!processingTime) return null;

  const match = processingTime.match(/^(\d+(?:\.\d+)?)s?$/);
  if (!match) return processingTime; // Retourner tel quel si format inattendu

  const seconds = parseFloat(match[1]);

  if (seconds < 1) {
    const milliseconds = Math.round(seconds * 1000);
    return `${milliseconds}ms`;
  }

  if (seconds < 10) {
    return `${seconds.toFixed(2)}s`;
  }

  if (seconds < 60) {
    return `${seconds.toFixed(1)}s`;
  }

  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = Math.round(seconds % 60);

  if (remainingSeconds === 0) {
    return `${minutes}m`;
  }

  return `${minutes}m ${remainingSeconds}s`;
}
