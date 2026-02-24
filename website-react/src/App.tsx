import './App.css'
import Navbar from './components/Navbar/Navbar'
import Hero from './components/Hero/Hero'
import Stats from './components/Stats/Stats'
import Features from './components/Features/Features'
import HowItWorks from './components/HowItWorks/HowItWorks'
import Demo from './components/Demo/Demo'
import Testimonials from './components/Testimonials/Testimonials'
import CTA from './components/CTA/CTA'
import Footer from './components/Footer/Footer'

function App() {
  return (
    <>
      <Navbar />
      <Hero />
      <Stats />
      <Features />
      <HowItWorks />
      <Demo />
      <Testimonials />
      <CTA />
      <Footer />
    </>
  )
}

export default App
