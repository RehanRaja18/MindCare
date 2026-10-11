import 'package:flutter/material.dart';
import '../models/settings_data.dart';

class SettingsProvider extends ChangeNotifier {
  // ----- Privacy & data -----
  List<PrivacyToggle> _privacyToggles = const [
    PrivacyToggle(
      id: 'therapist_vitals',
      title: 'Share vitals with your therapist',
      subtitle: 'Heart rate and breathing trends from Pulse.',
      enabled: true,
    ),
    PrivacyToggle(
      id: 'therapist_journal',
      title: 'Share journal entries',
      subtitle: 'Your reflect entries, visible in session notes.',
      enabled: true,
    ),
    PrivacyToggle(
      id: 'therapist_mood',
      title: 'Share daily mood check-ins',
      subtitle: 'How you\'re arriving into the day, each morning.',
      enabled: true,
    ),
    PrivacyToggle(
      id: 'aida_context',
      title: 'Let Aida use your care plan for context',
      subtitle: 'So she can reference what your therapist set.',
      enabled: true,
    ),
    PrivacyToggle(
      id: 'analytics',
      title: 'Anonymous usage analytics',
      subtitle: 'Helps us improve the app. Never includes your content.',
      enabled: false,
    ),
    PrivacyToggle(
      id: 'cnic_encryption',
      title: 'CNIC encrypted at rest',
      subtitle: 'Always on — required for identity verification.',
      enabled: true,
      locked: true,
    ),
  ];

  List<PrivacyToggle> get privacyToggles => _privacyToggles;

  void togglePrivacy(String id) {
    _privacyToggles = _privacyToggles.map((t) {
      if (t.id == id && !t.locked) return t.copyWith(enabled: !t.enabled);
      return t;
    }).toList();
    notifyListeners();
  }

  Future<void> requestDataExport() async {
    await Future.delayed(const Duration(milliseconds: 600));
  }

  // ----- Notifications -----
  List<NotificationCategory> _notificationCategories = const [
    NotificationCategory(id: 'sessions', title: 'Session reminders', subtitle: 'Upcoming and confirmed appointments.', enabled: true),
    NotificationCategory(id: 'aida', title: 'Aida check-ins', subtitle: 'When she notices something in your vitals.', enabled: true),
    NotificationCategory(id: 'streaks', title: 'Streaks & rewards', subtitle: 'Milestones, badges, and level-ups.', enabled: true),
    NotificationCategory(id: 'circles', title: 'Circles activity', subtitle: 'Replies and reactions on your posts.', enabled: false),
    NotificationCategory(id: 'marketing', title: 'Tips & product updates', subtitle: 'Occasional emails about new features.', enabled: false),
  ];

  List<NotificationCategory> get notificationCategories => _notificationCategories;

  bool get allNotificationsOn => _notificationCategories.any((c) => c.enabled);

  void toggleNotificationCategory(String id) {
    _notificationCategories = _notificationCategories.map((c) {
      if (c.id == id) return c.copyWith(enabled: !c.enabled);
      return c;
    }).toList();
    notifyListeners();
  }

  void setAllNotifications(bool enabled) {
    _notificationCategories = _notificationCategories.map((c) => c.copyWith(enabled: enabled)).toList();
    notifyListeners();
  }

  // ----- Wearables -----
  WearableDevice wearable = const WearableDevice(
    name: 'MindBand',
    model: 'MindBand 2',
    batteryPercent: 68,
    lastSynced: '2 minutes ago',
    connected: true,
  );

  Future<void> disconnectWearable() async {
    await Future.delayed(const Duration(milliseconds: 400));
    wearable = WearableDevice(
      name: wearable.name,
      model: wearable.model,
      batteryPercent: wearable.batteryPercent,
      lastSynced: wearable.lastSynced,
      connected: false,
    );
    notifyListeners();
  }

  Future<void> reconnectWearable() async {
    await Future.delayed(const Duration(milliseconds: 700));
    wearable = WearableDevice(
      name: wearable.name,
      model: wearable.model,
      batteryPercent: wearable.batteryPercent,
      lastSynced: 'just now',
      connected: true,
    );
    notifyListeners();
  }

  // ----- Appearance -----
  /// 0 = Small, 1 = Default, 2 = Large. Applied app-wide via
  /// MediaQuery.textScaler in main.dart, so this genuinely resizes
  /// all text in the app, not just a preview.
  int textSizeIndex = 1;

  static const List<String> textSizeLabels = ['Small', 'Default', 'Large'];
  static const List<double> textSizeScales = [0.9, 1.0, 1.15];

  double get textScale => textSizeScales[textSizeIndex];

  void setTextSizeIndex(int index) {
    textSizeIndex = index;
    notifyListeners();
  }

  /// Dark mode isn't built yet — this is tracked honestly rather than
  /// silently doing nothing when toggled.
  bool darkModeRequested = false;

  void setDarkModeRequested(bool value) {
    darkModeRequested = value;
    notifyListeners();
  }
}