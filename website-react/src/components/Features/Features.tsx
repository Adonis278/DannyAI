import { motion } from 'framer-motion';
import {
  Phone,
  CalendarCheck,
  Shield,
  Languages,
  Clock,
  UserCheck,
} from 'lucide-react';
import './Features.css';

const features = [
  {
    icon: <Phone size={24} />,
    title: 'Instant Call Answering',
    description:
      'Danny picks up every call within one ring — no hold music, no voicemail, ever. Patients get help 24/7.',
  },
  {
    icon: <CalendarCheck size={24} />,
    title: 'Smart Scheduling',
    description:
      'Checks real-time availability and books appointments directly into your practice management system.',
  },
  {
    icon: <Shield size={24} />,
    title: 'Insurance Verification',
    description:
      'Performs instant eligibility checks about coverage, co-pays, and accepted plans during the call.',
  },
  {
    icon: <Languages size={24} />,
    title: 'Bilingual Support',
    description:
      'Fluent in English and Spanish, Danny communicates naturally with every patient who calls.',
  },
  {
    icon: <Clock size={24} />,
    title: '24/7 Availability',
    description:
      'Never miss after-hours calls. Danny handles emergencies, schedules callbacks, and triages urgent requests.',
  },
  {
    icon: <UserCheck size={24} />,
    title: 'Human Handoff',
    description:
      'When patients need a real person, Danny warm-transfers with full context so staff never miss a beat.',
  },
];

const containerVariants = {
  hidden: {},
  visible: {
    transition: { staggerChildren: 0.08 },
  },
};

const cardVariants = {
  hidden: { opacity: 0, y: 24 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.16, 1, 0.3, 1] as [number, number, number, number] } },
};

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
          <span className="features__label">Features</span>
          <h2 className="features__title">
            Everything your front desk does,
            <br />
            <span className="text-accent">automated.</span>
          </h2>
          <p className="features__subtitle">
            Danny handles the repetitive work so your team can focus on what matters most — patient care.
          </p>
        </motion.div>

        <motion.div
          className="features__grid"
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: '-60px' }}
        >
          {features.map((feat, i) => (
            <motion.div key={i} className="feature-card" variants={cardVariants}>
              <div className="feature-card__icon">{feat.icon}</div>
              <h3 className="feature-card__title">{feat.title}</h3>
              <p className="feature-card__desc">{feat.description}</p>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
