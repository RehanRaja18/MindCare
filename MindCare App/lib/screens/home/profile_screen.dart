import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_text_styles.dart';
import '../../core/utils/app_feedback.dart';
import '../../main.dart';
import '../../core/utils/date_labels.dart';
import '../../models/account_data.dart';
import '../../models/premium_data.dart';
import '../../providers/account_provider.dart';
import '../../providers/journal_provider.dart';
import '../../providers/premium_provider.dart';
import '../../providers/user_session_provider.dart';
import '../../widgets/common/sos_button.dart';
import '../../widgets/profile/profile_header.dart';
import '../../widgets/profile/profile_list_section.dart';
import '../care/aida_personality_screen.dart';
import '../care/past_sessions_screen.dart';
import '../care/therapist_detail_screen.dart';
import '../premium/journal_screen.dart';
import '../premium/manage_subscription_screen.dart';
import '../premium/outings_screen.dart';
import '../premium/premium_screen.dart';
import '../settings/appearance_screen.dart';
import '../settings/notification_settings_screen.dart';
import '../settings/privacy_data_screen.dart';
import '../settings/wearables_screen.dart';
import 'rewards_screen.dart';
import 'wallet_screen.dart';

class ProfileScreen extends StatelessWidget {
  const ProfileScreen({super.key});

