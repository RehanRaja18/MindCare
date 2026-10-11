import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_text_styles.dart';
import '../../core/utils/date_labels.dart';
import '../../main.dart';
import '../../providers/premium_provider.dart';
import '../../widgets/common/primary_button.dart';
import '../../widgets/premium/card_form.dart';
import '../../widgets/premium/premium_widgets.dart';
import 'journal_screen.dart';
import 'outings_screen.dart';

enum CheckoutMode {
  /// Add a card and start the 7-day free trial.
  trial,

  /// Trial already used: pay Rs 1,500 now and renew monthly.
  subscribe,

  /// Replace the card on file.
  updateCard,
}

/// Add a card, agree to the renewal terms, then start the free trial (or
/// subscribe). In [CheckoutMode.updateCard] it just replaces the card.
class PremiumCheckoutScreen extends StatefulWidget {
  const PremiumCheckoutScreen({super.key, this.mode = CheckoutMode.trial});
  final CheckoutMode mode;

  bool get updateOnly => mode == CheckoutMode.updateCard;
  bool get subscribing => mode == CheckoutMode.subscribe;
  bool get trial => mode == CheckoutMode.trial;

  @override
  State<PremiumCheckoutScreen> createState() => _PremiumCheckoutScreenState();
}

class _PremiumCheckoutScreenState extends State<PremiumCheckoutScreen> {
  final _cardForm = GlobalKey<CardFormState>();
  bool _agreed = false;
  bool _working = false;

