import { motion } from 'framer-motion';
import { PhoneIncoming, Cpu, CalendarPlus, CheckCircle } from 'lucide-react';
import './HowItWorks.css';

const steps = [
  {
    icon: <PhoneIncoming size={28} />,
    step: '01',
    title: 'Patient Calls In',
    description:
      'Danny answers instantly, greets the patient by name if recognized, and asks how it can help.',
  },
  {
    icon: <Cpu size={28} />,
    step: '02',
    title: 'AI Understands Intent',
    description:
      'Powered by Claude, Danny identifies whether the patient needs scheduling, insurance info, or something else.',
  },
  {
    icon: <CalendarPlus size={28} />,
    step: '03',
    title: 'Takes Action',
    description:
      'Danny checks availability, verifies insurance, or routes to staff — all in real time, within the same call.',
  },
  {
    icon: <CheckCircle size={28} />,
    step: '04',
    title: 'Confirms & Logs',
    description:
      'Appointment confirmed, details logged to your PMS, and a summary sent to the office — all HIPAA compliant.',
  },
];

export default function HowItWorks() {
  return (
    <section id="how-it-works" className="how-it-works">
      <div className="container">
        <motion.div
          className="how-it-works__header"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-80px' }}
          transition={{ duration: 0.6 }}
        >
          <span className="how-it-works__label">How It Works</span>
          <h2 className="how-it-works__title">
            From ring to booked
            <br />
            <span className="text-accent">in under 60 seconds.</span>
          </h2>
        </motion.div>

        <div className="how-it-works__steps">
          {steps.map((step, i) => (
            <motion.div
              key={i}
              className="step-card"
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-40px' }}
              transition={{ delay: i * 0.1, duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
            >
              <div className="step-card__number">{step.step}</div>
              <div className="step-card__icon">{step.icon}</div>
              <h3 className="step-card__title">{step.title}</h3>
              <p className="step-card__desc">{step.description}</p>
              {i < steps.length - 1 && <div className="step-card__connector" />}
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
