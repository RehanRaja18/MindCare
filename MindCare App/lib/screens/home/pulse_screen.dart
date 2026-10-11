import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_text_styles.dart';
import '../../models/checkin_data.dart';
import '../../providers/checkin_provider.dart';
import '../../widgets/pulse/calm_activated_strip.dart';
import '../../widgets/pulse/nervous_system_dial.dart';
import '../../widgets/pulse/vital_metric_card.dart';
import '../care/wellbeing_view.dart';

class PulseScreen extends StatefulWidget {
  const PulseScreen({super.key});

  @override
  State<PulseScreen> createState() => _PulseScreenState();
}

class _PulseScreenState extends State<PulseScreen> {
  String _view = 'pulse'; // 'pulse' | 'wellbeing'

  String _formatSteps(int steps) {
    final s = steps.toString();
    if (s.length <= 3) return s;
    return '${s.substring(0, s.length - 3)},${s.substring(s.length - 3)}';
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<CheckinProvider>();
    final vitals = provider.vitals;

    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        bottom: false,
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(24, 16, 24, 0),
              child: Container(
                padding: const EdgeInsets.all(4),
                decoration: BoxDecoration(color: AppColors.cardBackground, borderRadius: BorderRadius.circular(16)),
                child: Row(
                  children: [
                    Expanded(child: _ToggleButton(label: 'Pulse', selected: _view == 'pulse', onTap: () => setState(() => _view = 'pulse'))),
                    Expanded(child: _ToggleButton(label: 'Wellbeing', selected: _view == 'wellbeing', onTap: () => setState(() => _view = 'wellbeing'))),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 12),
            Expanded(
              child: _view == 'pulse'
                  ? ListView(
                      padding: const EdgeInsets.fromLTRB(24, 0, 24, 110),
                      children: [
                        Text('PULSE', style: AppTextStyles.label()),
                        const SizedBox(height: 8),
                        Text('Your nervous system today', style: AppTextStyles.heading(size: 26)),
                        const SizedBox(height: 18),
                        Container(
                          width: double.infinity,
                          padding: const EdgeInsets.symmetric(vertical: 26),
                          decoration: BoxDecoration(color: AppColors.cardBackground, borderRadius: BorderRadius.circular(24)),
                          child: Column(
                            children: [
                              Text('STATE RIGHT NOW', style: AppTextStyles.label()),
                              const SizedBox(height: 18),
                              NervousSystemDial(
                                state: vitals?.stateLabel ?? '—',
                                subtitle: vitals == null
                                    ? 'no reading yet'
                                    : vitals.state == NervousSystemState.calm
                                        ? 'parasympathetic'
                                        : 'sympathetic',
                              ),
                              const SizedBox(height: 18),
                              Padding(
                                padding: const EdgeInsets.symmetric(horizontal: 24),
                                child: Text(
                                  vitals == null
                                      ? 'No readings yet. Your heart rate, breathing and steps will show here once your sensor shares them with MindCare.'
                                      : vitals.state == NervousSystemState.calm
                                          ? 'Your body is settled. Stay with it — sip water, soften your shoulders.'
                                          : 'Your body is a little activated. Try a slow breath — in for 4, out for 6.',
                                  textAlign: TextAlign.center,
                                  style: AppTextStyles.body(size: 14),
                                ),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(height: 18),
                        Row(
                          children: [
                            Expanded(
                              child: VitalMetricCard(
                                label: 'HEART RATE',
                                value: vitals == null ? '—' : '${vitals.heartRate}',
                                unit: 'bpm',
                                trend: vitals?.heartTrend ?? const [],
                                color: AppColors.moodStressed,
                              ),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: VitalMetricCard(
                                label: 'BREATHING',
                                value: vitals == null ? '—' : '${vitals.breathingRate}',
                                unit: '/min',
                                trend: vitals?.breathingTrend ?? const [],
                                color: AppColors.moodLow,
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 12),
                        VitalMetricCard(
                          label: 'STEPS',
                          value: vitals?.steps == null ? '—' : _formatSteps(vitals!.steps!),
                          unit: 'today',
                          trend: vitals?.stepsTrend ?? const [],
                          color: AppColors.progressActive,
                        ),
                        const SizedBox(height: 22),
                        Text('CALM VS. ACTIVATED · RECENT READINGS', style: AppTextStyles.label()),
                        const SizedBox(height: 12),
                        CalmActivatedStrip(segments: provider.calmActivated),
                      ],
                    )
                  : const WellbeingView(),
            ),
          ],
        ),
      ),
    );
  }
}

class _ToggleButton extends StatelessWidget {
  const _ToggleButton({required this.label, required this.selected, required this.onTap});
  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 12),
        decoration: BoxDecoration(
          color: selected ? AppColors.textDark : Colors.transparent,
          borderRadius: BorderRadius.circular(13),
        ),
        alignment: Alignment.center,
        child: Text(label, style: TextStyle(color: selected ? Colors.white : AppColors.textMuted, fontWeight: FontWeight.w600, fontSize: 13)),
      ),
    );
  }
}