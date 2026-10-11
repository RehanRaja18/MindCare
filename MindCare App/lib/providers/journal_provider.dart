import 'package:flutter/material.dart';
import '../models/premium_data.dart';

/// The patient's private journal (a Premium feature).
///
/// Starts empty. Entries live in memory until the backend's journals API
/// exists; then load them with [setEntries] and save through it. Entries
/// are only visible to the therapist when [JournalEntry.sharedWithTherapist]
/// is on.
class JournalProvider extends ChangeNotifier {
  final List<JournalEntry> _entries = [];

  /// Newest first.
  List<JournalEntry> get entries => List.unmodifiable(_entries);

  int get sharedCount => _entries.where((e) => e.sharedWithTherapist).length;

  void setEntries(List<JournalEntry> entries) {
    _entries
      ..clear()
      ..addAll(entries)
      ..sort((a, b) => b.createdAt.compareTo(a.createdAt));
    notifyListeners();
  }

  JournalEntry addEntry({required String body, String? title, String? moodId, bool share = false}) {
    final entry = JournalEntry(
      id: DateTime.now().microsecondsSinceEpoch.toString(),
      createdAt: DateTime.now(),
      title: (title == null || title.trim().isEmpty) ? null : title.trim(),
      body: body.trim(),
      moodId: moodId,
      sharedWithTherapist: share,
    );
    _entries.insert(0, entry);
    notifyListeners();
    return entry;
  }

  void setShared(String id, bool shared) {
    final i = _entries.indexWhere((e) => e.id == id);
    if (i == -1) return;
    _entries[i] = _entries[i].copyWith(sharedWithTherapist: shared);
    notifyListeners();
  }

  void deleteEntry(String id) {
    _entries.removeWhere((e) => e.id == id);
    notifyListeners();
  }

  JournalEntry? byId(String id) {
    for (final e in _entries) {
      if (e.id == id) return e;
    }
    return null;
  }
}
