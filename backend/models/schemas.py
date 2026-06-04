from pydantic import BaseModel
from typing import Optional, List


# ── Session / Turn ────────────────────────────────────────────────────────────

class ErrorItem(BaseModel):
    error_type: str
    pattern_key: str
    severity: str  # 'high' | 'medium' | 'low'
    user_fragment: str
    correct_form: str
    rule_shown: bool = False
    rule: Optional[str] = None  # one-sentence rule, high severity only


class TurnRequest(BaseModel):
    session_id: Optional[int] = None  # None = auto-create new session
    user_input: str
    mode: str = "chat"    # 'voice' | 'chat'
    topic: str = "daily_life"


class TurnResponse(BaseModel):
    turn_id: int
    session_id: int
    ai_response: str
    english_switch: bool
    errors: List[ErrorItem] = []
    corrected_input: Optional[str] = None


class SessionEndRequest(BaseModel):
    session_id: int
    duration_s: int


class SessionEndResponse(BaseModel):
    session_id: int
    turn_count: int
    duration_s: int


# ── Profile ───────────────────────────────────────────────────────────────────

class WeakPattern(BaseModel):
    pattern_key: str
    accuracy: float
    error_count: int


class WeaknessResponse(BaseModel):
    top_weak_patterns: List[WeakPattern]
    low_confidence_words: List[str]
    current_level_estimate: str
    days_to_next_level: int


class ProfileSummary(BaseModel):
    current_level: str
    total_sessions: int
    sessions_this_week: int
    total_turns: int
    streak_days: int
    words_confident: int
    words_learning: int
    v2_accuracy: float = 0.0
    latest_test_score: float = 0.0


# ── Analytics ─────────────────────────────────────────────────────────────────

class WeeklyAnalytics(BaseModel):
    week: str
    sessions: int
    total_minutes: int
    turns_total: int
    error_rate_trend: List[float]
    best_day: Optional[str]
    pattern_improvements: List[str]
    pattern_regressions: List[str]
    words_added_to_confident: int

# ── Test ──────────────────────────────────────────────────────────────────────

class WordOrderQuestion(BaseModel):
    id: str
    jumbled: List[str]
    correct: str

class VocabularyQuestion(BaseModel):
    id: str
    prompt: str
    options: List[str]
    correct_index: int

class ShortResponseQuestion(BaseModel):
    id: str
    prompt: str

class TestGenerateResponse(BaseModel):
    word_order: List[WordOrderQuestion]
    vocabulary: List[VocabularyQuestion]
    short_response: List[ShortResponseQuestion]

class TestSubmissionItem(BaseModel):
    id: str
    type: str
    answer: str

class TestSubmitRequest(BaseModel):
    level: str
    answers: List[TestSubmissionItem]

class TestQuestionResult(BaseModel):
    id: str
    type: str
    is_correct: bool
    user_answer: str
    correct_answer: str

class TestSubmitResponse(BaseModel):
    score: float
    cefr_level: str
    details: dict
    breakdown: List[TestQuestionResult]


# ── Settings ──────────────────────────────────────────────────────────────────

class PreferencesResponse(BaseModel):
    user_name: str
    conv_model: str
    analysis_model: str
    onboarding_complete: bool


class PreferencesUpdate(BaseModel):
    user_name: Optional[str] = None
    conv_model: Optional[str] = None
    analysis_model: Optional[str] = None
    onboarding_complete: Optional[bool] = None


class ApiKeySet(BaseModel):
    service: str  # 'openrouter' | 'openai' | 'deepl'
    key: str


class ApiKeyStatus(BaseModel):
    openrouter: bool
    openai: bool
    deepl: bool


class ApiKeyTestRequest(BaseModel):
    service: str


class ApiKeyTestResult(BaseModel):
    ok: bool
    detail: Optional[str] = None


class ModelOption(BaseModel):
    id: str
    name: str


class ModelsResponse(BaseModel):
    models: List[ModelOption]


class TranslateWordRequest(BaseModel):
    word: str


class TranslateSentenceRequest(BaseModel):
    text: str


class TranslateResponse(BaseModel):
    translation: str

