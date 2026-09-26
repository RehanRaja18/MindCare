import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'core/theme/app_theme.dart';
import 'providers/onboarding_provider.dart';
import 'providers/checkin_provider.dart';
import 'providers/therapy_provider.dart';
import 'providers/program_provider.dart';
import 'providers/community_provider.dart';
import 'providers/account_provider.dart';
import 'providers/notifications_provider.dart';
import 'providers/user_session_provider.dart';
import 'providers/settings_provider.dart';
import 'screens/onboarding/welcome_screen.dart';
import 'screens/home/home_shell.dart';
import 'screens/splash/splash_screen.dart';

void main() {
  runApp(const MindCareApp());
}

class MindCareApp extends StatelessWidget {
  const MindCareApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => UserSessionProvider()),
        ChangeNotifierProvider(create: (_) => OnboardingProvider()),
        ChangeNotifierProvider(create: (_) => CheckinProvider()),
        ChangeNotifierProvider(create: (_) => TherapyProvider()),
        ChangeNotifierProvider(create: (_) => ProgramProvider()),
        ChangeNotifierProvider(create: (_) => CommunityProvider()),
        ChangeNotifierProvider(create: (_) => AccountProvider()),
        ChangeNotifierProvider(create: (_) => NotificationsProvider()),
        ChangeNotifierProvider(create: (_) => SettingsProvider()),
      ],
      child: Consumer<SettingsProvider>(
        builder: (context, settings, _) {
          return MaterialApp(
            title: 'MindCare',
            debugShowCheckedModeBanner: false,
            theme: AppTheme.light(),
            builder: (context, child) {
              return MediaQuery(
                data: MediaQuery.of(
                  context,
                ).copyWith(textScaler: TextScaler.linear(settings.textScale)),
                child: child!,
              );
            },
            home: const MobileFrame(child: SplashScreen()),
            onGenerateRoute: (settings) {
              if (settings.name == '/home') {
                return MaterialPageRoute(
                  builder: (_) => const MobileFrame(child: HomeShell()),
                );
              }
              if (settings.name == '/welcome') {
                return MaterialPageRoute(
                  builder: (_) => const MobileFrame(child: WelcomeScreen()),
                );
              }
              return null;
            },
          );
        },
      ),
    );
  }
}

class MobileFrame extends StatelessWidget {
  const MobileFrame({super.key, required this.child});
  final Widget child;

  @override
  Widget build(BuildContext context) {
    final screenWidth = MediaQuery.of(context).size.width;
    final isWideScreen = screenWidth > 430;

    if (!isWideScreen) return child;

    return Scaffold(
      backgroundColor: const Color(0xFF0D0D0D),
      body: Center(
        child: Container(
          width: 430,
          clipBehavior: Clip.antiAlias,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(28),
            boxShadow: const [
              BoxShadow(color: Colors.black54, blurRadius: 40, spreadRadius: 4),
            ],
          ),
          child: child,
        ),
      ),
    );
  }
}
