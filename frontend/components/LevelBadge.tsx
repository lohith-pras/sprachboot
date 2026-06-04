type Level = 'A1' | 'A1+' | 'A2' | 'A2+' | 'B1' | 'B2'

const levelClass: Record<Level, string> = {
  'A1':  'level-badge--a1',
  'A1+': 'level-badge--a1p',
  'A2':  'level-badge--a2',
  'A2+': 'level-badge--a2p',
  'B1':  'level-badge--b1',
  'B2':  'level-badge--b2',
}

export default function LevelBadge({ level }: { level: Level }) {
  return (
    <span className={`level-badge ${levelClass[level] ?? 'level-badge--a1'}`}>
      {level}
    </span>
  )
}
