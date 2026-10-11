import 'package:flutter/material.dart';

/// The patient's MindCare Premium status. Matches the plan on the website:
/// Rs 1,500 / month with a 7-day free trial.
///
/// There is no payment or subscription API yet, so the trial is held in
/// memory only. Once the backend exposes the subscription, load it with
/// [setStatus] after sign-in.
class PremiumProvider extends ChangeNotifier {
  static const int monthlyPrice = 1500;
  static const int trialDays = 7;

  bool _active = false;
  DateTime? _trialEndsAt;

  bool get isPremium => _active || isOnTrial;

  bool get isOnTrial => _trialEndsAt != null && DateTime.now().isBefore(_trialEndsAt!);

  DateTime? get trialEndsAt => _trialEndsAt;

  bool get trialUsed => _trialEndsAt != null;

  int get trialDaysLeft {
    if (!isOnTrial) return 0;
    return (_trialEndsAt!.difference(DateTime.now()).inHours / 24).ceil();
  }

  void startTrial() {
    if (trialUsed) return;
    _trialEndsAt = DateTime.now().add(const Duration(days: trialDays));
    notifyListeners();
  }

  void setStatus({required bool active, DateTime? trialEndsAt}) {
    _active = active;
    _trialEndsAt = trialEndsAt;
    notifyListeners();
  }
}
