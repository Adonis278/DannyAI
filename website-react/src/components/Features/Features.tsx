import { motion } from 'framer-motion';
import {
  Phone,
  CalendarCheck,
  Shield,
  ArrowRight,
} from 'lucide-react';
import './Features.css';

const solutions = [
  {
    icon: <Phone size={28} />,
    title: 'Automated Call Handling',
    description:
      'Every call answered instantly. No hold times, no voicemails — just immediate, professional service around the clock.',
    link: '#demo',
  },
  {
    icon: <CalendarCheck size={28} />,
    title: 'Smart Scheduling',
    description:
      'Appointments booked directly into your practice management system with real-time availability checks.',
    link: '#demo',
  },
  {
    icon: <Shield size={28} />,
    title: 'Insurance Verification',
    description:
      'Instant eligibility checks during the call. Coverage, co-pays, and accepted plans — verified in seconds.',
    link: '#demo',
  },
];

export default function Features() {
  return (
    <section id="features" className="features">
      <div className="container">
        <motion.div
          className="features__header"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-80px' }}
          transition={{ duration: 0.6 }}
        >
          <h2 className="features__title">
            <span className="features__title-small">Built to automate</span>
            <span className="features__title-main">the everyday.</span>
          </h2>
          <p className="features__subtitle">
            Danny handles the repetitive front desk tasks so your team 
            can focus entirely on patient care.
          </p>
        </motion.div>

        <div className="features__grid">
          {solutions.map((sol, i) => (
            <motion.a
              key={i}
              href={sol.link}
              className="solution-card"
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-60px' }}
              transition={{ delay: i * 0.1, duration: 0.5 }}
            >
              <div className="solution-card__icon">{sol.icon}</div>
              <h3 className="solution-card__title">{sol.title}</h3>
              <p className="solution-card__desc">{sol.description}</p>
              <span className="solution-card__link">
                Learn more <ArrowRight size={16} />
              </span>
            </motion.a>
          ))}
        </div>
      </div>
    </section>
  );
}
