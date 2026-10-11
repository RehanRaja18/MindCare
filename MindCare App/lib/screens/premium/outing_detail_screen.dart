import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_text_styles.dart';
import '../../core/utils/date_labels.dart';
import '../../models/premium_data.dart';
import '../../providers/outings_provider.dart';
import '../../widgets/common/primary_button.dart';
import '../../widgets/common/sos_button.dart';
import '../../widgets/premium/premium_widgets.dart';

class OutingDetailScreen extends StatelessWidget {
  const OutingDetailScreen({super.key, required this.outing});
  final Outing outing;

  Future<void> _rate(BuildContext context) async {
    final result = await showModalBottomSheet<(int, String)>(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppColors.background,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
      builder: (_) => _RateSheet(companionName: outing.companionName),
    );
    if (result != null && context.mounted) {
      context.read<OutingsProvider>().rate(outing.id, result.$1, feedback: result.$2.trim().isEmpty ? null : result.$2.trim());
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Thank you. Your rating helps keep outings safe.')));
    }
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<OutingsProvider>();
    final booking = provider.bookingFor(outing.id);
    final status = booking?.status;

    final String buttonLabel;
    VoidCallback? onPressed;
    switch (status) {
      case null:
      case OutingStatus.cancelled:
        buttonLabel = 'Request to join';
        onPressed = status == OutingStatus.cancelled
            ? null
            : () {
                context.read<OutingsProvider>().requestOuting(outing);
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(content: Text('Request sent. ${outing.companionName} will confirm soon.')),
                );
              };
      case OutingStatus.requested:
        buttonLabel = 'Cancel request';
        onPressed = () => context.read<OutingsProvider>().cancelRequest(outing.id);
      case OutingStatus.confirmed:
        buttonLabel = 'Confirmed · see you there';
        onPressed = null;
      case OutingStatus.completed:
        buttonLabel = booking!.rating == null ? 'Rate this outing' : 'Rated ${booking.rating}/5 · thank you';
        onPressed = booking.rating == null ? () => _rate(context) : null;
    }

    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: Stack(
          children: [
            ListView(
              padding: const EdgeInsets.fromLTRB(24, 8, 24, 130),
              children: [
                const PremiumTopBar(label: 'OUTING'),
                const SizedBox(height: 10),
                Row(
                  children: [
                    Container(
                      width: 60,
                      height: 60,
                      decoration: BoxDecoration(color: outing.type.color.withValues(alpha: 0.15), borderRadius: BorderRadius.circular(18)),
                      child: Icon(outing.type.icon, color: outing.type.color, size: 28),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('${outing.type.label} with ${outing.companionName}', style: AppTextStyles.heading(size: 24)),
                          const SizedBox(height: 4),
                          Row(
                            children: [
                              const Icon(Icons.verified_outlined, size: 14, color: AppColors.progressActive),
                              const SizedBox(width: 4),
                              Text('Reviewed companion', style: AppTextStyles.body(size: 12, color: AppColors.progressActive)),
                              if (outing.companionRating != null) ...[
                                Text('  ·  ', style: AppTextStyles.body(size: 12)),
                                const Icon(Icons.star, size: 13, color: AppColors.amberSegment),
                                const SizedBox(width: 2),
                                Text(outing.companionRating!.toStringAsFixed(1), style: AppTextStyles.body(size: 12, color: AppColors.textDark)),
                              ],
                            ],
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
                if (status != null) ...[
                  const SizedBox(height: 14),
                  Align(alignment: Alignment.centerLeft, child: PremiumBadge(label: status.label.toUpperCase())),
                ],
                const SizedBox(height: 20),
                Container(
                  decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(20)),
                  child: Column(
                    children: [
                      _InfoRow(icon: Icons.calendar_today_outlined, label: 'When', value: '${DateLabels.long(outing.startsAt)} · ${DateLabels.time(outing.startsAt)}'),
                      _InfoRow(icon: Icons.schedule, label: 'How long', value: DateLabels.duration(outing.durationMinutes)),
                      _InfoRow(icon: Icons.place_outlined, label: 'Where', value: outing.area, showDivider: false),
                    ],
                  ),
                ),
                if (outing.note != null) ...[
                  const SizedBox(height: 18),
                  Text('FROM ${outing.companionName.toUpperCase()}', style: AppTextStyles.label()),
                  const SizedBox(height: 10),
                  Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(color: AppColors.cardBackground, borderRadius: BorderRadius.circular(18)),
                    child: Text(outing.note!, style: AppTextStyles.body(size: 14, color: AppColors.textDark)),
                  ),
                ],
                const SizedBox(height: 18),
                Text('GOOD TO KNOW', style: AppTextStyles.label()),
                const SizedBox(height: 10),
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(color: AppColors.cardBackground, borderRadius: BorderRadius.circular(18)),
                  child: const Column(
                    children: [
                      _Tip(icon: Icons.payments_outlined, text: 'You cover costs for you and your companion, such as coffee or a meal.'),
                      _Tip(icon: Icons.storefront_outlined, text: 'Meet only at the public place listed above.'),
                      _Tip(icon: Icons.people_outline, text: 'Tell someone you trust where you are going.'),
                      _Tip(icon: Icons.sos_outlined, text: 'Feel unsafe at any point? Tap SOS and leave.', last: true),
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
                  Expanded(
                    child: PrimaryButton(
                      label: buttonLabel,
                      icon: status == null ? Icons.arrow_forward : null,
                      backgroundColor: status == OutingStatus.requested ? AppColors.textMuted : null,
                      onPressed: onPressed,
                    ),
                  ),
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

class _InfoRow extends StatelessWidget {
  const _InfoRow({required this.icon, required this.label, required this.value, this.showDivider = true});
  final IconData icon;
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
              Icon(icon, size: 18, color: AppColors.textMuted),
              const SizedBox(width: 12),
              Text(label, style: AppTextStyles.body(size: 13)),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  value,
                  textAlign: TextAlign.right,
                  style: const TextStyle(fontWeight: FontWeight.w600, color: AppColors.textDark, fontSize: 13),
                ),
              ),
            ],
          ),
        ),
        if (showDivider) const Divider(height: 1, color: AppColors.border, indent: 16, endIndent: 16),
      ],
    );
  }
}

class _Tip extends StatelessWidget {
  const _Tip({required this.icon, required this.text, this.last = false});
  final IconData icon;
  final String text;
  final bool last;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(bottom: last ? 0 : 12),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: 17, color: AppColors.progressActive),
          const SizedBox(width: 12),
          Expanded(child: Text(text, style: AppTextStyles.body(size: 13, color: AppColors.textDark))),
        ],
      ),
    );
  }
}

