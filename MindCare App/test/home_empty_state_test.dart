import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';

import 'package:mindcare_mobile/providers/account_provider.dart';
import 'package:mindcare_mobile/providers/checkin_provider.dart';
import 'package:mindcare_mobile/providers/community_provider.dart';
import 'package:mindcare_mobile/providers/notifications_provider.dart';
import 'package:mindcare_mobile/providers/onboarding_provider.dart';
import 'package:mindcare_mobile/providers/program_provider.dart';
import 'package:mindcare_mobile/providers/settings_provider.dart';
import 'package:mindcare_mobile/providers/therapy_provider.dart';
import 'package:mindcare_mobile/providers/user_session_provider.dart';
import 'package:mindcare_mobile/screens/home/home_screen.dart';
import 'package:mindcare_mobile/screens/home/pulse_screen.dart';

Widget _wrap(Widget child) => MultiProvider(
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
      child: MaterialApp(home: child),
    );

void main() {
  // Before the backend supplies data, Home and Pulse must show empty
  // states rather than sample numbers.
  testWidgets('Home shows empty states with no backend data', (tester) async {
    tester.view.physicalSize = const Size(1500, 2700);
    tester.view.devicePixelRatio = 3;
    addTearDown(tester.view.reset);

    await tester.pumpWidget(_wrap(const HomeScreen()));
    await tester.pump();

    expect(find.text('None booked'), findsOneWidget);
    expect(find.text('No readings yet'), findsOneWidget);
    expect(find.text('Fri · 5:00 PM'), findsNothing);
    expect(find.text('6,612'), findsNothing);
  });

  testWidgets('Pulse shows empty states with no backend data', (tester) async {
    tester.view.physicalSize = const Size(1500, 2700);
    tester.view.devicePixelRatio = 3;
    addTearDown(tester.view.reset);

    await tester.pumpWidget(_wrap(const PulseScreen()));
    await tester.pump();

    expect(find.text('no reading yet'), findsOneWidget);
    await tester.drag(find.byType(ListView).first, const Offset(0, -1500));
    await tester.pump();
    expect(find.text('No readings yet today'), findsOneWidget);
  });
}
