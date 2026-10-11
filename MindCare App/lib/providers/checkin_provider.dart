import 'package:flutter/material.dart';
import '../core/theme/app_colors.dart';
import '../models/checkin_data.dart';

class CheckinProvider extends ChangeNotifier {
  CheckinProvider() {
    _seedChat();
  }

  // ----- Daily mood (Home) -----
  static const List<DailyMoodOption> dailyMoods = [
    DailyMoodOption('bright', 'Bright', AppColors.dailyBright),
    DailyMoodOption('okay', 'Okay', AppColors.dailyOkay),
    DailyMoodOption('wobbly', 'Wobbly', AppColors.dailyWobbly),
    DailyMoodOption('heavy', 'Heavy', AppColors.dailyHeavy),
    DailyMoodOption('lost', 'Lost', AppColors.dailyLost),
  ];

  String? selectedDailyMoodId;

  void selectDailyMood(String id) {
    selectedDailyMoodId = selectedDailyMoodId == id ? null : id;
    notifyListeners();
  }

  // ----- Vitals -----
  // Built only from real sensor readings fed in through [addReading] /
  // [addReadings]. With no readings, [vitals] is null and screens show an
  // empty state instead of made-up numbers.

  /// How many recent readings the trend graphs and the calm strip show.
  static const int trendWindow = 12;

  // Adult resting upper limits. A reading at or above either one counts as
  // "activated". Replace with a per-user baseline or the AI model's output
  // once the backend provides one.
  static const int activatedHeartRate = 100;
  static const int activatedBreathingRate = 20;

  final List<VitalReading> _readings = [];

  List<VitalReading> get readings => List.unmodifiable(_readings);

  void addReading(VitalReading reading) => addReadings([reading]);

  void addReadings(Iterable<VitalReading> readings) {
    _readings
      ..addAll(readings)
      ..sort((a, b) => a.at.compareTo(b.at));
    // Keep a little more than the graphs need so the window stays full.
    if (_readings.length > trendWindow * 4) {
      _readings.removeRange(0, _readings.length - trendWindow * 4);
    }
    notifyListeners();
  }

  void clearReadings() {
    _readings.clear();
    notifyListeners();
  }

  static NervousSystemState classify(VitalReading r) =>
      r.heartRate >= activatedHeartRate || r.breathingRate >= activatedBreathingRate
          ? NervousSystemState.activated
          : NervousSystemState.calm;

  List<VitalReading> get _recent =>
      _readings.length <= trendWindow ? _readings : _readings.sublist(_readings.length - trendWindow);

  VitalsSnapshot? get vitals {
    if (_readings.isEmpty) return null;
    final recent = _recent;
    final latest = recent.last;
    // Steps are a running daily total, so only today's readings belong in the graph.
    final now = DateTime.now();
    final todaySteps = recent
        .where((r) => r.steps != null && r.at.year == now.year && r.at.month == now.month && r.at.day == now.day)
        .map((r) => r.steps!.toDouble())
        .toList();
    return VitalsSnapshot(
      heartRate: latest.heartRate,
      breathingRate: latest.breathingRate,
      steps: todaySteps.isEmpty ? null : todaySteps.last.round(),
      heartTrend: recent.map((r) => r.heartRate.toDouble()).toList(),
      breathingTrend: recent.map((r) => r.breathingRate.toDouble()).toList(),
      stepsTrend: todaySteps,
      state: classify(latest),
    );
  }

  List<NervousSystemState> get calmActivated => _recent.map(classify).toList();

  // ----- Progress -----
  final int streakDays = 14;
  final double avgMood = 3.4;
  final double avgMoodDelta = 0.6;

  String moodRange = '30d';

  static const Map<String, List<double>> _moodSeries = {
    '30d': [
      0.55, 0.62, 0.40, 0.35, 0.58, 0.78, 0.60, 0.42, 0.38,
      0.50, 0.72, 0.58, 0.62, 0.30, 0.45, 0.55, 0.68, 0.66,
      0.70, 0.80,
    ],
    '90d': [0.40, 0.52, 0.60, 0.35, 0.48, 0.66, 0.58, 0.44, 0.50, 0.62, 0.70, 0.55],
    '1y': [0.45, 0.50, 0.55, 0.48, 0.60, 0.65, 0.58, 0.62, 0.66, 0.60, 0.70, 0.75],
  };

  static const Map<String, List<String>> _moodLabels = {
    '30d': ['Apr 21', 'May 6', 'May 21'],
    '90d': ['Feb', 'Apr', 'May'],
    '1y': ["Jun '25", "Dec '25", "May '26"],
  };

  List<double> get moodTimeline => _moodSeries[moodRange]!;
  List<String> get moodTimelineLabels => _moodLabels[moodRange]!;

  void setMoodRange(String range) {
    moodRange = range;
    notifyListeners();
  }

