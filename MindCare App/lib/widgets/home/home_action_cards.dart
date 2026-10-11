import 'package:flutter/material.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_text_styles.dart';
import '../../models/therapy_data.dart';

class AidaListeningCard extends StatelessWidget {
  const AidaListeningCard({super.key, this.onTap});
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.all(18),
        decoration: BoxDecoration(color: AppColors.infoBoxBackground, borderRadius: BorderRadius.circular(20)),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: 34,
              height: 34,
              decoration: const BoxDecoration(color: AppColors.primaryDark, shape: BoxShape.circle),
              child: const Icon(Icons.auto_awesome, color: Colors.white, size: 16),
            ),
            const SizedBox(height: 36),
            Text.rich(
              TextSpan(
                style: AppTextStyles.heading(size: 22),
                children: [
                  const TextSpan(text: 'Aida is\n'),
                  TextSpan(text: 'listening', style: AppTextStyles.heading(size: 22, style: FontStyle.italic)),
                ],
              ),
            ),
            const SizedBox(height: 4),
            Text('your guide', style: AppTextStyles.body(size: 13)),
          ],
        ),
      ),
    );
  }
}

class AppointmentCard extends StatelessWidget {
  const AppointmentCard({super.key, this.session, this.onTap});
  final UpcomingSession? session;
  final VoidCallback? onTap;

  static const _weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

  String _dueLabel(DateTime startsAt) {
    final now = DateTime.now();
    final days = DateTime(startsAt.year, startsAt.month, startsAt.day)
        .difference(DateTime(now.year, now.month, now.day))
        .inDays;
    if (days <= 0) return 'TODAY';
    if (days == 1) return 'TOMORROW';
    return 'IN $days DAYS';
  }

  String _timeLabel(DateTime t) {
    final hour = t.hour % 12 == 0 ? 12 : t.hour % 12;
    final minute = t.minute.toString().padLeft(2, '0');
    final period = t.hour < 12 ? 'AM' : 'PM';
    return '${_weekdays[t.weekday - 1]} · $hour:$minute $period';
  }

  @override
  Widget build(BuildContext context) {
    final s = session;
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(20)),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Icon(Icons.calendar_today_outlined, size: 18, color: AppColors.textDark),
            const SizedBox(height: 10),
            if (s == null) ...[
              Text('NEXT SESSION', style: AppTextStyles.label()),
              const SizedBox(height: 4),
              const Text('None booked', style: TextStyle(fontWeight: FontWeight.w700, color: AppColors.textDark)),
              Text('Tap to find a therapist', style: AppTextStyles.body(size: 12)),
            ] else ...[
              Text(_dueLabel(s.startsAt), style: AppTextStyles.label()),
              const SizedBox(height: 4),
              Text(_timeLabel(s.startsAt), style: const TextStyle(fontWeight: FontWeight.w700, color: AppColors.textDark)),
              Text('${s.therapistName} · ${s.mode}', style: AppTextStyles.body(size: 12)),
            ],
          ],
        ),
      ),
    );
  }
}

class QuickBreathCard extends StatelessWidget {
  const QuickBreathCard({super.key, this.onTap});
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(color: AppColors.cardBackground, borderRadius: BorderRadius.circular(20)),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Icon(Icons.eco_outlined, size: 18, color: AppColors.textDark),
            const SizedBox(height: 10),
            Text('QUICK', style: AppTextStyles.label()),
            const SizedBox(height: 4),
            const Text('3-min breath', style: TextStyle(fontWeight: FontWeight.w700, color: AppColors.textDark)),
          ],
        ),
      ),
    );
  }
}

class ActionPillRow extends StatelessWidget {
  const ActionPillRow({super.key, this.onBreathTap, this.onReflectTap});
  final VoidCallback? onBreathTap;
  final VoidCallback? onReflectTap;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: _GradientPill(
            label: 'BREATH',
            colors: const [AppColors.breathGradientStart, AppColors.breathGradientEnd],
            onTap: onBreathTap ?? () {},
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: _GradientPill(
            label: 'REFLECT',
            colors: const [AppColors.reflectGradientStart, AppColors.reflectGradientEnd],
            onTap: onReflectTap ?? () {},
          ),
        ),
      ],
    );
  }
}

class _GradientPill extends StatelessWidget {
  const _GradientPill({required this.label, required this.colors, required this.onTap});
  final String label;
  final List<Color> colors;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        height: 64,
        padding: const EdgeInsets.symmetric(horizontal: 18),
        alignment: Alignment.centerLeft,
        decoration: BoxDecoration(
          gradient: LinearGradient(colors: colors, begin: Alignment.topLeft, end: Alignment.bottomRight),
          borderRadius: BorderRadius.circular(18),
        ),
        child: Text(label, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700, letterSpacing: 0.5)),
      ),
    );
  }
}