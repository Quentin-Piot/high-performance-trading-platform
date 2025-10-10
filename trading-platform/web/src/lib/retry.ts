export type RetryOptions = {
  attempts?: number
  baseDelayMs?: number
  maxDelayMs?: number
  shouldRetry?: (err: unknown, attempt: number) => boolean
}

export async function retry<T>(fn: () => Promise<T>, opts: RetryOptions = {}): Promise<T> {
  const attempts = opts.attempts ?? 3
  const base = opts.baseDelayMs ?? 300
  const max = opts.maxDelayMs ?? 3000
  let lastErr: unknown

  for (let i = 1; i <= attempts; i++) {
    try {
      return await fn()
    } catch (err) {
      lastErr = err
      const should = opts.shouldRetry ? opts.shouldRetry(err, i) : i < attempts
      if (!should || i === attempts) break
      const delay = Math.min(max, base * 2 ** (i - 1) + Math.random() * 100)
      await new Promise(res => setTimeout(res, delay))
    }
  }
  throw lastErr
}