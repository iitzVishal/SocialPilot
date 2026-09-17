import React, { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import './LandingPage.css';

// ─── NAVBAR ────────────────────────────────────────────────────────────────
const Navbar = () => {
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  const navLinks = ['Features', 'How It Works', 'Resources', 'Testimonials', 'FAQ'];

  const scrollTo = (id) => {
    setMobileOpen(false);
    const el = document.getElementById(id.toLowerCase().replace(/\s+/g, '-'));
    if (el) el.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <nav className={`sp-nav${scrolled ? ' sp-nav--scrolled' : ''}`}>
      <div className="sp-nav__inner">
        {/* Logo */}
        <Link to="/" className="sp-logo">
          <div className="sp-logo__icon">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
              <path d="M12 2L4 6v6c0 5.25 3.5 10.15 8 11.35C16.5 22.15 20 17.25 20 12V6l-8-4z" fill="url(#logoGrad)" opacity="0.9"/>
              <path d="M9 12l2 2 4-4" stroke="#fff" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
              <defs>
                <linearGradient id="logoGrad" x1="4" y1="2" x2="20" y2="23" gradientUnits="userSpaceOnUse">
                  <stop stopColor="#4ade80"/>
                  <stop offset="1" stopColor="#16a34a"/>
                </linearGradient>
              </defs>
            </svg>
          </div>
          <div className="sp-logo__text">
            <span className="sp-logo__name">SocialPilot</span>
            <span className="sp-logo__tagline">Plan. Publish. Perform.</span>
          </div>
        </Link>

        {/* Desktop nav links */}
        <div className="sp-nav__links">
          {navLinks.map(link => (
            <button key={link} className="sp-nav__link" onClick={() => scrollTo(link)}>
              {link}
            </button>
          ))}
        </div>

        {/* Desktop CTA */}
        <div className="sp-nav__actions">
          <Link to="/login" className="sp-btn sp-btn--ghost">Login</Link>
          <Link to="/register" className="sp-btn sp-btn--primary">Get Started</Link>
        </div>

        {/* Hamburger */}
        <button className="sp-hamburger" onClick={() => setMobileOpen(!mobileOpen)} aria-label="Toggle menu">
          <span className={`sp-hamburger__bar${mobileOpen ? ' sp-hamburger__bar--open-1' : ''}`}></span>
          <span className={`sp-hamburger__bar${mobileOpen ? ' sp-hamburger__bar--open-2' : ''}`}></span>
          <span className={`sp-hamburger__bar${mobileOpen ? ' sp-hamburger__bar--open-3' : ''}`}></span>
        </button>
      </div>

      {/* Mobile menu */}
      {mobileOpen && (
        <div className="sp-mobile-menu">
          {navLinks.map(link => (
            <button key={link} className="sp-mobile-menu__link" onClick={() => scrollTo(link)}>{link}</button>
          ))}
          <div className="sp-mobile-menu__actions">
            <Link to="/login" className="sp-btn sp-btn--ghost sp-btn--full" onClick={() => setMobileOpen(false)}>Login</Link>
            <Link to="/register" className="sp-btn sp-btn--primary sp-btn--full" onClick={() => setMobileOpen(false)}>Get Started</Link>
          </div>
        </div>
      )}
    </nav>
  );
};

// ─── SECTION REVEAL HOOK ───────────────────────────────────────────────────
const useReveal = () => {
  const ref = useRef(null);
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      setVisible(true);
      return;
    }
    const obs = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) { setVisible(true); obs.disconnect(); }
    }, { threshold: 0.12 });
    if (ref.current) obs.observe(ref.current);
    return () => obs.disconnect();
  }, []);
  return [ref, visible];
};

