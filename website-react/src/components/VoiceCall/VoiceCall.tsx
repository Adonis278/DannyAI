import { useState, useRef, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Phone, PhoneOff, Mic, MicOff, Volume2 } from 'lucide-react';
import './VoiceCall.css';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/* ------------------------------------------------------------------ */
/* Web Speech API type shims (not all TS libs include these)           */
/* ------------------------------------------------------------------ */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type SpeechRecognitionType = any;

/* ------------------------------------------------------------------ */
/* Types                                                               */
/* ------------------------------------------------------------------ */
interface TranscriptEntry {
  id: number;
  role: 'user' | 'assistant';
  text: string;
}

type CallState = 'idle' | 'connecting' | 'active' | 'processing' | 'speaking' | 'ended';

/* ------------------------------------------------------------------ */
/* Component                                                           */
/* ------------------------------------------------------------------ */
export default function VoiceCall() {
  const [callState, setCallState] = useState<CallState>('idle');
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([]);
  const [liveText, setLiveText] = useState('');
  const [elapsed, setElapsed] = useState(0);
  const [isMuted, setIsMuted] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [ttsAvailable, setTtsAvailable] = useState<boolean | null>(null);

  const recognitionRef = useRef<SpeechRecognitionType | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const transcriptEndRef = useRef<HTMLDivElement>(null);
  const callStartRef = useRef<number>(0);
  const idleTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  /* ---- helpers --------------------------------------------------- */
  const fmt = (s: number) => {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return `${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`;
  };

  const scrollToBottom = useCallback(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(scrollToBottom, [transcript, liveText, scrollToBottom]);

  /* Check TTS availability on mount */
  useEffect(() => {
    fetch(`${API_URL}/health`)
      .then(r => r.json())
      .then(() => setTtsAvailable(true))
      .catch(() => setTtsAvailable(false));
  }, []);

  /* ---- speech recognition setup ---------------------------------- */
  const createRecognition = useCallback(() => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SR) return null;

    const rec = new SR();
    rec.continuous = true;
    rec.interimResults = true;
    rec.lang = 'en-US';
    return rec;
  }, []);

  /* ---- TTS: prefer Polly via API, fall back to browser ----------- */
  const speak = useCallback(
    async (text: string): Promise<void> => {
      // Try Polly endpoint first
      if (ttsAvailable) {
        try {
          const res = await fetch(`${API_URL}/tts`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text }),
          });
          if (res.ok) {
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            return new Promise<void>((resolve) => {
              const audio = new Audio(url);
              audioRef.current = audio;
              audio.onended = () => {
                URL.revokeObjectURL(url);
                resolve();
              };
              audio.onerror = () => {
                URL.revokeObjectURL(url);
                resolve();
              };
              audio.play().catch(() => resolve());
            });
          }
        } catch {
          /* fall through to browser TTS */
        }
      }

      // Browser SpeechSynthesis fallback
      return new Promise<void>((resolve) => {
        const synth = window.speechSynthesis;
        if (!synth) { resolve(); return; }

        // Clean markdown
        const clean = text
          .replace(/\*\*(.*?)\*\*/g, '$1')
          .replace(/\*(.*?)\*/g, '$1')
          .replace(/[•\-#]/g, '')
          .replace(/[✅⚠️📅📍🦷🚨💰🛡️❓🕐📋🏥😊]/g, '')
          .replace(/\n/g, '. ');

        const utter = new SpeechSynthesisUtterance(clean);
        utter.rate = 1.05;
        utter.pitch = 1.0;
        // Try to pick a good voice
        const voices = synth.getVoices();
        const preferred = voices.find(
          (v) =>
            v.name.includes('Samantha') ||
            v.name.includes('Google US English') ||
            v.name.includes('Microsoft Zira')
        );
        if (preferred) utter.voice = preferred;
        utter.onend = () => resolve();
        utter.onerror = () => resolve();
        synth.speak(utter);
      });
    },
    [ttsAvailable]
  );

  /* ---- core: handle one listen-respond turn ---------------------- */
  const processUserSpeech = useCallback(
    async (text: string) => {
      if (!text.trim()) return;

      // Add user entry
      const userEntry: TranscriptEntry = {
        id: Date.now(),
        role: 'user',
        text: text.trim(),
      };
      setTranscript((prev) => [...prev, userEntry]);
      setLiveText('');
      setCallState('processing');

      try {
        // Send to agent API
        const res = await fetch(`${API_URL}/chat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: text.trim(), session_id: sessionId }),
        });

        if (!res.ok) throw new Error(`API ${res.status}`);
        const data = await res.json();
        if (data.session_id) setSessionId(data.session_id);

        const reply = data.reply as string;

        // Add assistant entry
        const assistantEntry: TranscriptEntry = {
          id: Date.now() + 1,
          role: 'assistant',
          text: reply,
        };
        setTranscript((prev) => [...prev, assistantEntry]);

        // Speak the reply
        setCallState('speaking');
        await speak(reply);

        // Back to active listening
        setCallState('active');
      } catch (err) {
        console.error('[VoiceCall] Agent error', err);
        const errEntry: TranscriptEntry = {
          id: Date.now() + 1,
          role: 'assistant',
          text: "I'm sorry, I had a technical issue. Could you repeat that?",
        };
        setTranscript((prev) => [...prev, errEntry]);
        setCallState('active');
      }
    },
    [sessionId, speak]
  );

  /* ---- start / stop call ----------------------------------------- */
  const startCall = useCallback(() => {
    const rec = createRecognition();
    if (!rec) {
      alert('Your browser does not support speech recognition. Please use Chrome or Edge.');
      return;
    }

    setCallState('connecting');
    setTranscript([]);
    setElapsed(0);
    setSessionId(null);
    callStartRef.current = Date.now();

    // Simulate brief connecting delay
    setTimeout(async () => {
      setCallState('active');

      // Start timer
      timerRef.current = setInterval(() => {
        setElapsed(Math.floor((Date.now() - callStartRef.current) / 1000));
      }, 1000);

      // Danny's greeting
      const greeting =
        "Hi there! I'm Danny, your AI dental assistant. How can I help you today?";
      setTranscript([{ id: 0, role: 'assistant', text: greeting }]);

      setCallState('speaking');
      await speak(greeting);
      setCallState('active');

      // Start listening
      recognitionRef.current = rec;
      let finalBuffer = '';

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      rec.onresult = (e: any) => {
        let interim = '';
        let final_ = '';
        for (let i = e.resultIndex; i < e.results.length; i++) {
          const t = e.results[i][0].transcript;
          if (e.results[i].isFinal) {
            final_ += t;
          } else {
            interim += t;
          }
        }

        if (final_) {
          finalBuffer += ' ' + final_;
          setLiveText(finalBuffer.trim());

          // Reset idle timer — process after 1.5 s of silence
          if (idleTimerRef.current) clearTimeout(idleTimerRef.current);
          idleTimerRef.current = setTimeout(() => {
            const toSend = finalBuffer.trim();
            finalBuffer = '';
            if (toSend) {
              // Pause recognition while Danny processes + speaks
              rec.stop();
              processUserSpeech(toSend).then(() => {
                // Restart recognition after Danny replies
                try { rec.start(); } catch { /* already running */ }
              });
            }
          }, 1500);
        } else if (interim) {
          setLiveText((finalBuffer + ' ' + interim).trim());
        }
      };

      rec.onerror = (e: Event) => {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const errorEvent = e as any;
        if (errorEvent.error !== 'no-speech' && errorEvent.error !== 'aborted') {
          console.error('[VoiceCall] Recognition error:', errorEvent.error);
        }
      };

      rec.onend = () => {
        // Auto-restart recognition if call is still active
        if (
          recognitionRef.current &&
          !['ended', 'idle'].includes(
            (document.querySelector('[data-call-state]') as HTMLElement)?.dataset.callState || 'idle'
          )
        ) {
          try { rec.start(); } catch { /* noop */ }
        }
      };

      try { rec.start(); } catch { /* noop */ }
    }, 1200);
  }, [createRecognition, speak, processUserSpeech]);

  const endCall = useCallback(() => {
    // Stop recognition
    if (recognitionRef.current) {
      recognitionRef.current.onend = null;
      recognitionRef.current.onresult = null;
      recognitionRef.current.abort();
      recognitionRef.current = null;
    }

    // Stop timer
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }

    // Stop idle timer
    if (idleTimerRef.current) {
      clearTimeout(idleTimerRef.current);
      idleTimerRef.current = null;
    }

    // Stop any playing audio
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    window.speechSynthesis?.cancel();

    // Clean up API session
    if (sessionId) {
      fetch(`${API_URL}/session/${sessionId}`, { method: 'DELETE' }).catch(() => {});
    }

    setCallState('ended');
    setLiveText('');

    // Reset after a moment
    setTimeout(() => setCallState('idle'), 3000);
  }, [sessionId]);

  const toggleMute = () => {
    setIsMuted((m) => {
      if (recognitionRef.current) {
        if (!m) {
          recognitionRef.current.abort();
        } else {
          try { recognitionRef.current.start(); } catch { /* already running */ }
        }
      }
      return !m;
    });
  };

  /* Cleanup on unmount */
  useEffect(() => {
    return () => {
      if (recognitionRef.current) { recognitionRef.current.abort(); }
      if (timerRef.current) { clearInterval(timerRef.current); }
      if (idleTimerRef.current) { clearTimeout(idleTimerRef.current); }
      window.speechSynthesis?.cancel();
    };
  }, []);

  /* ---- render ---------------------------------------------------- */
  const isCallActive = ['active', 'processing', 'speaking', 'connecting'].includes(callState);

  return (
    <div className="voice" data-call-state={callState}>
      <AnimatePresence mode="wait">
        {!isCallActive && callState !== 'ended' && (
          /* ─── Idle: Call button ─── */
          <motion.div
            key="idle"
            className="voice__idle"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9 }}
            transition={{ duration: 0.3 }}
          >
            <button className="voice__call-btn" onClick={startCall}>
              <div className="voice__call-btn-ring" />
              <div className="voice__call-btn-ring voice__call-btn-ring--2" />
              <Phone size={28} />
            </button>
            <p className="voice__call-label">Tap to call Danny</p>
            <p className="voice__call-hint">
              Uses your microphone &bull; Works best in Chrome / Edge
            </p>
          </motion.div>
        )}

        {callState === 'connecting' && (
          /* ─── Connecting ─── */
          <motion.div
            key="connecting"
            className="voice__connecting"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <div className="voice__connecting-ring" />
            <p className="voice__connecting-text">Calling Danny AI...</p>
          </motion.div>
        )}

        {['active', 'processing', 'speaking'].includes(callState) && (
          /* ─── Active call ─── */
          <motion.div
            key="active"
            className="voice__active"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.4 }}
          >
            {/* Call info bar */}
            <div className="voice__info">
              <div className="voice__info-left">
                <div className="voice__avatar">
                  <Phone size={18} />
                </div>
                <div>
                  <div className="voice__caller-name">Danny AI</div>
                  <div className="voice__call-timer">{fmt(elapsed)}</div>
                </div>
              </div>
              <div className="voice__status-pill">
                {callState === 'processing' && (
                  <><span className="voice__status-dot voice__status-dot--thinking" /> Thinking...</>
                )}
                {callState === 'speaking' && (
                  <><Volume2 size={12} className="voice__status-icon" /> Speaking</>
                )}
                {callState === 'active' && (
                  <><span className="voice__status-dot voice__status-dot--live" /> Listening</>
                )}
              </div>
            </div>

            {/* Waveform visualiser */}
            <div className="voice__waveform">
              {Array.from({ length: 32 }).map((_, i) => (
                <div
                  key={i}
                  className={`voice__bar ${callState === 'speaking' ? 'voice__bar--speaking' : ''} ${callState === 'active' && !isMuted ? 'voice__bar--listening' : ''}`}
                  style={{
                    animationDelay: `${i * 0.04}s`,
                    height: callState === 'processing' ? '4px' : undefined,
                  }}
                />
              ))}
            </div>

            {/* Live transcript */}
            <div className="voice__transcript">
              {transcript.map((entry) => (
                <div key={entry.id} className={`voice__line voice__line--${entry.role}`}>
                  <span className="voice__line-role">
                    {entry.role === 'assistant' ? 'Danny' : 'You'}
                  </span>
                  <span className="voice__line-text">{entry.text}</span>
                </div>
              ))}
              {liveText && (
                <div className="voice__line voice__line--user voice__line--live">
                  <span className="voice__line-role">You</span>
                  <span className="voice__line-text">{liveText}</span>
                </div>
              )}
              <div ref={transcriptEndRef} />
            </div>

            {/* Call controls */}
            <div className="voice__controls">
              <button
                className={`voice__ctrl-btn ${isMuted ? 'voice__ctrl-btn--active' : ''}`}
                onClick={toggleMute}
                title={isMuted ? 'Unmute' : 'Mute'}
              >
                {isMuted ? <MicOff size={20} /> : <Mic size={20} />}
              </button>
              <button className="voice__ctrl-btn voice__ctrl-btn--end" onClick={endCall} title="End call">
                <PhoneOff size={22} />
              </button>
            </div>
          </motion.div>
        )}

        {callState === 'ended' && (
          /* ─── Call ended ─── */
          <motion.div
            key="ended"
            className="voice__ended"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <p className="voice__ended-text">Call ended</p>
            <p className="voice__ended-duration">{fmt(elapsed)}</p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
