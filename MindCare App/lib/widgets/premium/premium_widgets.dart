import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_text_styles.dart';
import '../../main.dart';
import '../../providers/premium_provider.dart';
import '../../screens/premium/premium_screen.dart';
import '../common/primary_button.dart';

/// Back button + small centred caption, as used across the app's sub-screens.
class PremiumTopBar extends StatelessWidget {
  const PremiumTopBar({super.key, required this.label, this.trailing});
  final String label;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        IconButton(
          onPressed: () => Navigator.of(context).maybePop(),
          icon: const Icon(Icons.chevron_left, color: AppColors.textDark),
        ),
        Expanded(
          child: Text(
            label,
            textAlign: TextAlign.center,
            style: const TextStyle(letterSpacing: 1, color: AppColors.textLabel, fontWeight: FontWeight.w600, fontSize: 12),
          ),
        ),
        SizedBox(width: 48, child: trailing),
      ],
    );
  }
}

/// Small gold "PREMIUM" pill.
class PremiumBadge extends StatelessWidget {
  const PremiumBadge({super.key, this.label = 'PREMIUM'});
  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
      decoration: BoxDecoration(color: AppColors.insightSunBg, borderRadius: BorderRadius.circular(20)),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.workspace_premium_outlined, size: 12, color: Color(0xFF8A6A2F)),
          const SizedBox(width: 4),
          Text(label, style: const TextStyle(fontSize: 10, letterSpacing: 0.8, fontWeight: FontWeight.w700, color: Color(0xFF8A6A2F))),
        ],
      ),
    );
  }
}

/// Shows [child] to Premium members; everyone else sees a calm locked
/// screen that explains the feature and links to the Premium page.
class PremiumGate extends StatelessWidget {
  const PremiumGate({
    super.key,
    required this.caption,
    required this.icon,
    required this.title,
    required this.description,
    required this.child,
  });

  final String caption;
  final IconData icon;
  final String title;
  final String description;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    if (context.watch<PremiumProvider>().isPremium) return child;

    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(24, 8, 24, 32),
          children: [
            PremiumTopBar(label: caption),
            const SizedBox(height: 40),
            Center(
              child: Container(
                width: 88,
                height: 88,
                decoration: const BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: [AppColors.insightSunBg, AppColors.insightLeafBg],
                  ),
                ),
                child: Icon(icon, size: 36, color: AppColors.primaryDark),
              ),
            ),
            const SizedBox(height: 22),
            const Center(child: PremiumBadge()),
            const SizedBox(height: 14),
            Text(title, textAlign: TextAlign.center, style: AppTextStyles.heading(size: 28)),
            const SizedBox(height: 10),
            Text(description, textAlign: TextAlign.center, style: AppTextStyles.body()),
            const SizedBox(height: 28),
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(color: AppColors.cardBackground, borderRadius: BorderRadius.circular(18)),
              child: Row(
                children: [
                  const Icon(Icons.lock_outline, size: 18, color: AppColors.textMuted),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      'Included with Premium · Rs 1,500 / month · ${PremiumProvider.trialDays}-day free trial',
                      style: AppTextStyles.body(size: 13),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),
            PrimaryButton(
              label: 'See Premium',
              onPressed: () => Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => const MobileFrame(child: PremiumScreen())),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
