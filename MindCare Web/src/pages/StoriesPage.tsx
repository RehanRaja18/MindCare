// ============================================================
// MindCare — Stories Page ("Words from people walking it.")
// ============================================================

import React, { useCallback, useState } from 'react';
import { motion } from 'framer-motion';
import Navbar from '../components/layout/Navbar';
import Footer from '../components/layout/Footer';
import Button from '../components/common/Button';
import Avatar from '../components/common/Avatar';
import Reveal, { RevealGroup, RevealItem } from '../components/motion/Reveal';
import ShareStoryModal from '../components/stories/ShareStoryModal';
import { STORIES, STORIES_TOTAL_COUNT } from '../constants';
import { getMyStories } from '../services/api.service';
import type { StoryEntry } from '../types';

// The grid reveals once on scroll; stories submitted after that animate in on
// their own, otherwise they would mount into the finished reveal and stay hidden.
const StoryCardWrapper: React.FC<{ pending?: boolean; children: React.ReactNode }> = ({ pending, children }) =>
  pending ? (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.55, ease: [0.22, 1, 0.36, 1] }}>
      {children}
    </motion.div>
  ) : (
    <RevealItem>{children}</RevealItem>
  );

const StoriesPage: React.FC = () => {
  const [myStories, setMyStories] = useState<StoryEntry[]>(getMyStories);
  const [shareOpen, setShareOpen] = useState(false);
  const closeShare = useCallback(() => setShareOpen(false), []);
  const stories = [...myStories, ...STORIES];

  return (
    <div className="min-h-screen mc-page-glow">
      <Navbar />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-32 pb-24">
        <Reveal>
          <p className="text-xs font-semibold tracking-widest text-gray-500 uppercase mb-6">
            Stories · Consented, real
          </p>

          <h1 className="text-4xl sm:text-6xl font-black text-gray-900 leading-[1.05] mb-16 max-w-3xl">
            Words from people <span className="italic font-serif font-normal">walking it.</span>
          </h1>
        </Reveal>

        <RevealGroup className="grid grid-cols-1 sm:grid-cols-2 gap-6 lg:ml-auto lg:max-w-3xl" stagger={0.1}>
          {stories.map((story) => (
            <StoryCardWrapper key={story.id} pending={story.pending}>
              <article className="relative bg-white rounded-2xl shadow-sm border border-gray-100 p-6 sm:p-8 flex flex-col justify-between min-h-[220px] sm:min-h-[260px] h-full">
                {story.pending && (
                  <span className="absolute top-4 right-4 rounded-full bg-amber-50 border border-amber-200 px-2.5 py-0.5 text-[10px] font-semibold tracking-wide text-amber-700 uppercase">
                    Awaiting review
                  </span>
                )}
                <p
                  className={`text-lg sm:text-xl text-gray-900 leading-snug font-medium break-words ${
                    story.pending ? 'mt-6' : ''
                  }`}
                >
                  &ldquo;{story.quote}&rdquo;
                </p>

                <div className="flex items-center gap-3 mt-8">
                  <Avatar initials={story.avatarInitials} color={story.avatarColor} />
                  <div className="min-w-0">
                    <p className="text-sm font-bold text-gray-900 truncate">
                      {story.name}
                      {story.age ? `, ${story.age}` : ''}
                    </p>
                    <p className="text-xs text-gray-500 truncate">
                      {story.location} · {story.tag}
                    </p>
                  </div>
                </div>
              </article>
            </StoryCardWrapper>
          ))}
        </RevealGroup>

        <Reveal delay={0.1}>
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6 mt-14 pt-8 border-t border-gray-200">
            <p className="text-sm text-gray-500">Names changed in some · all stories shared with explicit consent.</p>
            <div className="flex flex-col sm:flex-row gap-3 w-full sm:w-auto shrink-0">
              <Button variant="secondary" size="md" onClick={() => setShareOpen(true)}>
                Share your story
              </Button>
              <Button variant="primary" size="md">
                See all {STORIES_TOTAL_COUNT + myStories.length} stories →
              </Button>
            </div>
          </div>
        </Reveal>
      </main>

      <Footer />

      <ShareStoryModal
        open={shareOpen}
        onClose={closeShare}
        onSubmitted={(story) => setMyStories((prev) => [story, ...prev])}
      />
    </div>
  );
};

export default StoriesPage;
