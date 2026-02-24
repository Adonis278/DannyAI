import { motion } from 'framer-motion';
import { ArrowRight } from 'lucide-react';
import './Hero.css';

export default function Hero() {
  return (
    <section className="hero">
      <div className="hero__bg-gradient" />
      
      <div className="container hero__container">
        <motion.div
          className="hero__content"
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
        >
          <h1 className="hero__title">
            <span className="hero__title-line">Less missed calls.</span>
            <span className="hero__title-gradient">Better patient care.</span>
          </h1>

          <p className="hero__subtitle">
            Danny automates your front desk operations — answering calls, 
            scheduling appointments, and verifying insurance — so your team 
            can focus on what matters most.
          </p>

          <div className="hero__actions">
            <a href="#demo" className="hero__btn hero__btn--primary">
              Book a demo
              <ArrowRight size={18} />
            </a>
          </div>
        </motion.div>

        <motion.div
          className="hero__visual"
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.3, duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
        >
          <div className="hero__preview">
            <div className="hero__preview-header">
              <div className="hero__preview-dots">
                <span></span><span></span><span></span>
              </div>
              <span className="hero__preview-title">Danny Dashboard</span>
            </div>
            <div className="hero__preview-content">
              <div className="hero__preview-stats">
                <div className="hero__preview-stat">
                  <span className="hero__preview-stat-value">847</span>
                  <span className="hero__preview-stat-label">Calls this month</span>
                </div>
                <div className="hero__preview-stat">
                  <span className="hero__preview-stat-value">98.5%</span>
                  <span className="hero__preview-stat-label">Resolution rate</span>
                </div>
                <div className="hero__preview-stat">
                  <span className="hero__preview-stat-value">2.3s</span>
                  <span className="hero__preview-stat-label">Avg response</span>
                </div>
              </div>
              <div className="hero__preview-activity">
                <div className="hero__activity-item">
                  <div className="hero__activity-icon hero__activity-icon--success"></div>
                  <span>Appointment booked — Sarah M. — Cleaning 10:30 AM</span>
                </div>
                <div className="hero__activity-item">
                  <div className="hero__activity-icon hero__activity-icon--info"></div>
                  <span>Insurance verified — Delta Dental PPO</span>
                </div>
                <div className="hero__activity-item">
                  <div className="hero__activity-icon hero__activity-icon--success"></div>
                  <span>Callback scheduled — Dr. Park availability</span>
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
