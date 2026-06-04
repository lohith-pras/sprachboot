"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

type Question = {
  id: string;
  type: "word_order" | "vocabulary" | "short_response";
  prompt?: string;
  jumbled?: string[];
  options?: string[];
};

type TestResult = {
  score: number;
  cefr_level: string;
  breakdown: {
    id: string;
    type: string;
    is_correct: boolean;
    user_answer: string;
    correct_answer: string;
  }[];
};

export default function TestPage() {
  const router = useRouter();
  const [started, setStarted] = useState(false);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<{ id: string, type: string, answer: string }[]>([]);
  
  // Question specific states
  const [woOrder, setWoOrder] = useState<string[]>([]);
  const [vocChoice, setVocChoice] = useState<number | null>(null);
  const [srText, setSrText] = useState("");
  
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<TestResult | null>(null);

  useEffect(() => {
    if (started && questions.length === 0) {
      setLoading(true);
      fetch("http://localhost:8000/test/weekly?level=A1")
        .then(res => res.json())
        .then(data => {
          const combined: Question[] = [
            ...data.word_order.map((q: any) => ({ ...q, type: "word_order" })),
            ...data.vocabulary.map((q: any) => ({ ...q, type: "vocabulary" })),
            ...data.short_response.map((q: any) => ({ ...q, type: "short_response" }))
          ];
          setQuestions(combined);
          setLoading(false);
        })
        .catch(e => {
          console.error(e);
          setLoading(false);
        });
    }
  }, [started, questions.length]);

  const currentQ = questions[currentIndex];

  useEffect(() => {
    // Reset specific states when question changes
    setWoOrder([]);
    setVocChoice(null);
    setSrText("");
  }, [currentIndex]);

  const handleWoClick = (word: string) => {
    if (woOrder.includes(word)) {
      setWoOrder(woOrder.filter(w => w !== word));
    } else {
      setWoOrder([...woOrder, word]);
    }
  };

  const handleNext = () => {
    let answer = "";
    if (currentQ.type === "word_order") answer = woOrder.join(" ");
    if (currentQ.type === "vocabulary") answer = String(vocChoice);
    if (currentQ.type === "short_response") answer = srText;

    const newAnswers = [...answers, { id: currentQ.id, type: currentQ.type, answer }];
    setAnswers(newAnswers);

    if (currentIndex < questions.length - 1) {
      setCurrentIndex(currentIndex + 1);
    } else {
      submitTest(newAnswers);
    }
  };

  const submitTest = async (finalAnswers: any) => {
    setLoading(true);
    try {
      const res = await fetch("http://localhost:8000/test/weekly/submit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ level: "A1", answers: finalAnswers })
      });
      const data = await res.json();
      setResult(data);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  if (result) {
    return (
      <main className="page section" style={{ maxWidth: '800px', margin: '0 auto', paddingTop: 'var(--space-3xl)' }}>
        <div style={{ textAlign: 'center', marginBottom: 'var(--space-2xl)' }}>
          <span className="mono-label" style={{ color: 'var(--color-accent-2)' }}>Test Complete</span>
          <h1 style={{ fontSize: 'var(--text-counter)', margin: 'var(--space-md) 0', color: 'var(--color-accent-3)' }}>
            {Math.round(result.score * 100)}%
          </h1>
          <p style={{ fontSize: 'var(--text-lg)', marginBottom: 'var(--space-xl)' }}>
            Your estimated level remains <strong>{result.cefr_level}</strong>.
          </p>
        </div>

        <h3 style={{ marginBottom: 'var(--space-lg)' }}>Detailed Report</h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)', marginBottom: 'var(--space-3xl)' }}>
          {result.breakdown?.map((item, i) => (
            <div key={i} className="cell" style={{ background: item.is_correct ? 'var(--color-paper-2)' : 'var(--color-paper)', borderLeft: `4px solid ${item.is_correct ? 'var(--color-accent)' : 'var(--color-accent-3)'}` }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 'var(--space-sm)' }}>
                <span className="mono-label cell__tag" style={{ margin: 0 }}>Question {i + 1} • {item.type.replace('_', ' ')}</span>
                <span style={{ fontWeight: 600, color: item.is_correct ? 'var(--color-accent)' : 'var(--color-accent-3)' }}>
                  {item.is_correct ? '✓ Correct' : '✗ Needs work'}
                </span>
              </div>
              <p style={{ margin: 'var(--space-xs) 0', color: 'var(--color-ink-2)' }}><strong>Your answer:</strong> {item.user_answer}</p>
              {!item.is_correct && (
                <p style={{ margin: 0, color: 'var(--color-ink)' }}><strong>Correct:</strong> {item.correct_answer}</p>
              )}
            </div>
          ))}
        </div>

        <div style={{ textAlign: 'center', paddingBottom: 'var(--space-4xl)' }}>
          <Link href="/" className="btn btn--lg">Back to Dashboard</Link>
        </div>
      </main>
    );
  }

  if (!started) {
    return (
      <main className="page section" style={{ maxWidth: '600px', margin: '0 auto', textAlign: 'center', paddingTop: 'var(--space-4xl)' }}>
        <h1 style={{ fontSize: 'var(--text-display-s)' }}>Weekly Check-in</h1>
        <p style={{ fontSize: 'var(--text-lg)', color: 'var(--color-ink-2)', margin: 'var(--space-md) 0 var(--space-2xl)' }}>
          10 questions to track your progress and calibrate the AI. This usually takes about 3 minutes.
        </p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-sm)', textAlign: 'left', background: 'var(--color-paper-2)', padding: 'var(--space-xl)', borderRadius: 'var(--radius-card)', marginBottom: 'var(--space-2xl)' }}>
          <div style={{ display: 'flex', gap: 'var(--space-md)', alignItems: 'center' }}>
            <div style={{ width: '32px', height: '32px', borderRadius: '50%', background: 'var(--color-accent-2)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontWeight: 'bold' }}>1</div>
            <div><strong>Word Order</strong> (4 questions)</div>
          </div>
          <div style={{ display: 'flex', gap: 'var(--space-md)', alignItems: 'center' }}>
            <div style={{ width: '32px', height: '32px', borderRadius: '50%', background: 'var(--color-accent)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--color-ink)', fontWeight: 'bold' }}>2</div>
            <div><strong>Vocabulary</strong> (3 questions)</div>
          </div>
          <div style={{ display: 'flex', gap: 'var(--space-md)', alignItems: 'center' }}>
            <div style={{ width: '32px', height: '32px', borderRadius: '50%', background: 'var(--color-accent-3)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontWeight: 'bold' }}>3</div>
            <div><strong>Short Response</strong> (3 questions)</div>
          </div>
        </div>
        <button className="btn btn--lg" onClick={() => setStarted(true)} style={{ width: '100%', justifyContent: 'center' }}>
          Start Test
        </button>
      </main>
    );
  }

  if (loading || !currentQ) {
    return (
      <main className="page section" style={{ display: 'flex', justifyContent: 'center', paddingTop: '20vh' }}>
        <div className="typing-dots"><span /><span /><span /></div>
      </main>
    );
  }

  // The Test Wizard UI
  return (
    <main className="page section" style={{ maxWidth: '700px', margin: '0 auto' }}>
      
      {/* Top Progress */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-2xl)' }}>
        <span className="mono-label" style={{ fontSize: 'var(--text-sm)' }}>
          {currentIndex + 1} / {questions.length}
        </span>
        <div style={{ flex: 1, height: '4px', background: 'var(--color-rule)', marginLeft: 'var(--space-md)', borderRadius: '2px', overflow: 'hidden' }}>
          <div style={{ height: '100%', background: 'var(--color-accent-3)', width: `${((currentIndex + 1) / questions.length) * 100}%`, transition: 'width 0.3s ease' }}></div>
        </div>
      </div>

      <div style={{ minHeight: '350px' }}>
        {/* Word Order */}
        {currentQ.type === "word_order" && (
          <div className="animation-fade-in">
            <h2 style={{ marginBottom: 'var(--space-xl)' }}>Put the words in the correct order:</h2>
            
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-sm)', marginBottom: 'var(--space-2xl)', minHeight: '60px', padding: 'var(--space-md)', background: 'var(--color-paper-2)', border: '2px dashed var(--color-rule)', borderRadius: '16px' }}>
              {woOrder.length === 0 && <span style={{ color: 'var(--color-ink-2)', fontStyle: 'italic' }}>Select words below...</span>}
              {woOrder.map((w, i) => (
                <button key={i} onClick={() => handleWoClick(w)} className="btn" style={{ background: 'var(--color-paper)', border: '1px solid var(--color-rule)', boxShadow: 'none' }}>
                  {w}
                </button>
              ))}
            </div>

            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-sm)' }}>
              {currentQ.jumbled?.map((w, i) => {
                const isSelected = woOrder.includes(w);
                return (
                  <button 
                    key={i} 
                    onClick={() => handleWoClick(w)} 
                    disabled={isSelected}
                    className="btn btn--soft"
                    style={{ 
                      opacity: isSelected ? 0.3 : 1, 
                      transform: isSelected ? 'scale(0.95)' : 'none',
                      transition: 'all 0.2s ease'
                    }}
                  >
                    {w}
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* Vocabulary */}
        {currentQ.type === "vocabulary" && (
          <div className="animation-fade-in">
            <h2 style={{ marginBottom: 'var(--space-xl)' }}>Select the missing word:</h2>
            <div style={{ fontSize: 'var(--text-2xl)', fontWeight: 600, marginBottom: 'var(--space-2xl)', background: 'var(--color-paper-2)', padding: 'var(--space-xl)', borderRadius: 'var(--radius-card)', textAlign: 'center' }}>
              {currentQ.prompt?.replace('___', '______')}
            </div>
            
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-md)' }}>
              {currentQ.options?.map((opt, i) => (
                <button 
                  key={i} 
                  onClick={() => setVocChoice(i)}
                  className={`btn ${vocChoice === i ? '' : 'btn--soft'}`}
                  style={{ 
                    justifyContent: 'center', 
                    padding: 'var(--space-md)', 
                    fontSize: 'var(--text-lg)',
                    boxShadow: vocChoice === i ? '0 4px 12px var(--color-cast-cyan)' : 'none',
                    backgroundColor: vocChoice === i ? 'var(--color-accent-2)' : undefined,
                    color: vocChoice === i ? '#fff' : undefined,
                  }}
                >
                  {opt}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Short Response */}
        {currentQ.type === "short_response" && (
          <div className="animation-fade-in">
            <h2 style={{ marginBottom: 'var(--space-xl)' }}>Answer the question:</h2>
            <div className="bubble bubble--ai" style={{ marginBottom: 'var(--space-lg)' }}>
              {currentQ.prompt}
            </div>
            
            <textarea
              className="speak-input"
              value={srText}
              onChange={(e) => setSrText(e.target.value)}
              placeholder="Schreib deine Antwort auf Deutsch..."
              style={{ width: '100%', minHeight: '120px', borderRadius: '16px' }}
              autoFocus
            />
          </div>
        )}
      </div>

      <div style={{ marginTop: 'var(--space-3xl)', display: 'flex', justifyContent: 'flex-end', borderTop: '1px solid var(--color-rule)', paddingTop: 'var(--space-lg)' }}>
        <button 
          className="btn btn--lg" 
          onClick={handleNext}
          disabled={
            (currentQ.type === "word_order" && woOrder.length !== currentQ.jumbled?.length) ||
            (currentQ.type === "vocabulary" && vocChoice === null) ||
            (currentQ.type === "short_response" && srText.trim().length < 2)
          }
        >
          {currentIndex === questions.length - 1 ? 'Submit Test' : 'Next Question'}
        </button>
      </div>
      
      <style dangerouslySetInnerHTML={{__html: `
        .animation-fade-in { animation: fade-in 0.3s ease-out; }
        @keyframes fade-in { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
      `}} />
    </main>
  );
}
