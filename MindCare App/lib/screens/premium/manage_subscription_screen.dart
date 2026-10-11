import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_text_styles.dart';
import '../../core/utils/date_labels.dart';
import '../../main.dart';
import '../../models/premium_data.dart';
import '../../providers/premium_provider.dart';
import '../../widgets/common/primary_button.dart';
import '../../widgets/premium/premium_widgets.dart';
import 'cancel_subscription_screen.dart';
import 'premium_checkout_screen.dart';

class ManageSubscriptionScreen extends StatelessWidget {
  const ManageSubscriptionScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final premium = context.watch<PremiumProvider>();
    final status = premium.status;
    final card = premium.card;

    final (String title, String subtitle) = switch (status) {
      PremiumStatus.trial => ('Free trial', '${premium.trialDaysLeft} ${premium.trialDaysLeft == 1 ? 'day' : 'days'} left · first charge ${DateLabels.long(premium.trialEndsAt!)}'),
      PremiumStatus.trialCancelled => ('Cancelled', 'Premium stays on until ${DateLabels.long(premium.accessEndsAt!)}. You won\x27t be charged.'),
      PremiumStatus.active => ('Premium · monthly', 'Renews ${DateLabels.long(premium.nextChargeAt!)}'),
      PremiumStatus.cancelled => ('Cancelled', 'Premium stays on until ${DateLabels.long(premium.accessEndsAt!)}. No further charges.'),
      PremiumStatus.none => ('No active plan', 'Start a free trial to unlock Journal and Outings.'),
    };

    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(24, 8, 24, 32),
          children: [
            const PremiumTopBar(label: 'MANAGE SUBSCRIPTION'),
            const SizedBox(height: 10),
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: [AppColors.breathGradientStart, AppColors.primaryDark],
                ),
                borderRadius: BorderRadius.circular(24),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('MINDCARE PREMIUM', style: TextStyle(color: Colors.white70, letterSpacing: 1.2, fontSize: 12, fontWeight: FontWeight.w600)),
                  const SizedBox(height: 12),
                  Text(title, style: AppTextStyles.heading(size: 26).copyWith(color: Colors.white)),
                  const SizedBox(height: 6),
                  Text(subtitle, style: const TextStyle(color: Color(0xFFF0DEB9), fontSize: 13, fontWeight: FontWeight.w600)),
                ],
              ),
            ),
            const SizedBox(height: 22),
            Text('BILLING', style: AppTextStyles.label()),
            const SizedBox(height: 12),
            Container(
              decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(20)),
              child: Column(
                children: [
                  _Row(label: 'Plan', value: 'Rs 1,500 / month'),
                  _Row(
                    label: 'Next charge',
                    value: premium.nextChargeAt == null ? 'None' : 'Rs 1,500 on ${DateLabels.long(premium.nextChargeAt!)}',
                  ),
                  _Row(label: 'Auto-renew', value: premium.autoRenew ? 'On' : 'Off', showDivider: premium.accessEndsAt != null || card != null),
                  if (premium.accessEndsAt != null) _Row(label: 'Access until', value: DateLabels.long(premium.accessEndsAt!), showDivider: card != null),
                  if (card != null)
                    InkWell(
                      onTap: () => Navigator.of(context).push(
                        MaterialPageRoute(builder: (_) => const MobileFrame(child: PremiumCheckoutScreen(mode: CheckoutMode.updateCard))),
                      ),
                      child: Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                        child: Row(
                          children: [
                            Container(
                              width: 42,
                              height: 30,
                              alignment: Alignment.center,
                              decoration: BoxDecoration(color: AppColors.primaryDark, borderRadius: BorderRadius.circular(6)),
                              child: Text(
                                const {'Visa': 'VISA', 'Mastercard': 'MC', 'Amex': 'AMEX'}[card.brand] ?? 'CARD',
                                style: const TextStyle(color: Colors.white, fontSize: 9, fontWeight: FontWeight.w800, letterSpacing: 0.5),
                              ),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(card.masked, style: const TextStyle(fontWeight: FontWeight.w600, color: AppColors.textDark)),
                                  Text('Expires ${card.expiryLabel}', style: AppTextStyles.body(size: 12)),
                                ],
                              ),
                            ),
                            Text('Change', style: AppTextStyles.body(size: 13, weight: FontWeight.w700, color: AppColors.progressActive)),
                          ],
                        ),
                      ),
                    ),
                ],
              ),
            ),
            const SizedBox(height: 24),
            if (premium.canCancel)
              SizedBox(
                height: 54,
                child: OutlinedButton(
                  onPressed: () => Navigator.of(context).push(
                    MaterialPageRoute(builder: (_) => const MobileFrame(child: CancelSubscriptionScreen())),
                  ),
                  style: OutlinedButton.styleFrom(
                    backgroundColor: Colors.white,
                    side: const BorderSide(color: AppColors.border),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
                  ),
                  child: const Text('Cancel subscription', style: TextStyle(color: AppColors.sos, fontWeight: FontWeight.w700, fontSize: 15)),
                ),
              ),
            if (premium.canResume)
              PrimaryButton(
                label: 'Resume subscription',
                icon: Icons.refresh,
                onPressed: () {
                  final p = context.read<PremiumProvider>()..resume();
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(content: Text('Welcome back. Your next charge is ${DateLabels.long(p.nextChargeAt!)}.')),
                  );
                },
              ),
            if (premium.status == PremiumStatus.none)
              PrimaryButton(
                label: premium.trialUsed ? 'Subscribe · Rs 1,500 / month' : 'Start free trial',
                onPressed: () => Navigator.of(context).pushReplacement(
                  MaterialPageRoute(
                    builder: (_) => MobileFrame(
                      child: PremiumCheckoutScreen(mode: premium.trialUsed ? CheckoutMode.subscribe : CheckoutMode.trial),
                    ),
                  ),
                ),
              ),
            const SizedBox(height: 16),
            Text(
              'Charges show on your statement as MINDCARE PREMIUM. Cancelling stops future charges; you keep access until the end of the period you are in.',
              textAlign: TextAlign.center,
              style: AppTextStyles.body(size: 12),
            ),
          ],
        ),
      ),
    );
  }
}

class _Row extends StatelessWidget {
  const _Row({required this.label, required this.value, this.showDivider = true});
  final String label;
  final String value;
  final bool showDivider;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
          child: Row(
            children: [
              Text(label, style: AppTextStyles.body(size: 13)),
              const SizedBox(width: 12),
              Expanded(
                child: Text(value, textAlign: TextAlign.right, style: const TextStyle(fontWeight: FontWeight.w600, color: AppColors.textDark, fontSize: 13)),
              ),
            ],
          ),
        ),
        if (showDivider) const Divider(height: 1, color: AppColors.border, indent: 16, endIndent: 16),
      ],
    );
  }
}
