import './Footer.css';

const footerLinks = {
  Product: ['Features', 'Demo', 'Pricing', 'Integrations'],
  Company: ['About', 'Blog', 'Careers', 'Contact'],
  Legal: ['Privacy Policy', 'Terms of Service', 'HIPAA Compliance', 'BAA'],
};

export default function Footer() {
  return (
    <footer className="footer">
      <div className="container">
        <div className="footer__grid">
          <div className="footer__brand">
            <div className="footer__logo">
              <svg viewBox="0 0 32 32" fill="none" width="28" height="28">
                <path d="M16 3C10.5 3 5 7.5 5 13.5C5 18 7 23 10 28C11.5 31 13 32 14 32C15 32 15.5 29 16 26C16.5 29 17 32 18 32C19 32 20.5 31 22 28C25 23 27 18 27 13.5C27 7.5 21.5 3 16 3Z" fill="url(#footerGrad)"/>
                <defs>
                  <linearGradient id="footerGrad" x1="5" y1="3" x2="27" y2="32" gradientUnits="userSpaceOnUse">
                    <stop stopColor="#00E6BB"/>
                    <stop offset="1" stopColor="#00D4AA"/>
                  </linearGradient>
                </defs>
              </svg>
              <span className="footer__logo-text">
                Danny<span className="footer__logo-accent">AI</span>
              </span>
            </div>
            <p className="footer__tagline">
              The AI dental concierge that never misses a call. Built by Spiritus Agentic Solutions.
            </p>
          </div>

          {Object.entries(footerLinks).map(([category, links]) => (
            <div key={category} className="footer__col">
              <h4 className="footer__col-title">{category}</h4>
              <ul>
                {links.map(link => (
                  <li key={link}>
                    <a href="#" className="footer__link">{link}</a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="footer__bottom">
          <p>&copy; {new Date().getFullYear()} DannyAI by Spiritus Agentic Solutions. All rights reserved.</p>
          <p className="footer__hipaa">HIPAA Compliant &bull; SOC 2 Type II &bull; ADA Compliant</p>
        </div>
      </div>
    </footer>
  );
}
