import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/theme/app_colors.dart';
import '../../core/theme/app_text_styles.dart';
import '../../main.dart';
import '../../providers/premium_provider.dart';
import '../../widgets/common/primary_button.dart';
import '../../widgets/common/sos_button.dart';
import '../../widgets/premium/premium_widgets.dart';
import 'journal_screen.dart';
import 'outings_screen.dart';

/// MindCare Premium — the same plan as the pricing page on the website.
class PremiumScreen extends StatelessWidget {
  const PremiumScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final premium = context.watch<PremiumProvider>();

    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: Stack(
          children: [
            ListView(
              padding: const EdgeInsets.fromLTRB(24, 8, 24, 150),
              children: [
                const PremiumTopBar(label: 'MINDCARE PREMIUM'),
                const SizedBox(height: 10),
                Text.rich(
                  TextSpan(
                    style: AppTextStyles.heading(size: 30),
                    children: [
                      const TextSpan(text: 'A little more\n'),
                      TextSpan(
                        text: 'room to heal.',
                        style: AppTextStyles.heading(size: 30, style: FontStyle.italic),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 10),
                Text(
                  'Write things down privately, and get out of the house with a kind companion. Your care plan and SOS stay free, always.',
                  style: AppTextStyles.body(),
                ),
                const SizedBox(height: 22),
                _PlanCard(premium: premium),
                const SizedBox(height: 24),
                Text("WHAT'S INCLUDED", style: AppTextStyles.label()),
                const SizedBox(height: 12),
                Container(
                  decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(20)),
                  child: Column(
                    children: [
                      _FeatureRow(
                        icon: Icons.menu_book_outlined,
                        title: 'Patient Journal',
                        subtitle: 'Private entries with your mood. Share only the ones you choose with your therapist.',
                        onTap: premium.isPremium
                            ? () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const MobileFrame(child: JournalScreen())))
                            : null,
                      ),
                      _FeatureRow(
                        icon: Icons.directions_walk,
                        title: 'Outing activities',
                        subtitle: 'Walks, coffee, meals and hikes with a volunteer companion, in public places.',
                        onTap: premium.isPremium
                            ? () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const MobileFrame(child: OutingsScreen())))
                            : null,
                      ),
                      const _FeatureRow(
                        icon: Icons.extension_outlined,
                        title: 'Games',
                        subtitle: 'Gentle games for focus and calm.',
                        comingSoon: true,
                        showDivider: false,
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 18),
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Icon(Icons.favorite_border, size: 16, color: AppColors.textMuted),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        "Can't afford it? NGO scholarships can cover up to 80%. Ask your therapist or our support team.",
                        style: AppTextStyles.body(size: 13),
                      ),
                    ),
                  ],
                ),
              ],
            ),
            Positioned(
              left: 24,
              right: 24,
              bottom: 16,
              child: Column(
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: PrimaryButton(
                          label: premium.isPremium
                              ? 'Open your journal'
                              : premium.trialUsed
                              ? 'Trial ended'
                              : 'Start free trial',
                          onPressed: premium.isPremium
                              ? () =>
                                    Navigator.of(context).push(MaterialPageRoute(builder: (_) => const MobileFrame(child: JournalScreen())))
                              : premium.trialUsed
                              ? null
                              : () {
                                  context.read<PremiumProvider>().startTrial();
                                  ScaffoldMessenger.of(context)
                                      .showSnackBar(const SnackBar(content: Text('Your free trial has started. Enjoy Premium.')));
                                },
                        ),
                      ),
                      const SizedBox(width: 12),
                      const SosButton(),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Text(
                    premium.isOnTrial
                        ? 'Trial ends in ${premium.trialDaysLeft} ${premium.trialDaysLeft == 1 ? 'day' : 'days'}. Then Rs 1,500 / month.'
                        : 'Then Rs 1,500 / month. Cancel any time, no fee.',
                    style: AppTextStyles.body(size: 11),
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

class _PlanCard extends StatelessWidget {
  const _PlanCard({required this.premium});
  final PremiumProvider premium;

  @override
  Widget build(BuildContext context) {
    return Container(
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
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                'PREMIUM',
                style: TextStyle(color: Colors.white70, letterSpacing: 1.2, fontSize: 12, fontWeight: FontWeight.w600),
              ),
              if (premium.isPremium)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.18), borderRadius: BorderRadius.circular(20)),
                  child: Text(
                    premium.isOnTrial ? 'On free trial' : 'Active',
                    style: const TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.w700),
                  ),
                ),
            ],
          ),
          const SizedBox(height: 14),
          Row(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text('Rs 1,500', style: AppTextStyles.heading(size: 34).copyWith(color: Colors.white)),
              const SizedBox(width: 6),
              const Padding(
                padding: EdgeInsets.only(bottom: 6),
                child: Text('/ month', style: TextStyle(color: Colors.white70, fontSize: 13)),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              const Icon(Icons.eco_outlined, size: 15, color: Color(0xFFF0DEB9)),
              const SizedBox(width: 6),
              Flexible(
                child: Text(
                  '${PremiumProvider.trialDays}-day free trial · cancel any time',
                  style: const TextStyle(color: Color(0xFFF0DEB9), fontSize: 13, fontWeight: FontWeight.w600),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _FeatureRow extends StatelessWidget {
  const _FeatureRow({
    required this.icon,
    required this.title,
    required this.subtitle,
    this.onTap,
    this.comingSoon = false,
    this.showDivider = true,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback? onTap;
  final bool comingSoon;
  final bool showDivider;

  @override
  Widget build(BuildContext context) {
    final row = Padding(
      padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 18),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              color: comingSoon ? AppColors.background : AppColors.chipUnselected,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(icon, size: 19, color: comingSoon ? AppColors.textLabel : AppColors.primaryDark),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Flexible(
                      child: Text(
                        title,
                        style: TextStyle(fontWeight: FontWeight.w700, color: comingSoon ? AppColors.textMuted : AppColors.textDark),
                      ),
                    ),
                    if (comingSoon) ...[
                      const SizedBox(width: 8),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                        decoration: BoxDecoration(color: AppColors.background, borderRadius: BorderRadius.circular(10)),
                        child: const Text(
                          'COMING SOON',
                          style: TextStyle(fontSize: 9, letterSpacing: 0.6, fontWeight: FontWeight.w700, color: AppColors.textLabel),
                        ),
                      ),
                    ],
                  ],
                ),
                const SizedBox(height: 3),
                Text(subtitle, style: const TextStyle(fontSize: 12, color: AppColors.textMuted, height: 1.35)),
              ],
            ),
          ),
          if (onTap != null) ...[const SizedBox(width: 8), const Icon(Icons.chevron_right, size: 20, color: AppColors.textMuted)],
        ],
      ),
    );

    return Column(
      children: [
        onTap != null ? InkWell(onTap: onTap, child: row) : row,
        if (showDivider) const Divider(height: 1, color: AppColors.border, indent: 18, endIndent: 18),
      ],
    );
  }
}
