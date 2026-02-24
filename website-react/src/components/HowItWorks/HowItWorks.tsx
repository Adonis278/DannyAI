import { motion } from 'framer-motion';
import { Clock, Zap, CheckCircle } from 'lucide-react';
import './HowItWorks.css';

const features = [
  {
    icon: <Clock size={24} />,
    title: 'Real-time availability',
    description:
      'Danny checks your practice management system in real-time to offer patients accurate, up-to-date appointment slots.',
  },
  {
    icon: <Zap size={24} />,
    title: 'Instant verification',
    description:
      'Insurance eligibility verified during the call. No callbacks, no waiting — patients get answers immediately.',
  },
  {
    icon: <CheckCircle size={24} />,
    title: 'Human when you need it',
    description:
      'When situations require personal attention, Danny seamlessly transfers with full context to your staff.',
  },
];

export default function HowItWorks() {
  return (
    <section id="how-it-works" className="how-it-works">
      <div className="container">
        <div className="how-it-works__grid">
          <motion.div
            className="how-it-works__content"
            initial={{ opacity: 0, x: -30 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true, margin: '-80px' }}
            transition={{ duration: 0.6 }}
          >
            <h2 className="how-it-works__title">
              <span className="how-it-works__title-small">Real-time</span>
              <span className="how-it-works__title-main">peace of mind.</span>
            </h2>
            <p className="how-it-works__subtitle">
              No more missed calls or frustrated patients. Danny handles 
              everything instantly, keeping your practice running smoothly.
            </p>
          </motion.div>

          <div className="how-it-works__features">
            {features.map((feat, i) => (
              <motion.div
                key={i}
                className="hiw-feature"
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: '-40px' }}
                transition={{ delay: i * 0.15, duration: 0.5 }}
              >
                <div className="hiw-feature__icon">{feat.icon}</div>
                <div className="hiw-feature__content">
                  <h3 className="hiw-feature__title">{feat.title}</h3>
                  <p className="hiw-feature__desc">{feat.description}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
