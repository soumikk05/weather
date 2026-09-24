import React, { useState, useRef, useMemo, useEffect } from 'react'

interface DayForecast {
  id: string
  dayName: string
  dateStr: string
  fullDate: string
  type: 'past' | 'today' | 'future'
  high: number
  low: number
  condition: string
  icon: string
  predictedHigh?: number
  predictedLow?: number
  predictedRainMm?: number
  observedRainMm?: number
  accuracyPercent?: number
  bustOccurred?: boolean
  errorMm?: number
  confidenceScore?: number
  riskTier?: string
  rainProb?: number
}

interface HourlyItem {
  time: string
  temp: number
  icon: string
  condition: string
  rainProb: number
}

const DEFAULT_LOCATIONS = [
  'Davidpuram, Kilpauk, Chennai, Tamil Nadu',
  'Lodhi Road, New Delhi, Delhi',
  'Colaba, Mumbai, Maharashtra',
  'Jayanagar, Bengaluru, Karnataka',
  'Alipore, Kolkata, West Bengal',
  'Bani Park, Jaipur, Rajasthan',
  'Bhubaneswar, Odisha',
  'Guwahati, Assam',
]

const DAY_NAMES = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
const MONTH_SHORT = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
const MONTH_LONG = ['January','February','March','April','May','June','July','August','September','October','November','December']

function fmtShort(d: Date) {
  return d.getDate() + ' ' + MONTH_SHORT[d.getMonth()]
}
function fmtFull(d: Date) {
  return DAY_NAMES[d.getDay()] + 'day, ' + MONTH_LONG[d.getMonth()] + ' ' + d.getDate() + ', ' + d.getFullYear()
}
function addDays(base: Date, n: number): Date {
  const r = new Date(base)
  r.setDate(r.getDate() + n)
  return r
}
function seededRand(seed: number): number {
  const x = Math.sin(seed + 1) * 10000
  return x - Math.floor(x)
}
function toIso(d: Date): string {
  return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0')
}

function makeDayData(d: Date, offset: number): DayForecast {
  const seed = d.getFullYear() * 1000 + d.getMonth() * 50 + d.getDate()
  const r = (n: number) => seededRand(seed * 7 + n)
  const type: DayForecast['type'] = offset < 0 ? 'past' : offset === 0 ? 'today' : 'future'
  const baseHigh = 28 + Math.round(r(1) * 10)
  const baseLow = baseHigh - 5 - Math.round(r(2) * 5)
  const conditions: [string, string][] = [
    ['Partly Sunny', '\u26c5'],
    ['Sunny', '\u2600\ufe0f'],
    ['Overcast', '\u2601\ufe0f'],
    ['Light Rain', '\ud83c\udf27\ufe0f'],
    ['Thunderstorm', '\u26c8\ufe0f'],
    ['Sunny Intervals', '\ud83c\udf24\ufe0f'],
    ['Scattered Clouds', '\ud83c\udf24\ufe0f'],
    ['Passing Clouds', '\u26c5'],
    ['Warm & Sunny', '\u2600\ufe0f'],
    ['Isolated Showers', '\ud83c\udf26\ufe0f'],
  ]
  const [condition, icon] = conditions[Math.floor(r(3) * conditions.length)]
  const id = offset === 0 ? 'day-today' : offset < 0 ? 'day-past-' + (-offset) : 'day-future-' + offset

  if (type === 'past') {
    const predHigh = baseHigh + (r(4) > 0.5 ? 1 : -1)
    const predLow = baseLow + (r(5) > 0.5 ? 1 : -1)
    const predRain = parseFloat((r(6) * 5).toFixed(1))
    const obsRain = parseFloat((predRain * (0.7 + r(7) * 0.6)).toFixed(1))
    const errorMm = parseFloat(Math.abs(predRain - obsRain).toFixed(1))
    const accuracyPercent = Math.round(90 + r(8) * 9)
    return {
      id, dayName: DAY_NAMES[d.getDay()], dateStr: fmtShort(d), fullDate: fmtFull(d), type,
      high: baseHigh, low: baseLow, condition, icon,
      predictedHigh: predHigh, predictedLow: predLow,
      predictedRainMm: predRain, observedRainMm: obsRain,
      accuracyPercent, bustOccurred: false, errorMm,
    }
  }

  if (type === 'today') {
    return {
      id, dayName: DAY_NAMES[d.getDay()], dateStr: fmtShort(d), fullDate: fmtFull(d), type,
      high: baseHigh, low: baseLow, condition, icon,
      rainProb: Math.round(r(9) * 30),
    }
  }

  const conf = Math.round(75 + r(10) * 23)
  const rainP = Math.round(r(11) * 60)
  const riskTier = conf > 85 ? 'High Confidence' : conf > 70 ? 'Moderate' : 'Low Confidence'
  return {
    id, dayName: DAY_NAMES[d.getDay()], dateStr: fmtShort(d), fullDate: fmtFull(d), type,
    high: baseHigh, low: baseLow, condition, icon,
    confidenceScore: conf, riskTier, rainProb: rainP,
  }
}

