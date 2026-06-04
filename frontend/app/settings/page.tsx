'use client'

import { useEffect, useState } from 'react'
import {
  getPreferences, updatePreferences, getKeyStatus, setApiKey, testApiKey,
  getModels, ModelOption, KeyStatus,
} from '@/lib/settings'
import styles from '../onboard/onboard.module.css'

export default function SettingsPage() {
  const [name, setName] = useState('')
  const [convModel, setConvModel] = useState('')
  const [analysisModel, setAnalysisModel] = useState('')
  const [models, setModels] = useState<ModelOption[]>([])
  const [status, setStatus] = useState<KeyStatus>({ openrouter: false, openai: false, deepl: false })
  const [keys, setKeys] = useState({ openrouter: '', openai: '', deepl: '' })
  const [testResult, setTestResult] = useState<Record<string, string>>({})
  const [saved, setSaved] = useState(false)
  const [saveError, setSaveError] = useState('')
  const [keyError, setKeyError] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      getPreferences().then((p) => {
        setName(p.user_name)
        setConvModel(p.conv_model)
        setAnalysisModel(p.analysis_model)
      }).catch(() => {}),
      getKeyStatus().then(setStatus).catch(() => {}),
      getModels().then(setModels).catch(() => setModels([])),
    ]).finally(() => setLoading(false))
  }, [])

  const saveAccount = async () => {
    setSaveError('')
    try {
      await updatePreferences({ user_name: name, conv_model: convModel, analysis_model: analysisModel })
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : 'Save failed — is the backend running?')
    }
  }

  const saveKey = async (svc: 'openrouter' | 'openai' | 'deepl') => {
    if (!keys[svc]) return
    setKeyError((k) => ({ ...k, [svc]: '' }))
    try {
      await setApiKey(svc, keys[svc])
      const res = await testApiKey(svc)
      setTestResult((t) => ({ ...t, [svc]: res.ok ? '✓ Connected' : `✗ ${res.detail ?? 'failed'}` }))
      setStatus(await getKeyStatus())
      setKeys((k) => ({ ...k, [svc]: '' }))
    } catch (e) {
      setKeyError((k) => ({ ...k, [svc]: e instanceof Error ? e.message : 'Failed to save key' }))
    }
  }

  return (
    <main className={styles.wrap}>
      <div className={styles.card}>
        <h1>Settings</h1>

        {loading && <p style={{ opacity: 0.5 }}>Loading…</p>}

        <h2>Account</h2>
        <label>Name</label>
        <input className={styles.input} value={name} onChange={(e) => setName(e.target.value)} />

        <h2>AI Configuration</h2>
        <label>Conversation model</label>
        <select className={styles.input} value={convModel} onChange={(e) => setConvModel(e.target.value)}>
          <option value={convModel}>{convModel}</option>
          {models.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
        </select>
        <label>Analysis model</label>
        <select className={styles.input} value={analysisModel} onChange={(e) => setAnalysisModel(e.target.value)}>
          <option value={analysisModel}>{analysisModel}</option>
          {models.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
        </select>
        <button className={styles.btn} onClick={saveAccount}>{saved ? 'Saved ✓' : 'Save'}</button>
        {saveError && <p style={{ color: 'red', fontSize: '0.85rem', marginTop: '0.25rem' }}>{saveError}</p>}

        <h2>API Keys</h2>
        {(['openrouter', 'openai', 'deepl'] as const).map((svc) => (
          <div key={svc} className={styles.keyRow}>
            <label>{svc} {status[svc] ? '✓' : '✗'}</label>
            <div className={styles.keyInput}>
              <input
                className={styles.input}
                type="password"
                value={keys[svc]}
                onChange={(e) => setKeys((k) => ({ ...k, [svc]: e.target.value }))}
                placeholder={status[svc] ? 'Replace key…' : `${svc} key`}
              />
              <button className={styles.btnGhost} onClick={() => saveKey(svc)}>Save</button>
            </div>
            {testResult[svc] && <span className={styles.test}>{testResult[svc]}</span>}
            {keyError[svc] && <span style={{ color: 'red', fontSize: '0.8rem' }}>{keyError[svc]}</span>}
          </div>
        ))}
      </div>
    </main>
  )
}
