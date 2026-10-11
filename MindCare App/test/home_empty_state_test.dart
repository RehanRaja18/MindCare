import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';

import 'package:mindcare_mobile/models/checkin_data.dart';
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

Widget _wrap(Widget child, {CheckinProvider? checkin}) => MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => UserSessionProvider()),
        ChangeNotifierProvider(create: (_) => OnboardingProvider()),
        ChangeNotifierProvider(create: (_) => checkin ?? CheckinProvider()),
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
    expect(find.text('SWEAT (EDA)'), findsNothing);
  });

  testWidgets('Pulse shows the latest sensor reading and its state', (tester) async {
    tester.view.physicalSize = const Size(1500, 2700);
    tester.view.devicePixelRatio = 3;
    addTearDown(tester.view.reset);

    final now = DateTime.now();
    final checkin = CheckinProvider()
      ..addReadings([
        VitalReading(at: now.subtract(const Duration(minutes: 10)), heartRate: 72, breathingRate: 14, steps: 1200),
        VitalReading(at: now.subtract(const Duration(minutes: 5)), heartRate: 88, breathingRate: 16, steps: 1800),
        VitalReading(at: now, heartRate: 108, breathingRate: 22, steps: 2400),
      ]);

    await tester.pumpWidget(_wrap(const PulseScreen(), checkin: checkin));
    await tester.pump();

    expect(find.text('108'), findsOneWidget);
    expect(find.text('22'), findsOneWidget);
    expect(find.text('Activated'), findsOneWidget);
    await tester.drag(find.byType(ListView).first, const Offset(0, -1500));
    await tester.pump();
    expect(find.text('2,400'), findsOneWidget);
  });

  group('CheckinProvider readings', () {
    test('trends follow the readings in time order', () {
      final t = DateTime.now();
      final p = CheckinProvider()
        ..addReadings([
          VitalReading(at: t, heartRate: 80, breathingRate: 15),
          VitalReading(at: t.subtract(const Duration(minutes: 1)), heartRate: 70, breathingRate: 12),
        ]);
      expect(p.vitals!.heartTrend, [70, 80]);
      expect(p.vitals!.breathingTrend, [12, 15]);
      expect(p.vitals!.heartRate, 80);
      expect(p.vitals!.steps, isNull);
      expect(p.calmActivated, [NervousSystemState.calm, NervousSystemState.calm]);
    });

    test('graphs show only the most recent window', () {
      final t = DateTime.now();
      final p = CheckinProvider()
        ..addReadings([
          for (var i = 0; i < 30; i++) VitalReading(at: t.add(Duration(minutes: i)), heartRate: 60 + i, breathingRate: 12),
        ]);
      expect(p.vitals!.heartTrend.length, CheckinProvider.trendWindow);
      expect(p.vitals!.heartTrend.last, 89);
      expect(p.calmActivated.length, CheckinProvider.trendWindow);
    });
  });
}
