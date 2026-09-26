// ============================================================
// MindCare — "Share your story" dialog
// Bottom sheet on phones, centred dialog from `sm` up.
// ============================================================

import React, { useEffect, useRef, useState } from 'react';
import { CheckCircle2 } from 'lucide-react';
import Button from '../common/Button';
import Sheet, { sheetInputClass as inputClass } from '../common/Sheet';
import { submitStory } from '../../services/api.service';
import { cn } from '../../utils/cn';
import type { StoryEntry } from '../../types';

interface ShareStoryModalProps {
  open: boolean;
  onClose: () => void;
  onSubmitted: (story: StoryEntry) => void;
}

const TOPICS = ['anxiety', 'grief', 'burnout', 'depression', 'relationships', 'sobriety', 'other'];
const MIN_CHARS = 20;
const MAX_CHARS = 400;

const ShareStoryModal: React.FC<ShareStoryModalProps> = ({ open, onClose, onSubmitted }) => {
  const [quote, setQuote] = useState('');
  const [name, setName] = useState('');
  const [age, setAge] = useState('');
  const [location, setLocation] = useState('');
  const [tag, setTag] = useState(TOPICS[0]);
  const [consent, setConsent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);
  const firstFieldRef = useRef<HTMLTextAreaElement>(null);

  // Reset the form each time the dialog opens
  useEffect(() => {
    if (!open) return;
    setQuote('');
    setName('');
    setAge('');
    setLocation('');
    setTag(TOPICS[0]);
    setConsent(false);
    setError(null);
    setDone(false);
    const t = setTimeout(() => firstFieldRef.current?.focus(), 150);
    return () => clearTimeout(t);
  }, [open]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = quote.trim();
    const ageNum = age ? Number(age) : null;

    if (trimmed.length < MIN_CHARS) return setError(`Please write at least ${MIN_CHARS} characters.`);
    if (ageNum !== null && (!Number.isInteger(ageNum) || ageNum < 13 || ageNum > 110))
      return setError('Please enter an age between 13 and 110, or leave it blank.');
    if (!location.trim()) return setError('Please add your city.');
    if (!consent) return setError('Please confirm you consent to sharing your story.');

    setError(null);
    setSubmitting(true);
    const res = await submitStory({ quote: trimmed, name, age: ageNum, location, tag });
    setSubmitting(false);

    if (res.error || !res.data) return setError(res.error ?? 'Something went wrong. Please try again.');
    onSubmitted(res.data);
    setDone(true);
  };

  return (
    <Sheet open={open} onClose={onClose} labelledBy="share-story-title">
            {done ? (
              <div className="px-6 sm:px-8 py-12 text-center">
                <CheckCircle2 size={44} className="mx-auto text-emerald-500 mb-4" aria-hidden="true" />
                <h2 id="share-story-title" className="text-2xl font-black text-gray-900 mb-3">
                  Thank you for sharing.
                </h2>
                <p className="text-sm text-gray-600 leading-relaxed max-w-sm mx-auto mb-8">
                  Your story is with our moderation team. You'll see it on this page marked
                  &ldquo;awaiting review&rdquo; until it's approved.
                </p>
                <Button variant="primary" size="md" onClick={onClose} className="rounded-full">
                  Back to stories
                </Button>
              </div>
            ) : (
              <form onSubmit={handleSubmit} noValidate className="px-6 sm:px-8 pt-6 sm:pt-8 pb-6">
                <p className="text-xs font-semibold tracking-widest text-gray-500 uppercase mb-2">
                  Share your story
                </p>
                <h2 id="share-story-title" className="text-2xl sm:text-3xl font-black text-gray-900 leading-tight mb-6 pr-8">
                  What has the path <span className="italic font-serif font-normal">felt like?</span>
                </h2>

                <div className="space-y-4">
                  <div>
                    <label htmlFor="story-quote" className="block text-sm font-semibold text-gray-800 mb-1.5">
                      Your story
                    </label>
                    <textarea
                      id="story-quote"
                      ref={firstFieldRef}
                      value={quote}
                      onChange={(e) => setQuote(e.target.value.slice(0, MAX_CHARS))}
                      rows={4}
                      placeholder="A moment, a small win, what helped…"
                      className={cn(inputClass, 'resize-none')}
                      required
                    />
                    <p className="mt-1 text-right text-xs text-gray-400">
                      {quote.length}/{MAX_CHARS}
                    </p>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-[1fr_96px] gap-4">
                    <div>
                      <label htmlFor="story-name" className="block text-sm font-semibold text-gray-800 mb-1.5">
                        First name <span className="font-normal text-gray-400">(optional)</span>
                      </label>
                      <input
                        id="story-name"
                        value={name}
                        onChange={(e) => setName(e.target.value.slice(0, 30))}
                        placeholder="Anonymous"
                        autoComplete="given-name"
                        className={inputClass}
                      />
                    </div>
                    <div>
                      <label htmlFor="story-age" className="block text-sm font-semibold text-gray-800 mb-1.5">
                        Age <span className="font-normal text-gray-400 sm:hidden">(optional)</span>
                      </label>
                      <input
                        id="story-age"
                        type="number"
                        inputMode="numeric"
                        min={13}
                        max={110}
                        value={age}
                        onChange={(e) => setAge(e.target.value.slice(0, 3))}
                        placeholder="—"
                        className={inputClass}
                      />
                    </div>
                  </div>

                  <div>
                    <label htmlFor="story-city" className="block text-sm font-semibold text-gray-800 mb-1.5">
                      City
                    </label>
                    <input
                      id="story-city"
                      value={location}
                      onChange={(e) => setLocation(e.target.value.slice(0, 40))}
                      placeholder="e.g. Lahore"
                      autoComplete="address-level2"
                      className={inputClass}
                      required
                    />
                  </div>

                  <fieldset>
                    <legend className="block text-sm font-semibold text-gray-800 mb-2">Topic</legend>
                    <div className="flex flex-wrap gap-2">
                      {TOPICS.map((t) => (
                        <button
                          key={t}
                          type="button"
                          onClick={() => setTag(t)}
                          aria-pressed={tag === t}
                          className={cn(
                            'px-3.5 py-1.5 rounded-full border text-sm capitalize transition-colors',
                            tag === t
                              ? 'bg-gray-900 border-gray-900 text-white'
                              : 'bg-white border-gray-200 text-gray-700 hover:border-gray-400'
                          )}
                        >
                          {t}
                        </button>
                      ))}
                    </div>
                  </fieldset>

                  <label className="flex items-start gap-3 rounded-xl bg-white border border-gray-200 p-4 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={consent}
                      onChange={(e) => setConsent(e.target.checked)}
                      className="mt-0.5 h-4 w-4 shrink-0 accent-gray-900"
                    />
                    <span className="text-xs text-gray-600 leading-relaxed">
                      I consent to MindCare publishing this story after review. I can ask for it to be
                      removed at any time. Please don't include anyone's full name or contact details.
                    </span>
                  </label>
                </div>

                {error && (
                  <p role="alert" className="mt-4 text-sm text-rose-600">
                    {error}
                  </p>
                )}

                <div className="mt-6 flex flex-col-reverse sm:flex-row sm:justify-end gap-3">
                  <Button type="button" variant="ghost" size="md" onClick={onClose}>
                    Cancel
                  </Button>
                  <Button type="submit" variant="primary" size="md" loading={submitting}>
                    Submit story
                  </Button>
                </div>
              </form>
            )}
    </Sheet>
  );
};

export default ShareStoryModal;
