import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_text_styles.dart';
import '../../core/utils/date_labels.dart';
import '../../models/premium_data.dart';
import '../../providers/premium_provider.dart';
import '../../widgets/common/primary_button.dart';
import '../../widgets/premium/premium_widgets.dart';

/// Cancelling Premium: what changes, an optional reason, then a confirmation.
class CancelSubscriptionScreen extends StatefulWidget {
  const CancelSubscriptionScreen({super.key});

  static const reasons = [
    'Too expensive',
    "I'm not using it enough",
    'I got what I needed',
    'Something is not working',
    'Something else',
  ];

  @override
  State<CancelSubscriptionScreen> createState() => _CancelSubscriptionScreenState();
}

class _CancelSubscriptionScreenState extends State<CancelSubscriptionScreen> {
  String? _reason;
  final _details = TextEditingController();
  bool _working = false;
  DateTime? _endedAt;
  bool _done = false;

  @override
  void dispose() {
    _details.dispose();
    super.dispose();
  }

  Future<void> _cancel() async {
    setState(() => _working = true);
    // The backend cancellation call goes here once it exists.
    await Future.delayed(const Duration(milliseconds: 500));
    if (!mounted) return;
    final reason = [_reason, _details.text.trim()].where((s) => s != null && s.isNotEmpty).join(' · ');
    final until = context.read<PremiumProvider>().cancel(reason: reason);
    setState(() {
      _working = false;
      _endedAt = until;
      _done = true;
    });
  }

  @override
  Widget build(BuildContext context) {
    return _done ? _buildDone(context) : _buildForm(context);
  }

