import { forwardRef, useEffect, useState } from 'react'
import { cn } from '../../lib/utils.js'

export const RippleButton = forwardRef(function RippleButton(
  {
    className,
    children,
    rippleColor = '#ffffff',
    duration = '600ms',
    onClick,
    ...props
  },
  ref
) {
  const [ripples, setRipples] = useState([])

  const handleClick = (event) => {
    const button = event.currentTarget
    const rect = button.getBoundingClientRect()
    const size = Math.max(rect.width, rect.height)
    const x = event.clientX - rect.left - size / 2
    const y = event.clientY - rect.top - size / 2
    setRipples((prev) => [...prev, { x, y, size, key: Date.now() }])
    onClick?.(event)
  }

  useEffect(() => {
    if (ripples.length === 0) return undefined
    const last = ripples[ripples.length - 1]
    const timeout = setTimeout(() => {
      setRipples((prev) => prev.filter((ripple) => ripple.key !== last.key))
    }, parseInt(duration, 10))
    return () => clearTimeout(timeout)
  }, [ripples, duration])

  return (
    <button
      ref={ref}
      className={cn(
        'relative flex cursor-pointer items-center justify-center overflow-hidden rounded-lg border-2 px-4 py-2 text-center',
        className
      )}
      onClick={handleClick}
      {...props}
    >
      <div className="relative z-10">{children}</div>
      <span className="pointer-events-none absolute inset-0">
        {ripples.map((ripple) => (
          <span
            key={ripple.key}
            className="animate-rippling absolute rounded-full opacity-30"
            style={{
              width: `${ripple.size}px`,
              height: `${ripple.size}px`,
              top: `${ripple.y}px`,
              left: `${ripple.x}px`,
              backgroundColor: rippleColor,
              transform: 'scale(0)',
              '--duration': duration,
            }}
          />
        ))}
      </span>
    </button>
  )
})
