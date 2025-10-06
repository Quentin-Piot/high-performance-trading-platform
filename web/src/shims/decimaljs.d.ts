declare module 'decimal.js' {
  export default class Decimal {
    constructor(value: string | number)
    static ROUND_HALF_UP: number
    static set(config: { precision?: number; rounding?: number }): void

    add(n: string | number | Decimal): Decimal
    sub(n: string | number | Decimal): Decimal
    mul(n: string | number | Decimal): Decimal
    div(n: string | number | Decimal): Decimal
    toString(): string
    toNumber(): number
  }
}