import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_text_styles.dart';
import '../../core/utils/date_labels.dart';
import '../../main.dart';
import '../../models/checkin_data.dart';
import '../../models/premium_data.dart';
import '../../providers/checkin_provider.dart';
import '../../providers/journal_provider.dart';
import '../../widgets/common/primary_button.dart';
import '../../widgets/common/sos_button.dart';
import '../../widgets/premium/premium_widgets.dart';
import 'journal_editor_screen.dart';
import 'journal_entry_screen.dart';

DailyMoodOption? moodById(String? id) {
  if (id == null) return null;
  for (final m in CheckinProvider.dailyMoods) {
    if (m.id == id) return m;
  }
  return null;
}

class JournalScreen extends StatelessWidget {
  const JournalScreen({super.key});

  void _write(BuildContext context) => Navigator.of(context).push(
        MaterialPageRoute(builder: (_) => const MobileFrame(child: JournalEditorScreen())),
      );

  @override
  Widget build(BuildContext context) {
    return PremiumGate(
      caption: 'JOURNAL',
      icon: Icons.menu_book_outlined,
      title: 'Your private journal',
      description: 'A quiet place to write things down. Add your mood, look back over time, and share only the entries you choose with your therapist.',
      child: _JournalBody(onWrite: () => _write(context)),
    );
  }
}

class _JournalBody extends StatelessWidget {
  const _JournalBody({required this.onWrite});
  final VoidCallback onWrite;

  @override
  Widget build(BuildContext context) {
    final journal = context.watch<JournalProvider>();
    final entries = journal.entries;

    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: Stack(
          children: [
            ListView(
              padding: const EdgeInsets.fromLTRB(24, 8, 24, 130),
              children: [
                const PremiumTopBar(label: 'JOURNAL'),
                const SizedBox(height: 10),
                Text.rich(
                  TextSpan(
                    style: AppTextStyles.heading(size: 30),
                    children: [
                      const TextSpan(text: 'Write it\n'),
                      TextSpan(text: 'down.', style: AppTextStyles.heading(size: 30, style: FontStyle.italic)),
                    ],
                  ),
                ),
                const SizedBox(height: 8),
                Text('Only you can read your journal, unless you share an entry with your therapist.', style: AppTextStyles.body()),
                const SizedBox(height: 20),
                _PromptCard(onTap: onWrite),
                const SizedBox(height: 24),
                if (entries.isEmpty)
                  const _EmptyJournal()
                else ...[
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text('YOUR ENTRIES', style: AppTextStyles.label()),
                      Text(
                        '${entries.length} ${entries.length == 1 ? 'entry' : 'entries'} · ${journal.sharedCount} shared',
                        style: AppTextStyles.body(size: 12),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  for (final entry in entries) _EntryTile(entry: entry),
                ],
              ],
            ),
            Positioned(
              left: 24,
              right: 24,
              bottom: 16,
              child: Row(
                children: [
                  Expanded(child: PrimaryButton(label: 'New entry', icon: Icons.edit_outlined, onPressed: onWrite)),
                  const SizedBox(width: 12),
                  const SosButton(),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _PromptCard extends StatelessWidget {
  const _PromptCard({required this.onTap});
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(18),
        decoration: BoxDecoration(color: AppColors.infoBoxBackground, borderRadius: BorderRadius.circular(20)),
        child: Row(
          children: [
            Container(
              width: 40,
              height: 40,
              decoration: const BoxDecoration(color: AppColors.primaryDark, shape: BoxShape.circle),
              child: const Icon(Icons.auto_awesome, color: Colors.white, size: 18),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text("TODAY'S PROMPT", style: AppTextStyles.label().copyWith(color: AppColors.infoBoxText)),
                  const SizedBox(height: 4),
                  Text('What took up most of your mind today?', style: AppTextStyles.heading(size: 17)),
                ],
              ),
            ),
            const Icon(Icons.chevron_right, color: AppColors.infoBoxText),
          ],
        ),
      ),
    );
  }
}

class _EmptyJournal extends StatelessWidget {
  const _EmptyJournal();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 32, horizontal: 24),
      decoration: BoxDecoration(color: AppColors.cardBackground, borderRadius: BorderRadius.circular(22)),
      child: Column(
        children: [
          Container(
            width: 56,
            height: 56,
            decoration: const BoxDecoration(color: AppColors.chipUnselected, shape: BoxShape.circle),
            child: const Icon(Icons.edit_note, size: 28, color: AppColors.primaryDark),
          ),
          const SizedBox(height: 14),
          Text('No entries yet', style: AppTextStyles.heading(size: 20)),
          const SizedBox(height: 6),
          Text(
            'A few lines is enough. Your first entry will appear here.',
            textAlign: TextAlign.center,
            style: AppTextStyles.body(size: 13),
          ),
        ],
      ),
    );
  }
}

class _EntryTile extends StatelessWidget {
  const _EntryTile({required this.entry});
  final JournalEntry entry;

  @override
  Widget build(BuildContext context) {
    final mood = moodById(entry.moodId);
    return GestureDetector(
      onTap: () => Navigator.of(context).push(
        MaterialPageRoute(builder: (_) => MobileFrame(child: JournalEntryScreen(entryId: entry.id))),
      ),
      child: Container(
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(18)),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: 12,
              height: 12,
              margin: const EdgeInsets.only(top: 4),
              decoration: BoxDecoration(color: mood?.color ?? AppColors.border, shape: BoxShape.circle),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Text(
                        '${DateLabels.day(entry.createdAt)} · ${DateLabels.time(entry.createdAt)}',
                        style: AppTextStyles.label().copyWith(fontSize: 11),
                      ),
                      const Spacer(),
                      if (entry.sharedWithTherapist)
                        const Row(
                          children: [
                            Icon(Icons.visibility_outlined, size: 13, color: AppColors.progressActive),
                            SizedBox(width: 4),
                            Text('Shared', style: TextStyle(fontSize: 11, color: AppColors.progressActive, fontWeight: FontWeight.w600)),
                          ],
                        ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  if (entry.title != null) ...[
                    Text(entry.title!, style: const TextStyle(fontWeight: FontWeight.w700, color: AppColors.textDark, fontSize: 15)),
                    const SizedBox(height: 3),
                  ],
                  Text(
                    entry.body,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: AppTextStyles.body(size: 13),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
