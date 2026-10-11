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
import 'premium_checkout_screen.dart';

class ManageSubscriptionScreen extends StatelessWidget {
  const ManageSubscriptionScreen({super.key});

  Future<void> _confirmCancel(BuildContext context, PremiumProvider premium) async {
    final until = premium.status == PremiumStatus.trial ? premium.trialEndsAt : premium.nextChargeAt;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        backgroundColor: AppColors.background,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: const Text('Turn off auto-renew?', style: TextStyle(fontWeight: FontWeight.w700, color: AppColors.textDark)),
        content: Text(
          until == null
              ? "You won't be charged again."
              : "You'll keep Premium until ${DateLabels.long(until)}, and you won't be charged after that.",
          style: AppTextStyles.body(size: 14),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.of(dialogContext).pop(false), child: const Text('Keep Premium', style: TextStyle(color: AppColors.textMuted))),
          TextButton(onPressed: () => Navigator.of(dialogContext).pop(true), child: const Text('Turn off', style: TextStyle(color: AppColors.sos, fontWeight: FontWeight.w700))),
        ],
      ),
    );
    if (confirmed == true && context.mounted) {
      context.read<PremiumProvider>().setAutoRenew(false);
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Auto-renew is off. You won't be charged.")));
    }
  }

  @override
  Widget build(BuildContext context) {
    final premium = context.watch<PremiumProvider>();
    final status = premium.status;
    final card = premium.card;

    final (String title, String subtitle) = switch (status) {
      PremiumStatus.trial => ('Free trial', '${premium.trialDaysLeft} ${premium.trialDaysLeft == 1 ? 'day' : 'days'} left · first charge ${DateLabels.long(premium.trialEndsAt!)}'),
      PremiumStatus.trialCancelled => ('Free trial · ending', 'Premium ends ${DateLabels.long(premium.accessEndsAt!)}. No charge.'),
      PremiumStatus.active => ('Premium · monthly', 'Renews ${DateLabels.long(premium.nextChargeAt!)}'),
      PremiumStatus.cancelled => ('Premium · ending', 'Premium ends ${DateLabels.long(premium.accessEndsAt!)}. No further charges.'),
      PremiumStatus.none => ('No active plan', 'Start a free trial to unlock Journal and Outings.'),
    };
    final renewing = status == PremiumStatus.trial || status == PremiumStatus.active;
    final canResume = status == PremiumStatus.trialCancelled || status == PremiumStatus.cancelled;

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
                  _Row(label: 'Auto-renew', value: premium.autoRenew ? 'On' : 'Off', showDivider: card != null),
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
            if (renewing)
              GestureDetector(
                onTap: () => _confirmCancel(context, premium),
                child: Container(
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(20)),
                  child: const Center(
                    child: Text('Turn off auto-renew', style: TextStyle(color: AppColors.sos, fontWeight: FontWeight.w700, fontSize: 14)),
                  ),
                ),
              ),
            if (canResume)
              PrimaryButton(
                label: 'Turn auto-renew back on',
                icon: Icons.refresh,
                onPressed: () {
                  context.read<PremiumProvider>().setAutoRenew(true);
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(content: Text('Auto-renew is on. Next charge ${DateLabels.long(context.read<PremiumProvider>().nextChargeAt!)}.')),
                  );
                },
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
