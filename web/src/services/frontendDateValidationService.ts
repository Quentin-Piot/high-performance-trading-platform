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
export function calculateDateRangeIntersection(datasetIds: string[]): DateRange | null {
  if (datasetIds.length === 0) {
    return null
  }
  const dateRanges = datasetIds
    .map(id => getDatasetDateRange(id))
    .filter(range => range !== null) as DateRange[]
  if (dateRanges.length === 0) {
    return null
  }
  const latestMinDate = dateRanges.reduce((latest, range) => {
    return new Date(range.minDate) > new Date(latest) ? range.minDate : latest
  }, dateRanges[0]!.minDate)
  const earliestMaxDate = dateRanges.reduce((earliest, range) => {
    return new Date(range.maxDate) < new Date(earliest) ? range.maxDate : earliest
  }, dateRanges[0]!.maxDate)
  if (new Date(latestMinDate) > new Date(earliestMaxDate)) {
    return null 
  }
  return {
    minDate: latestMinDate,
    maxDate: earliestMaxDate
  }
}
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
  if (startDate >= intersection.minDate && endDate <= intersection.maxDate) {
    return { valid: true }
  }
  const suggestedStart = new Date(Math.max(requestedStart.getTime(), availableStart.getTime()))
  const suggestedEnd = new Date(Math.min(requestedEnd.getTime(), availableEnd.getTime()))
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
export function calculateFullDateRange(datasetIds: string[]): DateRange | null {
  const intersection = calculateDateRangeIntersection(datasetIds)
  if (!intersection) {
    return null
  }
  return {
    minDate: intersection.minDate,
    maxDate: intersection.maxDate
  }
}
function formatDateISO(date: Date): string {
  return date.toISOString().split('T')[0] || ''
}
export async function analyzeCsvDateRange(file: File): Promise<DateRange | null> {
  try {
    const text = await file.text()
    const lines = text.split('\n').filter(line => line.trim())
    if (lines.length < 2) {
      return null 
    }
    const header = lines[0]?.toLowerCase() || ''
    const dateColumnNames = ['date', 'timestamp', 'time', 'datetime']
    const headerColumns = header.split(',').map(col => col.trim().toLowerCase())
    let dateColumnIndex = -1
    for (const dateCol of dateColumnNames) {
      dateColumnIndex = headerColumns.findIndex(col => col.includes(dateCol))
      if (dateColumnIndex !== -1) break
    }
    if (dateColumnIndex === -1) {
      dateColumnIndex = 0
    }
    const dates: Date[] = []
    for (let i = 1; i < lines.length; i++) {
      const line = lines[i]
      if (!line?.trim()) continue
      const columns = line.split(',')
      const dateStr = columns[dateColumnIndex]?.trim()
      if (dateStr) {
        const date = parseFlexibleDate(dateStr)
        if (date && !isNaN(date.getTime())) {
          dates.push(date)
        }
      }
    }
    if (dates.length === 0) {
      return null
    }
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
function parseFlexibleDate(dateStr: string): Date | null {
  const cleaned = dateStr.replace(/['"]/g, '').trim()
  let date = new Date(cleaned)
  if (!isNaN(date.getTime())) {
    return date
  }
  if (/^\d{1,2}\/\d{1,2}\/\d{4}$/.test(cleaned)) {
    const [month, day, year] = cleaned.split('/')
    if (month && day && year) {
      date = new Date(`${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`)
      if (!isNaN(date.getTime())) {
        return date
      }
    }
  }
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
export async function calculateDateRangeWithCsvFiles(
  datasetIds: string[],
  csvFiles: File[]
): Promise<DateRange | null> {
  const ranges: DateRange[] = []
  for (const datasetId of datasetIds) {
    const range = getDatasetDateRange(datasetId)
    if (range) {
      ranges.push(range)
    }
  }
  for (const file of csvFiles) {
    const range = await analyzeCsvDateRange(file)
    if (range) {
      ranges.push(range)
    }
  }
  if (ranges.length === 0) {
    return null
  }
  const latestMinDate = ranges.reduce((latest, range) => {
    return new Date(range.minDate) > new Date(latest) ? range.minDate : latest
  }, ranges[0]!.minDate)
  const earliestMaxDate = ranges.reduce((earliest, range) => {
    return new Date(range.maxDate) < new Date(earliest) ? range.maxDate : earliest
  }, ranges[0]!.maxDate)
  if (new Date(latestMinDate) > new Date(earliestMaxDate)) {
    return null 
  }
  return {
    minDate: latestMinDate,
    maxDate: earliestMaxDate
  }
}