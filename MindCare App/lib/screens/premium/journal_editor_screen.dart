import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_text_styles.dart';
import '../../core/utils/date_labels.dart';
import '../../providers/checkin_provider.dart';
import '../../providers/journal_provider.dart';
import '../../widgets/common/primary_button.dart';
import '../../widgets/common/sos_button.dart';

class JournalEditorScreen extends StatefulWidget {
  const JournalEditorScreen({super.key});

  @override
  State<JournalEditorScreen> createState() => _JournalEditorScreenState();
}

class _JournalEditorScreenState extends State<JournalEditorScreen> {
  final _title = TextEditingController();
  final _body = TextEditingController();
  String? _moodId;
  bool _share = false;

  @override
  void dispose() {
    _title.dispose();
    _body.dispose();
    super.dispose();
  }

  void _save() {
    if (_body.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Write a few words before saving.')),
      );
      return;
    }
    context.read<JournalProvider>().addEntry(body: _body.text, title: _title.text, moodId: _moodId, share: _share);
    Navigator.of(context).pop();
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(_share ? 'Saved and shared with your therapist.' : 'Saved to your journal.')),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: Stack(
          children: [
            ListView(
              padding: const EdgeInsets.fromLTRB(24, 8, 24, 130),
              children: [
                Row(
                  children: [
                    IconButton(
                      onPressed: () => Navigator.of(context).maybePop(),
                      icon: const Icon(Icons.close, color: AppColors.textDark),
                    ),
                    const Expanded(
                      child: Text(
                        'NEW ENTRY',
                        textAlign: TextAlign.center,
                        style: TextStyle(letterSpacing: 1, color: AppColors.textLabel, fontWeight: FontWeight.w600, fontSize: 12),
                      ),
                    ),
                    const SizedBox(width: 48),
                  ],
                ),
                const SizedBox(height: 8),
                Text(DateLabels.long(DateTime.now()).toUpperCase(), style: AppTextStyles.label()),
                const SizedBox(height: 6),
                Text.rich(
                  TextSpan(
                    style: AppTextStyles.heading(size: 28),
                    children: [
                      const TextSpan(text: "What's on "),
                      TextSpan(text: 'your mind?', style: AppTextStyles.heading(size: 28, style: FontStyle.italic)),
                    ],
                  ),
                ),
                const SizedBox(height: 22),
                Text('HOW ARE YOU FEELING?', style: AppTextStyles.label()),
                const SizedBox(height: 12),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    for (final mood in CheckinProvider.dailyMoods)
                      _MoodDot(
                        label: mood.label,
                        color: mood.color,
                        selected: _moodId == mood.id,
                        onTap: () => setState(() => _moodId = _moodId == mood.id ? null : mood.id),
                      ),
                  ],
                ),
                const SizedBox(height: 22),
                Container(
                  padding: const EdgeInsets.fromLTRB(18, 6, 18, 6),
                  decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(18)),
                  child: Column(
                    children: [
                      TextField(
                        controller: _title,
                        textCapitalization: TextCapitalization.sentences,
                        style: AppTextStyles.heading(size: 19),
                        decoration: InputDecoration(
                          hintText: 'Title (optional)',
                          hintStyle: AppTextStyles.heading(size: 19).copyWith(color: AppColors.textLabel),
                          border: InputBorder.none,
                          contentPadding: const EdgeInsets.symmetric(vertical: 14),
                        ),
                      ),
                      const Divider(height: 1, color: AppColors.border),
                      TextField(
                        controller: _body,
                        minLines: 8,
                        maxLines: null,
                        textCapitalization: TextCapitalization.sentences,
                        style: AppTextStyles.body(color: AppColors.textDark),
                        decoration: InputDecoration(
                          hintText: 'Start writing. No one will grade this.',
                          hintStyle: AppTextStyles.body(),
                          border: InputBorder.none,
                          contentPadding: const EdgeInsets.symmetric(vertical: 14),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 14),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
                  decoration: BoxDecoration(color: AppColors.cardBackground, borderRadius: BorderRadius.circular(18)),
                  child: Row(
                    children: [
                      const Icon(Icons.visibility_outlined, size: 18, color: AppColors.textDark),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text('Share with my therapist', style: TextStyle(fontWeight: FontWeight.w600, color: AppColors.textDark)),
                            Text('Off means only you can read it.', style: AppTextStyles.body(size: 12)),
                          ],
                        ),
                      ),
                      Switch(
                        value: _share,
                        activeThumbColor: Colors.white,
                        activeTrackColor: AppColors.progressActive,
                        onChanged: (v) => setState(() => _share = v),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            Positioned(
              left: 24,
              right: 24,
              bottom: 16,
              child: Row(
                children: [
                  Expanded(child: PrimaryButton(label: 'Save entry', icon: Icons.check, onPressed: _save)),
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

class _MoodDot extends StatelessWidget {
  const _MoodDot({required this.label, required this.color, required this.selected, required this.onTap});
  final String label;
  final Color color;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Column(
        children: [
          AnimatedContainer(
            duration: const Duration(milliseconds: 160),
            width: 46,
            height: 46,
            padding: const EdgeInsets.all(3),
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              border: Border.all(color: selected ? AppColors.textDark : Colors.transparent, width: 2),
            ),
            child: Container(
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: [Color.lerp(color, Colors.white, 0.4)!, color],
                ),
              ),
            ),
          ),
          const SizedBox(height: 6),
          Text(
            label,
            style: TextStyle(
              fontSize: 12,
              color: AppColors.textDark,
              fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }
}