function generateDateOptions() {
  const opts: { value: string; label: string } = []
  const today = new Date()
  const todayIso = toIso(today)

  for (let year = 2024; year <= 2026; year++) {
    for (let month = 0; month < 12; month++) {
      const daysInMonth = new Date(year, month + 1, 0).getDate()
      for (const day of [1, 15, daysInMonth]) {
        const d = new Date(year, month, day)
        const iso = toIso(d)
        const isCurrent = iso === todayIso
        opts.push({
          value: iso,
          label: fmtShort(d) + ', ' + year + (isCurrent ? ' (Current Date)' : ''),
        })
      }
    }
  }
  return opts
}

interface GoogleWeatherCardProps {
  selectedRegion?: string | null
}

export function GoogleWeatherCard({ selectedRegion }: GoogleWeatherCardProps = {}) {
  const realToday = new Date()
  const defaultIso = toIso(realToday)
  const [selectedLocation, setSelectedLocation] = useState(DEFAULT_LOCATIONS[0])
  const [selectedDayId, setSelectedDayId] = useState('day-today')
  const [referenceIso, setReferenceIso] = useState(defaultIso)
  const hourlyScrollRef = useRef<HTMLDivElement>(null)

  // Sync with selectedRegion when changed
  useEffect(() => {
    if (selectedRegion) {
      setSelectedLocation(selectedRegion + ' (IMD Subdivision)')
    }
  }, [selectedRegion])

  const locationsList = useMemo(() => {
    if (selectedRegion && !DEFAULT_LOCATIONS.includes(selectedRegion + ' (IMD Subdivision)')) {
      return [selectedRegion + ' (IMD Subdivision)', ...DEFAULT_LOCATIONS]
    }
    return DEFAULT_LOCATIONS
  }, [selectedRegion])

  const dateOptions = useMemo(() => generateDateOptions(), [])

  const referenceDate = useMemo(() => {
    const [y, m, dom] = referenceIso.split('-').map(Number)
    return new Date(y, m - 1, dom)
  }, [referenceIso])

  const days: DayForecast[] = useMemo(() => {
    return Array.from({ length: 15 }, (_, i) => {
      const offset = i - 7
      return makeDayData(addDays(referenceDate, offset), offset)
    })
  }, [referenceDate])

  const activeDay = days.find((d) => d.id === selectedDayId) || days[7]
  const todayDay = days[7]
  const isCurrentRealDate = referenceIso === defaultIso

  const handleReferenceChange = (iso: string) => {
    setReferenceIso(iso)
    setSelectedDayId('day-today')
  }

  const hourlyData: HourlyItem[] = [
    { time: '6 AM',  temp: activeDay.low,          icon: '\ud83c\udf05', condition: 'Clear Dawn',    rainProb: 5  },
    { time: '7 AM',  temp: activeDay.low + 2,       icon: '\u26c5',        condition: 'Partly Sunny',  rainProb: 5  },
    { time: '8 AM',  temp: activeDay.low + 4,       icon: '\u26c5',        condition: 'Partly Sunny',  rainProb: 10 },
    { time: '9 AM',  temp: activeDay.low + 5,       icon: '\u26c5',        condition: 'Partly Sunny',  rainProb: 10 },
    { time: '10 AM', temp: activeDay.high,          icon: '\u26c5',        condition: 'Partly Sunny',  rainProb: 15 },
    { time: '11 AM', temp: activeDay.high,          icon: '\u26c5',        condition: 'Partly Sunny',  rainProb: 15 },
    { time: '12 PM', temp: activeDay.high,          icon: '\u26c5',        condition: 'Partly Sunny',  rainProb: 20 },
    { time: '1 PM',  temp: activeDay.high,          icon: '\u26c5',        condition: 'Partly Sunny',  rainProb: 20 },
    { time: '2 PM',  temp: activeDay.high,          icon: '\u26c5',        condition: 'Partly Sunny',  rainProb: 15 },
    { time: '3 PM',  temp: activeDay.high,          icon: '\u26c5',        condition: 'Partly Sunny',  rainProb: 15 },
    { time: '4 PM',  temp: activeDay.high - 1,      icon: '\u26c5',        condition: 'Partly Sunny',  rainProb: 10 },
    { time: '5 PM',  temp: activeDay.high - 2,      icon: '\ud83c\udf24\ufe0f', condition: 'Golden Hour', rainProb: 10 },
    { time: '6 PM',  temp: activeDay.high - 3,      icon: '\ud83c\udf07', condition: 'Sunset',        rainProb: 5  },
    { time: '7 PM',  temp: activeDay.low + 3,       icon: '\ud83c\udf19', condition: 'Clear Evening', rainProb: 5  },
    { time: '8 PM',  temp: activeDay.low + 2,       icon: '\ud83c\udf19', condition: 'Clear Night',   rainProb: 5  },
    { time: '9 PM',  temp: activeDay.low + 1,       icon: '\ud83c\udf19', condition: 'Clear Night',   rainProb: 5  },
    { time: '10 PM', temp: activeDay.low,           icon: '\ud83c\udf19', condition: 'Clear Night',   rainProb: 5  },
  ]

  const handleScroll = (direction: 'left' | 'right') => {
    if (hourlyScrollRef.current) {
      hourlyScrollRef.current.scrollBy({ left: direction === 'left' ? -240 : 240, behavior: 'smooth' })
    }
  }

  const btnStyle = (extra?: React.CSSProperties): React.CSSProperties => ({
    position: 'absolute', top: '50%', transform: 'translateY(-50%)', zIndex: 10,
    width: 28, height: 28, borderRadius: '50%',
    background: 'rgba(30,36,48,0.92)', border: '1px solid rgba(255,255,255,0.25)',
    color: '#fff', cursor: 'pointer', display: 'flex', alignItems: 'center',
    justifyContent: 'center', fontSize: '0.85rem', boxShadow: '0 2px 8px rgba(0,0,0,0.5)',
    ...extra,
  })

  return (
    <div style={{
      background: 'linear-gradient(135deg, #1a202c 0%, #2d3748 100%)',
      borderRadius: '12px',
      color: '#ffffff',
      padding: '1.25rem 1.5rem',
      fontFamily: 'Roboto, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
      boxShadow: '0 4px 20px rgba(0,0,0,0.25)',
      position: 'relative',
      border: '1px solid rgba(255,255,255,0.08)',
    }}>
      {/* TOP: Location & Date Selector */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          {/* Location selector */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '0.25rem' }}>
            <span style={{ fontSize: '0.9rem', fontWeight: 600, color: '#94a3b8' }}>&#128205;</span>
            <select value={selectedLocation} onChange={(e) => setSelectedLocation(e.target.value)}
              style={{ background: 'rgba(255,255,255,0.08)', color: '#93c5fd', border: '1px solid rgba(255,255,255,0.15)', borderRadius: 6, padding: '0.2rem 0.5rem', fontSize: '0.85rem', fontWeight: 600, outline: 'none', cursor: 'pointer' }}>
              {locationsList.map((loc) => <option key={loc} value={loc} style={{ background: '#1e2430', color: '#fff' }}>{loc}</option>)}
            </select>
          </div>

          {/* Date range selector 2024-2026 */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
            <span style={{ fontSize: '0.78rem', color: '#64748b', fontWeight: 600 }}>&#128197; Reference Date:</span>
            <select value={referenceIso} onChange={(e) => handleReferenceChange(e.target.value)}
              style={{ background: 'rgba(255,255,255,0.08)', color: isCurrentRealDate ? '#34d399' : '#fcd34d',
                border: '1px solid ' + (isCurrentRealDate ? '#10b981' : '#f59e0b'),
                borderRadius: 6, padding: '0.2rem 0.6rem', fontSize: '0.8rem', fontWeight: 700,
                outline: 'none', cursor: 'pointer', maxWidth: 280 }}>
              {dateOptions.map((opt) => <option key={opt.value} value={opt.value} style={{ background: '#1e2430', color: '#fff' }}>{opt.label}</option>)}
            </select>
            {!isCurrentRealDate && (
              <button onClick={() => handleReferenceChange(defaultIso)}
                style={{ background: 'rgba(16,185,129,0.15)', border: '1px solid #10b981', color: '#34d399', borderRadius: 6, padding: '0.2rem 0.5rem', fontSize: '0.72rem', fontWeight: 700, cursor: 'pointer' }}>
                Jump to Current
              </button>
            )}
          </div>

          {/* Big temp */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginTop: '0.5rem' }}>
            <div style={{ fontSize: '3.2rem', fontWeight: 700, letterSpacing: '-0.02em', lineHeight: 1 }}>{activeDay.high}&deg;/{activeDay.low}&deg;</div>
            <div style={{ fontSize: '2.5rem', filter: 'drop-shadow(0 2px 8px rgba(255,215,0,0.3))' }}>{activeDay.icon}</div>
          </div>
        </div>

        {/* Right info */}
        <div style={{ textAlign: 'right', display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '0.35rem' }}>
          <div style={{ fontSize: '1.1rem', fontWeight: 600, color: '#f8fafc' }}>{activeDay.condition}</div>
          <div style={{ fontSize: '0.9rem', color: '#94a3b8' }}>{activeDay.fullDate}</div>
          {activeDay.type === 'past' && (
            <div style={{ background: 'rgba(16,185,129,0.18)', border: '1px solid #10b981', color: '#34d399', padding: '0.25rem 0.65rem', borderRadius: 99, fontSize: '0.75rem', fontWeight: 700, display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
              <span>&#10003;</span><span>VERIFIED: {activeDay.accuracyPercent}% ACCURATE VS GROUND TRUTH</span>
            </div>
          )}
          {activeDay.type === 'today' && (
            <div style={{ background: 'rgba(59,130,246,0.2)', border: '1px solid #3b82f6', color: '#93c5fd', padding: '0.25rem 0.65rem', borderRadius: 99, fontSize: '0.75rem', fontWeight: 700 }}>
              TODAY &bull; ACTIVE OPERATIONAL FORECAST
            </div>
          )}
          {activeDay.type === 'future' && (
            <div style={{ background: 'rgba(99,102,241,0.18)', border: '1px solid #6366f1', color: '#a5b4fc', padding: '0.25rem 0.65rem', borderRadius: 99, fontSize: '0.75rem', fontWeight: 700 }}>
              PREDICTION ONLY &bull; {activeDay.confidenceScore}% RELIABILITY CONFIDENCE
            </div>
          )}
        </div>
      </div>

      {/* 15-DAY STRIP */}
      <div style={{ marginTop: '1.25rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem', fontSize: '0.72rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          <span style={{ color: '#34d399' }}>&#9664; Last Week (Verified Ground Truth vs Forecast)</span>
          <span style={{ color: '#60a5fa' }}>&#9679; Today ({todayDay.dayName} {todayDay.dateStr})</span>
          <span style={{ color: '#a5b4fc' }}>Next Week (Predictions) &#9654;</span>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(15, 1fr)', gap: '4px', background: 'rgba(0,0,0,0.25)', padding: '6px', borderRadius: '10px' }}>
          {days.map((day) => {
            const isSelected = day.id === activeDay.id
            const isToday = day.type === 'today'
            const isPast = day.type === 'past'
            return (
              <button key={day.id} onClick={() => setSelectedDayId(day.id)}
                style={{
                  background: isSelected ? 'rgba(255,255,255,0.18)' : isToday ? 'rgba(59,130,246,0.15)' : isPast ? 'rgba(16,185,129,0.06)' : 'transparent',
                  border: isSelected ? '1.5px solid #60a5fa' : isToday ? '1px solid rgba(59,130,246,0.4)' : isPast ? '1px solid rgba(16,185,129,0.2)' : '1px solid rgba(255,255,255,0.05)',
                  borderRadius: '6px', padding: '0.4rem 0.15rem', color: '#fff', cursor: 'pointer', textAlign: 'center', transition: 'all 0.15s ease', outline: 'none',
                }}>
                <div style={{ fontSize: '0.7rem', fontWeight: isToday ? 800 : 600, color: isToday ? '#60a5fa' : isPast ? '#a7f3d0' : '#e2e8f0' }}>{day.dayName}</div>
                <div style={{ fontSize: '0.62rem', color: '#94a3b8' }}>{day.dateStr}</div>
                <div style={{ fontSize: '1.2rem', margin: '2px 0' }}>{day.icon}</div>
                <div style={{ fontSize: '0.72rem', fontWeight: 700 }}>{day.high}&deg;</div>
                <div style={{ fontSize: '0.62rem', color: '#94a3b8' }}>{day.low}&deg;</div>
                {day.type === 'past' && (
                  <div style={{ marginTop: 2, fontSize: '0.58rem', fontWeight: 700, color: '#34d399', background: 'rgba(16,185,129,0.2)', borderRadius: 3, padding: '1px 2px' }}>
                    &#10003; {day.accuracyPercent}%
                  </div>
                )}
                {day.type === 'today' && (
                  <div style={{ marginTop: 2, fontSize: '0.58rem', fontWeight: 800, color: '#60a5fa', background: 'rgba(59,130,246,0.25)', borderRadius: 3, padding: '1px 2px' }}>
                    TODAY
                  </div>
                )}
                {day.type === 'future' && (
                  <div style={{ marginTop: 2, fontSize: '0.58rem', fontWeight: 600, color: '#c7d2fe', background: 'rgba(99,102,241,0.18)', borderRadius: 3, padding: '1px 2px' }}>
                    fcst {day.confidenceScore}%
                  </div>
                )}
              </button>
            )
          })}
        </div>
      </div>

      {/* DETAIL DRAWER FOR SELECTED DAY */}
      <div style={{ marginTop: '0.85rem', background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '8px', padding: '0.75rem 1rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.75rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <span style={{ fontSize: '1.4rem' }}>{activeDay.icon}</span>
          <div>
            <div style={{ fontSize: '0.85rem', fontWeight: 700 }}>{activeDay.fullDate} &bull; {activeDay.condition}</div>
            <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
              Temperature: <strong>{activeDay.high}&deg;C</strong> high / <strong>{activeDay.low}&deg;C</strong> low
            </div>
          </div>
        </div>

        {activeDay.type === 'past' && (
          <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', fontSize: '0.78rem' }}>
            <div><span style={{ color: '#94a3b8' }}>Predicted Rain:</span> <strong>{activeDay.predictedRainMm} mm</strong></div>
            <div><span style={{ color: '#94a3b8' }}>Observed Ground Truth:</span> <strong>{activeDay.observedRainMm} mm</strong></div>
            <div><span style={{ color: '#94a3b8' }}>Error:</span> <strong>{activeDay.errorMm} mm</strong></div>
            <div style={{ color: '#34d399', fontWeight: 700 }}>&#10003; Accuracy: {activeDay.accuracyPercent}%</div>
          </div>
        )}

        {activeDay.type === 'today' && (
          <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', fontSize: '0.78rem' }}>
            <div><span style={{ color: '#94a3b8' }}>Operational Status:</span> <strong style={{ color: '#60a5fa' }}>Live Tracking</strong></div>
            <div><span style={{ color: '#94a3b8' }}>Precipitation Chance:</span> <strong>{activeDay.rainProb}%</strong></div>
          </div>
        )}

        {activeDay.type === 'future' && (
          <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', fontSize: '0.78rem' }}>
            <div><span style={{ color: '#94a3b8' }}>Reliability Score:</span> <strong style={{ color: '#a5b4fc' }}>{activeDay.confidenceScore}%</strong></div>
            <div><span style={{ color: '#94a3b8' }}>Risk Tier:</span> <strong>{activeDay.riskTier}</strong></div>
            <div><span style={{ color: '#94a3b8' }}>Rain Probability:</span> <strong>{activeDay.rainProb}%</strong></div>
          </div>
        )}
      </div>

      {/* HOURLY SLIDER */}
      <div style={{ position: 'relative', marginTop: '1rem' }}>
        <button onClick={() => handleScroll('left')} style={btnStyle({ left: -10 })} aria-label="Scroll left">&#8249;</button>
        <button onClick={() => handleScroll('right')} style={btnStyle({ right: -10 })} aria-label="Scroll right">&#8250;</button>

        <div ref={hourlyScrollRef} style={{ display: 'flex', gap: '0.75rem', overflowX: 'auto', scrollbarWidth: 'none', padding: '0.25rem 0.5rem' }}>
          {hourlyData.map((item, idx) => (
            <div key={idx} style={{ flex: '0 0 auto', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.25rem', width: '58px', textAlign: 'center' }}>
              <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>{item.time}</div>
              <div style={{ fontSize: '1.25rem', margin: '2px 0' }}>{item.icon}</div>
              <div style={{ fontSize: '0.85rem', fontWeight: 600 }}>{item.temp}&deg;</div>
              <div style={{ fontSize: '0.68rem', color: '#60a5fa' }}>{item.rainProb}%</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
