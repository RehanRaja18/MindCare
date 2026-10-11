import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';

import 'package:mindcare_mobile/core/utils/card_utils.dart';
import 'package:mindcare_mobile/models/premium_data.dart';
import 'package:mindcare_mobile/providers/journal_provider.dart';
import 'package:mindcare_mobile/providers/outings_provider.dart';
import 'package:mindcare_mobile/providers/premium_provider.dart';
import 'package:mindcare_mobile/screens/premium/manage_subscription_screen.dart';
import 'package:mindcare_mobile/screens/premium/premium_checkout_screen.dart';

const _card = PaymentCard(brand: 'Visa', last4: '4242', expMonth: 12, expYear: 2030, holderName: 'Test Patient');

/// A clock the tests can move forward.
class _Clock {
  _Clock(this.now);
  DateTime now;
  DateTime call() => now;
}

Widget _wrap(Widget child, PremiumProvider premium) => MultiProvider(
      providers: [
        ChangeNotifierProvider.value(value: premium),
        ChangeNotifierProvider(create: (_) => JournalProvider()),
        ChangeNotifierProvider(create: (_) => OutingsProvider()),
      ],
      child: MaterialApp(home: child),
    );

Future<void> _tapStart(WidgetTester tester) async {
  await tester.scrollUntilVisible(find.text('Start free trial'), 200, scrollable: find.byType(Scrollable).first);
  await tester.tap(find.text('Start free trial'));
}

void _phone(WidgetTester tester) {
  tester.view.physicalSize = const Size(1500, 4200);
  tester.view.devicePixelRatio = 3;
  addTearDown(tester.view.reset);
}

