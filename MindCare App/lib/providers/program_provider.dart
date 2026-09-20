import 'package:flutter/material.dart';

import '../core/theme/app_colors.dart';
import '../models/program_data.dart';

class ProgramProvider extends ChangeNotifier {
  // ----- Weekly care plan (set by therapist) -----
  final List<WeeklyTask> weeklyTasks = const [
    WeeklyTask(
      category: 'BREATH · DAILY · 5 MIN',
      schedule: '',
      title: 'Box breathing',
      done: 5,
      total: 7,
      color: AppColors.programBreath,
    ),
    WeeklyTask(
      category: 'BODY · MON · WED · FRI',
      schedule: '',
      title: '10-min body scan',
      done: 1,
      total: 3,
      color: AppColors.programBody,
    ),
    WeeklyTask(
      category: 'THINKING · TUE · THU',
      schedule: '',
      title: 'Cognitive reframe',
      done: 0,
      total: 2,
      color: AppColors.programThinking,
    ),
    WeeklyTask(
      category: 'REFLECT · DAILY · 3 MIN',
      schedule: '',
      title: 'Evening journal',
      done: 4,
      total: 7,
      color: AppColors.programReflect,
    ),
  ];

  int get totalDone => weeklyTasks.fold(0, (sum, t) => sum + t.done);
  int get totalTasks => weeklyTasks.fold(0, (sum, t) => sum + t.total);

  // ----- Wellbeing -----
  final int stepsToday = 6612;
  final int stepsChangePercent = 12;
  final List<double> movementByDay = const [
    0.40,
    0.55,
    0.85,
    0.70,
    0.60,
    0.65,
    0.95,
  ];
  final List<String> movementDayLabels = const [
    'Th',
    'Fr',
    'Sa',
    'Su',
    'Mo',
    'Tu',
    'We',
  ];
  final String movementTip =
      'a 10-minute walk after lunch tends to drop your resting heart rate by 6 bpm in the afternoon.';

  final List<bool> mealsDone = const [true, true, true, false];
  final String dinnerTime = 'Dinner — 8 PM';

  final int waterGlassesTotal = 8;
  final int waterGlassesFilled = 5;

  final double calmTimePercent = 0.74;
  final String calmTimeLabel = '7h 38m today';
  final String calmTimeSubtitle = 'Sensor-detected · low sweat & steady breath';

  final List<DailyStep> smallSteps = const [
    DailyStep('Sunlight before 10 AM', true),
    DailyStep('Stretch for 5 minutes', true),
  ];

  // ----- Motivation -----
  static const List<String> motivationTabs = ['Duas', 'Quotes', 'Surahs'];
  String selectedMotivationTab = 'Duas';

  void setMotivationTab(String tab) {
    selectedMotivationTab = tab;
    notifyListeners();
  }

  final String todayQuote = 'And He found you lost and guided you.';
  final String todayQuoteReference = "QUR'AN 93:7";

  final AudioTrack featuredTrack = const AudioTrack(
    id: 'dua_yunus',
    tag: 'FOR ANXIETY',
    title: 'Dua of Yunus',
    arabic: 'لَا إِلَٰهَ إِلَّا أَنْتَ سُبْحَانَكَ',
    translation: '"There is no god but You — glory be to You."',
    duration: '3:02',
  );

  final String featuredPosition = '1:14';

  final List<AudioTrack> moreTracks = const [
    AudioTrack(
      id: 'dua_ease',
      tag: 'For stress',
      title: 'Dua for ease',
      translation: '"My Lord, expand my chest..."',
      duration: '1:42',
    ),
    AudioTrack(
      id: 'ash_sharh',
      tag: 'For relief',
      title: 'Surah Ash-Sharh',
      translation: 'Indeed, with hardship comes ease.',
      duration: '0:58',
    ),
    AudioTrack(
      id: 'dua_sleep',
      tag: '',
      title: 'Dua for sleep',
      translation: 'In Your name I die and live.',
      duration: '0:46',
    ),
    AudioTrack(
      id: 'al_falaq',
      tag: '',
      title: 'Surah Al-Falaq',
      translation: '',
      duration: '0:34',
    ),
  ];

  /// Unified playback: the id of whichever track is currently
  /// "playing" (featured or from the list) — only one at a time.
  /// Null means nothing is playing.
  String? playingTrackId;

  bool isPlaying(String trackId) => playingTrackId == trackId;

  void togglePlay(String trackId) {
    playingTrackId = playingTrackId == trackId ? null : trackId;
    notifyListeners();
  }

  /// Bookmarked tracks — shown as filled once saved.
  Set<String> bookmarkedTrackIds = {};

  bool isTrackBookmarked(String trackId) =>
      bookmarkedTrackIds.contains(trackId);

  List<AudioTrack> get bookmarkedTracks => [
    featuredTrack,
    ...moreTracks,
  ].where((track) => bookmarkedTrackIds.contains(track.id)).toList();

  void toggleTrackBookmark(String trackId) {
    if (bookmarkedTrackIds.contains(trackId)) {
      bookmarkedTrackIds.remove(trackId);
    } else {
      bookmarkedTrackIds.add(trackId);
    }
    notifyListeners();
  }
}