  final List<ProgressInsight> insights = const [
    ProgressInsight(
      icon: Icons.wb_sunny_outlined,
      iconBackground: AppColors.insightSunBg,
      title: 'Sundays feel lightest',
      description: 'Your mood averages 4.1 on Sundays — keep that recovery routine.',
    ),
    ProgressInsight(
      icon: Icons.bolt,
      iconBackground: AppColors.insightBoltBg,
      title: 'Tuesday mornings stir anxiety',
      description: '3 of last 4 spikes. Want a 10-min Monday-eve reset?',
    ),
    ProgressInsight(
      icon: Icons.eco_outlined,
      iconBackground: AppColors.insightLeafBg,
      title: 'Box breathing helps',
      description: 'Heart rate drops 8 bpm on average after.',
    ),
  ];

  // ----- Aida chat -----
  final List<ChatMessage> messages = [];
  bool isAssistantTyping = false;
  int _idCounter = 0;

  /// Set once, the first time the chat screen opens with a known
  /// user name — used to personalize the seeded greeting and canned
  /// replies instead of a hardcoded placeholder name.
  String _userFirstName = 'there';
  bool _greetingPersonalized = false;

  String _nextId() => 'msg_${_idCounter++}';

  void _seedChat() {
    messages.addAll([
      ChatMessage(
        id: _nextId(),
        sender: MessageSender.assistant,
        text: "Morning, {name}. Your resting heart rate is a touch high and your breathing's quick. Want to talk about it?",
      ),
      ChatMessage(
        id: _nextId(),
        sender: MessageSender.user,
        text: "Yeah, my mind wouldn't switch off. Work stuff.",
      ),
      ChatMessage(
        id: _nextId(),
        sender: MessageSender.assistant,
        text: "That sounds tiring. Before we dig in — let's settle your body a little. A 90-second box breath?",
      ),
      ChatMessage(
        id: _nextId(),
        sender: MessageSender.assistant,
        exercise: const BreathingExercise(
          title: 'Box breath · 90 sec',
          subtitle: '4 in · 4 hold · 4 out · 4 hold',
          ctaLabel: 'Begin',
        ),
      ),
      ChatMessage(
        id: _nextId(),
        sender: MessageSender.user,
        text: 'Okay, in a minute. Can you also remind me to journal it later?',
      ),
      ChatMessage(
        id: _nextId(),
        sender: MessageSender.assistant,
        text: "Done — added a 4 PM nudge. Whenever you're ready.",
      ),
    ]);
  }

  /// Replaces the `{name}` placeholder in the seeded greeting with
  /// the person's real first name, and remembers it for canned
  /// replies. Safe to call every time the chat screen opens — it
  /// only actually rewrites messages once.
  void personalizeGreeting(String firstName) {
    _userFirstName = firstName.isEmpty ? 'there' : firstName;
    if (_greetingPersonalized) return;
    _greetingPersonalized = true;

    for (int i = 0; i < messages.length; i++) {
      final m = messages[i];
      if (m.text != null && m.text!.contains('{name}')) {
        messages[i] = ChatMessage(
          id: m.id,
          sender: m.sender,
          text: m.text!.replaceAll('{name}', _userFirstName),
          exercise: m.exercise,
          timestamp: m.timestamp,
        );
      }
    }
    notifyListeners();
  }

  static const List<String> quickReplies = [
    'Help me name the feeling',
    "I don't want to journal",
    'Show me a calmer evening routine',
  ];

  /// Sends a message from the user and simulates a supportive reply.
  ///
  /// NOTE: this is placeholder/demo logic for testing the front-end data
  /// flow. In production this must call a backend endpoint over HTTPS —
  /// never embed a model API key inside the mobile app — and the backend
  /// must treat chat content as sensitive health data: encrypted at rest,
  /// access-controlled, and excluded from analytics/crash logs.
  Future<void> sendMessage(String text) async {
    final trimmed = text.trim();
    if (trimmed.isEmpty) return;

    messages.add(ChatMessage(id: _nextId(), sender: MessageSender.user, text: trimmed));
    isAssistantTyping = true;
    notifyListeners();

    await Future.delayed(const Duration(milliseconds: 900));

    messages.add(ChatMessage(id: _nextId(), sender: MessageSender.assistant, text: _canned(trimmed)));
    isAssistantTyping = false;
    notifyListeners();
  }

  String _canned(String userText) {
    final lower = userText.toLowerCase();
    if (lower.contains('anxious') || lower.contains('anxiety')) {
      return 'That makes sense. Anxiety often shows up in the body first. Want to try the box breath together?';
    }
    if (lower.contains('sleep') || lower.contains('tired')) {
      return 'Rest matters more than it gets credit for. Want a wind-down routine for tonight?';
    }
    if (lower.contains('thanks') || lower.contains('thank you')) {
      return 'Always here for you, $_userFirstName.';
    }
    return "I hear you. Tell me a little more, and we'll figure out the next small step together.";
  }
}