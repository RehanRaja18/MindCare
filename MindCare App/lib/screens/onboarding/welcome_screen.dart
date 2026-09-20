import 'package:flutter/material.dart';

import '../../core/theme/app_colors.dart';
import '../../core/theme/app_text_styles.dart';
import '../../main.dart';
import '../../widgets/common/sos_button.dart';
import '../../widgets/common/primary_button.dart';
import '../auth/sign_in_screen.dart';
import 'sign_up_screen.dart';

class WelcomeScreen extends StatelessWidget {
  const WelcomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Stack(
          children: [
            Positioned(
              top: -60,
              right: -80,
              child: Container(
                width: 280,
                height: 280,
                decoration: const BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: LinearGradient(
                    colors: [Color(0xFFB8CFC2), Color(0xFF7C8B93)],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 28),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Spacer(flex: 2),
                  RichText(
                    text: TextSpan(
                      style: AppTextStyles.heading(size: 40),
                      children: [
                        const TextSpan(text: 'A quieter\n'),
                        TextSpan(
                          text: 'mind ',
                          style: AppTextStyles.heading(
                            size: 40,
                            style: FontStyle.italic,
                          ).copyWith(color: AppColors.progressActive),
                        ),
                        const TextSpan(text: 'starts here.'),
                      ],
                    ),
                  ),
                  const SizedBox(height: 16),
                  Text(
                    "Therapy that fits your day. Care that doesn't judge. Quiet tools for the loud moments.",
                    style: AppTextStyles.body(size: 16),
                  ),
                  const Spacer(flex: 2),
                  PrimaryButton(
                    label: 'Create your account',
                    icon: null,
                    onPressed: () => Navigator.of(context).push(
                      MaterialPageRoute(
                        builder: (_) =>
                            const MobileFrame(child: SignUpScreen()),
                      ),
                    ),
                  ),
                  const SizedBox(height: 14),
                  Row(
                    children: [
                      Expanded(
                        child: OutlinedButton(
                          onPressed: () => Navigator.of(context).push(
                            MaterialPageRoute(
                              builder: (_) =>
                                  const MobileFrame(child: SignInScreen()),
                            ),
                          ),
                          style: OutlinedButton.styleFrom(
                            padding: const EdgeInsets.symmetric(vertical: 18),
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(18),
                            ),
                            side: const BorderSide(color: AppColors.border),
                          ),
                          child: const Text(
                            'I already have one',
                            style: TextStyle(color: AppColors.textDark),
                          ),
                        ),
                      ),
                      const SizedBox(width: 12),
                      const SosButton(),
                    ],
                  ),
                  const SizedBox(height: 16),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