void main() {
  group('CardUtils', () {
    test('accepts real test numbers and rejects typos', () {
      expect(CardUtils.validateNumber('4242 4242 4242 4242'), isNull);
      expect(CardUtils.validateNumber('5555 5555 5555 4444'), isNull);
      expect(CardUtils.validateNumber('4242 4242 4242 4241'), isNotNull);
      expect(CardUtils.validateNumber('4242'), isNotNull);
    });

    test('detects the brand', () {
      expect(CardUtils.brandOf('4242'), 'Visa');
      expect(CardUtils.brandOf('5555'), 'Mastercard');
      expect(CardUtils.brandOf('3782'), 'Amex');
      expect(CardUtils.cvcLength('Amex'), 4);
    });

    test('expiry is valid through the end of its month', () {
      final now = DateTime(2026, 10, 11);
      expect(CardUtils.validateExpiry('10/26', now: now), isNull);
      expect(CardUtils.validateExpiry('09/26', now: now), 'This card has expired');
      expect(CardUtils.validateExpiry('13/27', now: now), 'Use MM/YY');
    });

    test('formatters group the number and add the slash', () {
      final number = CardNumberFormatter().formatEditUpdate(TextEditingValue.empty, const TextEditingValue(text: '4242424242424242'));
      expect(number.text, '4242 4242 4242 4242');
      final expiry = ExpiryFormatter().formatEditUpdate(TextEditingValue.empty, const TextEditingValue(text: '1228'));
      expect(expiry.text, '12/28');
    });
  });

  group('Subscription lifecycle', () {
    test('trial, then the first charge, then monthly renewals', () {
      final clock = _Clock(DateTime(2026, 10, 11, 9));
      final p = PremiumProvider(clock: clock.call);

      expect(p.status, PremiumStatus.none);
      expect(p.startTrial(_card), isTrue);
      expect(p.status, PremiumStatus.trial);
      expect(p.nextChargeAt, DateTime(2026, 10, 18, 9));
      expect(p.trialDaysLeft, 7);

      clock.now = DateTime(2026, 10, 19);
      expect(p.status, PremiumStatus.active);
      expect(p.isPremium, isTrue);
      expect(p.nextChargeAt, DateTime(2026, 11, 18, 9));

      // A second trial is not allowed.
      expect(p.startTrial(_card), isFalse);
    });

    test('cancelling during the trial keeps access until it ends, then stops', () {
      final clock = _Clock(DateTime(2026, 10, 11));
      final p = PremiumProvider(clock: clock.call)..startTrial(_card);

      p.setAutoRenew(false);
      expect(p.status, PremiumStatus.trialCancelled);
      expect(p.nextChargeAt, isNull);
      expect(p.accessEndsAt, DateTime(2026, 10, 18));
      expect(p.isPremium, isTrue);

      clock.now = DateTime(2026, 10, 18, 1);
      expect(p.status, PremiumStatus.none);
      expect(p.isPremium, isFalse);
    });

    test('cancelling a paid month keeps access until that month ends', () {
      final clock = _Clock(DateTime(2026, 10, 11));
      final p = PremiumProvider(clock: clock.call)..startTrial(_card);
      clock.now = DateTime(2026, 10, 25);

      p.setAutoRenew(false);
      expect(p.status, PremiumStatus.cancelled);
      expect(p.accessEndsAt, DateTime(2026, 11, 18));

      p.setAutoRenew(true);
      expect(p.status, PremiumStatus.active);

      p.setAutoRenew(false);
      clock.now = DateTime(2026, 11, 19);
      expect(p.isPremium, isFalse);
    });

    test('subscribing after the trial charges today and renews monthly', () {
      final clock = _Clock(DateTime(2026, 12, 1, 10));
      final p = PremiumProvider(clock: clock.call)..subscribe(_card);
      expect(p.status, PremiumStatus.active);
      expect(p.nextChargeAt, DateTime(2027, 1, 1, 10));
    });
  });

  testWidgets('Checkout needs a valid card and the renewal consent', (tester) async {
    _phone(tester);
    final premium = PremiumProvider();
    await tester.pumpWidget(_wrap(const PremiumCheckoutScreen(), premium));

    expect(find.text('Due today'), findsOneWidget);
    expect(find.text('Rs 0'), findsOneWidget);

    // Empty form: nothing happens.
    await _tapStart(tester);
    await tester.pump();
    expect(find.text('Enter your card number'), findsOneWidget);
    expect(premium.isPremium, isFalse);

    await tester.enterText(find.byKey(const Key('card-number')), '4242424242424242');
    await tester.enterText(find.byKey(const Key('card-expiry')), '1230');
    await tester.enterText(find.byKey(const Key('card-cvc')), '123');
    await tester.enterText(find.byKey(const Key('card-name')), 'Test Patient');
    await tester.pump();
    expect(find.text('TEST PATIENT'), findsOneWidget); // live preview

    // Valid card but no consent yet.
    await _tapStart(tester);
    await tester.pump();
    expect(premium.isPremium, isFalse);

    await tester.scrollUntilVisible(find.byKey(const Key('renewal-consent')), 200, scrollable: find.byType(Scrollable).first);
    await tester.tap(find.byKey(const Key('renewal-consent')));
    await _tapStart(tester);
    await tester.pumpAndSettle();

    expect(premium.status, PremiumStatus.trial);
    expect(premium.card!.masked, 'Visa •••• 4242');
    expect(premium.card!.expiryLabel, '12/30');
    expect(find.text("You're in."), findsOneWidget);
  });

  testWidgets('Manage subscription turns auto-renew off and back on', (tester) async {
    _phone(tester);
    final premium = PremiumProvider()..startTrial(_card);
    await tester.pumpWidget(_wrap(const ManageSubscriptionScreen(), premium));

    expect(find.text('Free trial'), findsOneWidget);
    expect(find.text('Visa •••• 4242'), findsOneWidget);

    await tester.tap(find.text('Turn off auto-renew'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Turn off'));
    await tester.pumpAndSettle();

    expect(premium.status, PremiumStatus.trialCancelled);
    expect(find.text('Free trial · ending'), findsOneWidget);

    await tester.tap(find.text('Turn auto-renew back on'));
    await tester.pump();
    expect(premium.status, PremiumStatus.trial);
  });
}