  Widget _buildForm(BuildContext context) {
    final premium = context.watch<PremiumProvider>();
    final until = premium.status == PremiumStatus.trial ? premium.trialEndsAt : premium.nextChargeAt;
    final onTrial = premium.status == PremiumStatus.trial;

    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(24, 8, 24, 32),
          children: [
            const PremiumTopBar(label: 'CANCEL SUBSCRIPTION'),
            const SizedBox(height: 10),
            Text.rich(
              TextSpan(
                style: AppTextStyles.heading(size: 28),
                children: [
                  const TextSpan(text: "We're sorry to\n"),
                  TextSpan(text: 'see you go.', style: AppTextStyles.heading(size: 28, style: FontStyle.italic)),
                ],
              ),
            ),
            const SizedBox(height: 8),
            Text('Here is exactly what happens if you cancel.', style: AppTextStyles.body()),
            const SizedBox(height: 20),
            Container(
              padding: const EdgeInsets.all(18),
              decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(20)),
              child: Column(
                children: [
                  _Point(
                    icon: Icons.event_available_outlined,
                    color: AppColors.progressActive,
                    text: until == null
                        ? 'Premium stays on until the end of your current period.'
                        : 'You keep Premium until ${DateLabels.long(until)}${onTrial ? ', the end of your free trial' : ''}.',
                  ),
                  _Point(
                    icon: Icons.money_off_outlined,
                    color: AppColors.progressActive,
                    text: onTrial ? "You won't be charged anything." : "You won't be charged again.",
                  ),
                  const _Point(
                    icon: Icons.menu_book_outlined,
                    color: AppColors.amberSegment,
                    text: 'After that, Journal and Outings lock. Your entries are kept and come back if you return.',
                  ),
                  const _Point(
                    icon: Icons.favorite_border,
                    color: AppColors.amberSegment,
                    text: 'Your therapist, care plan and SOS are not affected. They stay free.',
                    last: true,
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),
            Text('WHY ARE YOU LEAVING? (OPTIONAL)', style: AppTextStyles.label()),
            const SizedBox(height: 12),
            Material(
              color: Colors.white,
              borderRadius: BorderRadius.circular(20),
              clipBehavior: Clip.antiAlias,
              child: RadioGroup<String>(
                groupValue: _reason,
                onChanged: (v) => setState(() => _reason = v),
                child: Column(
                  children: [
                    for (var i = 0; i < CancelSubscriptionScreen.reasons.length; i++) ...[
                      RadioListTile<String>(
                        value: CancelSubscriptionScreen.reasons[i],
                        activeColor: AppColors.primaryDark,
                        dense: true,
                        title: Text(
                          CancelSubscriptionScreen.reasons[i],
                          style: const TextStyle(fontSize: 14, color: AppColors.textDark, fontWeight: FontWeight.w500),
                        ),
                      ),
                      if (i < CancelSubscriptionScreen.reasons.length - 1)
                        const Divider(height: 1, color: AppColors.border, indent: 16, endIndent: 16),
                    ],
                  ],
                ),
              ),
            ),
            if (_reason == 'Too expensive') ...[
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(color: AppColors.insightLeafBg, borderRadius: BorderRadius.circular(16)),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Icon(Icons.volunteer_activism_outlined, size: 18, color: AppColors.progressActive),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        'NGO scholarships can cover up to 80% of the cost. Ask your therapist or our support team before you go.',
                        style: AppTextStyles.body(size: 13, color: AppColors.chipTextUnselected),
                      ),
                    ),
                  ],
                ),
              ),
            ],
            if (_reason != null) ...[
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 14),
                decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16)),
                child: TextField(
                  controller: _details,
                  maxLines: 3,
                  maxLength: 300,
                  textCapitalization: TextCapitalization.sentences,
                  decoration: InputDecoration(
                    hintText: 'Anything you want to tell us? (optional)',
                    hintStyle: AppTextStyles.body(size: 14),
                    border: InputBorder.none,
                    counterText: '',
                  ),
                ),
              ),
            ],
            const SizedBox(height: 26),
            PrimaryButton(label: 'Keep Premium', icon: null, onPressed: () => Navigator.of(context).pop()),
            const SizedBox(height: 12),
            SizedBox(
              height: 54,
              child: OutlinedButton(
                onPressed: _working ? null : _cancel,
                style: OutlinedButton.styleFrom(
                  side: const BorderSide(color: AppColors.sos),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
                ),
                child: _working
                    ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2.2, color: AppColors.sos))
                    : const Text('Cancel subscription', style: TextStyle(color: AppColors.sos, fontWeight: FontWeight.w700, fontSize: 15)),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDone(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(24, 8, 24, 32),
          children: [
            const PremiumTopBar(label: 'SUBSCRIPTION CANCELLED'),
            const SizedBox(height: 36),
            Center(
              child: Container(
                width: 88,
                height: 88,
                decoration: const BoxDecoration(color: AppColors.chipUnselected, shape: BoxShape.circle),
                child: const Icon(Icons.check_rounded, size: 42, color: AppColors.primaryDark),
              ),
            ),
            const SizedBox(height: 22),
            Text('Your subscription\nis cancelled.', textAlign: TextAlign.center, style: AppTextStyles.heading(size: 28)),
            const SizedBox(height: 12),
            Text(
              _endedAt == null
                  ? "You won't be charged again."
                  : "You won't be charged again. Premium stays on until ${DateLabels.long(_endedAt!)}, so you can keep using Journal and Outings until then.",
              textAlign: TextAlign.center,
              style: AppTextStyles.body(),
            ),
            const SizedBox(height: 10),
            Text(
              'Changed your mind? You can resume any time before then from Manage subscription.',
              textAlign: TextAlign.center,
              style: AppTextStyles.body(size: 13),
            ),
            const SizedBox(height: 30),
            PrimaryButton(label: 'Done', icon: null, onPressed: () => Navigator.of(context).pop()),
          ],
        ),
      ),
    );
  }
}

class _Point extends StatelessWidget {
  const _Point({required this.icon, required this.color, required this.text, this.last = false});
  final IconData icon;
  final Color color;
  final String text;
  final bool last;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(bottom: last ? 0 : 14),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 30,
            height: 30,
            decoration: BoxDecoration(color: color.withValues(alpha: 0.14), shape: BoxShape.circle),
            child: Icon(icon, size: 16, color: color),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Padding(
              padding: const EdgeInsets.only(top: 5),
              child: Text(text, style: AppTextStyles.body(size: 14, color: AppColors.textDark)),
            ),
          ),
        ],
      ),
    );
  }
}
