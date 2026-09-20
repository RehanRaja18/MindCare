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
    // transition settle, so no pending Timer/Ticker remains at teardown
    // (the splash screen's own animation controllers repeat forever, so
    // this must happen after it's been replaced).
    await tester.pump(const Duration(seconds: 3));
    await tester.pumpAndSettle();

    expect(find.text('Create your account'), findsOneWidget);
  });
}
