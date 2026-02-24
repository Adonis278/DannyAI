import { motion } from 'framer-motion';
import { Quote } from 'lucide-react';
import './Testimonials.css';

const testimonials = [
  {
    name: 'Dr. Sarah Mitchell',
    role: 'Bright Smile Dental',
    content:
      "Danny has transformed our front desk. We went from missing 30% of calls to answering every single one. Booking rates increased 40% in the first month.",
  },
  {
    name: 'Maria Rodriguez',
    role: 'Family Dental Care',
    content:
      "The seamless integration with our existing systems was impressive. Staff can finally focus on in-office patients while Danny handles the phones.",
  },
  {
    name: 'Dr. James Park',
    role: 'Modern Dental Group',
    content:
      "Patients don't realize they're not talking to a person. The insurance verification alone saves us hours every week.",
  },
];

export default function Testimonials() {
  return (
    <section id="testimonials" className="testimonials">
      <div className="container">
        <motion.div
          className="testimonials__header"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-80px' }}
          transition={{ duration: 0.6 }}
        >
          <h2 className="testimonials__title">
            <span className="testimonials__title-small">Trusted by practices</span>
            <span className="testimonials__title-main">across the country.</span>
          </h2>
        </motion.div>

        <div className="testimonials__grid">
          {testimonials.map((t, i) => (
            <motion.div
              key={i}
              className="testimonial-card"
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-40px' }}
              transition={{ delay: i * 0.1, duration: 0.5 }}
            >
              <Quote size={24} className="testimonial-card__quote" />
              <p className="testimonial-card__content">{t.content}</p>
              <div className="testimonial-card__author">
                <div className="testimonial-card__avatar">
                  {t.name.split(' ').map(n => n[0]).join('')}
                </div>
                <div>
                  <div className="testimonial-card__name">{t.name}</div>
                  <div className="testimonial-card__role">{t.role}</div>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