  Future<void> _submit() async {
    final card = _cardForm.currentState!.submit();
    if (card == null) return;
    if (!widget.updateOnly && !_agreed) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please confirm the renewal terms to continue.')),
      );
      return;
    }

    setState(() => _working = true);
    // The payment gateway call goes here once the backend supports it.
    await Future.delayed(const Duration(milliseconds: 600));
    if (!mounted) return;
    final premium = context.read<PremiumProvider>();

    if (widget.updateOnly) {
      premium.updateCard(card);
      Navigator.of(context).pop();
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Card updated to ${card.masked}.')));
      return;
    }

    if (widget.subscribing) {
      premium.subscribe(card);
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(builder: (_) => const MobileFrame(child: PremiumWelcomeScreen())),
      );
      return;
    }

    if (!premium.startTrial(card)) {
      setState(() => _working = false);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("You've already used your free trial on this account.")),
      );
      return;
    }
    Navigator.of(context).pushReplacement(
      MaterialPageRoute(builder: (_) => const MobileFrame(child: PremiumWelcomeScreen())),
    );
  }

  @override
  Widget build(BuildContext context) {
    final premium = context.watch<PremiumProvider>();
    final trialEnd = premium.trialEndIfStartedNow;
    final reminder = trialEnd.subtract(const Duration(days: PremiumProvider.reminderDaysBefore));

    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(24, 8, 24, 32),
          children: [
            PremiumTopBar(
              label: widget.updateOnly
                  ? 'CHANGE CARD'
                  : widget.subscribing
                      ? 'SUBSCRIBE'
                      : 'START YOUR TRIAL',
            ),
            const SizedBox(height: 10),
            Text.rich(
              TextSpan(
                style: AppTextStyles.heading(size: 28),
                children: !widget.trial
                    ? [
                        TextSpan(text: widget.updateOnly ? 'A new card for ' : 'Welcome back to '),
                        TextSpan(text: 'Premium.', style: AppTextStyles.heading(size: 28, style: FontStyle.italic)),
                      ]
                    : [
                        const TextSpan(text: '7 days free,\n'),
                        TextSpan(text: 'then decide.', style: AppTextStyles.heading(size: 28, style: FontStyle.italic)),
                      ],
              ),
            ),
            const SizedBox(height: 8),
            Text(
              widget.updateOnly
                  ? 'Future renewals will be charged to this card.'
                  : widget.subscribing
                      ? 'Your free trial has been used. Rs 1,500 is charged today, then every month until you cancel.'
                      : "You won't be charged today. Cancel any time before ${DateLabels.long(trialEnd)} and you pay nothing.",
              style: AppTextStyles.body(),
            ),
            if (widget.trial) ...[
              const SizedBox(height: 20),
              _Summary(trialEnd: trialEnd),
              const SizedBox(height: 18),
              _Timeline(reminder: reminder, trialEnd: trialEnd),
            ],
            const SizedBox(height: 24),
            Text('PAYMENT METHOD', style: AppTextStyles.label()),
            const SizedBox(height: 12),
            CardForm(key: _cardForm),
            const SizedBox(height: 16),
            const _SecureNote(),
            if (!widget.updateOnly) ...[
              const SizedBox(height: 16),
              GestureDetector(
                onTap: () => setState(() => _agreed = !_agreed),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    SizedBox(
                      width: 24,
                      height: 24,
                      child: Checkbox(
                        key: const Key('renewal-consent'),
                        value: _agreed,
                        activeColor: AppColors.primaryDark,
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
                        onChanged: (v) => setState(() => _agreed = v ?? false),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        widget.subscribing
                            ? 'I agree that Rs 1,500 will be charged to this card today and every month until I cancel. I can cancel any time in Manage subscription.'
                            : 'I agree that after my free trial ends on ${DateLabels.long(trialEnd)}, Rs 1,500 will be charged to this card every month until I cancel. I can cancel any time in Manage subscription.',
                        style: AppTextStyles.body(size: 13, color: AppColors.textDark),
                      ),
                    ),
                  ],
                ),
              ),
            ],
            const SizedBox(height: 22),
            PrimaryButton(
              label: widget.updateOnly
                  ? 'Save card'
                  : widget.subscribing
                      ? 'Pay Rs 1,500 and subscribe'
                      : 'Start free trial',
              icon: widget.updateOnly ? Icons.check : Icons.lock_outline,
              loading: _working,
              onPressed: _submit,
            ),
            if (widget.trial) ...[
              const SizedBox(height: 10),
              Text(
                'Rs 0 today · Rs 1,500 / month from ${DateLabels.long(trialEnd)}',
                textAlign: TextAlign.center,
                style: AppTextStyles.body(size: 12),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _Summary extends StatelessWidget {
  const _Summary({required this.trialEnd});
  final DateTime trialEnd;

  @override
  Widget build(BuildContext context) {
    Widget row(String label, String value, {bool bold = false}) => Padding(
          padding: const EdgeInsets.symmetric(vertical: 6),
          child: Row(
            children: [
              Expanded(child: Text(label, style: AppTextStyles.body(size: 14, color: bold ? AppColors.textDark : null))),
              Text(value, style: TextStyle(fontSize: 14, fontWeight: bold ? FontWeight.w800 : FontWeight.w600, color: AppColors.textDark)),
            ],
          ),
        );

    return Container(
      padding: const EdgeInsets.fromLTRB(18, 12, 18, 12),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(20)),
      child: Column(
        children: [
          row('MindCare Premium · monthly', 'Rs 1,500'),
          row('Free trial · ${PremiumProvider.trialDays} days', '− Rs 1,500'),
          const Divider(color: AppColors.border),
          row('Due today', 'Rs 0', bold: true),
          row('From ${DateLabels.long(trialEnd)}', 'Rs 1,500 / month'),
        ],
      ),
    );
  }
}

class _Timeline extends StatelessWidget {
  const _Timeline({required this.reminder, required this.trialEnd});
  final DateTime reminder;
  final DateTime trialEnd;

  @override
  Widget build(BuildContext context) {
    final steps = [
      (Icons.lock_open_outlined, 'Today', 'Full access to Journal and Outings.', AppColors.progressActive),
      (Icons.notifications_none, DateLabels.long(reminder), "We'll remind you before the trial ends.", AppColors.amberSegment),
      (Icons.credit_card, DateLabels.long(trialEnd), 'Rs 1,500 is charged, then monthly. Cancel before to pay nothing.', AppColors.primaryDark),
    ];
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(color: AppColors.cardBackground, borderRadius: BorderRadius.circular(20)),
      child: Column(
        children: [
          for (var i = 0; i < steps.length; i++)
            IntrinsicHeight(
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Column(
                    children: [
                      Container(
                        width: 32,
                        height: 32,
                        decoration: BoxDecoration(color: steps[i].$4, shape: BoxShape.circle),
                        child: Icon(steps[i].$1, size: 16, color: Colors.white),
                      ),
                      if (i < steps.length - 1) Expanded(child: Container(width: 2, color: AppColors.border)),
                    ],
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Padding(
                      padding: EdgeInsets.only(bottom: i < steps.length - 1 ? 16 : 0, top: 4),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(steps[i].$2, style: const TextStyle(fontWeight: FontWeight.w700, color: AppColors.textDark)),
                          const SizedBox(height: 2),
                          Text(steps[i].$3, style: AppTextStyles.body(size: 13)),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }
}

class _SecureNote extends StatelessWidget {
  const _SecureNote();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(color: AppColors.infoBoxBackground, borderRadius: BorderRadius.circular(16)),
      child: const Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(Icons.verified_user_outlined, size: 17, color: AppColors.infoBoxText),
          SizedBox(width: 10),
          Expanded(
            child: Text(
              'Your card is handled by our secure payment partner. MindCare only keeps the card type and last four digits, never the full number or CVC.',
              style: TextStyle(fontSize: 12, color: AppColors.infoBoxText, height: 1.4),
            ),
          ),
        ],
      ),
    );
  }
}

/// Shown once the trial has started.
class PremiumWelcomeScreen extends StatelessWidget {
  const PremiumWelcomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final premium = context.watch<PremiumProvider>();
    final end = premium.trialEndsAt;

    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(24, 8, 24, 32),
          children: [
            Row(
              children: [
                IconButton(
                  onPressed: () => Navigator.of(context).maybePop(),
                  icon: const Icon(Icons.close, color: AppColors.textDark),
                ),
              ],
            ),
            const SizedBox(height: 30),
            Center(
              child: Container(
                width: 92,
                height: 92,
                decoration: const BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: LinearGradient(colors: [AppColors.breathGradientStart, AppColors.primaryDark]),
                ),
                child: const Icon(Icons.check_rounded, size: 46, color: Colors.white),
              ),
            ),
            const SizedBox(height: 22),
            Center(child: PremiumBadge(label: premium.isOnTrial ? 'FREE TRIAL ACTIVE' : 'PREMIUM ACTIVE')),
            const SizedBox(height: 14),
            Text("You're in.", textAlign: TextAlign.center, style: AppTextStyles.heading(size: 32)),
            const SizedBox(height: 10),
            Text(
              premium.isOnTrial && end != null
                  ? 'Enjoy everything in Premium until ${DateLabels.long(end)}. After that, Rs 1,500 a month goes on ${premium.card?.masked ?? 'your card'} unless you cancel.'
                  : premium.nextChargeAt != null
                      ? 'Thank you. Your next Rs 1,500 charge is on ${DateLabels.long(premium.nextChargeAt!)}.'
                      : 'Premium is ready for you.',
              textAlign: TextAlign.center,
              style: AppTextStyles.body(),
            ),
            const SizedBox(height: 30),
            PrimaryButton(
              label: 'Open your journal',
              onPressed: () => Navigator.of(context).pushReplacement(
                MaterialPageRoute(builder: (_) => const MobileFrame(child: JournalScreen())),
              ),
            ),
            const SizedBox(height: 12),
            SizedBox(
              height: 54,
              child: OutlinedButton(
                onPressed: () => Navigator.of(context).pushReplacement(
                  MaterialPageRoute(builder: (_) => const MobileFrame(child: OutingsScreen())),
                ),
                style: OutlinedButton.styleFrom(
                  side: const BorderSide(color: AppColors.primaryDark),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
                ),
                child: const Text('Find an outing', style: TextStyle(color: AppColors.primaryDark, fontWeight: FontWeight.w700, fontSize: 15)),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
