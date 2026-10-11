import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_text_styles.dart';
import '../../core/utils/date_labels.dart';
import '../../providers/journal_provider.dart';
import '../../widgets/premium/premium_widgets.dart';
import 'journal_screen.dart';

class JournalEntryScreen extends StatelessWidget {
  const JournalEntryScreen({super.key, required this.entryId});
  final String entryId;

  Future<void> _confirmDelete(BuildContext context) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        backgroundColor: AppColors.background,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: const Text('Delete this entry?', style: TextStyle(fontWeight: FontWeight.w700, color: AppColors.textDark)),
        content: Text("It can't be recovered afterwards.", style: AppTextStyles.body(size: 14)),
        actions: [
          TextButton(onPressed: () => Navigator.of(dialogContext).pop(false), child: const Text('Cancel', style: TextStyle(color: AppColors.textMuted))),
          TextButton(onPressed: () => Navigator.of(dialogContext).pop(true), child: const Text('Delete', style: TextStyle(color: AppColors.sos, fontWeight: FontWeight.w700))),
        ],
      ),
    );
    if (confirmed == true && context.mounted) {
      context.read<JournalProvider>().deleteEntry(entryId);
      Navigator.of(context).pop();
    }
  }

  @override
  Widget build(BuildContext context) {
    final entry = context.watch<JournalProvider>().byId(entryId);
    if (entry == null) {
      return const Scaffold(backgroundColor: AppColors.background, body: SizedBox.shrink());
    }
    final mood = moodById(entry.moodId);

    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(24, 8, 24, 32),
          children: [
            PremiumTopBar(
              label: 'JOURNAL',
              trailing: IconButton(
                tooltip: 'Delete entry',
                onPressed: () => _confirmDelete(context),
                icon: const Icon(Icons.delete_outline, color: AppColors.textMuted, size: 20),
              ),
            ),
            const SizedBox(height: 10),
            Text(
              '${DateLabels.long(entry.createdAt)} · ${DateLabels.time(entry.createdAt)}'.toUpperCase(),
              style: AppTextStyles.label(),
            ),
            const SizedBox(height: 10),
            if (mood != null)
              Row(
                children: [
                  Container(width: 12, height: 12, decoration: BoxDecoration(color: mood.color, shape: BoxShape.circle)),
                  const SizedBox(width: 8),
                  Text('Feeling ${mood.label.toLowerCase()}', style: AppTextStyles.body(size: 13, color: AppColors.textDark)),
                ],
              ),
            const SizedBox(height: 14),
            if (entry.title != null) ...[
              Text(entry.title!, style: AppTextStyles.heading(size: 26)),
              const SizedBox(height: 14),
            ],
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(20)),
              child: SelectableText(entry.body, style: AppTextStyles.body(size: 15, color: AppColors.textDark).copyWith(height: 1.6)),
            ),
            const SizedBox(height: 14),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
              decoration: BoxDecoration(color: AppColors.cardBackground, borderRadius: BorderRadius.circular(18)),
              child: Row(
                children: [
                  Icon(
                    entry.sharedWithTherapist ? Icons.visibility_outlined : Icons.lock_outline,
                    size: 18,
                    color: AppColors.textDark,
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          entry.sharedWithTherapist ? 'Shared with your therapist' : 'Private to you',
                          style: const TextStyle(fontWeight: FontWeight.w600, color: AppColors.textDark),
                        ),
                        Text(
                          entry.sharedWithTherapist ? 'They can read this entry.' : 'Turn on to let your therapist read it.',
                          style: AppTextStyles.body(size: 12),
                        ),
                      ],
                    ),
                  ),
                  Switch(
                    value: entry.sharedWithTherapist,
                    activeThumbColor: Colors.white,
                    activeTrackColor: AppColors.progressActive,
                    onChanged: (v) => context.read<JournalProvider>().setShared(entry.id, v),
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
