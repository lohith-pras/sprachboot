import { ErrorItem } from '@/lib/types'
import ErrorDot from './ErrorDot'

interface Props {
  role: 'user' | 'ai'
  content: string
  errors?: ErrorItem[]
  onErrorClick?: () => void
}

export default function ChatBubble({ role, content, errors = [], onErrorClick }: Props) {
  return (
    <div className={`bubble-row bubble-row--${role === 'user' ? 'user' : 'ai'}`}>
      <div className={`bubble bubble--${role === 'user' ? 'user' : 'ai'}`}>
        {content}
      </div>
      {role === 'user' && errors.length > 0 && (
        <ErrorDot count={errors.length} onClick={onErrorClick} />
      )}
    </div>
  )
}
