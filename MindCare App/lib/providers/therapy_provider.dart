import 'package:flutter/material.dart';
import '../models/therapy_data.dart';

class TherapyProvider extends ChangeNotifier {
  // ----- Browse -----
  static const List<Therapist> therapists = [
    Therapist(
      id: 'tariq',
      name: 'Dr. Tariq Mahmood',
      initials: 'TM',
      avatarColor: Color(0xFFE5382B),
      title: 'Clinical psychologist · CBT, ACT',
      specialty: 'Anxiety · Burnout · CBT',
      rating: 4.9,
      reviewCount: 218,
      yearsExperience: 12,
      languages: 'En · Ur',
      priceMonthly: 18000,
      priceYearly: 180000,
      trialAvailable: true,
      status: 'Open',
      credentialBadge: 'PMDC',
    ),
    Therapist(
      id: 'sana',
      name: 'Dr. Sana Yousaf',
      initials: 'SY',
      avatarColor: Color(0xFF8E5FE0),
      title: 'Clinical psychologist',
      specialty: 'Depression · Grief',
      rating: 4.8,
      reviewCount: 142,
      yearsExperience: 8,
      languages: 'En · Ur',
      priceMonthly: 20000,
      priceYearly: 200000,
      trialAvailable: true,
      status: 'Open',
      credentialBadge: 'PMDC',
    ),
    Therapist(
      id: 'hira',
      name: 'Hira Khan, MSc',
      initials: 'HK',
      avatarColor: Color(0xFF1CB88A),
      title: 'Licensed counselor',
      specialty: 'Couples · Family',
      rating: 4.7,
      reviewCount: 96,
      yearsExperience: 6,
      languages: 'En · Ur · Pa',
      priceMonthly: 14000,
      priceYearly: 140000,
      trialAvailable: true,
      status: 'Open',
      credentialBadge: 'PMDC',
    ),
    Therapist(
      id: 'omar',
      name: 'Dr. Omar Raza',
      initials: 'OR',
      avatarColor: Color(0xFF2497D9),
      title: 'Clinical psychologist',
      specialty: 'Trauma · PTSD',
      rating: 4.6,
      reviewCount: 74,
      yearsExperience: 10,
      languages: 'En · Ur',
      priceMonthly: 26000,
      priceYearly: 260000,
      trialAvailable: false,
      status: 'Busy',
      credentialBadge: 'PMDC',
    ),
  ];

  static const List<String> filterChips = ['All', 'Anxiety', 'Depression', 'Couples', 'Trauma'];
  String selectedFilter = 'All';
  String searchQuery = '';

  void setFilter(String filter) {
    selectedFilter = filter;
    notifyListeners();
  }

  void setSearchQuery(String query) {
    searchQuery = query;
    notifyListeners();
  }

  // ----- Sort & extra filters -----
  /// 'default' | 'rating' | 'price_low' | 'trial' | 'language'
  String sortMode = 'default';
  String? languageFilter;

  static const List<String> availableLanguages = ['English', 'Urdu', 'Pashto'];

  void setSortMode(String mode) {
    sortMode = mode;
    // Choosing a sort mode other than the language filter clears any
    // active language filter, so only one refinement applies at a
    // time — keeps the UI predictable rather than silently stacking.
    if (mode != 'language') languageFilter = null;
    notifyListeners();
  }

  void setLanguageFilter(String? language) {
    languageFilter = language;
    sortMode = language == null ? 'default' : 'language';
    notifyListeners();
  }