// ─── HERO ──────────────────────────────────────────────────────────────────
const HeroSection = () => {
  const [ref, visible] = useReveal();
  return (
    <section className="sp-hero" id="features">
      {/* ambient glow */}
      <div className="sp-hero__glow sp-hero__glow--left" aria-hidden="true"/>
      <div className="sp-hero__glow sp-hero__glow--right" aria-hidden="true"/>

      <div className={`sp-container sp-hero__inner${visible ? ' sp-reveal--in' : ' sp-reveal'}`} ref={ref}>
        {/* Left */}
        <div className="sp-hero__content">
          <div className="sp-pill">🚀 Advanced Social Media Management Platform</div>
          <h1 className="sp-hero__heading">
            Smarter Social<br />Management.<br />
            <span className="sp-green">Better Results.</span>
          </h1>
          <p className="sp-hero__sub">
            SocialPilot helps you plan, publish, automate and analyze your social media content —
            all from one powerful dashboard. Save time, increase engagement and grow your brand faster than ever.
          </p>
          <div className="sp-hero__ctas">
            <Link to="/register" className="sp-btn sp-btn--primary sp-btn--lg">Get Started →</Link>
          </div>
          <ul className="sp-hero__guarantees">
            <li><span className="sp-check">✓</span> Plan</li>
            <li><span className="sp-check">✓</span> Publish</li>
            <li><span className="sp-check">✓</span> Analyze</li>
          </ul>
        </div>

        {/* Right — dashboard mockup */}
        <div className="sp-hero__showcase">
          <div className="sp-dashboard-mock">
            {/* Glow behind mockup */}
            <div className="sp-dashboard-mock__glow" aria-hidden="true"/>
            {/* Laptop frame */}
            <div className="sp-laptop">
              <div className="sp-laptop__screen">
                {/* Mini dashboard UI */}
                <div className="sp-dash">
                  <div className="sp-dash__sidebar">
                    <div className="sp-dash__logo-mini">SP</div>
                    {['📊','📅','✏️','📁','👥','⚙️'].map((ico,i) => (
                      <div key={i} className={`sp-dash__nav-item${i===0?' sp-dash__nav-item--active':''}`}>{ico}</div>
                    ))}
                  </div>
                  <div className="sp-dash__main">
                    <div className="sp-dash__header">
                      <span className="sp-dash__title">Dashboard Overview</span>
                      <div className="sp-dash__actions">
                        <div className="sp-dash__btn-mini">+ New Post</div>
                      </div>
                    </div>
                    <div className="sp-dash__stats">
                      {[
                        { label: 'Posts Today', val: '12', up: true },
                        { label: 'Reach', val: '48.2K', up: true },
                        { label: 'Engagement', val: '6.4%', up: true },
                        { label: 'Scheduled', val: '34', up: false },
                      ].map((s, i) => (
                        <div key={i} className="sp-stat-card">
                          <div className="sp-stat-card__val">{s.val}</div>
                          <div className="sp-stat-card__label">{s.label}</div>
                          <div className={`sp-stat-card__badge${s.up?' sp-stat-card__badge--up':' sp-stat-card__badge--neutral'}`}>{s.up?'↑ 12%':'→'}</div>
                        </div>
                      ))}
                    </div>
                    <div className="sp-dash__chart-row">
                      <div className="sp-chart-block">
                        <div className="sp-chart-block__label">Weekly Engagement</div>
                        <div className="sp-chart-bars">
                          {[40,65,45,80,55,90,70].map((h,i)=>(
                            <div key={i} className="sp-chart-bar" style={{height:`${h}%`}}/>
                          ))}
                        </div>
                      </div>
                      <div className="sp-posts-list">
                        <div className="sp-posts-list__label">Upcoming Posts</div>
                        {[
                          { platform: '📸', text: 'Product Launch Post', time: '2:00 PM' },
                          { platform: '🐦', text: 'Weekly tip thread', time: '4:30 PM' },
                          { platform: '💼', text: 'Industry insights', time: '6:00 PM' },
                        ].map((p,i)=>(
                          <div key={i} className="sp-post-item">
                            <span className="sp-post-item__ico">{p.platform}</span>
                            <span className="sp-post-item__text">{p.text}</span>
                            <span className="sp-post-item__time">{p.time}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              <div className="sp-laptop__base"><div className="sp-laptop__notch"/></div>
            </div>

            {/* Floating phone */}
            <div className="sp-phone">
              <div className="sp-phone__screen">
                <div className="sp-phone__header">SocialPilot</div>
                <div className="sp-phone__content">
                  {[
                    { ico: '📸', txt: 'Instagram', val: '+24%' },
                    { ico: '🐦', txt: 'Twitter/X', val: '+18%' },
                    { ico: '💼', txt: 'LinkedIn', val: '+31%' },
                  ].map((r,i)=>(
                    <div key={i} className="sp-phone__row">
                      <span>{r.ico}</span>
                      <span className="sp-phone__row-label">{r.txt}</span>
                      <span className="sp-phone__row-val">{r.val}</span>
                    </div>
                  ))}
                  <div className="sp-phone__compose">+ Compose Post</div>
                </div>
              </div>
            </div>

            {/* Floating stat badges */}
            <div className="sp-badge sp-badge--1">🔥 12K reach today</div>
            <div className="sp-badge sp-badge--2">✅ 34 posts scheduled</div>
          </div>
        </div>
      </div>
    </section>
  );
};

// ─── TRUSTED BY ────────────────────────────────────────────────────────────
const TrustedBrands = () => {
  const [ref, visible] = useReveal();
  const brands = ['Google', 'Microsoft', 'Slack', 'Shopify', 'AWS', 'HubSpot'];
  return (
    <section className="sp-trusted" ref={ref}>
      <div className="sp-container">
        <p className={`sp-trusted__label${visible?' sp-reveal--in':' sp-reveal'}`}>
          Trusted by <span className="sp-green">10,000+</span> businesses worldwide
        </p>
        <div className="sp-trusted__logos">
          {brands.map((b,i) => (
            <div key={i} className="sp-trusted__logo">{b}</div>
          ))}
        </div>
      </div>
    </section>
  );
};

// ─── PLATFORM INTRO ────────────────────────────────────────────────────────
const PlatformIntro = () => {
  const [ref, visible] = useReveal();
  const platforms = ['Instagram','Facebook','LinkedIn','X (Twitter)','YouTube','Pinterest'];
  const checks = [
    'Manage all your social accounts in one place',
    'Create, schedule and publish content effortlessly',
    'Analyze performance with advanced analytics',
    'Collaborate with your team in real-time',
    'Save hours every week and scale your brand',
  ];
  return (
    <section className="sp-intro" ref={ref}>
      <div className={`sp-container sp-intro__inner${visible?' sp-reveal--in':' sp-reveal'}`}>
        <div className="sp-intro__left">
          <div className="sp-label">AUTOMATE. PUBLISH. ANALYZE.</div>
          <h2 className="sp-section-heading">
            All Your Social Media<br />Tasks. <span className="sp-green">One Platform.</span>
          </h2>
          <p className="sp-section-text">
            Plan, collaborate and publish content across all major social networks.
            SocialPilot makes social media management simple, fast and effective.
          </p>
          <ul className="sp-checklist">
            {checks.map((c,i) => (
              <li key={i}><span className="sp-check">✓</span>{c}</li>
            ))}
          </ul>
          <Link to="/register" className="sp-btn sp-btn--primary sp-btn--lg" style={{marginTop:'2rem',display:'inline-flex'}}>
            Get Started →
          </Link>
        </div>
        <div className="sp-intro__right">
          <div className="sp-platform-hub">
            <div className="sp-platform-hub__center">
              <div className="sp-platform-hub__phone">
                <div className="sp-ph-screen">
                  <div className="sp-ph-header">SocialPilot</div>
                  <div className="sp-ph-feed">
                    {['📸','🐦','💼','▶️'].map((ico,i)=>(
                      <div key={i} className="sp-ph-post">
                        <span>{ico}</span>
                        <div className="sp-ph-post__bar" style={{width:`${60+i*10}%`}}/>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
            {platforms.map((p,i) => {
              const angle = (i / platforms.length) * 360;
              const rad = (angle * Math.PI) / 180;
              const r = 130;
              const x = 50 + (r / 2.8) * Math.sin(rad);
              const y = 50 - (r / 2.8) * Math.cos(rad);
              return (
                <div
                  key={i}
                  className="sp-platform-chip"
                  style={{ left: `${x}%`, top: `${y}%` }}
                >
                  {p}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
};

// ─── FEATURES ──────────────────────────────────────────────────────────────
const FeaturesSection = () => {
  const [ref, visible] = useReveal();
  const features = [
    { icon: '📅', title: 'Content Scheduling', desc: 'Schedule posts across multiple platforms and timezones.' },
    { icon: '🤖', title: 'AI Content Assistant', desc: 'Generate engaging captions, ideas and content in seconds.' },
    { icon: '📊', title: 'Analytics & Reports', desc: 'Track performance and get actionable insights that drive results.' },
    { icon: '👥', title: 'Team Collaboration', desc: 'Collaborate with your team and manage approvals easily.' },
    { icon: '📬', title: 'Inbox Management', desc: 'Manage messages, comments and mentions from one inbox.' },
    { icon: '📋', title: 'White Label Reports', desc: 'Create professional reports and impress your clients.' },
  ];
  return (
    <section className="sp-features" id="features" ref={ref}>
      <div className="sp-container">
        <div className={`sp-section-header${visible?' sp-reveal--in':' sp-reveal'}`}>
          <div className="sp-label">POWERFUL FEATURES</div>
          <h2 className="sp-section-heading">Everything You Need to Grow</h2>
        </div>
        <div className="sp-features__grid">
          {features.map((f,i) => (
            <div key={i} className={`sp-feature-card${visible?' sp-reveal--in':' sp-reveal'}`} style={{transitionDelay:`${i*80}ms`}}>
              <div className="sp-feature-card__icon">{f.icon}</div>
              <h3 className="sp-feature-card__title">{f.title}</h3>
              <p className="sp-feature-card__desc">{f.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

// ─── HOW IT WORKS ──────────────────────────────────────────────────────────
const HowItWorks = () => {
  const [ref, visible] = useReveal();
  const steps = [
    { num: '01', title: 'Connect Accounts', desc: 'Connect your social media accounts in just a few clicks.' },
    { num: '02', title: 'Create & Schedule', desc: 'Create amazing content and schedule it at the perfect time.' },
    { num: '03', title: 'Analyze & Grow', desc: 'Track performance and grow your brand consistently.' },
  ];
  return (
    <section className="sp-how" id="how-it-works" ref={ref}>
      <div className="sp-container">
        <div className={`sp-section-header${visible?' sp-reveal--in':' sp-reveal'}`}>
          <div className="sp-label">HOW IT WORKS</div>
          <h2 className="sp-section-heading">Get Started in 3 Simple Steps</h2>
        </div>
        <div className="sp-how__steps">
          {steps.map((s,i) => (
            <React.Fragment key={i}>
              <div className={`sp-step${visible?' sp-reveal--in':' sp-reveal'}`} style={{transitionDelay:`${i*120}ms`}}>
                <div className="sp-step__num">{s.num}</div>
                <h3 className="sp-step__title">{s.title}</h3>
                <p className="sp-step__desc">{s.desc}</p>
              </div>
              {i < steps.length - 1 && <div className="sp-step__connector" aria-hidden="true">···</div>}
            </React.Fragment>
          ))}
        </div>
      </div>
    </section>
  );
};

// ─── RESOURCES & INTEGRATIONS ───────────────────────────────────────────────
const Resources = () => {
  const [ref, visible] = useReveal();
  const integrations = [
    { icon: '💬', name: 'Slack' },
    { icon: '📂', name: 'Google Drive' },
    { icon: '🎨', name: 'Canva' },
    { icon: '📦', name: 'Dropbox' },
    { icon: '⚡', name: 'Zapier' },
    { icon: '🔗', name: 'Bitly' },
    { icon: '🖼️', name: 'Unsplash' },
    { icon: '📷', name: 'Pexels' },
  ];
  return (
    <section className="sp-integrations" id="resources" ref={ref}>
      <div className="sp-container">
        <div className={`sp-section-header${visible?' sp-reveal--in':' sp-reveal'}`}>
          <div className="sp-label">RESOURCES & INTEGRATIONS</div>
          <h2 className="sp-section-heading">Seamlessly Integrates With Your Favorite Tools</h2>
        </div>
        <div className="sp-integrations__grid">
          {integrations.map((t,i) => (
            <div key={i} className={`sp-integration-card${visible?' sp-reveal--in':' sp-reveal'}`} style={{transitionDelay:`${i*60}ms`}}>
              <span className="sp-integration-card__icon">{t.icon}</span>
              <span className="sp-integration-card__name">{t.name}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

// ─── TESTIMONIALS ──────────────────────────────────────────────────────────
const Testimonials = () => {
  const [ref, visible] = useReveal();
  const [active, setActive] = useState(0);
  const testimonials = [
    {
      quote: '"SocialPilot has completely simplified our social media workflow. We save hours every day and our engagement has grown significantly."',
      name: 'Rohit Sharma',
      role: 'Marketing Head, TechNova',
      initials: 'RS',
    },
    {
      quote: '"The analytics and reporting features are outstanding. SocialPilot gives us insights that actually help us make better decisions."',
      name: 'Priya Verma',
      role: 'Digital Strategist, GrowthX',
      initials: 'PV',
    },
    {
      quote: '"Managing multiple client accounts is so easy now. The team collaboration and approval workflow is a game changer."',
      name: 'Aman Singh',
      role: 'Founder, GrowthCraft',
      initials: 'AS',
    },
  ];
  return (
    <section className="sp-testimonials" id="testimonials" ref={ref}>
      <div className="sp-container">
        <div className={`sp-section-header${visible?' sp-reveal--in':' sp-reveal'}`}>
          <div className="sp-label">TESTIMONIALS</div>
          <h2 className="sp-section-heading">Loved by Businesses Like Yours</h2>
        </div>
        <div className="sp-testimonials__grid">
          {testimonials.map((t,i) => (
            <div
              key={i}
              className={`sp-testimonial-card${i===active?' sp-testimonial-card--active':''}${visible?' sp-reveal--in':' sp-reveal'}`}
              style={{transitionDelay:`${i*100}ms`}}
              onClick={() => setActive(i)}
            >
              <div className="sp-stars">★★★★★</div>
              <p className="sp-testimonial-card__quote">{t.quote}</p>
              <div className="sp-testimonial-card__author">
                <div className="sp-avatar">{t.initials}</div>
                <div>
                  <div className="sp-testimonial-card__name">{t.name}</div>
                  <div className="sp-testimonial-card__role">{t.role}</div>
                </div>
              </div>
            </div>
          ))}
        </div>
        <div className="sp-testimonials__dots">
          {testimonials.map((_,i) => (
            <button key={i} className={`sp-dot${i===active?' sp-dot--active':''}`} onClick={() => setActive(i)} aria-label={`Testimonial ${i+1}`}/>
          ))}
        </div>
      </div>
    </section>
  );
};

// ─── FAQ ───────────────────────────────────────────────────────────────────
const FAQSection = () => {
  const [ref, visible] = useReveal();
  const [openIdx, setOpenIdx] = useState(null);
  const faqs = [
    {
      q: 'What social media platforms does SocialPilot support?',
      a: 'SocialPilot supports all major platforms including Instagram, Facebook, LinkedIn, X (Twitter), YouTube, and Pinterest.',
    },
    {
      q: 'Can I collaborate with my team members on SocialPilot?',
      a: 'Yes! SocialPilot features full team workspace collaboration, role-based access control, and post approval workflows.',
    },
    {
      q: 'How does post scheduling work?',
      a: 'You can draft posts, customize them for each social network, attach media, and schedule them for automatic publishing at your preferred time.',
    },
    {
      q: 'Is there a limit to how many posts I can schedule?',
      a: 'SocialPilot allows you to schedule unlimited posts across all your connected social media accounts.',
    },
  ];

  return (
    <section className="sp-features" id="faq" ref={ref} style={{ borderTop: '1px solid var(--sp-border, rgba(255,255,255,0.08))' }}>
      <div className="sp-container">
        <div className={`sp-section-header${visible ? ' sp-reveal--in' : ' sp-reveal'}`}>
          <div className="sp-label">FAQ</div>
          <h2 className="sp-section-heading">Frequently Asked Questions</h2>
        </div>
        <div className="sp-features__grid" style={{ gridTemplateColumns: '1fr', maxWidth: '800px', margin: '0 auto' }}>
          {faqs.map((faq, i) => (
            <div
              key={i}
              className={`sp-feature-card${visible ? ' sp-reveal--in' : ' sp-reveal'}`}
              style={{ cursor: 'pointer', transitionDelay: `${i * 60}ms` }}
              onClick={() => setOpenIdx(openIdx === i ? null : i)}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h3 className="sp-feature-card__title" style={{ margin: 0, fontSize: '1.1rem' }}>{faq.q}</h3>
                <span style={{ fontSize: '1.2rem', color: 'var(--sp-primary, #4ade80)' }}>{openIdx === i ? '−' : '+'}</span>
              </div>
              {openIdx === i && (
                <p className="sp-feature-card__desc" style={{ marginTop: '0.8rem', color: 'var(--sp-text-secondary, #9ca3af)' }}>
                  {faq.a}
                </p>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

// ─── FINAL CTA ─────────────────────────────────────────────────────────────
const FinalCTA = () => {
  const [ref, visible] = useReveal();
  const [email, setEmail] = useState('');
  return (
    <section className="sp-cta" ref={ref}>
      <div className="sp-cta__glow" aria-hidden="true"/>
      <div className={`sp-container sp-cta__inner${visible?' sp-reveal--in':' sp-reveal'}`}>
        <h2 className="sp-cta__heading">
          Ready to Take Your<br />Social Media to the Next Level?
        </h2>
        <p className="sp-cta__sub">Join thousands of businesses already growing with SocialPilot.</p>
        <div className="sp-cta__form">
          <input
            type="email"
            className="sp-cta__input"
            placeholder="Enter your email"
            value={email}
            onChange={e => setEmail(e.target.value)}
          />
          <Link to={email ? `/register?email=${encodeURIComponent(email)}` : '/register'} className="sp-btn sp-btn--cta">
            Get Started →
          </Link>
        </div>
        <ul className="sp-cta__guarantees">
          <li><span className="sp-check">✓</span> Plan</li>
          <li><span className="sp-check">✓</span> Publish</li>
          <li><span className="sp-check">✓</span> Analyze</li>
        </ul>
      </div>
    </section>
  );
};

// ─── FOOTER ────────────────────────────────────────────────────────────────
const Footer = () => {
  const cols = [
    { title: 'Product', links: [{ label: 'Features', to: '#' }, { label: 'Integrations', to: '#' }, { label: 'Updates', to: '#' }] },
    { title: 'Resources', links: [{ label: 'Blog', to: '#' }, { label: 'Guides', to: '#' }, { label: 'Help Center', to: '#' }, { label: 'Templates', to: '#' }] },
    { title: 'Company', links: [{ label: 'About Us', to: '#' }, { label: 'Careers', to: '#' }, { label: 'Contact Us', to: '#' }, { label: 'Affiliates', to: '#' }] },
    { title: 'Legal', links: [
        { label: 'Privacy Policy', to: '/privacy-policy' },
        { label: 'Terms of Service', to: '/terms' },
        { label: 'Data Deletion', to: '/data-deletion' }
      ] 
    },
  ];
  const socials = [
    { name: 'Instagram', icon: '📸' },
    { name: 'Facebook', icon: '🤝' },
    { name: 'LinkedIn', icon: '💼' },
    { name: 'X', icon: '🐦' },
    { name: 'YouTube', icon: '▶️' },
  ];
  return (
    <footer className="sp-footer">
      <div className="sp-container sp-footer__inner">
        <div className="sp-footer__brand">
          <div className="sp-logo">
            <div className="sp-logo__icon sp-logo__icon--sm">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                <path d="M12 2L4 6v6c0 5.25 3.5 10.15 8 11.35C16.5 22.15 20 17.25 20 12V6l-8-4z" fill="url(#lgF)" opacity="0.9"/>
                <path d="M9 12l2 2 4-4" stroke="#fff" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
                <defs><linearGradient id="lgF" x1="4" y1="2" x2="20" y2="23" gradientUnits="userSpaceOnUse"><stop stopColor="#4ade80"/><stop offset="1" stopColor="#16a34a"/></linearGradient></defs>
              </svg>
            </div>
            <div className="sp-logo__text">
              <span className="sp-logo__name">SocialPilot</span>
              <span className="sp-logo__tagline">Plan. Publish. Perform.</span>
            </div>
          </div>
          <p className="sp-footer__desc">
            The all-in-one social media management platform for planning, publishing and growing your brand effectively.
          </p>
          <div className="sp-footer__socials">
            {socials.map(s => (
              <button key={s.name} className="sp-social-btn" aria-label={s.name}>{s.icon}</button>
            ))}
          </div>
        </div>
        <div className="sp-footer__cols">
          {cols.map(col => (
            <div key={col.title} className="sp-footer__col">
              <h4 className="sp-footer__col-title">{col.title}</h4>
              {col.links.map(link => (
                link.to.startsWith('/') ? (
                  <Link key={link.label} to={link.to} className="sp-footer__link">{link.label}</Link>
                ) : (
                  <a key={link.label} href={link.to} className="sp-footer__link">{link.label}</a>
                )
              ))}
            </div>
          ))}
        </div>
      </div>
      <div className="sp-footer__bottom">
        <div className="sp-container sp-footer__bottom-inner">
          <span>© 2025 SocialPilot. All rights reserved.</span>
          <select className="sp-footer__lang">
            <option>🌐 English</option>
          </select>
        </div>
      </div>
    </footer>
  );
};

// ─── MAIN PAGE ─────────────────────────────────────────────────────────────
export const LandingPage = () => {
  return (
    <div className="sp-landing">
      <Navbar />
      <HeroSection />
      <TrustedBrands />
      <PlatformIntro />
      <FeaturesSection />
      <HowItWorks />
      <Resources />
      <Testimonials />
      <FAQSection />
      <FinalCTA />
      <Footer />
    </div>
  );
};

export default LandingPage;