class _RateSheet extends StatefulWidget {
  const _RateSheet({required this.companionName});
  final String companionName;

  @override
  State<_RateSheet> createState() => _RateSheetState();
}

class _RateSheetState extends State<_RateSheet> {
  int _stars = 0;
  final _feedback = TextEditingController();

  @override
  void dispose() {
    _feedback.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.fromLTRB(24, 20, 24, 24 + MediaQuery.of(context).viewInsets.bottom),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Center(
            child: Container(width: 40, height: 4, decoration: BoxDecoration(color: AppColors.border, borderRadius: BorderRadius.circular(4))),
          ),
          const SizedBox(height: 18),
          Text('How was your outing with ${widget.companionName}?', style: AppTextStyles.heading(size: 22)),
          const SizedBox(height: 16),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              for (var i = 1; i <= 5; i++)
                IconButton(
                  onPressed: () => setState(() => _stars = i),
                  icon: Icon(i <= _stars ? Icons.star_rounded : Icons.star_outline_rounded, size: 36, color: AppColors.amberSegment),
                ),
            ],
          ),
          const SizedBox(height: 10),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14),
            decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16)),
            child: TextField(
              controller: _feedback,
              maxLines: 3,
              decoration: InputDecoration(
                hintText: 'Anything we should know? (optional)',
                hintStyle: AppTextStyles.body(size: 14),
                border: InputBorder.none,
              ),
            ),
          ),
          const SizedBox(height: 18),
          PrimaryButton(
            label: 'Submit rating',
            icon: null,
            onPressed: _stars == 0 ? null : () => Navigator.of(context).pop((_stars, _feedback.text)),
          ),
        ],
      ),
    );
  }
}
