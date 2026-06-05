"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer,
  BarChart, Bar, AreaChart, Area
} from "recharts";

type AnalyticsData = {
  week: string;
  sessions: number;
  total_minutes: number;
  turns_total: number;
  error_rate_trend: number[];
  best_day: string;
  pattern_improvements: string[];
  pattern_regressions: string[];
  words_added_to_confident: number;
};

// Mock data for charts since backend only returns array of floats for trend currently
const scoreData = [
  { name: "W1", score: 40 },
  { name: "W2", score: 55 },
  { name: "W3", score: 65 },
  { name: "W4", score: 72 },
  { name: "W5", score: 85 },
];

const errorData = [
  { name: "W1", word_order: 15, gender: 10, case: 5 },
  { name: "W2", word_order: 12, gender: 8, case: 6 },
  { name: "W3", word_order: 8, gender: 5, case: 8 },
  { name: "W4", word_order: 5, gender: 3, case: 5 },
  { name: "W5", word_order: 2, gender: 2, case: 3 },
];

const vocabData = [
  { name: "W1", words: 20 },
  { name: "W2", words: 45 },
  { name: "W3", words: 80 },
  { name: "W4", words: 120 },
  { name: "W5", words: 180 },
];

const PATTERN_NAMES: Record<string, string> = {
  "V2_violation": "Verb Position (V2)",
  "verb_final_missing": "Verb at end of subordinate clause",
  "false_friend_gift": "False Friend (Gift)",
  "false_friend_bekommen": "False Friend (Bekommen)",
  "noun_not_capitalised": "Noun Capitalization",
  "gender_article_wrong": "Der/Die/Das (Gender)",
  "dativ_after_mit": "Dative after 'mit'",
  "accusative_after_durch": "Accusative after 'durch'",
  "dativ_after_in": "Dative after 'in'",
  "dativ_after_zu": "Dative after 'zu'",
};

const formatPattern = (key: string) => {
  if (PATTERN_NAMES[key]) return PATTERN_NAMES[key];
  return key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
};

