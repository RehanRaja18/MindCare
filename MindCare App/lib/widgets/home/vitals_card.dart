import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/theme/app_colors.dart';
import '../../providers/checkin_provider.dart';

class VitalsSummaryCard extends StatelessWidget {
  const VitalsSummaryCard({super.key});

  @override
  Widget build(BuildContext context) {
    final vitals = context.watch<CheckinProvider>().vitals;
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 18),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(20)),
      child: Row(
        children: [
          // '—' until a reading arrives from a wearable or the backend.
          Expanded(child: _Metric(label: 'HEART', value: vitals == null ? '—' : '${vitals.heartRate}', unit: 'bpm')),
          const _Divider(),
          Expanded(child: _Metric(label: 'BREATH', value: vitals == null ? '—' : '${vitals.breathingRate}', unit: '/min')),
          const _Divider(),
          Expanded(child: _Metric(label: 'STEPS', value: vitals == null ? '—' : _formatSteps(vitals.steps), unit: 'today')),
        ],
      ),
    );
  }

  String _formatSteps(int steps) {
    final s = steps.toString();
    if (s.length <= 3) return s;
    return '${s.substring(0, s.length - 3)},${s.substring(s.length - 3)}';
  }
}

class _Metric extends StatelessWidget {
  const _Metric({required this.label, required this.value, required this.unit});
  final String label;
  final String value;
  final String unit;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Text(label, style: const TextStyle(fontSize: 11, letterSpacing: 1, color: AppColors.textLabel, fontWeight: FontWeight.w600)),
        const SizedBox(height: 6),
        Text(value, style: const TextStyle(fontSize: 24, fontWeight: FontWeight.w600, color: AppColors.textDark)),
        Text(unit, style: const TextStyle(fontSize: 11, color: AppColors.textMuted)),
      ],
    );
  }
}

class _Divider extends StatelessWidget {
  const _Divider();
  @override
  Widget build(BuildContext context) => Container(width: 1, height: 44, color: AppColors.border);
}