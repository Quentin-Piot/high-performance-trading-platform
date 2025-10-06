import Decimal from 'decimal.js'

Decimal.set({ precision: 40, rounding: Decimal.ROUND_HALF_UP })

export function toDecimal(n: number | string): Decimal {
  return new Decimal(n)
}

export function add(a: number | string, b: number | string): Decimal {
  return toDecimal(a).add(b)
}

export function sub(a: number | string, b: number | string): Decimal {
  return toDecimal(a).sub(b)
}

export function mul(a: number | string, b: number | string): Decimal {
  return toDecimal(a).mul(b)
}

export function div(a: number | string, b: number | string): Decimal {
  return toDecimal(a).div(b)
}

export function formatCurrency(value: number | string, currency = 'USD', locale = 'en-US'): string {
  const v = Number(toDecimal(value).toString())
  return new Intl.NumberFormat(locale, { style: 'currency', currency }).format(v)
}

export function formatPercent(value: number | string, locale = 'en-US', fractionDigits = 2): string {
  const v = Number(toDecimal(value).toString())
  return new Intl.NumberFormat(locale, { style: 'percent', minimumFractionDigits: fractionDigits, maximumFractionDigits: fractionDigits }).format(v)
}