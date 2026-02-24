import { useState, useRef, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, Bot, User, RotateCcw, Sparkles, Wifi, WifiOff, MessageSquare, Phone } from 'lucide-react';
import VoiceCall from '../VoiceCall/VoiceCall';
import './Demo.css';

// API backend URL — the FastAPI server wrapping the Strands agent
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface Message {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

const INITIAL_MESSAGE: Message = {
  id: 0,
  role: 'assistant',
  content:
    "Hi there! I'm Danny, your AI dental assistant. I can help you schedule appointments, check insurance coverage, answer questions about our services, and more. How can I help you today?",
  timestamp: new Date(),
};

const SUGGESTED_PROMPTS = [
  'I need to schedule a cleaning',
  'Do you accept Delta Dental?',
  'What are your office hours?',
  'I have a toothache — is this an emergency?',
];

// Simulated Danny responses with conversation context awareness
function getDannyResponse(userMessage: string, history: Message[]): string {
  const msg = userMessage.toLowerCase();

  // Check what the last assistant message was about (conversation context)
  const lastAssistantMsg = [...history].reverse().find(m => m.role === 'assistant')?.content.toLowerCase() || '';
  const isInSchedulingFlow = lastAssistantMsg.includes('which time works best') || lastAssistantMsg.includes('openings this week');
  const isInEmergencyFlow = lastAssistantMsg.includes('book that emergency appointment');
  const isAskingForName = lastAssistantMsg.includes('may i have your full name');
  const isAskingForContact = lastAssistantMsg.includes('phone number or email');

  // ── Appointment time selection (user picks a slot) ──
  if (isInSchedulingFlow) {
    // Detect time/day references
    const hasThursday = msg.includes('thursday') || msg.includes('thurs') || msg.includes('26');
    const hasFriday = msg.includes('friday') || msg.includes('fri') || msg.includes('27');
    const has10 = msg.includes('10') || msg.includes('ten');
    const has230 = msg.includes('2:30') || msg.includes('2 30') || msg.includes('230');
    const has9 = msg.includes('9') || msg.includes('nine');
    const has1130 = msg.includes('11:30') || msg.includes('11 30') || msg.includes('1130');

    let selectedSlot = '';
    if (hasThursday && has10) selectedSlot = 'Thursday, February 26 at 10:00 AM';
    else if (hasThursday && has230) selectedSlot = 'Thursday, February 26 at 2:30 PM';
    else if (hasFriday && has9) selectedSlot = 'Friday, February 27 at 9:00 AM';
    else if (hasFriday && has1130) selectedSlot = 'Friday, February 27 at 11:30 AM';
    else if (hasThursday) selectedSlot = 'Thursday, February 26 at 10:00 AM';
    else if (hasFriday) selectedSlot = 'Friday, February 27 at 9:00 AM';
    else if (has10) selectedSlot = 'Thursday, February 26 at 10:00 AM';
    else if (msg.includes('first') || msg.includes('1st') || msg.includes('earliest')) selectedSlot = 'Thursday, February 26 at 10:00 AM';
    else if (msg.includes('last') || msg.includes('latest')) selectedSlot = 'Friday, February 27 at 11:30 AM';

    if (selectedSlot) {
      return `Great choice! I'm booking you in for **${selectedSlot}** for a routine cleaning.\n\nTo complete the booking, may I have your full name please?`;
    }

    // Could not parse a slot — ask again, don't escalate
    return "I want to make sure I get the right time for you. Could you let me know which of these slots you'd prefer?\n\n• **Thursday, Feb 26** at 10:00 AM\n• **Thursday, Feb 26** at 2:30 PM\n• **Friday, Feb 27** at 9:00 AM\n• **Friday, Feb 27** at 11:30 AM";
  }

  // ── Collecting patient name for booking ──
  if (isAskingForName) {
    // Accept whatever they type as a name
    const name = userMessage.trim();
    if (name.length >= 2) {
      return `Thank you, **${name}**! And could I get a phone number or email address so we can send you a confirmation?`;
    }
    return "I didn't catch your name. Could you please tell me your full name so I can complete the booking?";
  }

  // ── Collecting contact info for booking ──
  if (isAskingForContact) {
    const hasPhone = msg.match(/\d{3}[-.]?\d{3}[-.]?\d{4}/) || msg.match(/\d{10}/) || msg.includes('phone');
    const hasEmail = msg.includes('@') || msg.includes('email');

    if (hasPhone || hasEmail || msg.length >= 5) {
      return "✅ **Your appointment is confirmed!**\n\n📅 **Thursday, February 26 at 10:00 AM**\n🦷 **Routine Cleaning**\n📍 **Bright Smile Dental** — 123 Main Street, Suite 100\n\nYou'll receive a confirmation text and email shortly. Please arrive **10 minutes early** to complete any paperwork.\n\nIs there anything else I can help you with?";
    }
    return "Could you share a phone number or email so we can send your appointment confirmation?";
  }

  // ── Emergency booking confirmation ──
  if (isInEmergencyFlow && (msg.includes('yes') || msg.includes('book') || msg.includes('please') || msg.includes('yeah') || msg.includes('sure'))) {
    return "✅ **Emergency appointment booked!**\n\n📅 **Today at 3:00 PM**\n🚨 **Emergency Exam**\n📍 **Bright Smile Dental** — 123 Main Street, Suite 100\n\nPlease arrive as soon as you can. If your pain worsens before then, call 911 or go to the nearest ER.\n\nWe'll take great care of you. See you soon!";
  }

  // ── Standard intent matching ──
  if (msg.includes('schedule') || msg.includes('appointment') || msg.includes('book') || msg.includes('cleaning')) {
    return "I'd love to help you schedule an appointment! We have several openings this week:\n\n• **Thursday, Feb 26** at 10:00 AM\n• **Thursday, Feb 26** at 2:30 PM\n• **Friday, Feb 27** at 9:00 AM\n• **Friday, Feb 27** at 11:30 AM\n\nWhich time works best for you? And will this be a routine cleaning, or is there something specific you'd like to address?";
  }

  if (msg.includes('insurance') || msg.includes('delta') || msg.includes('coverage') || msg.includes('accept')) {
    return "Great question! We work with most major dental insurance plans, including:\n\n• **Delta Dental** (Premier & PPO)\n• **Cigna Dental**\n• **MetLife**\n• **Aetna**\n• **United Healthcare Dental**\n\nIf you'd like, I can verify your specific coverage right now. Could you share your insurance ID number and date of birth?";
  }

  if (msg.includes('hour') || msg.includes('open') || msg.includes('when')) {
    return "Our office hours are:\n\n• **Monday – Friday:** 8:00 AM – 5:00 PM\n• **Saturday:** 9:00 AM – 2:00 PM\n• **Sunday:** Closed\n\nWe're also available for dental emergencies 24/7. Would you like to schedule an appointment?";
  }

  if (msg.includes('emergency') || msg.includes('pain') || msg.includes('toothache') || msg.includes('hurt')) {
    return "I'm sorry to hear you're in discomfort. Tooth pain can definitely be concerning.\n\n**If this is severe**, we can get you in for a same-day emergency visit. We have a slot available **today at 3:00 PM**.\n\n**What you can do right now:**\n• Take an over-the-counter pain reliever\n• Apply a cold compress to the outside of your cheek\n• Avoid very hot or cold foods\n\nWould you like me to book that emergency appointment?";
  }

  if (msg.includes('cost') || msg.includes('price') || msg.includes('how much')) {
    return "Here are our typical costs for common procedures:\n\n• **Routine Cleaning:** $75 – $150\n• **Deep Cleaning:** $150 – $350 per quadrant\n• **Exam & X-Rays:** $50 – $200\n• **Filling:** $100 – $300\n\nWith insurance, your out-of-pocket costs are usually much lower. Would you like me to check your specific coverage?";
  }

  if (msg.includes('cancel') || msg.includes('reschedule')) {
    return "I can help with that! To cancel or reschedule, I'll need:\n\n1. Your **full name** on the appointment\n2. The **date** of your scheduled visit\n\nPlease note our cancellation policy requires 24 hours notice. Would you like to reschedule for a different time?";
  }

  if (msg.includes('transfer') || msg.includes('person') || msg.includes('human') || msg.includes('staff')) {
    return "Of course! Let me connect you with one of our staff members. I'll pass along the details from our conversation so you don't have to repeat anything.\n\n*Transferring you now...*\n\nThank you for calling, and have a wonderful day! 😊";
  }

  if (msg.includes('hello') || msg.includes('hi') || msg.includes('hey')) {
    return "Hello! Welcome to Bright Smile Dental. I'm Danny, your AI assistant. I can help you with:\n\n• 📅 **Scheduling** appointments\n• 🛡️ **Insurance** verification\n• ❓ **Questions** about our services\n• 🚨 **Emergency** dental care\n\nWhat can I help you with today?";
  }

  if (msg.includes('thank') || msg.includes('bye') || msg.includes('goodbye')) {
    return "You're very welcome! If you need anything else, don't hesitate to call back. We're always here to help.\n\nHave a wonderful day! 🦷✨";
  }

  // ── Yes/no/affirmative handling (context-dependent) ──
  if (msg.match(/^(yes|yeah|yep|sure|ok|okay|please|yea|y)\b/)) {
    if (lastAssistantMsg.includes('schedule an appointment')) {
      return "Great! We have several openings this week:\n\n• **Thursday, Feb 26** at 10:00 AM\n• **Thursday, Feb 26** at 2:30 PM\n• **Friday, Feb 27** at 9:00 AM\n• **Friday, Feb 27** at 11:30 AM\n\nWhich time works best for you?";
    }
    if (lastAssistantMsg.includes('check your specific coverage')) {
      return "Perfect! To look up your coverage, I'll need:\n\n1. Your **insurance provider** name\n2. Your **member ID** number\n3. Your **date of birth**\n\nGo ahead whenever you're ready!";
    }
    return "Sure! What would you like help with? I can assist with scheduling, insurance questions, or general practice info.";
  }

  // ── Fallback — stay helpful, do NOT escalate to human ──
  return "I'd be happy to help with that! Here's what I can assist you with:\n\n• 📅 **Schedule** an appointment\n• 🛡️ **Check insurance** coverage\n• 🕐 **Office hours** and location\n• 🚨 **Emergency** dental care\n• 💰 **Pricing** information\n\nJust let me know what you need!";
}

export default function Demo() {
  const [messages, setMessages] = useState<Message[]>([INITIAL_MESSAGE]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isLive, setIsLive] = useState<boolean | null>(null); // null = checking
  const [mode, setMode] = useState<'chat' | 'voice'>('chat');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Check if the API backend is available on mount
  useEffect(() => {
    fetch(`${API_URL}/health`, { method: 'GET' })
      .then(res => res.json())
      .then(data => {
        setIsLive(data.status === 'ok');
        console.log('[DannyAI] API connected — live mode', data);
      })
      .catch(() => {
        setIsLive(false);
        console.log('[DannyAI] API not available — using simulated mode');
      });
  }, []);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(scrollToBottom, [messages, isTyping]);

  // ── Call the real Strands agent API ──
  const callAgentAPI = useCallback(async (text: string): Promise<string> => {
    const res = await fetch(`${API_URL}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text, session_id: sessionId }),
    });
    if (!res.ok) throw new Error(`API error ${res.status}`);
    const data = await res.json();
    // Persist session across turns so the agent keeps context
    if (data.session_id) setSessionId(data.session_id);
    return data.reply;
  }, [sessionId]);

  const sendMessage = async (text: string) => {
    if (!text.trim()) return;

    const userMsg: Message = {
      id: Date.now(),
      role: 'user',
      content: text.trim(),
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsTyping(true);

    try {
      let replyText: string;

      if (isLive) {
        // Live mode — real Strands agent with Calendly
        replyText = await callAgentAPI(text);
      } else {
        // Fallback — simulated responses
        await new Promise(r => setTimeout(r, 800 + Math.random() * 1200));
        replyText = getDannyResponse(text, [...messages, userMsg]);
      }

      const reply: Message = {
        id: Date.now() + 1,
        role: 'assistant',
        content: replyText,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, reply]);
    } catch (err) {
      console.error('[DannyAI] Agent API error, falling back to simulated', err);
      // Fallback to simulated on API failure
      const reply: Message = {
        id: Date.now() + 1,
        role: 'assistant',
        content: getDannyResponse(text, [...messages, userMsg]),
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, reply]);
    } finally {
      setIsTyping(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    sendMessage(input);
  };

  const handleReset = () => {
    // Clean up server session
    if (sessionId && isLive) {
      fetch(`${API_URL}/session/${sessionId}`, { method: 'DELETE' }).catch(() => {});
    }
    setMessages([INITIAL_MESSAGE]);
    setInput('');
    setIsTyping(false);
    setSessionId(null);
  };

  const formatContent = (content: string) => {
    // Simple markdown-like formatting
    return content.split('\n').map((line, i) => {
      // Bold
      const boldFormatted = line.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
      // Italic
      const italicFormatted = boldFormatted.replace(/\*(.*?)\*/g, '<em>$1</em>');
      // Bullet points
      if (line.startsWith('• ') || line.startsWith('- ')) {
        return (
          <div key={i} className="demo-msg__bullet" dangerouslySetInnerHTML={{ __html: italicFormatted }} />
        );
      }
      if (line.match(/^\d+\./)) {
        return (
          <div key={i} className="demo-msg__bullet" dangerouslySetInnerHTML={{ __html: italicFormatted }} />
        );
      }
      if (line.trim() === '') return <br key={i} />;
      return <p key={i} dangerouslySetInnerHTML={{ __html: italicFormatted }} />;
    });
  };

  return (
    <section id="demo" className="demo">
      <div className="container">
        <motion.div
          className="demo__header"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-80px' }}
          transition={{ duration: 0.6 }}
        >
          <h2 className="demo__title">
            <span className="demo__title-small">Try it yourself</span>
            <span className="demo__title-main">Talk to Danny.</span>
          </h2>
          <p className="demo__subtitle">
            Experience what your patients will hear. Ask about appointments, insurance, or office hours.
          </p>

          {/* Mode toggle */}
          <div className="demo__mode-toggle">
            <button
              className={`demo__mode-btn ${mode === 'chat' ? 'demo__mode-btn--active' : ''}`}
              onClick={() => setMode('chat')}
            >
              <MessageSquare size={16} />
              Chat
            </button>
            <button
              className={`demo__mode-btn ${mode === 'voice' ? 'demo__mode-btn--active' : ''}`}
              onClick={() => setMode('voice')}
            >
              <Phone size={16} />
              Voice Call
            </button>
          </div>
        </motion.div>

        {/* ─── Voice Call mode ─── */}
        {mode === 'voice' && (
          <motion.div
            className="demo__chat"
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-40px' }}
            transition={{ duration: 0.6, delay: 0.1 }}
          >
            <VoiceCall />
          </motion.div>
        )}

        {/* ─── Chat mode ─── */}
        {mode === 'chat' && (
        <motion.div
          className="demo__chat"
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-40px' }}
          transition={{ duration: 0.6, delay: 0.1 }}
        >
          {/* Chat Header */}
          <div className="demo__chat-header">
            <div className="demo__chat-identity">
              <div className="demo__chat-avatar">
                <Bot size={20} />
              </div>
              <div>
                <div className="demo__chat-name">Danny AI</div>
                <div className="demo__chat-status">
                  <span className="demo__chat-dot" />
                  {isLive === null
                    ? 'Connecting...'
                    : isLive
                      ? 'Live — Strands Agent + Calendly'
                      : 'Demo Mode — Simulated'}
                </div>
              </div>
            </div>
            <div className="demo__chat-header-right">
              <span className={`demo__live-badge ${isLive ? 'demo__live-badge--live' : ''}`} title={isLive ? 'Connected to real AI agent' : 'Using simulated responses'}>
                {isLive ? <Wifi size={12} /> : <WifiOff size={12} />}
                {isLive ? 'LIVE' : 'DEMO'}
              </span>
              <button className="demo__chat-reset" onClick={handleReset} title="Reset conversation">
                <RotateCcw size={16} />
              </button>
            </div>
          </div>

          {/* Messages */}
          <div className="demo__chat-messages">
            <AnimatePresence>
              {messages.map(msg => (
                <motion.div
                  key={msg.id}
                  className={`demo-msg demo-msg--${msg.role}`}
                  initial={{ opacity: 0, y: 12, scale: 0.97 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
                >
                  <div className="demo-msg__avatar">
                    {msg.role === 'assistant' ? <Bot size={16} /> : <User size={16} />}
                  </div>
                  <div className="demo-msg__bubble">
                    {msg.role === 'assistant' && (
                      <span className="demo-msg__sender">Danny AI</span>
                    )}
                    <div className="demo-msg__content">{formatContent(msg.content)}</div>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>

            {isTyping && (
              <motion.div
                className="demo-msg demo-msg--assistant"
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
              >
                <div className="demo-msg__avatar">
                  <Bot size={16} />
                </div>
                <div className="demo-msg__bubble">
                  <span className="demo-msg__sender">Danny AI</span>
                  <div className="demo-msg__typing">
                    <span /><span /><span />
                  </div>
                </div>
              </motion.div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Suggestions */}
          {messages.length <= 1 && (
            <div className="demo__suggestions">
              {SUGGESTED_PROMPTS.map((prompt, i) => (
                <button
                  key={i}
                  className="demo__suggestion"
                  onClick={() => sendMessage(prompt)}
                >
                  <Sparkles size={12} />
                  {prompt}
                </button>
              ))}
            </div>
          )}

          {/* Input */}
          <form className="demo__chat-input" onSubmit={handleSubmit}>
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={e => setInput(e.target.value)}
              placeholder="Type a message to Danny..."
              disabled={isTyping}
            />
            <button type="submit" disabled={!input.trim() || isTyping}>
              <Send size={18} />
            </button>
          </form>
        </motion.div>
        )}
      </div>
    </section>
  );
}
