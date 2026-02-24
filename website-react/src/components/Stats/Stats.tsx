import { motion } from 'framer-motion';
import './Stats.css';

const stats = [
  { value: '99.8%', label: 'Call Answer Rate' },
  { value: '<3s', label: 'Average Response Time' },
  { value: '85%', label: 'Calls Resolved Without Staff' },
  { value: '24/7', label: 'Always Available' },
];

export default function Stats() {
  return (
    <section className="stats">
      <div className="container">
        <div className="stats__grid">
          {stats.map((stat, i) => (
            <motion.div
              key={i}
              className="stat-item"
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1, duration: 0.5 }}
            >
              <span className="stat-item__value">{stat.value}</span>
              <span className="stat-item__label">{stat.label}</span>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
