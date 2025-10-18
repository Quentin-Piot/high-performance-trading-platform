/**
 * Service de validation de dates côté frontend
 * Remplace les appels backend pour la validation des plages de dates
 */

import { AVAILABLE_DATASETS } from '@/config/datasets'

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
  // Utiliser des comparaisons de chaînes pour éviter les problèmes de timezone
  if (startDate >= intersection.minDate && endDate <= intersection.maxDate) {
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
 * Calcule la plage de dates complète basée sur les datasets sélectionnés
 * Utilise la première date disponible comme début et la dernière comme fin
 */
export function calculateFullDateRange(datasetIds: string[]): DateRange | null {
  const intersection = calculateDateRangeIntersection(datasetIds)
  
  if (!intersection) {
    return null
  }

  // Retourner directement l'intersection complète (première à dernière date)
  return {
    minDate: intersection.minDate,
    maxDate: intersection.maxDate
  }
}

/**
 * Formate une date en ISO (YYYY-MM-DD)
 */
function formatDateISO(date: Date): string {
  return date.toISOString().split('T')[0] || ''
}

/**
 * Analyse un fichier CSV pour extraire les plages de dates
 */
export async function analyzeCsvDateRange(file: File): Promise<DateRange | null> {
  try {
    const text = await file.text()
    const lines = text.split('\n').filter(line => line.trim())
    
    if (lines.length < 2) {
      return null // Pas assez de données
    }
    
    // Supposer que la première ligne est l'en-tête
    const header = lines[0]?.toLowerCase() || ''
    
    // Chercher la colonne de date (formats courants)
    const dateColumnNames = ['date', 'timestamp', 'time', 'datetime']
    const headerColumns = header.split(',').map(col => col.trim().toLowerCase())
    
    let dateColumnIndex = -1
    for (const dateCol of dateColumnNames) {
      dateColumnIndex = headerColumns.findIndex(col => col.includes(dateCol))
      if (dateColumnIndex !== -1) break
    }
    
    // Si aucune colonne de date trouvée, essayer la première colonne
    if (dateColumnIndex === -1) {
      dateColumnIndex = 0
    }
    
    const dates: Date[] = []
    
    // Analyser les lignes de données (ignorer l'en-tête)
    for (let i = 1; i < lines.length; i++) {
      const line = lines[i]
      if (!line?.trim()) continue
      
      const columns = line.split(',')
      const dateStr = columns[dateColumnIndex]?.trim()
      
      if (dateStr) {
        // Essayer différents formats de date
        const date = parseFlexibleDate(dateStr)
        if (date && !isNaN(date.getTime())) {
          dates.push(date)
        }
      }
    }
    
    if (dates.length === 0) {
      return null
    }
    
    // Trier les dates et prendre la première et la dernière
    dates.sort((a, b) => a.getTime() - b.getTime())
    
    return {
      minDate: formatDateISO(dates[0]!),
      maxDate: formatDateISO(dates[dates.length - 1]!)
    }
  } catch (error) {
    console.error('Erreur lors de l\'analyse du CSV:', error)
    return null
  }
}

/**
 * Parse une date avec différents formats possibles
 */
function parseFlexibleDate(dateStr: string): Date | null {
  // Nettoyer la chaîne
  const cleaned = dateStr.replace(/['"]/g, '').trim()
  
  // Essayer le parsing direct d'abord
  let date = new Date(cleaned)
  if (!isNaN(date.getTime())) {
    return date
  }
  
  // Si le format US (MM/DD/YYYY), convertir en ISO
  if (/^\d{1,2}\/\d{1,2}\/\d{4}$/.test(cleaned)) {
    const [month, day, year] = cleaned.split('/')
    if (month && day && year) {
      date = new Date(`${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`)
      if (!isNaN(date.getTime())) {
        return date
      }
    }
  }
  
  // Si le format européen (DD-MM-YYYY), convertir en ISO
  if (/^\d{1,2}-\d{1,2}-\d{4}$/.test(cleaned)) {
    const [day, month, year] = cleaned.split('-')
    if (day && month && year) {
      date = new Date(`${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`)
      if (!isNaN(date.getTime())) {
        return date
      }
    }
  }
  
  return null
}

/**
 * Calcule l'intersection des plages de dates incluant les fichiers CSV uploadés
 */
export async function calculateDateRangeWithCsvFiles(
  datasetIds: string[],
  csvFiles: File[]
): Promise<DateRange | null> {
  const ranges: DateRange[] = []
  
  // Ajouter les plages des datasets sélectionnés
  for (const datasetId of datasetIds) {
    const range = getDatasetDateRange(datasetId)
    if (range) {
      ranges.push(range)
    }
  }
  
  // Analyser les fichiers CSV uploadés
  for (const file of csvFiles) {
    const range = await analyzeCsvDateRange(file)
    if (range) {
      ranges.push(range)
    }
  }
  
  if (ranges.length === 0) {
    return null
  }
  
  // Calculer l'intersection de toutes les plages
  const latestMinDate = ranges.reduce((latest, range) => {
    return new Date(range.minDate) > new Date(latest) ? range.minDate : latest
  }, ranges[0]!.minDate)

  const earliestMaxDate = ranges.reduce((earliest, range) => {
    return new Date(range.maxDate) < new Date(earliest) ? range.maxDate : earliest
  }, ranges[0]!.maxDate)

  // Vérifier si l'intersection est valide
  if (new Date(latestMinDate) > new Date(earliestMaxDate)) {
    return null // Pas d'intersection valide
  }

  return {
    minDate: latestMinDate,
    maxDate: earliestMaxDate
  }
}