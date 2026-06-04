'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import {
  updatePreferences, setApiKey, testApiKey, getModels, ModelOption,
} from '@/lib/settings'
import styles from './onboard.module.css'

export default function OnboardPage() {
  const router = useRouter()
  const [step, setStep] = useState(1)
  const [name, setName] = useState('')
  const [keys, setKeys] = useState({ openrouter: '', openai: '', deepl: '' })
  const [testResult, setTestResult] = useState<Record<string, string>>({})
  const [models, setModels] = useState<ModelOption[]>([])
  const [convModel, setConvModel] = useState('meta-llama/llama-3.3-70b-instruct')
  const [analysisModel, setAnalysisModel] = useState('deepseek/deepseek-v4-flash')
  const [filter, setFilter] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (step === 3) getModels().then(setModels).catch(() => setModels([]))
  }, [step])

  const saveKey = async (service: 'openrouter' | 'openai' | 'deepl') => {
    if (!keys[service]) return
    try {
      await setApiKey(service, keys[service])
      const res = await testApiKey(service)
      setTestResult((t) => ({ ...t, [service]: res.ok ? '✓ Connected' : `✗ ${res.detail ?? 'failed'}` }))
    } catch {
      setTestResult((t) => ({ ...t, [service]: '✗ Backend unreachable' }))
    }
  }

  const finish = async () => {
    setSaving(true)
    try {
      await updatePreferences({
        user_name: name || 'User',
        conv_model: convModel,
        analysis_model: analysisModel,
        onboarding_complete: true,
      })
      router.push('/')
    } catch {
      setSaving(false)
    }
  }

  const filtered = models.filter(
    (m) => m.id.toLowerCase().includes(filter.toLowerCase()) ||
           m.name.toLowerCase().includes(filter.toLowerCase())
  )

  return (
    <main className={styles.wrap}>
      <div className={styles.card}>
        <div className={styles.steps}>Step {step} of 3</div>

        {step === 1 && (
          <>
            <h1>Welcome to SprachBoot ⛵</h1>
            <p>What should I call you?</p>
            <input
              className={styles.input}
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Your name"
              autoFocus
            />
            <button className={styles.btn} disabled={!name} onClick={() => setStep(2)}>
              Next
            </button>
          </>
        )}

        {step === 2 && (
          <>
            <h1>API Keys</h1>
            <p>Stored securely in your OS keychain — never in a file.</p>
            {(['openrouter', 'openai', 'deepl'] as const).map((svc) => (
              <div key={svc} className={styles.keyRow}>
                <label>{svc}{svc === 'deepl' ? ' (optional)' : ''}</label>
                <div className={styles.keyInput}>
                  <input
                    className={styles.input}
                    type="password"
                    value={keys[svc]}
                    onChange={(e) => setKeys((k) => ({ ...k, [svc]: e.target.value }))}
                    placeholder={`${svc} key`}
                  />
                  <button className={styles.btnGhost} onClick={() => saveKey(svc)}>
                    Test
                  </button>
                </div>
                {testResult[svc] && <span className={styles.test}>{testResult[svc]}</span>}
              </div>
            ))}
            <div className={styles.row}>
              <button className={styles.btnGhost} onClick={() => setStep(1)}>Back</button>
              <button
                className={styles.btn}
                disabled={!keys.openrouter || !keys.openai}
                onClick={() => setStep(3)}
              >
                Next
              </button>
            </div>
          </>
        )}

        {step === 3 && (
          <>
            <h1>Choose your models</h1>
            <p>Defaults are recommended. Search to pick others.</p>
            <input
              className={styles.input}
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              placeholder="Filter models…"
            />
            <label>Conversation model</label>
            <select className={styles.input} value={convModel} onChange={(e) => setConvModel(e.target.value)}>
              <option value={convModel}>{convModel}</option>
              {filtered.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
            </select>
            <label>Analysis model</label>
            <select className={styles.input} value={analysisModel} onChange={(e) => setAnalysisModel(e.target.value)}>
              <option value={analysisModel}>{analysisModel}</option>
              {filtered.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
            </select>
            <div className={styles.row}>
              <button className={styles.btnGhost} onClick={() => setStep(2)}>Back</button>
              <button className={styles.btn} disabled={saving} onClick={finish}>
                {saving ? 'Saving…' : 'Finish'}
              </button>
            </div>
          </>
        )}
      </div>
    </main>
  )
}