  Future<void> _confirmSignOut(BuildContext context) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        backgroundColor: AppColors.background,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: const Text('Log out?', style: TextStyle(fontWeight: FontWeight.w700, color: AppColors.textDark)),
        content: Text("You'll need to sign in again to get back in.", style: AppTextStyles.body(size: 14)),
        actions: [
          TextButton(onPressed: () => Navigator.of(dialogContext).pop(false), child: const Text('Cancel', style: TextStyle(color: AppColors.textMuted))),
          TextButton(onPressed: () => Navigator.of(dialogContext).pop(true), child: const Text('Log out', style: TextStyle(color: AppColors.sos, fontWeight: FontWeight.w700))),
        ],
      ),
    );

    if (confirmed == true && context.mounted) {
      await context.read<UserSessionProvider>().signOut();
      if (!context.mounted) return;
      Navigator.of(context).pushNamedAndRemoveUntil('/welcome', (route) => false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<AccountProvider>();
    final session = context.watch<UserSessionProvider>();
    final displayName = session.fullName ?? provider.userName;

    final careItems = [
      ProfileListItem(icon: Icons.terrain, title: 'Your therapist', subtitle: '${provider.therapistName} · ${provider.therapistSince}'),
      ProfileListItem(icon: Icons.auto_awesome, title: 'Aida personality', trailing: provider.aidaPersonality),
      ProfileListItem(icon: Icons.bookmark_border, title: 'Past sessions & notes', trailing: '${provider.pastSessionsCount}', showDivider: false),
    ];

    final premium = context.watch<PremiumProvider>();
    final journalCount = context.watch<JournalProvider>().entries.length;
    final premiumItems = [
      ProfileListItem(
        icon: Icons.workspace_premium_outlined,
        title: 'MindCare Premium',
        subtitle: switch (premium.status) {
          PremiumStatus.trial => 'Free trial · ${premium.trialDaysLeft} ${premium.trialDaysLeft == 1 ? 'day' : 'days'} left',
          PremiumStatus.active => 'Renews ${DateLabels.day(premium.nextChargeAt!)}',
          PremiumStatus.trialCancelled || PremiumStatus.cancelled => 'Ends ${DateLabels.day(premium.accessEndsAt!)}',
          PremiumStatus.none => premium.trialUsed
              ? 'Rs 1,500 / month'
              : '${PremiumProvider.trialDays}-day free trial, then Rs 1,500 / month',
        },
      ),
      ProfileListItem(
        icon: Icons.menu_book_outlined,
        title: 'Patient Journal',
        trailing: premium.isPremium ? '$journalCount' : null,
        subtitle: premium.isPremium ? null : 'Premium',
      ),
      ProfileListItem(
        icon: Icons.directions_walk,
        title: 'Outing activities',
        subtitle: premium.isPremium ? 'Walks, coffee, meals, hikes' : 'Premium',
        showDivider: premium.trialUsed,
      ),
      if (premium.trialUsed)
        ProfileListItem(
          icon: Icons.receipt_long_outlined,
          title: 'Manage subscription',
          subtitle: premium.card == null ? 'Billing and cancellation' : '${premium.card!.masked} · cancel any time',
          showDivider: false,
        ),
    ];
    final premiumScreens = <Widget>[
      const PremiumScreen(),
      const JournalScreen(),
      const OutingsScreen(),
      if (premium.trialUsed) const ManageSubscriptionScreen(),
    ];

    final accountItems = [
      ProfileListItem(icon: Icons.watch_outlined, title: 'Wearables', subtitle: provider.wearableConnected ? 'MindBand · connected' : 'Not connected'),
      const ProfileListItem(icon: Icons.shield_outlined, title: 'Privacy & data', subtitle: 'What your therapist sees'),
      ProfileListItem(icon: Icons.notifications_none, title: 'Notifications', trailing: provider.notificationsOn ? 'On' : 'Off'),
      ProfileListItem(icon: Icons.credit_card, title: 'Billing & wallet', trailing: 'Rs ${provider.walletBalance}'),
    ];

    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        bottom: false,
        child: Stack(
          children: [
            ListView(
              padding: const EdgeInsets.fromLTRB(24, 16, 24, 110),
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text('YOU', style: TextStyle(letterSpacing: 1, color: AppColors.textLabel, fontWeight: FontWeight.w600, fontSize: 12)),
                    IconButton(
                      onPressed: () => Navigator.of(context).push(
                        MaterialPageRoute(builder: (_) => MobileFrame(child: AppearanceScreen())),
                      ),
                      icon: const Icon(Icons.wb_sunny_outlined, color: AppColors.textDark, size: 20),
                      padding: EdgeInsets.zero,
                      constraints: const BoxConstraints(),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                GestureDetector(
                  onTap: () => Navigator.of(context).push(
                    MaterialPageRoute(builder: (_) => const MobileFrame(child: RewardsScreen())),
                  ),
                  child: ProfileHeader(
                    name: displayName,
                    initials: session.fullName != null ? session.initials : null,
                    joinedInfo: provider.joinedInfo,
                    levelBadge: 'Level ${provider.levelNumber} · Centered',
                    streak: provider.checkinStreak,
                    sessions: provider.statsSessions,
                    exercises: provider.statsExercises,
                  ),
                ),
                const SizedBox(height: 22),
                const Text('YOUR CARE', style: TextStyle(letterSpacing: 1, color: AppColors.textLabel, fontWeight: FontWeight.w600, fontSize: 12)),
                const SizedBox(height: 12),
                ProfileListSection(
                  items: careItems,
                  onItemTap: (index) {
                    switch (index) {
                      case 0:
                        Navigator.of(context).push(
                          MaterialPageRoute(builder: (_) => MobileFrame(child: TherapistDetailScreen())),
                        );
                        break;
                      case 1:
                        Navigator.of(context).push(
                          MaterialPageRoute(builder: (_) => MobileFrame(child: AidaPersonalityScreen())),
                        );
                        break;
                      case 2:
                        Navigator.of(context).push(
                          MaterialPageRoute(builder: (_) => MobileFrame(child: PastSessionsScreen())),
                        );
                        break;
                    }
                  },
                ),
                const SizedBox(height: 22),
                const Row(
                  children: [
                    Text('PREMIUM', style: TextStyle(letterSpacing: 1, color: AppColors.textLabel, fontWeight: FontWeight.w600, fontSize: 12)),
                    SizedBox(width: 8),
                    Icon(Icons.workspace_premium_outlined, size: 14, color: AppColors.amberSegment),
                  ],
                ),
                const SizedBox(height: 12),
                ProfileListSection(
                  items: premiumItems,
                  onItemTap: (index) {
                    Navigator.of(context).push(
                      MaterialPageRoute(builder: (_) => MobileFrame(child: premiumScreens[index])),
                    );
                  },
                ),
                const SizedBox(height: 22),
                const Text('ACCOUNT', style: TextStyle(letterSpacing: 1, color: AppColors.textLabel, fontWeight: FontWeight.w600, fontSize: 12)),
                const SizedBox(height: 12),
                ProfileListSection(
                  items: accountItems,
                  onItemTap: (index) {
                    switch (index) {
                      case 0:
                        Navigator.of(context).push(
                          MaterialPageRoute(builder: (_) => MobileFrame(child: WearablesScreen())),
                        );
                        break;
                      case 1:
                        Navigator.of(context).push(
                          MaterialPageRoute(builder: (_) => MobileFrame(child: PrivacyDataScreen())),
                        );
                        break;
                      case 2:
                        Navigator.of(context).push(
                          MaterialPageRoute(builder: (_) => MobileFrame(child: NotificationSettingsScreen())),
                        );
                        break;
                      case 3:
                        Navigator.of(context).push(
                          MaterialPageRoute(builder: (_) => const MobileFrame(child: WalletScreen())),
                        );
                        break;
                    }
                  },
                ),
                const SizedBox(height: 22),
                GestureDetector(
                  onTap: () => _confirmSignOut(context),
                  child: Container(
                    padding: const EdgeInsets.symmetric(vertical: 16),
                    decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(20)),
                    child: const Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.logout, size: 18, color: AppColors.sos),
                        SizedBox(width: 10),
                        Text('Log out', style: TextStyle(color: AppColors.sos, fontWeight: FontWeight.w700, fontSize: 14)),
                      ],
                    ),
                  ),
                ),
              ],
            ),
            const Positioned(right: 16, bottom: 24, child: SosButton()),
          ],
        ),
      ),
    );
  }
}