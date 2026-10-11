import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_text_styles.dart';
import '../../providers/settings_provider.dart';
import '../../widgets/common/primary_button.dart';

class WearablesScreen extends StatefulWidget {
  const WearablesScreen({super.key});

  @override
  State<WearablesScreen> createState() => _WearablesScreenState();
}

class _WearablesScreenState extends State<WearablesScreen> {
  bool _loading = false;

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<SettingsProvider>();
    final device = provider.wearable;

    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(24, 8, 24, 30),
          children: [
            Row(
              children: [
                IconButton(
                  onPressed: () => Navigator.of(context).maybePop(),
                  icon: const Icon(Icons.chevron_left, color: AppColors.textDark),
                ),
                const Expanded(
                  child: Text(
                    'WEARABLES',
                    textAlign: TextAlign.center,
                    style: TextStyle(letterSpacing: 1, color: AppColors.textLabel, fontWeight: FontWeight.w600, fontSize: 12),
                  ),
                ),
                const SizedBox(width: 48),
              ],
            ),
            const SizedBox(height: 8),
            Text('Your connected device.', style: AppTextStyles.heading(size: 26)),
            const SizedBox(height: 20),
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                gradient: const LinearGradient(colors: [Color(0xFF2B453C), Color(0xFF162622)], begin: Alignment.topLeft, end: Alignment.bottomRight),
                borderRadius: BorderRadius.circular(24),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Container(
                        width: 46,
                        height: 46,
                        decoration: BoxDecoration(color: Colors.white.withOpacity(0.14), shape: BoxShape.circle),
                        child: const Icon(Icons.watch, color: Colors.white, size: 22),
                      ),
                      const SizedBox(width: 14),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(device.name, style: const TextStyle(color: Colors.white, fontSize: 18, fontFamily: 'serif')),
                            Text(device.model, style: const TextStyle(color: Colors.white54, fontSize: 12)),
                          ],
                        ),
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                        decoration: BoxDecoration(
                          color: device.connected ? Colors.white.withOpacity(0.16) : Colors.white.withOpacity(0.08),
                          borderRadius: BorderRadius.circular(20),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Container(width: 6, height: 6, decoration: BoxDecoration(color: device.connected ? AppColors.progressActive : Colors.white38, shape: BoxShape.circle)),
                            const SizedBox(width: 5),
                            Text(device.connected ? 'Connected' : 'Disconnected', style: const TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.w600)),
                          ],
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 20),
                  Row(
                    children: [
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text('BATTERY', style: TextStyle(color: Colors.white54, fontSize: 10, letterSpacing: 1)),
                            const SizedBox(height: 6),
                            Text('${device.batteryPercent}%', style: const TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.w600)),
                          ],
                        ),
                      ),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text('LAST SYNCED', style: TextStyle(color: Colors.white54, fontSize: 10, letterSpacing: 1)),
                            const SizedBox(height: 6),
                            Text(device.lastSynced, style: const TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.w600)),
                          ],
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 22),
            Text('WHAT IT SHARES', style: AppTextStyles.label()),
            const SizedBox(height: 12),
            Container(
              decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(20)),
              child: Column(
                children: const [
                  _DataRow(icon: Icons.favorite_outline, label: 'Heart rate'),
                  _DataRow(icon: Icons.air, label: 'Breathing rate'),
                  _DataRow(icon: Icons.directions_walk, label: 'Steps', showDivider: false),
                ],
              ),
            ),
            const SizedBox(height: 26),
            PrimaryButton(
              label: device.connected ? 'Disconnect device' : 'Reconnect device',
              icon: null,
              loading: _loading,
              onPressed: () async {
                setState(() => _loading = true);
                if (device.connected) {
                  await context.read<SettingsProvider>().disconnectWearable();
                } else {
                  await context.read<SettingsProvider>().reconnectWearable();
                }
                if (!mounted) return;
                setState(() => _loading = false);
              },
            ),
          ],
        ),
      ),
    );
  }
}

class _DataRow extends StatelessWidget {
  const _DataRow({required this.icon, required this.label, this.showDivider = true});
  final IconData icon;
  final String label;
  final bool showDivider;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 16),
          child: Row(
            children: [
              Icon(icon, size: 18, color: AppColors.textDark),
              const SizedBox(width: 14),
              Text(label, style: const TextStyle(fontWeight: FontWeight.w600, color: AppColors.textDark, fontSize: 14)),
            ],
          ),
        ),
        if (showDivider) const Divider(height: 1, indent: 16, endIndent: 16, color: AppColors.border),
      ],
    );
  }
}