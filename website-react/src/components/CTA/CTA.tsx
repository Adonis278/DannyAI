import { motion } from 'framer-motion';
import { ArrowRight } from 'lucide-react';
import './CTA.css';

export default function CTA() {
  return (
    <section className="cta">
      <div className="container">
        <motion.div
          className="cta__content"
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-60px' }}
          transition={{ duration: 0.6 }}
        >
          <h2 className="cta__title">
            Never say "we'll call you back" again.
          </h2>
          <p className="cta__subtitle">
            Get patient calls handled professionally, 24/7. 
            No more missed opportunities, no more frustrated patients.
          </p>
          <div className="cta__actions">
            <a href="#demo" className="cta__btn cta__btn--primary">
              Book a demo
              <ArrowRight size={18} />
            </a>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
