import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:mindcare_mobile/main.dart';

void main() {
  testWidgets('MindCareApp shows the splash screen, then the welcome screen', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(const MindCareApp());

    expect(find.byType(MaterialApp), findsOneWidget);

    // Let the splash screen's delayed navigation fire and the fade
    // transition finish. Both screens run looping animations, so pump a
    // fixed duration instead of pumpAndSettle (which would never settle).
    await tester.pump(const Duration(milliseconds: 3500));
    await tester.pump(const Duration(seconds: 1));
    await tester.pump(const Duration(seconds: 3));

    expect(find.text('Create your account'), findsOneWidget);
  });
}
