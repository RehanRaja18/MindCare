import 'package:flutter/material.dart';
import '../../core/theme/app_colors.dart';
import '../../models/checkin_data.dart';

class CalmActivatedStrip extends StatelessWidget {
  const CalmActivatedStrip({super.key, required this.segments});
  final List<NervousSystemState> segments;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(18)),
      child: segments.isEmpty
          ? const SizedBox(
              height: 28,
              child: Center(child: Text('No readings yet today', style: TextStyle(fontSize: 13, color: AppColors.textMuted))),
            )
          : Row(
        children: segments.map((segment) {
          final color = segment == NervousSystemState.calm ? AppColors.chipSelected : AppColors.amberSegment;
          return Expanded(
            child: Container(
              height: 28,
              margin: const EdgeInsets.symmetric(horizontal: 2),
              decoration: BoxDecoration(color: color, borderRadius: BorderRadius.circular(6)),
            ),
          );
        }).toList(),
      ),
    );
  }
}