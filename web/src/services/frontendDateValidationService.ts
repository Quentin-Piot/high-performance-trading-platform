/**
 * Service de validation de dates côté frontend
 * Remplace les appels backend pour la validation des plages de dates
 */

import { AVAILABLE_DATASETS, type Dataset } from '@/config/datasets'

export interface DateRange {
  minDate: string
  maxDate: string
}

export interface DateValidationResult {
  valid: boolean
  errorMessage?: string
  availableRange?: DateRange
  suggestedRange?: DateRange
}

/**
 * Obtient la plage de dates pour un dataset spécifique
 */
export function getDatasetDateRange(datasetId: string): DateRange | null {
  const dataset = AVAILABLE_DATASETS.find(d => d.id === datasetId)
  if (!dataset) {
    return null
  }
  
  return {
    minDate: dataset.dateRange.minDate,
    maxDate: dataset.dateRange.maxDate
  }
}

/**
 * Calcule l'intersection des plages de dates pour plusieurs datasets
 */
export function calculateDateRangeIntersection(datasetIds: string[]): DateRange | null {
  if (datasetIds.length === 0) {
    return null
  }

  // Récupérer les plages de dates pour tous les datasets sélectionnés
  const dateRanges = datasetIds
    .map(id => getDatasetDateRange(id))
    .filter(range => range !== null) as DateRange[]

  if (dateRanges.length === 0) {
    return null
  }

  // Calculer l'intersection : date min la plus tardive et date max la plus précoce
  const latestMinDate = dateRanges.reduce((latest, range) => {
    return new Date(range.minDate) > new Date(latest) ? range.minDate : latest
  }, dateRanges[0]!.minDate)

  const earliestMaxDate = dateRanges.reduce((earliest, range) => {
    return new Date(range.maxDate) < new Date(earliest) ? range.maxDate : earliest
  }, dateRanges[0]!.maxDate)

  // Vérifier si l'intersection est valide
  if (new Date(latestMinDate) > new Date(earliestMaxDate)) {
    return null // Pas d'intersection valide
  }

  return {
    minDate: latestMinDate,
    maxDate: earliestMaxDate
  }
}

/**
 * Valide une plage de dates par rapport aux datasets sélectionnés
 */
export function validateDateRange(
  startDate: string,
  endDate: string,
  datasetIds: string[]
): DateValidationResult {
  if (!startDate || !endDate) {
    return {
      valid: false,
      errorMessage: 'Les dates de début et de fin sont requises'
    }
  }

  if (datasetIds.length === 0) {
    return {
      valid: false,
      errorMessage: 'Aucun dataset sélectionné'
    }
  }

  // Calculer l'intersection des plages de dates
  const intersection = calculateDateRangeIntersection(datasetIds)
  
  if (!intersection) {
    const availableDatasets = datasetIds
      .map(id => AVAILABLE_DATASETS.find(d => d.id === id)?.name || id)
      .join(', ')
    
    return {
      valid: false,
      errorMessage: `Aucune intersection de dates valide trouvée pour les datasets : ${availableDatasets}`
    }
  }

  const requestedStart = new Date(startDate)
  const requestedEnd = new Date(endDate)
  const availableStart = new Date(intersection.minDate)
  const availableEnd = new Date(intersection.maxDate)

  // Vérifier si la plage demandée est dans l'intersection disponible
  if (requestedStart >= availableStart && requestedEnd <= availableEnd) {
    return { valid: true }
  }

  // Calculer une plage suggérée (intersection de la demande et de la disponibilité)
  const suggestedStart = new Date(Math.max(requestedStart.getTime(), availableStart.getTime()))
  const suggestedEnd = new Date(Math.min(requestedEnd.getTime(), availableEnd.getTime()))

  // Si la plage suggérée est invalide, utiliser toute la plage disponible
  let finalSuggestedStart = suggestedStart
  let finalSuggestedEnd = suggestedEnd

  if (suggestedStart > suggestedEnd) {
    finalSuggestedStart = availableStart
    finalSuggestedEnd = availableEnd
  }

  return {
    valid: false,
    errorMessage: `La plage de dates ${startDate} à ${endDate} est en dehors de la plage disponible (${intersection.minDate} à ${intersection.maxDate})`,
    availableRange: intersection,
    suggestedRange: {
      minDate: formatDateISO(finalSuggestedStart),
      maxDate: formatDateISO(finalSuggestedEnd)
    }
  }
}

/**
 * Calcule une plage de dates intelligente basée sur les datasets sélectionnés
 */
export function calculateSmartDateRange(datasetIds: string[]): DateRange | null {
  const intersection = calculateDateRangeIntersection(datasetIds)
  
  if (!intersection) {
    return null
  }

  const availableStart = new Date(intersection.minDate)
  const availableEnd = new Date(intersection.maxDate)
  
  // Calculer la durée totale en jours
  const totalDays = Math.floor((availableEnd.getTime() - availableStart.getTime()) / (1000 * 60 * 60 * 24))
  
  // Logique de sélection intelligente :
  // - Moins de 6 mois : utiliser toute la plage
  // - 6 mois à 2 ans : utiliser les 6 derniers mois
  // - Plus de 2 ans : utiliser la dernière année
  let smartStartDate: Date
  const smartEndDate: Date = availableEnd
  
  if (totalDays < 180) { // Moins de 6 mois
    smartStartDate = availableStart
  } else if (totalDays < 730) { // 6 mois à 2 ans
    smartStartDate = new Date(availableEnd)
    smartStartDate.setMonth(smartStartDate.getMonth() - 6)
    // S'assurer qu'on ne dépasse pas le début disponible
    if (smartStartDate < availableStart) {
      smartStartDate = availableStart
    }
  } else { // Plus de 2 ans
    smartStartDate = new Date(availableEnd)
    smartStartDate.setFullYear(smartStartDate.getFullYear() - 1)
    // S'assurer qu'on ne dépasse pas le début disponible
    if (smartStartDate < availableStart) {
      smartStartDate = availableStart
    }
  }
  
  return {
    minDate: formatDateISO(smartStartDate),
    maxDate: formatDateISO(smartEndDate)
  }
}

/**
 * Formate une date en ISO (YYYY-MM-DD)
 */
function formatDateISO(date: Date): string {
  return date.toISOString().split('T')[0] || ''
}

/**
 * Obtient la liste des datasets disponibles avec leurs plages de dates
 */
export function getAvailableDatasets(): Dataset[] {
  return AVAILABLE_DATASETS
}