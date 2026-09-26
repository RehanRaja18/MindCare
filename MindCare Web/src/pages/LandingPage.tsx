// ============================================================
// MindCare — Screen 1: Landing Page
// ============================================================

import React from 'react';
import { motion, type Variants } from 'framer-motion';
import Navbar from '../components/layout/Navbar';
import Footer from '../components/layout/Footer';
import HeroSection from '../components/sections/HeroSection';
import PartnersSection from '../components/sections/PartnersSection';
import VideoSection from '../components/sections/VideoSection';
import HowItWorksSection from '../components/sections/HowItWorksSection';
import PracticeGallerySection from '../components/sections/PracticeGallerySection';
import PathBannerSection from '../components/sections/PathBannerSection';
import VisionMissionSection from '../components/sections/VisionMissionSection';
import FeaturesSection from '../components/sections/FeaturesSection';
import TeamSection from '../components/sections/TeamSection';

// Calm, short fade + slight upward slide — used for every section below the fold.
const fadeUp: Variants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.4, ease: 'easeOut' } },
};

const LandingPage: React.FC = () => {
  return (
  <>
    <Navbar />
    <main id="main-content" className="mc-page-glow">
      {/* Hero is above the fold — fades in once on page load, not on scroll */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: 'easeOut' }}
      >
        <HeroSection />
      </motion.div>

      <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={fadeUp}>
        <PartnersSection />
      </motion.div>

      <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={fadeUp}>
        <VideoSection />
      </motion.div>

      <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={fadeUp}>
        <HowItWorksSection />
      </motion.div>

      <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={fadeUp}>
        <PracticeGallerySection />
      </motion.div>

      <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={fadeUp}>
        <PathBannerSection />
      </motion.div>

      <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={fadeUp}>
        <VisionMissionSection />
      </motion.div>

      <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={fadeUp}>
        <FeaturesSection />
      </motion.div>

      <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={fadeUp}>
        <TeamSection />
      </motion.div>
    </main>
    <Footer />
  </>
  );
};

export default LandingPage;
