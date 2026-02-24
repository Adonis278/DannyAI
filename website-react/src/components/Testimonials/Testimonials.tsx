import { motion } from 'framer-motion';
import { Star } from 'lucide-react';
import './Testimonials.css';

const testimonials = [
  {
    name: 'Dr. Sarah Mitchell',
    role: 'Owner, Bright Smile Dental',
    content:
      "Danny has completely transformed our front desk operations. We used to miss 30% of calls during busy hours — now every single call gets answered. Our booking rate increased by 40% in the first month.",
    rating: 5,
  },
  {
    name: 'Maria Rodriguez',
    role: 'Office Manager, Family Dental Care',
    content:
      "The bilingual support is a game-changer for our practice. Danny handles Spanish-speaking patients just as naturally as English speakers. Our staff can finally focus on in-office patients.",
    rating: 5,
  },
  {
    name: 'Dr. James Park',
    role: 'Lead Dentist, Modern Dental Group',
    content:
      "I was skeptical about AI answering our phones, but Danny sounds so natural that patients don't even realize they're talking to an AI. The insurance verification feature alone saves us hours every week.",
    rating: 5,
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
          <span className="testimonials__label">Testimonials</span>
          <h2 className="testimonials__title">
            Loved by dental <span className="text-accent">professionals.</span>
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
              <div className="testimonial-card__stars">
                {Array.from({ length: t.rating }).map((_, j) => (
                  <Star key={j} size={14} fill="#00D4AA" color="#00D4AA" />
                ))}
              </div>
              <p className="testimonial-card__content">"{t.content}"</p>
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
