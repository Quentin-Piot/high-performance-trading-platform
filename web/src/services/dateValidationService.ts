/**
 * Service for validating date ranges against available CSV data
 */

export interface SymbolDateRange {
  symbol: string
  min_date: string
  max_date: string
}

export interface DateRangesResponse {
  symbols: SymbolDateRange[]
}

export interface DateValidationResult {
  valid: boolean
  error_message?: string
  available_range?: {
    min_date: string
    max_date: string
  }
  suggested_range?: {
    start_date: string
    end_date: string
  }
}

/**
 * Fetch available date ranges for all symbols
 */
import { fetchJson } from '@/services/apiClient'

export async function fetchSymbolDateRanges(): Promise<DateRangesResponse> {
  // Use centralized API client to ensure correct BASE_URL and headers
  return fetchJson<DateRangesResponse>('/monte-carlo/symbols/date-ranges')
}

/**
 * Get date range for a specific symbol
 */
export function getSymbolDateRange(symbol: string, dateRanges: DateRangesResponse): SymbolDateRange | null {
  return dateRanges.symbols.find(s => s.symbol.toLowerCase() === symbol.toLowerCase()) || null
}

/**
 * Validate if a date range is valid for a given symbol
 */
export function validateDateRangeForSymbol(
  symbol: string,
  startDate: string,
  endDate: string,
  dateRanges: DateRangesResponse
): DateValidationResult {
  const symbolRange = getSymbolDateRange(symbol, dateRanges)
  
  if (!symbolRange) {
    const availableSymbols = dateRanges.symbols.map(s => s.symbol).join(', ')
    return {
      valid: false,
      error_message: `Symbol "${symbol}" is not supported. Available symbols: ${availableSymbols}`
    }
  }
  
  const requestedStart = new Date(startDate)
  const requestedEnd = new Date(endDate)
  const availableStart = new Date(symbolRange.min_date)
  const availableEnd = new Date(symbolRange.max_date)
  
  // Check if requested range is within available range
  if (requestedStart >= availableStart && requestedEnd <= availableEnd) {
    return { valid: true }
  }
  
  // Calculate suggested range (intersection of requested and available)
  const suggestedStart = new Date(Math.max(requestedStart.getTime(), availableStart.getTime()))
  const suggestedEnd = new Date(Math.min(requestedEnd.getTime(), availableEnd.getTime()))
  
  // If suggested range is invalid (start > end), use the full available range
  let finalSuggestedStart = suggestedStart
  let finalSuggestedEnd = suggestedEnd
  
  if (suggestedStart > suggestedEnd) {
    finalSuggestedStart = availableStart
    finalSuggestedEnd = availableEnd
  }
  
  return {
    valid: false,
    error_message: `Date range ${startDate} to ${endDate} is outside available data range (${symbolRange.min_date} to ${symbolRange.max_date})`,
    available_range: {
      min_date: symbolRange.min_date,
      max_date: symbolRange.max_date
    },
    suggested_range: {
      start_date: formatDateISO(finalSuggestedStart),
      end_date: formatDateISO(finalSuggestedEnd)
    }
  }
}

/**
 * Get the global date range (intersection of all symbols)
 */
export function getGlobalDateRange(dateRanges: DateRangesResponse): { min_date: string; max_date: string } | null {
  if (dateRanges.symbols.length === 0) {
    return null
  }
  
  // Find the latest min_date and earliest max_date across all symbols
  const dates = dateRanges.symbols.map(s => ({
    min: new Date(s.min_date),
    max: new Date(s.max_date)
  }))
  
  const latestMinDate = dates.reduce((latest, current) => 
    current.min > latest ? current.min : latest, dates[0]?.min || new Date())
  
  const earliestMaxDate = dates.reduce((earliest, current) => 
    current.max < earliest ? current.max : earliest, dates[0]?.max || new Date())
  
  // Check if there's a valid intersection
  if (latestMinDate > earliestMaxDate) {
    return null
  }
  
  return {
    min_date: formatDateISO(latestMinDate),
    max_date: formatDateISO(earliestMaxDate)
  }
}

function formatDateISO(date: Date): string {
  return date.toISOString().split('T')[0] || ''
}

/**
 * Calculate the intersection of date ranges for multiple symbols
 * @param symbols - Array of symbol names
 * @param dateRanges - Available date ranges for all symbols
 * @returns The intersection date range or null if no intersection exists
 */
export function getIntersectionDateRange(
  symbols: string[],
  dateRanges: DateRangesResponse
): SymbolDateRange | null {
  if (symbols.length === 0) {
    return null;
  }

  // Get date ranges for all selected symbols
  const symbolRanges = symbols
    .map(symbol => getSymbolDateRange(symbol, dateRanges))
    .filter(range => range !== null) as SymbolDateRange[];

  if (symbolRanges.length === 0) {
    return null;
  }

  // Find the intersection: latest min_date and earliest max_date
  const latestMinDate = symbolRanges.reduce((latest, range) => {
    return new Date(range.min_date) > new Date(latest) ? range.min_date : latest;
  }, symbolRanges[0]?.min_date || '');

  const earliestMaxDate = symbolRanges.reduce((earliest, range) => {
    return new Date(range.max_date) < new Date(earliest) ? range.max_date : earliest;
  }, symbolRanges[0]?.max_date || '');

  // Check if intersection is valid (min_date is before or equal to max_date)
  if (new Date(latestMinDate) > new Date(earliestMaxDate)) {
    return null; // No valid intersection
  }

  return {
    symbol: symbols.join(', '),
    min_date: latestMinDate,
    max_date: earliestMaxDate
  };
}