export default function AnalyticsPage() {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("http://localhost:8000/analytics/dashboard")
      .then((res) => res.json())
      .then((d) => {
        setData(d);
        setLoading(false);
      })
      .catch((e) => {
        console.error(e);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <main className="page section">
        <div className="section__head">
          <div className="typing-dots"><span /><span /><span /></div>
        </div>
      </main>
    );
  }

  return (
    <main className="page section" style={{ paddingBottom: 'var(--space-4xl)' }}>
      <div className="section__head">
        <h1>Your Progress</h1>
        <p>A deeper look at your conversational fluency.</p>
      </div>

      {/* Weekly Report Card */}
      <section style={{ marginBottom: "var(--space-2xl)" }}>
        <article className="cell tint-paper" style={{ borderLeft: "4px solid var(--color-accent-3)" }}>
          <span className="mono-label cell__tag">Weekly Report • {data?.week}</span>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-lg)", marginTop: "var(--space-sm)" }}>
            <div style={{ flex: "1 1 200px" }}>
              <h4 style={{ color: "var(--color-ink-2)" }}>What improved</h4>
              <p style={{ fontWeight: 600, fontSize: "var(--text-lg)" }}>
                {data?.pattern_improvements.map(formatPattern).join(", ") || "Word order in subordinate clauses"}
              </p>
            </div>
            <div style={{ flex: "1 1 200px" }}>
              <h4 style={{ color: "var(--color-ink-2)" }}>What to watch</h4>
              <p style={{ fontWeight: 600, fontSize: "var(--text-lg)" }}>
                {data?.pattern_regressions.map(formatPattern).join(", ") || "Dative vs. Accusative prepositions"}
              </p>
            </div>
            <div style={{ flex: "1 1 200px" }}>
              <h4 style={{ color: "var(--color-ink-2)" }}>Focus for next week</h4>
              <p style={{ fontWeight: 600, fontSize: "var(--text-lg)" }}>
                Take the weekly CEFR test to recalibrate.
              </p>
            </div>
          </div>
        </article>
      </section>

      {/* Chart Bento Grid */}
      <div className="bento">
        {/* Score Trend */}
        <article className="cell span-2x1 tint-paper">
          <span className="mono-label cell__tag">Test Scores</span>
          <h3>Fluency Trend</h3>
          <div style={{ width: "100%", height: 250, marginTop: "var(--space-md)" }}>
            <ResponsiveContainer>
              <LineChart data={scoreData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-rule)" vertical={false} />
                <XAxis dataKey="name" stroke="var(--color-ink-2)" fontSize={12} tickLine={false} axisLine={false} />
                <YAxis stroke="var(--color-ink-2)" fontSize={12} tickLine={false} axisLine={false} />
                <RechartsTooltip 
                  contentStyle={{ backgroundColor: 'var(--color-paper-2)', borderRadius: '12px', border: '1px solid var(--color-rule)', color: 'var(--color-ink)' }}
                />
                <Line type="monotone" dataKey="score" stroke="var(--color-accent-3)" strokeWidth={4} dot={{ r: 6, fill: "var(--color-accent-3)", strokeWidth: 0 }} activeDot={{ r: 8 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </article>

        {/* Highlight Stats */}
        <article className="cell tint-pear">
          <span className="mono-label cell__tag" style={{ color: "var(--color-ink-2)" }}>This Week</span>
          <div style={{ marginTop: "var(--space-lg)" }}>
            <div style={{ marginBottom: "var(--space-md)" }}>
              <p style={{ fontSize: "var(--text-xs)", textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--color-ink-2)" }}>Practice Time</p>
              <p style={{ fontSize: "var(--text-2xl)", fontWeight: 700, lineHeight: 1.1 }}>{data?.total_minutes} min</p>
            </div>
            <div style={{ marginBottom: "var(--space-md)" }}>
              <p style={{ fontSize: "var(--text-xs)", textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--color-ink-2)" }}>Conversations</p>
              <p style={{ fontSize: "var(--text-2xl)", fontWeight: 700, lineHeight: 1.1 }}>{data?.sessions}</p>
            </div>
            <div>
              <p style={{ fontSize: "var(--text-xs)", textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--color-ink-2)" }}>New Confident Words</p>
              <p style={{ fontSize: "var(--text-2xl)", fontWeight: 700, lineHeight: 1.1 }}>+{data?.words_added_to_confident}</p>
            </div>
          </div>
        </article>

        {/* Error Breakdown */}
        <article className="cell span-2x1 tint-paper">
          <span className="mono-label cell__tag">Error Breakdown</span>
          <h3>Mistakes by Category</h3>
          <div style={{ width: "100%", height: 250, marginTop: "var(--space-md)" }}>
            <ResponsiveContainer>
              <BarChart data={errorData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-rule)" vertical={false} />
                <XAxis dataKey="name" stroke="var(--color-ink-2)" fontSize={12} tickLine={false} axisLine={false} />
                <YAxis stroke="var(--color-ink-2)" fontSize={12} tickLine={false} axisLine={false} />
                <RechartsTooltip 
                  cursor={{ fill: 'var(--color-rule)' }}
                  contentStyle={{ backgroundColor: 'var(--color-paper-2)', borderRadius: '12px', border: '1px solid var(--color-rule)', color: 'var(--color-ink)' }}
                />
                <Bar dataKey="word_order" stackId="a" fill="var(--color-accent-3)" radius={[0, 0, 4, 4]} />
                <Bar dataKey="gender" stackId="a" fill="var(--color-accent-2)" />
                <Bar dataKey="case" stackId="a" fill="var(--color-accent)" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </article>

        {/* Vocab Growth */}
        <article className="cell tint-cyan">
          <span className="mono-label cell__tag">Vocabulary</span>
          <h3>Confident Words</h3>
          <div style={{ width: "100%", height: 200, marginTop: "var(--space-md)" }}>
            <ResponsiveContainer>
              <AreaChart data={vocabData} margin={{ top: 5, right: 0, bottom: 0, left: -25 }}>
                <defs>
                  <linearGradient id="colorWords" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--color-accent-2)" stopOpacity={0.8}/>
                    <stop offset="95%" stopColor="var(--color-accent-2)" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <XAxis dataKey="name" stroke="var(--color-ink-2)" fontSize={10} tickLine={false} axisLine={false} />
                <YAxis stroke="var(--color-ink-2)" fontSize={10} tickLine={false} axisLine={false} />
                <RechartsTooltip 
                  contentStyle={{ backgroundColor: 'var(--color-paper-2)', borderRadius: '8px', border: 'none', color: 'var(--color-ink)' }}
                />
                <Area type="monotone" dataKey="words" stroke="var(--color-accent-2)" strokeWidth={3} fillOpacity={1} fill="url(#colorWords)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </article>
      </div>
      
      <div style={{ marginTop: 'var(--space-2xl)', textAlign: 'center' }}>
        <Link href="/dashboard" className="btn btn--soft">Back to Dashboard</Link>
      </div>
    </main>
  );
}
