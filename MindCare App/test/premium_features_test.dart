import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';

import 'package:mindcare_mobile/models/premium_data.dart';
import 'package:mindcare_mobile/providers/checkin_provider.dart';
import 'package:mindcare_mobile/providers/journal_provider.dart';
import 'package:mindcare_mobile/providers/outings_provider.dart';
import 'package:mindcare_mobile/providers/premium_provider.dart';
import 'package:mindcare_mobile/screens/premium/journal_screen.dart';
import 'package:mindcare_mobile/screens/premium/outings_screen.dart';
import 'package:mindcare_mobile/screens/premium/premium_screen.dart';

Widget _wrap(Widget child, {PremiumProvider? premium, JournalProvider? journal, OutingsProvider? outings}) => MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => premium ?? PremiumProvider()),
        ChangeNotifierProvider(create: (_) => journal ?? JournalProvider()),
        ChangeNotifierProvider(create: (_) => outings ?? OutingsProvider()),
        ChangeNotifierProvider(create: (_) => CheckinProvider()),
      ],
      child: MaterialApp(home: child),
    );

void _phone(WidgetTester tester) {
  tester.view.physicalSize = const Size(1500, 2700);
  tester.view.devicePixelRatio = 3;
  addTearDown(tester.view.reset);
}

void main() {
  testWidgets('Journal is locked until Premium, then opens empty', (tester) async {
    _phone(tester);
    final premium = PremiumProvider();
    await tester.pumpWidget(_wrap(const JournalScreen(), premium: premium));

    expect(find.text('Your private journal'), findsOneWidget);
    expect(find.text('See Premium'), findsOneWidget);

    premium.startTrial();
    await tester.pump();

    expect(find.text('No entries yet'), findsOneWidget);
    expect(find.text('New entry'), findsOneWidget);
  });

  testWidgets('Premium page matches the website plan and starts the trial', (tester) async {
    _phone(tester);
    final premium = PremiumProvider();
    await tester.pumpWidget(_wrap(const PremiumScreen(), premium: premium));

    expect(find.text('Rs 1,500'), findsOneWidget);
    expect(find.text('Patient Journal'), findsOneWidget);
    expect(find.text('Outing activities'), findsOneWidget);
    expect(find.text('COMING SOON'), findsOneWidget);

    await tester.tap(find.text('Start free trial'));
    await tester.pump();

    expect(premium.isOnTrial, isTrue);
    expect(premium.trialDaysLeft, 7);
    expect(find.text('On free trial'), findsOneWidget);
  });

  testWidgets('Writing a journal entry adds it to the list', (tester) async {
    _phone(tester);
    final premium = PremiumProvider()..startTrial();
    final journal = JournalProvider();
    await tester.pumpWidget(_wrap(const JournalScreen(), premium: premium, journal: journal));

    await tester.tap(find.text('New entry'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Okay'));
    await tester.enterText(find.byType(TextField).at(0), 'Monday');
    await tester.enterText(find.byType(TextField).at(1), 'Long day, but the walk helped.');
    await tester.tap(find.byType(Switch));
    await tester.tap(find.text('Save entry'));
    await tester.pumpAndSettle();

    expect(journal.entries.single.title, 'Monday');
    expect(journal.entries.single.moodId, 'okay');
    expect(journal.entries.single.sharedWithTherapist, isTrue);
    expect(find.text('Long day, but the walk helped.'), findsOneWidget);
    expect(find.text('1 entry · 1 shared'), findsOneWidget);
  });

  testWidgets('Outings shows an empty state, then offered outings', (tester) async {
    _phone(tester);
    final premium = PremiumProvider()..startTrial();
    final outings = OutingsProvider();
    await tester.pumpWidget(_wrap(const OutingsScreen(), premium: premium, outings: outings));

    expect(find.text('No outings offered yet'), findsOneWidget);

    outings.setAvailable([
      Outing(
        id: 'o1',
        type: OutingType.walk,
        companionName: 'Sana',
        area: 'Lake View Park',
        startsAt: DateTime.now().add(const Duration(days: 1)),
        durationMinutes: 45,
      ),
    ]);
    await tester.pump();

    expect(find.text('Walk with Sana'), findsOneWidget);

    await tester.tap(find.text('Coffee'));
    await tester.pump();
    expect(find.text('Nothing like this yet'), findsOneWidget);
  });

  group('OutingsProvider', () {
    final outing = Outing(
      id: 'o1',
      type: OutingType.coffee,
      companionName: 'Ali',
      area: 'F-7 Markaz',
      startsAt: DateTime.now().add(const Duration(hours: 5)),
      durationMinutes: 60,
    );

    test('requesting moves an outing out of the offered list', () {
      final p = OutingsProvider()..setAvailable([outing]);
      p.requestOuting(outing);
      expect(p.available, isEmpty);
      expect(p.bookingFor('o1')!.status, OutingStatus.requested);
    });

    test('ratings are kept between 1 and 5', () {
      final p = OutingsProvider()..setBookings([OutingBooking(outing: outing, status: OutingStatus.completed)]);
      p.rate('o1', 9, feedback: 'Lovely');
      expect(p.bookingFor('o1')!.rating, 5);
      expect(p.bookingFor('o1')!.feedback, 'Lovely');
    });
  });
}