  List<Therapist> get filteredTherapists {
    var results = therapists.where((t) {
      final matchesFilter =
          selectedFilter == 'All' || t.specialty.toLowerCase().contains(selectedFilter.toLowerCase());
      final matchesSearch = searchQuery.isEmpty ||
          t.name.toLowerCase().contains(searchQuery.toLowerCase()) ||
          t.specialty.toLowerCase().contains(searchQuery.toLowerCase());
      return matchesFilter && matchesSearch;
    }).toList();

    switch (sortMode) {
      case 'rating':
        results.sort((a, b) => b.rating.compareTo(a.rating));
        break;
      case 'price_low':
        results.sort((a, b) => a.priceMonthly.compareTo(b.priceMonthly));
        break;
      case 'trial':
        results = results.where((t) => t.trialAvailable).toList();
        break;
      case 'language':
        if (languageFilter != null) {
          final shortCode = _languageShortCode(languageFilter!);
          results = results.where((t) => t.languages.contains(shortCode)).toList();
        }
        break;
      case 'default':
      default:
        break;
    }

    return results;
  }

  String _languageShortCode(String language) {
    switch (language) {
      case 'English':
        return 'En';
      case 'Urdu':
        return 'Ur';
      case 'Pashto':
        return 'Pa';
      default:
        return language;
    }
  }

  // ----- Bookmarks -----
  Set<String> bookmarkedTherapistIds = {};

  bool isBookmarked(String therapistId) => bookmarkedTherapistIds.contains(therapistId);

  void toggleBookmark(String therapistId) {
    if (bookmarkedTherapistIds.contains(therapistId)) {
      bookmarkedTherapistIds.remove(therapistId);
    } else {
      bookmarkedTherapistIds.add(therapistId);
    }
    notifyListeners();
  }

  // ----- Next session (Home) -----
  // Null until the backend reports a booked session.
  UpcomingSession? upcomingSession;

  void setUpcomingSession(UpcomingSession? session) {
    upcomingSession = session;
    notifyListeners();
  }

  // ----- Plan & trial -----
  Therapist? selectedTherapist;
  String selectedPlanId = 'monthly';

  void selectTherapist(Therapist therapist) {
    selectedTherapist = therapist;
    selectedPlanId = 'monthly';
    notifyListeners();
  }

  void selectPlan(String planId) {
    selectedPlanId = planId;
    notifyListeners();
  }

  // ----- Schedule -----
  final int sessionsUsed = 2;
  final int sessionsTotal = 4;

  static const List<WeekDay> weekDays = [
    WeekDay('Mon', 19),
    WeekDay('Tue', 20),
    WeekDay('Wed', 21),
    WeekDay('Thu', 22),
    WeekDay('Fri', 23),
    WeekDay('Sat', 24),
    WeekDay('Sun', 25),
  ];

  int selectedDayIndex = 2;

  static const List<ScheduleSlot> _daySlots = [
    ScheduleSlot('9:30 AM', 'booked'),
    ScheduleSlot('11:00 AM', 'free'),
    ScheduleSlot('12:30 PM', 'free'),
    ScheduleSlot('2:00 PM', 'booked'),
    ScheduleSlot('3:30 PM', 'free'),
    ScheduleSlot('5:00 PM', 'free'),
    ScheduleSlot('6:30 PM', 'booked'),
    ScheduleSlot('8:00 PM', 'off'),
  ];

  List<ScheduleSlot> get availabilityForSelectedDay => _daySlots;

  String? selectedSlotTime = '5:00 PM';

  void selectDay(int index) {
    selectedDayIndex = index;
    selectedSlotTime = null;
    notifyListeners();
  }

  void selectSlot(String time, String status) {
    if (status != 'free') return;
    selectedSlotTime = time;
    notifyListeners();
  }

  Future<void> requestSession() async {
    await Future.delayed(const Duration(milliseconds: 500));
    notifyListeners();
  }

  // ----- Next confirmed session -----
  String nextConfirmedLabel = 'Fri · 5:00 PM';
  bool nextConfirmedCancelled = false;

  Future<void> rescheduleSession(String dayLabel, int date, String time) async {
    await Future.delayed(const Duration(milliseconds: 600));
    nextConfirmedLabel = '$dayLabel · $time';
    notifyListeners();
  }

  Future<void> cancelSession(String note) async {
    await Future.delayed(const Duration(milliseconds: 600));
    nextConfirmedCancelled = true;
    notifyListeners();
  }
}