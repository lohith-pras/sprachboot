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

export interface ReceiptTurn {
  turn_id: number
  user_corrected: string
  user_raw: string
  ai_response: string
  error_count: number
}

export interface Scenario {
  id: number
  situation: string
  title: string
  counterpart_role: string
  opening_line: string
  goals: string[]
  topic: string
  status: string
  transfer_status: 'none' | 'pending' | 'reported'
  transfer_report: string | null
}

export interface GoalResult {
  goal: string
  hit: boolean
}

export interface Receipt {
  session_id: number
  topic: string
  turn_count: number
  overall_score: number | null
  provisional: boolean
  is_baseline: boolean
  delta: number | null
  trailing_avg: number | null
  prior_session_count: number
  replay: ReceiptTurn[]
  scenario_title: string | null
  counterpart_role: string | null
  goals: GoalResult[]
}
