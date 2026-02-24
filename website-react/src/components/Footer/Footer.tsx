import './Footer.css';

const footerLinks = {
  Solutions: ['Call Handling', 'Scheduling', 'Insurance', 'Integrations'],
  Company: ['About', 'Pricing', 'Contact', 'Careers'],
  Legal: ['Privacy Policy', 'Terms of Service', 'HIPAA', 'BAA'],
};

export default function Footer() {
  return (
    <footer className="footer">
      <div className="container">
        <div className="footer__grid">
          <div className="footer__brand">
            <div className="footer__logo">
              <img src="/logo.png" alt="Danny" className="footer__logo-img" />
              <span className="footer__logo-text">Danny</span>
            </div>
            <p className="footer__tagline">
              Automated front desk for modern dental practices.
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
          <p>&copy; {new Date().getFullYear()} Danny. All rights reserved.</p>
          <p className="footer__compliance">HIPAA Compliant</p>
        </div>
      </div>
    </footer>
  );
}
