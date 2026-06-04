export interface ErrorItem {
  error_type: string
  pattern_key: string
  severity: 'high' | 'medium' | 'low'
  user_fragment: string
  correct_form: string
  rule_shown: boolean
  rule?: string
}


export interface TurnPollResponse {
  turn_id: number
  corrected_input: string | null
  error_count: number
  errors: ErrorItem[]
}

export interface Message {
  role: 'user' | 'ai'
  content: string
  turn_id?: number
  errors?: ErrorItem[]
  corrected_input?: string | null
}

export type Topic = 'daily_life' | 'uni' | 'engineering' | 'test'
