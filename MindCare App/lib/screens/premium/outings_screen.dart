import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_text_styles.dart';
import '../../core/utils/date_labels.dart';
import '../../main.dart';
import '../../models/premium_data.dart';
import '../../providers/outings_provider.dart';
import '../../widgets/common/sos_button.dart';
import '../../widgets/premium/premium_widgets.dart';
import 'outing_detail_screen.dart';

class OutingsScreen extends StatelessWidget {
  const OutingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return const PremiumGate(
      caption: 'OUTINGS',
      icon: Icons.directions_walk,
      title: 'Outing activities',
      description: 'Go for a walk, a coffee, a meal or a hike with a kind volunteer companion. Always in a public place, always your pace.',
      child: _OutingsBody(),
    );
  }
}

class _OutingsBody extends StatelessWidget {
  const _OutingsBody();

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<OutingsProvider>();
    final available = provider.available;
    final bookings = provider.bookings.where((b) => b.status != OutingStatus.cancelled).toList();

    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: Stack(
          children: [
            ListView(
              padding: const EdgeInsets.fromLTRB(24, 8, 24, 110),
              children: [
                const PremiumTopBar(label: 'OUTINGS'),
                const SizedBox(height: 10),
                Text.rich(
                  TextSpan(
                    style: AppTextStyles.heading(size: 30),
                    children: [
                      const TextSpan(text: 'A little air,\n'),
                      TextSpan(text: 'good company.', style: AppTextStyles.heading(size: 30, style: FontStyle.italic)),
                    ],
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  'Volunteer companions offer short outings to ease loneliness. You cover your own and their costs, like a coffee or a meal.',
                  style: AppTextStyles.body(),
                ),
                const SizedBox(height: 20),
                const _SafetyCard(),
                const SizedBox(height: 22),
                Text('WHAT WOULD YOU LIKE TO DO?', style: AppTextStyles.label()),
                const SizedBox(height: 12),
                Row(
                  children: [
                    for (final type in OutingType.values) ...[
                      Expanded(
                        child: _TypeTile(
                          type: type,
                          selected: provider.filter == type,
                          onTap: () => context.read<OutingsProvider>().setFilter(type),
                        ),
                      ),
                      if (type != OutingType.values.last) const SizedBox(width: 10),
                    ],
                  ],
                ),
                if (bookings.isNotEmpty) ...[
                  const SizedBox(height: 26),
                  Text('YOUR OUTINGS', style: AppTextStyles.label()),
                  const SizedBox(height: 12),
                  for (final b in bookings) _OutingTile(outing: b.outing, status: b.status),
                ],
                const SizedBox(height: 26),
                Text(
                  provider.filter == null ? 'OFFERED NEAR YOU' : '${provider.filter!.label.toUpperCase()} OUTINGS NEAR YOU',
                  style: AppTextStyles.label(),
                ),
                const SizedBox(height: 12),
                if (available.isEmpty)
                  _EmptyOutings(filtered: provider.filter != null)
                else
                  for (final o in available) _OutingTile(outing: o),
              ],
            ),
            const Positioned(right: 16, bottom: 24, child: SosButton()),
          ],
        ),
      ),
    );
  }
}

class _SafetyCard extends StatelessWidget {
  const _SafetyCard();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(color: AppColors.insightLeafBg, borderRadius: BorderRadius.circular(20)),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 38,
            height: 38,
            decoration: BoxDecoration(color: AppColors.progressActive, borderRadius: BorderRadius.circular(12)),
            child: const Icon(Icons.verified_user_outlined, color: Colors.white, size: 18),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('Safety comes first', style: TextStyle(fontWeight: FontWeight.w700, color: AppColors.textDark)),
                const SizedBox(height: 4),
                Text(
                  'Companions are reviewed by MindCare. You always meet in public, and SOS stays one tap away.',
                  style: AppTextStyles.body(size: 13, color: AppColors.chipTextUnselected),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _TypeTile extends StatelessWidget {
  const _TypeTile({required this.type, required this.selected, required this.onTap});
  final OutingType type;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      selected: selected,
      label: type.label,
      child: GestureDetector(
        onTap: onTap,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 160),
          padding: const EdgeInsets.symmetric(vertical: 14),
          decoration: BoxDecoration(
            color: selected ? Color.alphaBlend(type.color.withValues(alpha: 0.10), Colors.white) : Colors.white,
            borderRadius: BorderRadius.circular(18),
            border: Border.all(color: selected ? type.color : AppColors.border, width: selected ? 1.6 : 1),
          ),
          child: Column(
            children: [
              Container(
                width: 38,
                height: 38,
                decoration: BoxDecoration(color: type.color.withValues(alpha: 0.15), shape: BoxShape.circle),
                child: Icon(type.icon, size: 19, color: type.color),
              ),
              const SizedBox(height: 8),
              Text(type.label, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: AppColors.textDark)),
            ],
          ),
        ),
      ),
    );
  }
}

class _OutingTile extends StatelessWidget {
  const _OutingTile({required this.outing, this.status});
  final Outing outing;
  final OutingStatus? status;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () => Navigator.of(context).push(
        MaterialPageRoute(builder: (_) => MobileFrame(child: OutingDetailScreen(outing: outing))),
      ),
      child: Container(
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(18)),
        child: Row(
          children: [
            Container(
              width: 46,
              height: 46,
              decoration: BoxDecoration(color: outing.type.color.withValues(alpha: 0.15), borderRadius: BorderRadius.circular(14)),
              child: Icon(outing.type.icon, color: outing.type.color, size: 22),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '${outing.type.label} with ${outing.companionName}',
                    style: const TextStyle(fontWeight: FontWeight.w700, color: AppColors.textDark),
                  ),
                  const SizedBox(height: 3),
                  Text(
                    '${DateLabels.day(outing.startsAt)} · ${DateLabels.time(outing.startsAt)} · ${outing.area}',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: AppTextStyles.body(size: 12),
                  ),
                ],
              ),
            ),
            if (status != null)
              _StatusPill(status: status!)
            else
              const Icon(Icons.chevron_right, size: 20, color: AppColors.textMuted),
          ],
        ),
      ),
    );
  }
}

class _StatusPill extends StatelessWidget {
  const _StatusPill({required this.status});
  final OutingStatus status;

  @override
  Widget build(BuildContext context) {
    final confirmed = status == OutingStatus.confirmed;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: confirmed ? AppColors.chipUnselected : AppColors.background,
        borderRadius: BorderRadius.circular(20),
      ),
      child: Text(
        status.label,
        style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: confirmed ? AppColors.progressActive : AppColors.textMuted),
      ),
    );
  }
}

class _EmptyOutings extends StatelessWidget {
  const _EmptyOutings({required this.filtered});
  final bool filtered;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 30, horizontal: 24),
      decoration: BoxDecoration(color: AppColors.cardBackground, borderRadius: BorderRadius.circular(22)),
      child: Column(
        children: [
          Container(
            width: 56,
            height: 56,
            decoration: const BoxDecoration(color: AppColors.insightSunBg, shape: BoxShape.circle),
            child: const Icon(Icons.wb_sunny_outlined, size: 26, color: Color(0xFF8A6A2F)),
          ),
          const SizedBox(height: 14),
          Text(filtered ? 'Nothing like this yet' : 'No outings offered yet', style: AppTextStyles.heading(size: 20)),
          const SizedBox(height: 6),
          Text(
            filtered
                ? 'Try another activity, or check back soon.'
                : 'When companions near you offer an outing, it will appear here.',
            textAlign: TextAlign.center,
            style: AppTextStyles.body(size: 13),
          ),
        ],
      ),
    );
  }
}
