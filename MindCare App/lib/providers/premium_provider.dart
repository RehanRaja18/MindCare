import 'package:flutter/material.dart';
import '../models/premium_data.dart';

/// The patient's MindCare Premium subscription. Matches the plan on the
/// website: Rs 1,500 / month after a 7-day free trial.
///
/// Flow: the patient adds a card, the trial starts with full access, and
/// unless auto-renew is turned off the card is charged Rs 1,500 when the
/// trial ends and then every month.
///
/// There is no payment or subscription API yet, so this holds the state in
/// memory and nothing is charged. Once the backend creates the Stripe
/// subscription, call [setStatus] with what it returns (after sign-in and
/// after each change) and send [startTrial] / [setAutoRenew] / [updateCard]
/// to it instead.
class PremiumProvider extends ChangeNotifier {
  PremiumProvider({DateTime Function()? clock}) : _now = clock ?? DateTime.now;

  static const int monthlyPrice = 1500;
  static const int trialDays = 7;

  /// Days before the trial ends that we remind the patient.
  static const int reminderDaysBefore = 2;

  final DateTime Function() _now;

  PaymentCard? _card;
  DateTime? _trialEndsAt;
  bool _autoRenew = false;
  bool _trialUsed = false;

  // When auto-renew is turned off after the trial, access lasts until the
  // end of the month already paid for.
  DateTime? _cancelledAccessEnd;

  PaymentCard? get card => _card;
  DateTime? get trialEndsAt => _trialEndsAt;
  bool get autoRenew => _autoRenew;
  bool get trialUsed => _trialUsed;

  /// End of the current paid month, counting monthly from the trial's end.
  DateTime _currentPeriodEnd() {
    final start = _trialEndsAt ?? _now();
    var end = DateTime(start.year, start.month + 1, start.day, start.hour, start.minute);
    while (!_now().isBefore(end)) {
      end = DateTime(end.year, end.month + 1, end.day, end.hour, end.minute);
    }
    return end;
  }

  bool get isOnTrial => _trialEndsAt != null && _now().isBefore(_trialEndsAt!);

  PremiumStatus get status {
    if (_trialEndsAt == null) return PremiumStatus.none;
    if (isOnTrial) return _autoRenew ? PremiumStatus.trial : PremiumStatus.trialCancelled;
    // Trial is over: it only continues if it renewed onto a card.
    if (_card == null) return PremiumStatus.none;
    if (_autoRenew) return PremiumStatus.active;
    return _cancelledAccessEnd != null && _now().isBefore(_cancelledAccessEnd!) ? PremiumStatus.cancelled : PremiumStatus.none;
  }

  bool get isPremium => status != PremiumStatus.none;

  int get trialDaysLeft {
    if (!isOnTrial) return 0;
    return (_trialEndsAt!.difference(_now()).inHours / 24).ceil();
  }

  /// When the card will next be charged, or null if nothing is due.
  DateTime? get nextChargeAt => switch (status) {
        PremiumStatus.trial => _trialEndsAt,
        PremiumStatus.active => _currentPeriodEnd(),
        _ => null,
      };

  /// When access ends because auto-renew is off, or null if it renews.
  DateTime? get accessEndsAt => switch (status) {
        PremiumStatus.trialCancelled => _trialEndsAt,
        PremiumStatus.cancelled => _cancelledAccessEnd,
        _ => null,
      };

  DateTime get trialEndIfStartedNow => _now().add(const Duration(days: trialDays));

  /// Saves the card and starts the 7-day free trial with auto-renew on.
  /// Returns false if the trial was already used.
  bool startTrial(PaymentCard card) {
    if (_trialUsed) return false;
    _card = card;
    _trialEndsAt = trialEndIfStartedNow;
    _autoRenew = true;
    _trialUsed = true;
    _cancelledAccessEnd = null;
    notifyListeners();
    return true;
  }

  /// For someone whose trial is used up: charges Rs 1,500 now and renews monthly.
  void subscribe(PaymentCard card) {
    _card = card;
    _trialEndsAt = _now(); // billing starts today, no trial
    _autoRenew = true;
    _trialUsed = true;
    _cancelledAccessEnd = null;
    notifyListeners();
  }

  void setAutoRenew(bool on) {
    if (_trialEndsAt == null || _card == null) return;
    if (!on && status == PremiumStatus.active) _cancelledAccessEnd = _currentPeriodEnd();
    if (on) {
      _cancelledAccessEnd = null;
      _cancellationReason = null;
    }
    _autoRenew = on;
    notifyListeners();
  }

  String? _cancellationReason;

  /// Why the patient cancelled, if they said. Sent to the backend with the
  /// cancellation so the team can learn from it.
  String? get cancellationReason => _cancellationReason;

  /// Whether there is a subscription that can be cancelled right now.
  bool get canCancel => status == PremiumStatus.trial || status == PremiumStatus.active;

  /// Whether a cancelled subscription can still be resumed before it ends.
  bool get canResume => status == PremiumStatus.trialCancelled || status == PremiumStatus.cancelled;

  /// Cancels the subscription: no further charges, and access continues to
  /// the end of the trial or the month already paid for. Returns that date.
  DateTime? cancel({String? reason}) {
    if (!canCancel) return null;
    _cancellationReason = (reason == null || reason.trim().isEmpty) ? null : reason.trim();
    setAutoRenew(false);
    return accessEndsAt;
  }

  void resume() => setAutoRenew(true);

  void updateCard(PaymentCard card) {
    _card = card;
    notifyListeners();
  }

  /// Loads the subscription as the backend reports it.
  void setStatus({
    PaymentCard? card,
    DateTime? trialEndsAt,
    required bool autoRenew,
    required bool trialUsed,
    DateTime? accessEndsAt,
  }) {
    _card = card;
    _trialEndsAt = trialEndsAt;
    _autoRenew = autoRenew;
    _trialUsed = trialUsed;
    _cancelledAccessEnd = accessEndsAt;
    notifyListeners();
  }
}
