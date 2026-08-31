import { useEffect, useRef, useState } from 'react'

/**
 * Calls `fetcher` immediately and then every `intervalMs`, storing the
 * latest result. `deps` controls when the effect resets (e.g. city change).
 */
export function usePolling(fetcher, deps = [], intervalMs = 30000) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const mounted = useRef(true)

  useEffect(() => {
    mounted.current = true
    let timer
    setLoading(true)

    async function tick() {
      const result = await fetcher()
      if (mounted.current) {
        setData(result)
        setLoading(false)
      }
    }

    tick()
    timer = setInterval(tick, intervalMs)

    return () => {
      mounted.current = false
      clearInterval(timer)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  return { data, loading }
}
