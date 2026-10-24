import { useState } from 'react'
import { motion, useReducedMotion } from 'motion/react'
import {
  ArrowUpRight, Sparkles, ShieldCheck, Compass, Layers3,
  Activity, Menu, X, Search, Check, MoveUpRight
} from 'lucide-react'
import config from './config.json'

const ICONS = { sparkles: Sparkles, shield: ShieldCheck, compass: Compass, layers: Layers3, activity: Activity }
const easing = [0.22, 1, 0.36, 1]

function IconFor({ name, size = 22 }) {
  const Component = ICONS[name] || Sparkles
  return <Component size={size} strokeWidth={1.65} aria-hidden="true" />
}

export default function App() {
  const [menuOpen, setMenuOpen] = useState(false)
  const [modal, setModal] = useState(null)
  const [search, setSearch] = useState('')
  const reduced = useReducedMotion()
  const cards = config.features.filter(item =>
    (item.title + ' ' + item.detail).toLocaleLowerCase('es')
      .includes(search.toLocaleLowerCase('es'))
  )
  const reveal = reduced ? {} : {
    initial: { opacity: 0, y: 20 },
    whileInView: { opacity: 1, y: 0 },
    viewport: { once: true, amount: 0.15 },
    transition: { duration: 0.55, ease: easing }
  }
  const theme = {
    '--accent': config.primary,
    '--accent-2': config.secondary,
    '--background': config.background,
    '--foreground': config.foreground
  }

  function closeMenu() { setMenuOpen(false) }

  return <div className="site" style={theme}
              data-style={config.style} data-layout={config.layout}>
    <a href="#main" className="skip">Saltar al contenido principal</a>
    <header className="topbar">
      <a href="#inicio" className="brand" onClick={closeMenu} aria-label={config.title + ', inicio'}>
        <span className="brand-icon"><Sparkles size={20} aria-hidden="true" /></span>
        <span>{config.title}</span>
      </a>
      <button className="menu-toggle" type="button"
        aria-label={menuOpen ? 'Cerrar menú' : 'Abrir menú'}
        aria-expanded={menuOpen} aria-controls="menu-primary"
        onClick={() => setMenuOpen(value => !value)}>
        {menuOpen ? <X size={22} /> : <Menu size={22} />}
      </button>
      <nav id="menu-primary" className={menuOpen ? 'menu open' : 'menu'} aria-label="Navegación principal">
        <a href="#experiencia" onClick={closeMenu}>Experiencia</a>
        <a href="#capacidades" onClick={closeMenu}>Capacidades</a>
        <a href="#contacto" onClick={closeMenu}>Contacto</a>
        <button type="button" className="nav-action"
          onClick={() => { closeMenu(); setModal('contacto') }}>
          Empezar <ArrowUpRight size={16} aria-hidden="true" />
        </button>
      </nav>
    </header>
    <main id="main">
      <section id="inicio" className="hero" aria-labelledby="hero-title">
        <div className="hero-glow" aria-hidden="true" />
        <motion.div className="hero-copy" {...reveal}>
          <p className="eyebrow"><span className="pulse" /> {config.eyebrow}</p>
          <h1 id="hero-title">{config.subtitle}</h1>
          <p className="hero-desc">{config.description}</p>
          <div className="hero-actions">
            <a href="#capacidades" className="primary-btn">
              Explorar capacidades <ArrowUpRight size={19} aria-hidden="true" />
            </a>
            <button type="button" className="subtle-btn" onClick={() => setModal('demo')}>
              Ver detalles <MoveUpRight size={19} aria-hidden="true" />
            </button>
          </div>
          <p className="microcopy"><ShieldCheck size={15} aria-hidden="true" /> Creado para personas, optimizado para experiencias.</p>
        </motion.div>
        <motion.div className="hero-visual" {...reveal}
          transition={{ delay: reduced ? 0 : 0.12, duration: 0.65, ease: easing }}>
          <div className="orbit orbit-one" aria-hidden="true" />
          <div className="orbit orbit-two" aria-hidden="true" />
          <div className="visual-core" aria-hidden="true"><Sparkles size={52} strokeWidth={1.25} /></div>
          <div className="visual-panel visual-panel-top">
            <span className="status-dot" /><span>Experiencia en vivo</span>
          </div>
          <div className="visual-panel visual-panel-bottom">
            <Layers3 size={18} aria-hidden="true" /><span>Diseño con propósito</span>
          </div>
        </motion.div>
      </section>
      <section id="experiencia" className="metrics" aria-label="Los tres pilares de la experiencia">
        {config.metrics.map(item =>
          <div className="metric" key={item.label}>
            <span className="metric-value">{item.value}</span>
            <span className="metric-label">{item.label}</span>
          </div>
        )}
      </section>
      <section id="capacidades" className="features" aria-labelledby="features-title">
        <motion.div className="section-head" {...reveal}>
          <div>
            <p className="section-kicker">SISTEMA DE EXPERIENCIAS</p>
            <h2 id="features-title">Diseñado para destacar.</h2>
          </div>
          <label className="search">
            <Search size={18} aria-hidden="true" />
            <span className="sr-only">Filtrar capacidades</span>
            <input type="search" placeholder="Buscar capacidades" value={search}
              onChange={event => setSearch(event.target.value)} />
          </label>
        </motion.div>
        <div className="feature-grid">
          {cards.map((item, index) =>
            <motion.button {...reveal} type="button" className="feature-card" key={item.title}
              whileHover={reduced ? undefined : { y: -5 }}
              onClick={() => setModal(item.title)}>
              <span className="feature-top">
                <span className="feature-icon"><IconFor name={item.icon} /></span>
                <span className="feature-index">0{index + 1}</span>
              </span>
              <span className="feature-title">{item.title}</span>
              <span className="feature-desc">{item.detail}</span>
              <span className="feature-bottom">Conocer más <ArrowUpRight size={17} aria-hidden="true" /></span>
            </motion.button>
          )}
          {cards.length === 0 && <p className="empty">No se encontraron capacidades. Probá otra búsqueda.</p>}
        </div>
      </section>
      <section id="contacto" className="cta">
        <motion.div {...reveal}>
          <p className="section-kicker">PRÓXIMA EXPERIENCIA</p>
          <h2>Construí algo que valga la pena explorar.</h2>
          <p>Una idea clara, una interfaz memorable y funcionalidades comprobables.</p>
          <button className="primary-btn" type="button" onClick={() => setModal('contacto')}>
            Comenzar ahora <ArrowUpRight size={18} aria-hidden="true" />
          </button>
        </motion.div>
      </section>
    </main>
    <footer className="footer"><span>{config.title}</span><span>Diseñado con SKY · {new Date().getFullYear()}</span></footer>
    {modal && <div className="modal-scrim" role="presentation" onMouseDown={event => {
      if (event.target === event.currentTarget) setModal(null)
    }}>
      <section className="modal" role="dialog" aria-modal="true" aria-labelledby="modal-title">
        <button className="close" type="button" aria-label="Cerrar diálogo" onClick={() => setModal(null)}><X size={21} /></button>
        <span className="feature-icon"><Check size={22} aria-hidden="true" /></span>
        <h2 id="modal-title">{modal === 'demo' ? 'Experiencia interactiva' :
          modal === 'contacto' ? 'Siguiente paso' : modal}</h2>
        <p>{modal === 'contacto'
          ? 'Este es un proyecto demostrativo. Conectá un formulario o un servicio de contacto autorizado para recibir solicitudes reales.'
          : config.features.find(item => item.title === modal)?.detail ||
            'Esta página demuestra animación, accesibilidad y navegación responsiva sin simular servicios inexistentes.'}</p>
        <button type="button" className="primary-btn" onClick={() => setModal(null)}>Entendido <Check size={17}/></button>
      </section>
    </div>}
  </div>
}
