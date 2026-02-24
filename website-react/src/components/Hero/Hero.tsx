import { motion } from 'framer-motion';
import { ArrowRight, Sparkles } from 'lucide-react';
import './Hero.css';

export default function Hero() {
  return (
    <section className="hero">
      {/* Ambient glow */}
      <div className="hero__glow hero__glow--1" />
      <div className="hero__glow hero__glow--2" />
      <div className="hero__grid-bg" />

      <div className="container hero__container">
        <motion.div
          className="hero__content"
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
        >
          <motion.div
            className="hero__badge"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.2, duration: 0.5 }}
          >
            <Sparkles size={14} />
            <span>AI-Powered Dental Receptionist</span>
          </motion.div>

          <h1 className="hero__title">
            Never Miss a
            <br />
            <span className="hero__title-accent">Patient Call</span> Again
          </h1>

          <p className="hero__subtitle">
            Danny is your AI dental concierge that answers every call, books appointments, 
            verifies insurance, and delivers a human-like experience — 24/7. Built for 
            modern dental practices.
          </p>

          <div className="hero__actions">
            <a href="#demo" className="hero__btn hero__btn--primary">
              Try the Live Demo
              <ArrowRight size={18} />
            </a>
            <a href="#how-it-works" className="hero__btn hero__btn--secondary">
              See How It Works
            </a>
          </div>

          <div className="hero__social-proof">
            <div className="hero__avatars">
              {[1, 2, 3, 4].map(i => (
                <div key={i} className="hero__avatar" style={{ '--i': i } as React.CSSProperties}>
                  <svg viewBox="0 0 36 36" fill="none">
                    <circle cx="18" cy="18" r="18" fill={`hsl(${160 + i * 20}, 60%, ${35 + i * 5}%)`}/>
                    <text x="18" y="22" textAnchor="middle" fill="white" fontSize="14" fontWeight="600">
                      {['D', 'S', 'M', 'A'][i-1]}
                    </text>
                  </svg>
                </div>
              ))}
            </div>
            <span className="hero__social-text">
              Trusted by <strong>50+</strong> dental practices
            </span>
          </div>
        </motion.div>

        <motion.div
          className="hero__visual"
          initial={{ opacity: 0, x: 40 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.3, duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
        >
          <div className="hero__phone">
            <div className="hero__phone-notch" />
            <div className="hero__phone-screen">
              <div className="hero__phone-header">
                <div className="hero__phone-status">
                  <span className="hero__phone-pulse" />
                  Active Call
                </div>
                <span className="hero__phone-time">2:34</span>
              </div>
              <div className="hero__phone-messages">
                <div className="hero__msg hero__msg--ai">
                  <span className="hero__msg-label">Danny AI</span>
                  Good morning! Thank you for calling Bright Smile Dental. How can I help you today?
                </div>
                <div className="hero__msg hero__msg--user">
                  Hi, I'd like to schedule a cleaning appointment.
                </div>
                <div className="hero__msg hero__msg--ai">
                  <span className="hero__msg-label">Danny AI</span>
                  I'd be happy to help! I have openings this Thursday at 10 AM and Friday at 2 PM. Which works better for you?
                </div>
                <div className="hero__msg hero__msg--user">
                  Thursday at 10 sounds great!
                </div>
                <div className="hero__msg hero__msg--ai">
                  <span className="hero__msg-label">Danny AI</span>
                  <span className="hero__msg-typing">
                    <span /><span /><span />
                  </span>
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
