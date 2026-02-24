import { motion } from 'framer-motion';
import { ArrowRight } from 'lucide-react';
import './CTA.css';

export default function CTA() {
  return (
    <section className="cta">
      <div className="cta__glow" />
      <div className="container">
        <motion.div
          className="cta__card"
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-60px' }}
          transition={{ duration: 0.6 }}
        >
          <h2 className="cta__title">
            Ready to stop missing calls?
          </h2>
          <p className="cta__subtitle">
            Join 50+ dental practices using Danny to deliver exceptional patient experiences while reducing admin workload by 60%.
          </p>
          <div className="cta__actions">
            <a href="#demo" className="cta__btn cta__btn--primary">
              Start Free Trial
              <ArrowRight size={18} />
            </a>
            <a href="mailto:hello@dannyai.com" className="cta__btn cta__btn--secondary">
              Schedule a Demo Call
            </a>
          </div>
          <p className="cta__note">No credit card required. Setup in under 10 minutes.</p>
        </motion.div>
      </div>
    </section>
  );
}
